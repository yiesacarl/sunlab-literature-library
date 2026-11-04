#!/usr/bin/env python3
"""Public literature discovery + deterministic digest selection. No paid APIs.
Discovery writes private evidence caches locally; only reviewed paraphrases are published.
"""
import argparse,datetime as dt,hashlib,html,json,re,time,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist' if (ROOT/'dist').is_dir() else ROOT
TOPICS=('spin','control','sense','matter','chem')
QUERIES={
 'spin':['molecular spin qubit coherence radical','molecular qubit spin phonon relaxation','exchange coupled molecular spin qubit'],
 'control':['dynamical decoupling electron spin magnetic resonance','quantum control pulse electron spin resonance','optimal control magnetic resonance spin coherence'],
 'sense':['quantum sensing molecular spin qubit','electron spin resonance nanoscale sensing','quantum sensing ion chemical recognition'],
 'matter':['conductive metal organic framework electronic transport','two dimensional metal organic framework device interface','metal organic framework magnetism electronic structure'],
 'chem':['metal organic framework single crystal growth','covalent organic framework radical synthesis','metal organic framework stacking crystallization']}
def today():return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()
def read(path,default):return json.loads(path.read_text()) if path.exists() else default
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s or ''))).strip()
def doi_key(s):return re.sub(r'^https?://(?:dx\.)?doi.org/','',s.strip().lower()).removeprefix('doi:').strip()
def title_key(s):return re.sub(r'[^a-z0-9]','',s.lower())
def keys(p):
 k={p['id'],'title:'+title_key(p['title'])}
 if p.get('doi'):k.add('doi:'+doi_key(p['doi']))
 if p.get('arxivId'):k.add('arxiv:'+re.sub(r'v\d+$','',p['arxivId']))
 return k

def request(url,timeout=25,attempts=2):
 for attempt in range(attempts):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'SunlabLiteratureDigest/1.0 (https://yiesacarl.github.io/sunlab-literature-library/; public metadata research)'})
   with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
  except Exception:
   if attempt==attempts-1:raise
   time.sleep(2*(attempt+1))

def cr_record(p):
 doi=doi_key(p.get('DOI',''));title=clean(' '.join(p.get('title',[])))
 if not doi or not title:return None
 dates=[(f,p[f].get('date-parts',[[]])[0]) for f in ['published-online','published','published-print'] if p.get(f,{}).get('date-parts')]
 if not dates:return None
 basis,parts=dates[0];date='-'.join(str(v).zfill(4 if i==0 else 2) for i,v in enumerate(parts))
 authors=', '.join(clean(' '.join([a.get('given',''),a.get('family','')])) for a in p.get('author',[]))
 return dict(id='doi:'+doi,doi=doi,title=title,authors=authors,journal=clean(' '.join(p.get('container-title',[]))),publicationDate=date,dateBasis='Crossref '+basis,sourceUrl='https://doi.org/'+doi,evidenceUrl='https://api.crossref.org/works/'+urllib.parse.quote(doi,safe=''),abstract=clean(p.get('abstract','')),metadataSource='Crossref',status='Published',aliases=[])

