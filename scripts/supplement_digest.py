#!/usr/bin/env python3
"""Explicitly authorized, append-only supplements to existing historical issues."""
import argparse,copy,datetime as dt,json
from pathlib import Path
import digest as d
from official_sources import identity

EXCLUDE={'abstract','feedSummary','approved','score','matchedTopics','lastSeenDate'}
def allocate(issues,candidates,known):
    out=copy.deepcopy(issues);seen=set(known)
    for issue in issues:
        for p in issue['papers']:seen.update(identity(p))
    # Prefer the actual publication day, then later eligible issues with spare space.
    for p in sorted(candidates,key=lambda x:(x['publicationDate'],-x.get('score',0),x['id'])):
        if not p.get('approved') or p.get('topic') not in d.TOPICS or identity(p)&seen:continue
        pub=dt.date.fromisoformat(p['publicationDate'])
        for issue in sorted(out,key=lambda x:x['date']):
            age=(dt.date.fromisoformat(issue['date'])-pub).days
            n=sum(q['topic']==p['topic'] for q in issue['papers'])
            if 0<=age<30 and n<(5 if age<7 else 3):
                issue['papers'].append({**{k:v for k,v in p.items() if k not in EXCLUDE},'earlierPublication':age>=7})
                seen.update(identity(p));break
    return out

def build(cache,start,end):
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=8)));stamp=now.isoformat(timespec='seconds')
    assert start<=end<now.date()
    allissues=[d.read(f,{}) for f in sorted((d.DIST/'digest/issues').glob('*.json'))]
    dates=[(start+dt.timedelta(days=i)).isoformat() for i in range((end-start).days+1)]
    old=[x for x in allissues if x['date'] in dates]
    assert len(old)==len(dates) and all(x.get('mode')=='historical-backfill' for x in old)
    state=d.read(cache/'discovery-state.json',{})
    baseline=d.read(d.DIST/'bibliography.json',{})['papers'];libraryids={p['id'] for p in baseline}
    known={k for p in baseline for k in identity(p)}
    for issue in allissues:
        for p in issue['papers']:known.update(identity(p))
    candidates={p['id']:p for p in d.read(cache/'candidates.json',[])};reviewed=[]
    for review in d.read(cache/'reviews.json',[]):
        assert review['id'] in candidates,'Missing evidence: '+review['id']
        p={**candidates[review['id']],**review}
        if not p.get('approved'):continue
        assert p.get('abstractComplete') and p.get('abstract'),'No full abstract read'
        assert len(p['publicationDate'])==10 and p['publicationDate']<=end.isoformat()
        assert p['firstSeenDate']<=now.date().isoformat()
        for f in ['summary','whyRelevant','readingBasis','dateBasis','authors','journal']:assert p.get(f),f
        assert 'requires publication-date check' not in p['dateBasis'],'Unverified feed date'
        assert len(p['summary'].split())<=110
        assert all(p[f].startswith('https://') for f in ['sourceUrl','evidenceUrl'])
        assert all(r['id'] in libraryids for r in p.get('relatedPapers',[]))
        assert p['topic'] in d.TOPICS
        reviewed.append(p)
        state['candidates'][p['id']]={k:v for k,v in p.items() if k not in ['abstract','feedSummary']}
    assert reviewed,'No reviewed candidates supplied'
    updated=allocate(old,reviewed,known)
    sources=d.read(cache/'sources.json',[]);assert any(s['status']=='ok' for s in sources)
    report=[];seen=set(known)
    for before,issue in zip(old,updated):
        assert issue['papers'][:len(before['papers'])]==before['papers'],'Existing cards changed'
        additions=issue['papers'][len(before['papers']):]
        for p in additions:
            assert not identity(p)&seen,'Duplicate addition';seen.update(identity(p))
        assert all(sum(p['topic']==t for p in issue['papers'])<=5 for t in d.TOPICS)
        issue.setdefault('initialSources',before['sources'])
        issue['sources']=sources;issue['collectorVersion']=2
        issue['sourceCoverageNote']='Official Nature, Science, ACS, APS and arXiv feeds; paginated arXiv date search; Crossref journal-date metadata for rolling-feed gaps; selected publisher abstracts checked directly. Successful queries do not guarantee exhaustive indexing.'
        issue['updatedAt']=stamp
        issue.setdefault('supplements',[]).append({'preparedAt':stamp,'reason':'Official-source expansion authorized by the user','addedIds':[p['id'] for p in additions]})
        report.append({'date':issue['date'],'before':len(before['papers']),'added':len(additions),'after':len(issue['papers']),'topics':{t:sum(p['topic']==t for p in issue['papers']) for t in d.TOPICS}})
    state.setdefault('supplements',[]).append({'preparedAt':stamp,'from':dates[0],'to':dates[-1],'report':report})
    # Unreviewed discovery entries retain identities/dates; retrieve evidence before later review.
    minimal={'id','title','doi','arxivId','aliases','firstSeenDate','lastSeenDate','publicationDate','sourceUrl','status','metadataSource','dateBasis'}
    for id,p in list(state['candidates'].items()):
        if not p.get('approved'):state['candidates'][id]={k:v for k,v in p.items() if k in minimal}
    for issue in updated:d.write(d.DIST/'digest/issues'/f"{issue['date']}.json",issue)
    d.write(d.DIST/'digest/state.json',state)
    merged=sorted([x for x in allissues if x['date'] not in dates]+updated,key=lambda x:x['date'],reverse=True)
    manifest={'version':1,'latest':merged[0]['date'],'timezone':'Asia/Shanghai','issues':[{'date':x['date'],'count':len(x['papers']),**({'mode':x['mode']} if x.get('mode') else {})} for x in merged]}
    d.write(d.DIST/'digest/manifest.json',manifest)
    (d.DIST/'digest-data.js').write_text('window.DIGEST_DATA = '+json.dumps({'manifest':manifest,'issues':merged},ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+';\n')
    d.write(cache/'supplement-report.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--start',type=dt.date.fromisoformat,required=True);p.add_argument('--end',type=dt.date.fromisoformat,required=True);a=p.parse_args();build(a.cache,a.start,a.end)
