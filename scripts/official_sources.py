#!/usr/bin/env python3
"""Official feeds + paginated arXiv; journal-date metadata fills short feed windows.
Raw abstracts remain in private caches. No inference of a full abstract from a feed teaser.
"""
import datetime as dt,email.utils,hashlib,html,json,re,time,unicodedata
import urllib.parse,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
CONFIG=Path(__file__).with_name('official_sources.json')
ATOM='{http://www.w3.org/2005/Atom}'
ARXIV='{http://arxiv.org/schemas/atom}'
OS='{http://a9.com/-/spec/opensearch/1.1/}'

def clean(value):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',value or ''))).strip()
def local(tag):return tag.rsplit('}',1)[-1]
def field(e,*names):return next((clean(c.text) for n in names for c in e if local(c.tag)==n and c.text),'')
def norm(s):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',html.unescape(s)).lower())
def doi(s):return re.sub(r'^(?:https?://(?:dx\.)?doi.org/|doi:)','',s.strip(),flags=re.I).lower()
def identity(p):
    out={p['id'],'title:'+norm(p['title'])}|set(p.get('aliases',[]))
    if p.get('doi'):out.add('doi:'+doi(p['doi']))
    if p.get('arxivId'):out.add('arxiv:'+re.sub(r'v\d+$','',p['arxivId']))
    return out

def merge(records):
    result=[];index={}
    for p in records:
        hits={index[k] for k in identity(p) if k in index}
        if not hits:
            i=len(result);result.append(dict(p))
        else:
            i=min(hits);old=result[i]
            # Prefer a published version and full evidence over a feed-only teaser.
            rank=lambda x:(x.get('status')=='Published',x.get('metadataSource') in ('Crossref','arXiv API'),x.get('abstractComplete',False))
            winner,loser=(p,old) if rank(p)>rank(old) else (old,p)
            combined={**loser,**winner}
            if loser.get('abstractComplete') and not winner.get('abstractComplete'):
                for key in ['abstract','abstractComplete','evidenceUrl','readingBasis']:combined[key]=loser.get(key)
            if winner.get('metadataSource')=='Crossref' and 'RSS' in loser.get('metadataSource',''):
                combined['sourceUrl']=loser['sourceUrl']
            combined['aliases']=sorted(identity(old)|identity(p))
            combined['discoveredVia']=list(dict.fromkeys(old.get('discoveredVia',[])+p.get('discoveredVia',[])))
            dates=[x['firstSeenDate'] for x in [old,p] if x.get('firstSeenDate')]
            if dates:combined['firstSeenDate']=min(dates)
            result[i]=combined
            for j in hits-{i}:
                result[i]['aliases']=sorted(identity(result[i])|identity(result[j]));result[j]=None
        for k in identity(result[i]):index[k]=i
    return [p for p in result if p]

def datevalue(value):
    if re.match(r'^\d{4}-\d{2}-\d{2}',value):return value[:10]
    try:return email.utils.parsedate_to_datetime(value).date().isoformat()
    except (ValueError,TypeError):return ''

def feed_records(raw,source):
    root=ET.fromstring(raw)
    if local(root.tag) not in ('rss','RDF','feed'):raise ValueError('Response is not an RSS/Atom feed')
    records=[]
    for e in root.iter():
        if local(e.tag)!='item':continue
        title=field(e,'title');link=field(e,'link','url');identifier=field(e,'doi','identifier')
        d=doi(identifier) if identifier.startswith(('10.','doi:')) else ''
        if not d:
            m=re.search(r'10\.\d{4,9}/[^\s?<>]+',link);d=m.group(0).lower() if m else ''
        ar=re.search(r'arxiv.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?',link)
        if not title or not (d or ar):continue
        desc=field(e,'description','encoded');datestr=field(e,'publicationDate','date','pubDate')
        pub=datevalue(datestr);authors=', '.join(clean(c.text) for c in e if local(c.tag)=='creator')
        if ar:
            aid=ar.group(1);abstract=desc.split('Abstract:',1)[-1].strip() if 'Abstract:' in desc else ''
            # RSS pubDate is an announcement date, never pretend it is initial submission.
            records.append(dict(id='arxiv:'+aid,arxivId=aid,doi='',title=title,authors=authors,journal='arXiv',publicationDate=pub,dateBasis='arXiv RSS announcement date',sourceUrl='https://arxiv.org/abs/'+aid,evidenceUrl=source['feed'],abstract=abstract,abstractComplete=bool(abstract),readingBasis='arXiv abstract via official RSS',metadataSource='arXiv RSS',status='Preprint',aliases=[],discoveredVia=[source['feed']],announceType=field(e,'announce_type')))
        else:
            complete=source['publisher']=='ACS' and len(desc.split())>40 and 'Abstract' in desc
            if complete:desc=desc.split('Abstract',1)[-1].strip()
            records.append(dict(id='doi:'+d,doi=d,title=title,authors=authors,journal=source['name'],publicationDate=pub,dateBasis=source['publisher']+' official feed date (requires publication-date check)',sourceUrl=link.replace('http://','https://',1),evidenceUrl=source['feed'],abstract=desc if complete else '',feedSummary='' if complete else desc,abstractComplete=complete,readingBasis='Publisher abstract via official RSS' if complete else 'Feed teaser only; further reading required',metadataSource=source['publisher']+' official RSS',status='Published',aliases=[],discoveredVia=[source['feed']],feedDate=pub,articleType=field(e,'type')))
    return records

