#!/usr/bin/env python3
"""Generate a byte/hash-checked upload inventory; never print the full ledger."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def inventory(date):
 paths=[f'digest/issues/{date}.json','digest/manifest.json','index.html']
 paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'digest/state-deltas').glob(date+'*'))]
 if not (ROOT/f'digest/state-deltas/{date}.json').exists():raise ValueError('Missing ledger delta descriptor')
 out=[]
 for path in paths:
  raw=(ROOT/path).read_bytes()
  out.append({'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'gitBlobSha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'chunks':(len(raw)+11999)//12000})
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--date',required=True);p.add_argument('--path');p.add_argument('--chunk',type=int);a=p.parse_args()
 entries=inventory(a.date)
 if a.path:
  if a.path not in [x['path'] for x in entries]:raise ValueError('Not a daily publication file')
  # Base64 keeps fixed byte boundaries valid for every UTF-8 character.
  import base64
  raw=(ROOT/a.path).read_bytes();start=(a.chunk or 0)*12000
  print(json.dumps({'path':a.path,'chunk':a.chunk or 0,'base64':base64.b64encode(raw[start:start+12000]).decode(),'bytes':len(raw[start:start+12000])}))
 else:print(json.dumps(entries,indent=2))