def discover(day,cache,lookback):
 state=read(DIST/'digest/state.json',{'version':1,'candidates':{},'runs':[]})
 baseline=read(DIST/'bibliography.json',{})['papers'];known=set()
 for p in baseline:known.update(keys(p))
 start=(day-dt.timedelta(days=lookback)).isoformat();date=day.isoformat();records={};sources=[]
 def fetch_one(topic,q):
  params={'query.bibliographic':q,'filter':f'from-pub-date:{start},until-pub-date:{date},type:journal-article','rows':25,'sort':'relevance'}
  url='https://api.crossref.org/works?'+urllib.parse.urlencode(params)
  cachefile=cache/('crossref-'+hashlib.sha256(q.encode()).hexdigest()[:12]+'.json')
  data=read(cachefile,None) or json.loads(request(url));write(cachefile,data)
  return topic,q,url,data['message']['items']
 with ThreadPoolExecutor(max_workers=3) as executor:
  futures={executor.submit(fetch_one,t,q):(t,q) for t,qs in QUERIES.items() for q in qs}
  for f in as_completed(futures):
   t,q=futures[f]
   try:
    t,q,url,items=f.result();sources.append({'source':'Crossref','topic':t,'query':q,'url':url,'status':'ok','records':len(items)})
    for raw in items:
     p=cr_record(raw)
     if not p or p['publicationDate']>date or keys(p)&known:continue
     old=records.get(p['id']);p['matchedTopics']=sorted(set((old or {}).get('matchedTopics',[])+[t]));records[p['id']]=p
   except Exception as e:sources.append({'source':'Crossref','topic':t,'query':q,'status':'failed','error':str(e)[:180]})
 arxiv_queries={
 'spin':'(ti:"molecular spin" OR ti:"molecular qubit" OR ti:"spin phonon")',
 'control':'(ti:"dynamical decoupling" OR (ti:"spin" AND ti:"quantum control"))',
 'sense':'(ti:"quantum sensing" OR (ti:"sensing" AND ti:"electron spin"))',
 'matter':'((ti:"metal organic" OR ti:"metal-organic") AND (all:conductive OR all:electronic))',
 'chem':'((ti:"metal organic" OR ti:"covalent organic") AND (all:synthesis OR all:crystallization))'}
 ns={'a':'http://www.w3.org/2005/Atom','r':'http://arxiv.org/schemas/atom'}
 arxiv_unavailable=False
 for topic,q in arxiv_queries.items():
  params={'search_query':q+' AND submittedDate:['+start.replace('-','')+'0000 TO '+date.replace('-','')+'2359]','sortBy':'submittedDate','sortOrder':'descending','max_results':20}
  url='https://export.arxiv.org/api/query?'+urllib.parse.urlencode(params)
  if arxiv_unavailable:
   sources.append({'source':'arXiv','topic':topic,'query':q,'url':url,'status':'skipped','error':'Endpoint unavailable in this run; skipped remaining requests'})
   continue
  try:
   raw=request(url,timeout=10,attempts=1);(cache/('arxiv-'+topic+'.xml')).write_bytes(raw);root=ET.fromstring(raw);entries=root.findall('a:entry',ns)
   for e in entries:
    urlp=e.findtext('a:id','',ns);aid=re.sub(r'v\d+$','',urlp.rsplit('/abs/',1)[-1]);datep=e.findtext('a:published','',ns)[:10]
    if not re.match(r'^\d{4}\.\d{4,5}$',aid) or datep>date:continue
    doi=doi_key(e.findtext('r:doi','',ns));p=dict(id='arxiv:'+aid,arxivId=aid,doi=doi,title=clean(e.findtext('a:title','',ns)),authors=', '.join(ea.findtext('a:name','',ns) for ea in e.findall('a:author',ns)),journal='arXiv',publicationDate=datep,dateBasis='arXiv initial submission',sourceUrl='https://arxiv.org/abs/'+aid,evidenceUrl=url,abstract=clean(e.findtext('a:summary','',ns)),metadataSource='arXiv',status='Preprint',matchedTopics=[topic],aliases=[])
    if keys(p)&known:continue
    match=next((v for v in records.values() if keys(v)&keys(p)),None)
    if match:match['aliases']=sorted(set(match['aliases']+list(keys(p))));continue
    records[p['id']]=p
   sources.append({'source':'arXiv','topic':topic,'query':q,'url':url,'status':'ok','records':len(entries)})
  except Exception as e:
   arxiv_unavailable=True
   sources.append({'source':'arXiv','topic':topic,'query':q,'url':url,'status':'failed','error':str(e)[:180]})
  time.sleep(3)
 # Preserve the earliest discovery for every known equivalent identity.
 index={k:p['firstSeenDate'] for p in state['candidates'].values() for k in keys(p)|set(p.get('aliases',[]))}
 for p in records.values():
  p['firstSeenDate']=min([date]+[index[k] for k in keys(p)|set(p.get('aliases',[])) if k in index]);p['lastSeenDate']=date
  prior=state['candidates'].get(p['id'],{})
  state['candidates'][p['id']]={**prior,**{k:v for k,v in p.items() if k!='abstract'}}
  state['candidates'][p['id']]['aliases']=sorted(set(prior.get('aliases',[])+p.get('aliases',[])))
  if prior.get('title') and prior['title']!=p['title']:state['candidates'][p['id']]['approved']=False
 state['runs'].append({'date':date,'sources':sources,'newCandidates':len(records)})
 write(cache/'candidates.json',list(records.values()));write(cache/'discovery-state.json',state);write(cache/'sources.json',sources)
 print(json.dumps({'candidates':len(records),'sourcesOk':sum(x['status']=='ok' for x in sources),'sourcesFailed':sum(x['status']!='ok' for x in sources)},indent=2))