def atom_records(raw,url):
    root=ET.fromstring(raw);out=[]
    if root.tag!=ATOM+'feed':raise ValueError('Not an arXiv Atom feed')
    for e in root.findall(ATOM+'entry'):
        idurl=e.findtext(ATOM+'id','');match=re.search(r'/abs/(\d{4}\.\d{4,5})(?:v\d+)?$',idurl)
        if not match:raise ValueError('arXiv API error entry or unexpected identifier')
        aid=match.group(1);urlp='https://arxiv.org/abs/'+aid
        out.append(dict(id='arxiv:'+aid,arxivId=aid,doi=doi(e.findtext(ARXIV+'doi','')),title=clean(e.findtext(ATOM+'title','')),authors=', '.join(clean(a.findtext(ATOM+'name','')) for a in e.findall(ATOM+'author')),journal='arXiv',publicationDate=e.findtext(ATOM+'published','')[:10],submissionTimestamp=e.findtext(ATOM+'published',''),dateBasis='arXiv initial submission (UTC)',sourceUrl=urlp,evidenceUrl=urlp,abstract=clean(e.findtext(ATOM+'summary','')),abstractComplete=True,readingBasis='arXiv abstract',metadataSource='arXiv API',status='Preprint',aliases=[],discoveredVia=[url],categories=[c.get('term') for c in e.findall(ATOM+'category')],journalReference=clean(e.findtext(ARXIV+'journal_ref',''))))
    return out,int(root.findtext(OS+'totalResults',str(len(out))))

def cached(url,cache,suffix='txt'):
    f=cache/('request-'+hashlib.sha256(url.encode()).hexdigest()[:16]+'.'+suffix)
    if f.exists():return f.read_bytes()
    req=urllib.request.Request(url,headers={'User-Agent':'SunlabLiteratureDigest/2.0 (https://yiesacarl.github.io/sunlab-literature-library/)'})
    last=None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req,timeout=35) as r:raw=r.read()
            f.write_bytes(raw);return raw
        except Exception as e:
            last=e
            if getattr(e,'code',None) in (403,404,410):break
            if attempt==0:time.sleep(2)
    raise last

def relevance(p):
    text=(p['title']+' '+p.get('abstract','')+' '+p.get('feedSummary','')).lower()
    return bool(re.search(r'\b(spin|qubit|quantum|magnetic|magnetism|resonance|coherence|decoherence|framework|frameworks|mof|cof|radical|radicals)\b|molecular electronic|molecular junction|molecular transport|organic semiconductor|single.crystal',text))

def journal_name(s):return norm(re.sub(r'^the\s+','',s,flags=re.I))

