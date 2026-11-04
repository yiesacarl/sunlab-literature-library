#!/usr/bin/env python3
"""Version local static assets after building an issue; works in source and Pages roots."""
from pathlib import Path
import hashlib,re
root=Path(__file__).resolve().parents[1];dist=root/'dist' if (root/'dist').is_dir() else root
p=dist/'index.html';s=p.read_text()
for name in ['style.css','data.js','app.js','digest-data.js','digest.js','favicon.svg']:
 digest=hashlib.sha256((dist/name).read_bytes()).hexdigest()[:10]
 s=re.sub(r'((?:src|href)=")'+re.escape(name)+r'(?:\?v=[a-z0-9]+)?"',lambda m:m.group(1)+name+'?v='+digest+'"',s)
p.write_text(s)
print('Asset versions updated.')
