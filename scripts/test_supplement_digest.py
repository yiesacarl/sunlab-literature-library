import unittest
from supplement_digest import allocate

def p(i,date='2026-10-28',topic='spin',**kw):return dict(id=str(i),title='Paper '+str(i),publicationDate=date,topic=topic,approved=True,firstSeenDate='2026-11-04',**kw)
def issue(date,papers):return dict(date=date,papers=papers)
class SupplementTests(unittest.TestCase):
 def test_preserves_cards_and_excludes_later_history(self):
  old=p(1);out=allocate([issue('2026-10-28',[old])],[p(1),p(2),p(3)],{'3'})
  self.assertEqual(out[0]['papers'][0],old);self.assertEqual([x['id'] for x in out[0]['papers']],['1','2'])
 def test_quota_spills_into_later_eligible_day(self):
  out=allocate([issue('2026-10-28',[p(i) for i in range(5)]),issue('2026-10-29',[])],[p(8)],set())
  self.assertEqual(len(out[0]['papers']),5);self.assertEqual(out[1]['papers'][0]['id'],'8')
  self.assertEqual(out[1]['papers'][0]['firstSeenDate'],'2026-11-04')
 def test_future_and_expired_are_not_inserted(self):
  out=allocate([issue('2026-11-01',[])],[p(1,'2026-11-02'),p(2,'2026-10-01')],set())
  self.assertEqual(out[0]['papers'],[])
 def test_old_window_only_tops_up_to_three(self):
  out=allocate([issue('2026-11-01',[p(0,'2026-11-01')])],[p(i,'2026-10-20') for i in range(1,5)],set())
  self.assertEqual(len(out[0]['papers']),3)
 def test_alias_dedup_across_dates(self):
  out=allocate([issue('2026-11-01',[]),issue('2026-11-02',[])],[p(1,'2026-11-01'),p(2,'2026-11-02',aliases=['1'])],set())
  self.assertEqual(sum(len(x['papers']) for x in out),1)
if __name__=='__main__':unittest.main()