def collect(day,cache,lookback=7,include_archives=True,max_arxiv_pages=20):
    """All official feeds are attempted independently; archives cover rolling feed gaps.
    Archives are explicitly Crossref journal-date metadata, not falsely marked official-site reads.
    """
    from digest import cr_record
    cache.mkdir(parents=True,exist_ok=True);config=json.loads(CONFIG.read_text());logs=[];records=[]
    start=(day-dt.timedelta(days=lookback-1)).isoformat();end=day.isoformat()
    def fetch_feed(s):
        rec=feed_records(cached(s['feed'],cache,'xml'),s)
        dates=[p['publicationDate'] for p in rec if p['publicationDate']]
        return rec,dict(source=s['name'],publisher=s['publisher'],kind='official-feed',url=s['feed'],status='ok',records=len(rec),oldestRecord=min(dates) if dates else None,newestRecord=max(dates) if dates else None,coverage='rolling feed; not a complete date-range archive')
    with ThreadPoolExecutor(max_workers=4) as ex:
        fs={ex.submit(fetch_feed,s):s for s in config}
        for f in as_completed(fs):
            s=fs[f]
            try:r,log=f.result();records.extend(r);logs.append(log)
            except Exception as e:logs.append(dict(source=s['name'],publisher=s['publisher'],kind='official-feed',url=s['feed'],status='failed',error=str(e)[:180]))
    print('Official feeds:',sum(x['status']=='ok' for x in logs),'/',len(config),flush=True)
    # One category-union query, paginated without relevance ranking truncation.
    cats=[s['id'] for s in config if s['publisher']=='arXiv']
    query='('+' OR '.join('cat:'+c for c in cats)+') AND submittedDate:['+start.replace('-','')+'0000 TO '+end.replace('-','')+'2359]'
    for page in range(max_arxiv_pages):
        params=dict(search_query=query,sortBy='submittedDate',sortOrder='descending',start=page*200,max_results=200)
        url='https://export.arxiv.org/api/query?'+urllib.parse.urlencode(params)
        try:
            r,total=atom_records(cached(url,cache,'xml'),url);records.extend(r)
            complete=(page*200+len(r)>=total)
            logs.append(dict(source='arXiv',kind='dated-api',url=url,status='ok',records=len(r),total=total,start=page*200,requestedFrom=start,requestedTo=end,rangeComplete=complete))
            if complete:break
            if not r:raise ValueError('Empty page before totalResults reached')
            if page==max_arxiv_pages-1:logs.append(dict(source='arXiv',kind='dated-api',url=url,status='partial',error='Pagination safety limit reached; additional pages require follow-up'))
        except Exception as e:logs.append(dict(source='arXiv',kind='dated-api',url=url,status='failed',error=str(e)[:180]));break
        time.sleep(3)
    def journal_archive(s):
        issn=s.get('issn')
        if not issn:
            lookup='https://api.crossref.org/journals?'+urllib.parse.urlencode({'query':s['name'],'rows':10})
            candidates=json.loads(cached(lookup,cache,'json'))['message']['items']
            journal=next((j for j in candidates if journal_name(j.get('title',''))==journal_name(s['name'])),None)
            if not journal:raise ValueError('No verified matching journal identifier')
            issn=journal['ISSN'][0]
        cursor='*';found=[];ll=[]
        for page in range(10):
            params={'filter':f'from-pub-date:{start},until-pub-date:{end},type:journal-article','rows':1000,'cursor':cursor}
            url='https://api.crossref.org/journals/'+issn+'/works?'+urllib.parse.urlencode(params)
            data=json.loads(cached(url,cache,'json'))['message'];items=data['items']
            for raw in items:
                p=cr_record(raw)
                if p:
                    p.update(abstractComplete=bool(p['abstract']),readingBasis='Publisher abstract via Crossref' if p['abstract'] else 'Metadata only; further reading required',discoveredVia=[url],archiveJournal=s['name'])
                    found.append(p)
            complete=len(found)>=data['total-results'] or not items
            ll.append(dict(source=s['name'],publisher=s['publisher'],kind='journal-date-metadata',provider='Crossref',url=url,status='ok',records=len(items),total=data['total-results'],rangeComplete=complete,requestedFrom=start,requestedTo=end))
            if complete:return found,ll
            next_cursor=data.get('next-cursor')
            if not next_cursor or next_cursor==cursor:raise ValueError('Journal archive pagination stalled')
            cursor=next_cursor
        ll.append(dict(source=s['name'],kind='journal-date-metadata',status='partial',error='Pagination safety limit reached'));return found,ll
    if include_archives:
        with ThreadPoolExecutor(max_workers=3) as ex:
            fs={ex.submit(journal_archive,s):s for s in config if s['publisher']!='arXiv'}
            for f in as_completed(fs):
                s=fs[f]
                try:r,ll=f.result();records.extend(r);logs.extend(ll)
                except Exception as e:logs.append(dict(source=s['name'],kind='journal-date-metadata',provider='Crossref',status='failed',error=str(e)[:180]))
    # Keep all raw records privately; candidate discovery remains broad, editorial review is separate.
    (cache/'all-source-records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    (cache/'sources.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2)+'\n')
    return merge([p for p in records if relevance(p)]),logs