def select(candidates,day,sent=()):
 """0–6 days: select up to five. Only if <3, add age 7–29 to reach three."""
 seen=set(sent);out={t:[] for t in TOPICS}
 eligible=[]
 for p in candidates:
  if not p.get('approved') or p.get('topic') not in TOPICS or keys(p)&seen:continue
  age=(day-dt.date.fromisoformat(p['firstSeenDate'])).days
  if 0<=age<30:eligible.append((p,age))
 for t in TOPICS:
  ranked=sorted([(p,a) for p,a in eligible if p['topic']==t],key=lambda v:(-v[0].get('score',0),v[1],v[0]['id']))
  for lower,upper,limit in [(0,7,5),(7,30,3)]:
   if lower==7 and len(out[t])>=3:continue
   for p,age in ranked:
    if len(out[t])>=limit:break
    identity=keys(p)|set(p.get('aliases',[]))
    if lower<=age<upper and not identity&seen:
     out[t].append({**p,'earlierDiscovery':age>=7});seen.update(identity)
 return out

def validate(issue,state,previous):
 day=dt.date.fromisoformat(issue['date']);sent={k for old in previous for p in old['papers'] for k in keys(p)|set(p.get('aliases',[]))}
 expected=select(list(state['candidates'].values()),day,sent)
 actual={t:[] for t in TOPICS};seen=set(sent)
 for p in issue['papers']:
  assert p['topic'] in TOPICS,'Unknown topic'
  assert not (keys(p)|set(p.get('aliases',[])))&seen,'Repeated work'
  seen.update(keys(p)|set(p.get('aliases',[])));actual[p['topic']].append(p['id'])
  assert p['id'] in state['candidates'],'Not in discovery ledger'
  assert p['firstSeenDate']==state['candidates'][p['id']]['firstSeenDate'],'Discovery date changed'
  assert p['publicationDate']<=issue['date'],'Future publication date'
  for name in ['title','sourceUrl','evidenceUrl','summary','whyRelevant','readingBasis','firstSeenDate','publicationDate','dateBasis']:assert p.get(name),f'Missing {name}'
  for name in ['sourceUrl','evidenceUrl']:assert p[name].startswith('https://'),'Unsafe source URL'
  assert len(p['summary'].split())<=110,'Summary too long'
 for t in TOPICS:assert actual[t]==[p['id'] for p in expected[t]],'Selection policy mismatch: '+t
 assert len(issue['papers'])<=25
 return True

def build(cache,date):
 day=dt.date.fromisoformat(date);state=read(cache/'discovery-state.json',{});reviews=read(cache/'reviews.json',[])
 assert any(s['status']=='ok' for s in read(cache/'sources.json',[])), 'All sources unavailable; preserve the previous issue'
 for r in reviews:
  assert r['id'] in state['candidates'];state['candidates'][r['id']].update(r)
 previous=[read(p,{}) for p in sorted((DIST/'digest/issues').glob('*.json'))]
 if any(x['date']==date for x in previous):raise ValueError('Issue already exists; do not republish or rewrite history')
 sent={k for old in previous for p in old['papers'] for k in keys(p)|set(p.get('aliases',[]))}
 selected=select(list(state['candidates'].values()),day,sent)
 papers=[{k:v for k,v in p.items() if k not in ['abstract','approved','score','matchedTopics','lastSeenDate']} for ps in selected.values() for p in ps]
 issue={'date':date,'generatedAt':dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec='seconds'),'timezone':'Asia/Shanghai','bootstrap':not previous,'papers':papers,'sources':read(cache/'sources.json',[]),'selectionPolicy':'Prefer first discovered in the last 7 calendar days; if a topic has fewer than 3 papers, supplement from days 8–30 to reach 3. Maximum 5 per topic. Never repeat a work.'}
 validate(issue,state,previous)
 write(DIST/'digest/issues'/f'{date}.json',issue);write(DIST/'digest/state.json',state)
 allissues=sorted(previous+[issue],key=lambda x:x['date'],reverse=True)
 manifest={'version':1,'latest':date,'timezone':'Asia/Shanghai','issues':[{'date':x['date'],'count':len(x['papers'])} for x in allissues]};write(DIST/'digest/manifest.json',manifest)
 payload={'manifest':manifest,'issues':allissues}
 (DIST/'digest-data.js').write_text('window.DIGEST_DATA = '+json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+';\n')
 print(json.dumps({'date':date,'count':len(papers),'topics':{t:len(v) for t,v in selected.items()}},indent=2))

def main():
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['discover','build']);parser.add_argument('--date',default=today().isoformat());parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--lookback',type=int,default=60);args=parser.parse_args();args.cache.mkdir(parents=True,exist_ok=True)
 if args.command=='discover':discover(dt.date.fromisoformat(args.date),args.cache,args.lookback)
 else:build(args.cache,args.date)
if __name__=='__main__':main()
