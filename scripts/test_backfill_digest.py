import datetime as dt
import unittest
from backfill_digest import select
from digest import keys

DAY=dt.date(2026,10,28)
def paper(i,age,score=1):
    return dict(id='doi:10.test/'+str(i),doi='10.test/'+str(i),title='Work '+str(i),
                topic='spin',approved=True,score=score,firstSeenDate='2026-11-04',
                publicationDate=(DAY-dt.timedelta(days=age)).isoformat())

class BackfillTests(unittest.TestCase):
    def test_publication_boundaries_and_actual_discovery_date(self):
        result=select([paper(1,0),paper(2,6),paper(3,29),paper(4,30),paper(5,-1)],DAY)['spin']
        self.assertEqual([p['id'] for p in result],[paper(i,0)['id'] for i in (1,2,3)])
        self.assertTrue(all(p['firstSeenDate']=='2026-11-04' for p in result))
        self.assertTrue(result[-1]['earlierPublication'])
        self.assertNotIn('earlierDiscovery',result[-1])
    def test_existing_later_issue_is_excluded(self):
        self.assertEqual(select([paper(1,0)],DAY,keys(paper(1,0)))['spin'],[])
    def test_partial_dates_not_backfilled(self):
        self.assertEqual(select([{**paper(1,0),'publicationDate':'2026-10'}],DAY)['spin'],[])
    def test_recent_priority_and_no_older_topup_above_three(self):
        result=select([paper(i,1) for i in range(4)]+[paper(9,7,99)],DAY)['spin']
        self.assertEqual(len(result),4)
        self.assertTrue(all(not p['earlierPublication'] for p in result))
    def test_no_repeats_across_reconstructed_days(self):
        candidates=[paper(i,1) for i in range(8)]
        first=select(candidates,DAY)['spin']
        second=select(candidates,DAY+dt.timedelta(days=1),{k for p in first for k in keys(p)})['spin']
        self.assertEqual((len(first),len(second)),(5,3))
        self.assertFalse({p['id'] for p in first}&{p['id'] for p in second})

if __name__=='__main__':unittest.main()
