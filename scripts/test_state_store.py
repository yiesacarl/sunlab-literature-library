import copy,json,tempfile,unittest
from pathlib import Path
import state_store
class LedgerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'digest').mkdir()
  self.base={'version':1,'candidates':{'a':{'id':'a','firstSeenDate':'2026-11-01','aliases':['doi:old']}},'runs':[{'date':'2026-11-01'}]}
  (self.root/'digest/state.json').write_text(json.dumps(self.base))
 def tearDown(self):self.tmp.cleanup()
 def test_roundtrip_and_base_unchanged(self):
  before=(self.root/'digest/state.json').read_bytes();new=copy.deepcopy(self.base)
  new['candidates']['a']['lastSeenDate']='2026-11-28';new['candidates']['b']={'id':'b','firstSeenDate':'2026-11-28'}
  new['runs'].append({'date':'2026-11-28','sources':[{'name':str(i),'url':'https://example.com/'+str(i)} for i in range(2000)]})
  paths=state_store.save(self.root,new,'2026-11-28')
  self.assertEqual(new,state_store.load(self.root));self.assertEqual(before,(self.root/'digest/state.json').read_bytes())
  self.assertTrue(all(p.stat().st_size<=state_store.MAX_BYTES for p in paths))
  newer=copy.deepcopy(new);newer['candidates']['a']['lastSeenDate']='2026-11-29';state_store.save(self.root,newer,'2026-11-29');self.assertEqual(newer,state_store.load(self.root))
 def test_reject_truncated_transport(self):
  paths=state_store.save(self.root,self.base,'2026-11-28');paths[0].write_bytes(paths[0].read_bytes()[:-1])
  with self.assertRaises(ValueError):state_store.load(self.root)
 def test_reject_private_text(self):
  new=copy.deepcopy(self.base);new['candidates']['a']['abstract']='private source text'
  with self.assertRaises(ValueError):state_store.save(self.root,new,'2026-11-28')
 def test_reject_reset_discovery(self):
  new=copy.deepcopy(self.base);new['candidates']['a']['firstSeenDate']='2026-11-28'
  with self.assertRaises(ValueError):state_store.save(self.root,new,'2026-11-28')
 def test_reject_lost_history_or_alias(self):
  for field in ['aliases','candidate','runs']:
   new=copy.deepcopy(self.base)
   if field=='aliases':new['candidates']['a']['aliases']=[]
   elif field=='candidate':new['candidates']={}
   else:new['runs']=[]
   with self.assertRaises(ValueError):state_store.save(self.root,new,'2026-11-28')
 def test_reject_duplicate_day(self):
  state_store.save(self.root,self.base,'2026-11-28')
  with self.assertRaises(ValueError):state_store.save(self.root,self.base,'2026-11-28')
if __name__=='__main__':unittest.main()
