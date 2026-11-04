import datetime as dt,unittest
from digest import select,keys
DAY=dt.date(2026,11,4)
def p(i,age,topic='spin',score=1,**kw):
 return dict(id='doi:10.test/'+str(i),doi='10.test/'+str(i),title='Paper '+str(i),topic=topic,firstSeenDate=(DAY-dt.timedelta(days=age)).isoformat(),approved=True,score=score,**kw)
class SelectionTests(unittest.TestCase):
 def test_recent_maximum_five(self):self.assertEqual(len(select([p(i,0) for i in range(8)],DAY)['spin']),5)
 def test_recent_precedes_higher_ranked_older(self):
  result=select([p(1,0),p(2,6),p(3,7,score=99),p(4,8)],DAY)['spin']
  self.assertEqual([v['id'] for v in result],['doi:10.test/1','doi:10.test/2','doi:10.test/3']);self.assertTrue(result[-1]['earlierDiscovery'])
 def test_no_topup_if_three_recent(self):
  self.assertEqual(len(select([p(i,1) for i in range(3)]+[p(9,7,score=99)],DAY)['spin']),3)
 def test_exact_window_boundaries(self):
  result=select([p(1,6),p(2,7),p(3,29),p(4,30),p(5,-1)],DAY)['spin'];self.assertEqual(len(result),3)
 def test_cross_topic_and_history_dedup(self):
  a=p(1,0);b={**a,'topic':'chem','id':'arxiv:duplicate','aliases':['doi:10.test/1']}
  out=select([a,b,p(2,0)],DAY,keys(p(2,0)));self.assertEqual(sum(map(len,out.values())),1)
 def test_unreviewed_and_other_excluded(self):
  self.assertEqual(sum(map(len,select([{**p(1,0),'approved':False},p(2,0,topic='other')],DAY).values())),0)
 def test_zero_candidate_is_not_filled(self):self.assertEqual(select([],DAY)['sense'],[])
if __name__=='__main__':unittest.main()
