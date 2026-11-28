"""Immutable base ledger and size-bounded, hashed public metadata deltas."""
import base64, gzip, hashlib, json, re
from pathlib import Path
MAX_BYTES = 24000
PRIVATE = {'abstract', 'feedSummary', 'rawAbstract', 'fullText'}
def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n').encode('utf-8')
def assert_public(value):
    if isinstance(value, dict):
        if PRIVATE.intersection(value): raise ValueError('Private source text must not be published')
        for item in value.values(): assert_public(item)
    elif isinstance(value, list):
        for item in value: assert_public(item)
def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
def load(root):
    root = Path(root);folder=root/'digest/state-deltas'
    state = json.loads((root/'digest/state.json').read_text())
    for path in sorted(folder.glob('*.json')):
        descriptor=json.loads(path.read_text()); chunks=[]
        if descriptor.get('version')!=1: raise ValueError('Unknown ledger delta version')
        for item in descriptor['parts']:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-\d{4}\.b64',item['name']): raise ValueError('Unsafe delta filename')
            chunk=(folder/item['name']).read_bytes()
            if len(chunk)!=item['bytes'] or hashlib.sha256(chunk).hexdigest()!=item['sha256']: raise ValueError('Truncated or corrupted ledger part')
            chunks.append(chunk)
        raw=gzip.decompress(base64.b64decode(b''.join(chunks),validate=True))
        if hashlib.sha256(raw).hexdigest()!=descriptor['sha256']: raise ValueError('Ledger payload hash mismatch')
        delta=json.loads(raw)
        for key, change in delta.get('changes', {}).items():
            old = state['candidates'].get(key, {})
            if change['before'] != fingerprint(old): raise ValueError('Ledger delta base mismatch: '+key)
            new = {**old, **change['set']}
            for field in change['remove']: new.pop(field, None)
            if old.get('firstSeenDate') and new.get('firstSeenDate', '9999') > old['firstSeenDate']: raise ValueError('Discovery date advanced')
            state['candidates'][key] = new
        if delta['priorRuns']!=fingerprint(state['runs']): raise ValueError('Source history base mismatch')
        state['runs'].extend(delta['runs'])
    return state

def save(root, state, date):
    root = Path(root)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date): raise ValueError('Invalid issue date')
    base = load(root);folder=root/'digest/state-deltas'
    if set(base)!=set(state) or base.get('version')!=state.get('version'): raise ValueError('Unexpected state schema change')
    if not set(base['candidates']) <= set(state['candidates']): raise ValueError('Cannot remove historical identities')
    if state['runs'][:len(base['runs'])] != base['runs']: raise ValueError('Cannot rewrite historical source runs')
    if (folder/(date+'.json')).exists(): raise ValueError('Daily ledger already exists')
    if any(p.stem>=date for p in folder.glob('*.json')): raise ValueError('Cannot backdate ledger')
    delta={'version':1,'date':date,'changes':{},'runs':state['runs'][len(base['runs']):],'priorRuns':fingerprint(base['runs'])}
    for key, value in sorted(state['candidates'].items()):
        old=base['candidates'].get(key,{})
        if old==value: continue
        if old.get('firstSeenDate') and value.get('firstSeenDate','9999')>old['firstSeenDate']: raise ValueError('Discovery date advanced')
        if not set(old.get('aliases',[]))<=set(value.get('aliases',[])): raise ValueError('Cannot discard identity aliases')
        delta['changes'][key]={'before':fingerprint(old),'set':{k:v for k,v in value.items() if k not in old or old[k]!=v},'remove':sorted(set(old)-set(value))}
    assert_public(delta)
    raw=encoded(delta);payload=base64.b64encode(gzip.compress(raw,compresslevel=9,mtime=0));parts=[];paths=[]
    folder.mkdir(parents=True,exist_ok=True)
    for i, offset in enumerate(range(0,len(payload),MAX_BYTES)):
        chunk=payload[offset:offset+MAX_BYTES];path=folder/f'{date}-{i:04d}.b64';path.write_bytes(chunk);paths.append(path)
        parts.append({'name':path.name,'bytes':len(chunk),'sha256':hashlib.sha256(chunk).hexdigest()})
    descriptor=folder/(date+'.json');descriptor.write_bytes(encoded({'version':1,'date':date,'sha256':hashlib.sha256(raw).hexdigest(),'parts':parts}));paths.append(descriptor)
    if load(root)!=state: raise ValueError('Ledger round-trip mismatch')
    return paths
