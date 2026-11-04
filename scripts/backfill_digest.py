#!/usr/bin/env python3
"""Explicit historical reconstruction; never pretend a paper was discovered earlier."""
import argparse
import datetime as dt
import json
from pathlib import Path
import digest as d

POLICY = ('Historical reconstruction by publication date, not discovery date: prefer papers '
          'published in the issue date or previous six days; only if fewer than three qualify '
          'in a direction, supplement from publication ages 7–29 days to reach three. '
          'Maximum five per direction; exclude existing library records and every other issue. '
          'First discovery and preparation timestamps retain their actual dates.')

def select(candidates, day, sent=()):
    # Reuse the tested quota/ranking policy with a private selection-only date field.
    eligible = []
    originals = {}
    for p in candidates:
        if len(p.get('publicationDate', '')) != 10:
            continue
        try:
            dt.date.fromisoformat(p['publicationDate'])
        except ValueError:
            continue
        originals[p['id']] = p
        eligible.append({**p, 'firstSeenDate': p['publicationDate']})
    chosen = d.select(eligible, day, sent)
    return {t: [{**originals[p['id']], 'earlierPublication': p['earlierDiscovery']}
                for p in papers] for t, papers in chosen.items()}

def build(cache, start, end):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    assert start <= end < now.date(), 'Backfill must refer to past dates'
    previous = [d.read(p,{}) for p in sorted((d.DIST/'digest/issues').glob('*.json'))]
    dates = [(start + dt.timedelta(days=i)).isoformat() for i in range((end-start).days+1)]
    assert not set(dates) & {p['date'] for p in previous}, 'Never rewrite an existing issue'
    sources = d.read(cache/'sources.json', [])
    assert any(s['status']=='ok' for s in sources), 'No successful source queries'
    state = d.read(d.DIST/'digest/state.json', {})
    candidates = {p['id']: p for p in d.read(cache/'candidates.json', [])}
    for r in d.read(cache/'reviews.json', []):
        assert r['id'] in candidates, 'Review without evidence'
        candidates[r['id']].update(r)
    baseline = d.read(d.DIST/'bibliography.json', {})['papers']
    sent = {k for p in baseline+[p for issue in previous for p in issue['papers']]
            for k in d.keys(p)|set(p.get('aliases', []))}
    reviewed = [p for p in candidates.values() if p.get('approved')]
    for p in reviewed:
        assert p['abstract'], 'Review needs read evidence'
        old = state['candidates'].get(p['id'], {})
        p['firstSeenDate'] = old.get('firstSeenDate', p['firstSeenDate'])
        assert p['firstSeenDate'] <= now.date().isoformat()
        assert p['topic'] in d.TOPICS
        for field in ['summary','whyRelevant','readingBasis','dateBasis','authors','journal']:
            assert p.get(field), 'Missing '+field
        assert len(p['summary'].split()) <= 110
        assert all(p[field].startswith('https://') for field in ['sourceUrl','evidenceUrl'])
        assert all(r['id'] in {x['id'] for x in baseline} for r in p.get('relatedPapers', []))
        state['candidates'][p['id']] = {**old, **{k:v for k,v in p.items() if k!='abstract'},
                                        'lastSeenDate':now.date().isoformat()}
    issues = []
    for date in dates:
        day = dt.date.fromisoformat(date)
        selected = select(reviewed, day, sent)
        papers = [{k:v for k,v in p.items() if k not in
                   ['abstract','approved','score','matchedTopics','lastSeenDate','earlierDiscovery']}
                  for topic in d.TOPICS for p in selected[topic]]
        for p in papers:
            identity = d.keys(p)|set(p.get('aliases', []))
            assert not identity & sent, 'Repeated work'
            assert 0 <= (day-dt.date.fromisoformat(p['publicationDate'])).days < 30
            assert p['firstSeenDate'] == state['candidates'][p['id']]['firstSeenDate']
            sent.update(identity)
        issues.append({'date':date,'generatedAt':now.isoformat(timespec='seconds'),
                       'timezone':'Asia/Shanghai','bootstrap':False,'mode':'historical-backfill',
                       'selectionDateBasis':'publicationDate','papers':papers,'sources':sources,
                       'selectionPolicy':POLICY})
    # All selections validated before writing. Existing issue files are never touched.
    for issue in issues:
        d.write(d.DIST/'digest/issues'/f"{issue['date']}.json", issue)
        print(json.dumps({'date':issue['date'],'count':len(issue['papers']),
                          'topics':{t:sum(p['topic']==t for p in issue['papers']) for t in d.TOPICS}}))
    state.setdefault('backfills', []).append({'generatedAt':now.isoformat(timespec='seconds'),
        'from':dates[0],'to':dates[-1],'selectionDateBasis':'publicationDate','sources':sources})
    d.write(d.DIST/'digest/state.json', state)
    allissues = sorted(previous+issues, key=lambda x:x['date'], reverse=True)
    manifest = {'version':1,'latest':allissues[0]['date'],'timezone':'Asia/Shanghai',
                'issues':[{'date':x['date'],'count':len(x['papers']),
                           **({'mode':x['mode']} if x.get('mode') else {})} for x in allissues]}
    d.write(d.DIST/'digest/manifest.json', manifest)
    (d.DIST/'digest-data.js').write_text('window.DIGEST_DATA = '+json.dumps(
        {'manifest':manifest,'issues':allissues},ensure_ascii=False,separators=(',',':')
        ).replace('<','\\u003c')+';\n')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--start',type=dt.date.fromisoformat,required=True)
    parser.add_argument('--end',type=dt.date.fromisoformat,required=True)
    args=parser.parse_args()
    build(args.cache,args.start,args.end)
