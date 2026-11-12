import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/g2-sram-feasibility-01'
OUT=ROOT/'evidence/E0042-sram-prefetch-screen/feasibility'
OUT.mkdir(parents=True,exist_ok=True)
result=json.loads((BASE/'inspection.json').read_bytes())
assert result['implementation']=='NOT_STARTED' and result['lef_area_um2']==49488.4992
for name,item in result['macro_inputs'].items():
    source=BASE/name
    if source.exists():
        raw=source.read_bytes()
        assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
        target=OUT/(name+'.gz')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(gzip.compress(raw,mtime=0))
(OUT/'inspection.json').write_bytes((BASE/'inspection.json').read_bytes())
(OUT/'inspector.py').write_bytes((ROOT/'build/inspect_g2_sram_option.py').read_bytes())
(OUT/'retention-runner.py').write_bytes(Path(__file__).read_bytes())
lines=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(OUT).as_posix() for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256SUMS']
(OUT/'SHA256SUMS').write_bytes(('\n'.join(lines)+'\n').encode())
print('PASS: exact installed SRAM feasibility inputs retained; implementation not yet qualified')
