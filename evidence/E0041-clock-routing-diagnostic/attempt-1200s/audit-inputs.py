import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'build/g2-physical-shared/13966350208'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original = read(BASE / 'runs/wokwi/resolved.json')
current = read(HERE / 'runs/no-clock-ndr/resolved.json')
def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, str):
        return (value.replace('/home/runner/work/protocol-emulator-asic/protocol-emulator-asic', '<design>')
                .replace('/workspace/build/g2-physical-shared/13966350208', '<design>')
                .replace('/home/runner/.ciel/ciel/ihp-sg13/versions/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008', '<pdk>')
                .replace('/pdk/ciel/ihp-sg13/versions/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008', '<pdk>'))
    return value
a, b = normalize(original), normalize(current)
differences = {k: [a.get(k), b.get(k)] for k in set(a)|set(b) if a.get(k) != b.get(k)}
assert set(differences) == {'OPENROAD_THREADS', 'FP_DEF_TEMPLATE', 'DESIGN_DIR'}, sorted(differences)
assert differences['OPENROAD_THREADS'] == [None, 4]
assert differences['DESIGN_DIR'] == ['<design>/src', '/workspace/build/g2-routing-diagnostic-02']
before = (HERE / 'before.def').read_bytes()
after = (HERE / 'after.def').read_bytes()
marker = b' + NONDEFAULTRULE CTS_NDR_0'
assert before.count(marker) == 16 and before.replace(marker, b'') == after
manifest = read(ROOT / 'evidence/E0038-shared-program-read/sources/source-manifest.json')['od128']['source_sha256']
assert {n: sha(BASE / 'src' / n) for n in manifest} == manifest
assert read(HERE / 'ablation-result.json')['spec_sha256'] == sha(HERE / 'spec-at-start.md')
assert read(HERE / 'ablation-result.json')['source_odb_sha256'] == sha(BASE / 'runs/wokwi/37-openroad-resizertimingpostcts/tt_um_khangelani_protocol_emulator.odb')
report = {'status': 'PASS_ISOLATED_ROUTING_INPUTS', 'differences_after_path_relocation': differences,
          'scope': '16 net NDR assignments only; four threads explicit instead of auto, matching original actual command; unused DEF template path relocated',
          'source_sha256': manifest, 'original_def_sha256': sha(HERE / 'before.def'), 'ablated_def_sha256': sha(HERE / 'after.def')}
(HERE / 'input-audit.json').write_bytes((json.dumps(report, indent=2)+'\n').encode())
print(report['status'])
