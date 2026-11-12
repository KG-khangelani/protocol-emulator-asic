# SPDX-License-Identifier: Apache-2.0
"""Audit the contact-rule diagnosis and optionally repeat native boundary checks."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile

here = Path(__file__).resolve().parent
root = here.parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--native', action='store_true')
args = parser.parse_args()
out = args.output.resolve()
assert out.is_relative_to(root / 'build') and not out.exists()
out.mkdir()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(p.read_bytes())
index = read(here / 'archive.json')
raw = (here / 'diagnostic.tar.gz').read_bytes()
assert len(raw) == index['bytes'] and sha(raw) == index['sha256']
with tarfile.open(here / 'diagnostic.tar.gz') as bundle:
    assert len(bundle.getmembers()) == len(index['files'])
    for member in bundle:
        assert member.isfile() and not PurePosixPath(member.name).is_absolute() and '..' not in PurePosixPath(member.name).parts
        contents = bundle.extractfile(member).read()
        assert sha(contents) == index['files'][member.name]
        target = out / member.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)

def findings(text):
    category, result = '', []
    for line in text.splitlines()[1:]:
        if not line or line.startswith(('-', '[INFO]')):
            continue
        if line.startswith(' '):
            result.append((category, line.strip()))
        else:
            category = line
    count = int(re.findall(r'\[INFO\] COUNT: (\d+)', text)[-1])
    assert count == len(result)
    return sorted(result)

old = read(out / 'original-macro/result.json')
new = read(out / 'correction-4/result.json')
assert old['reported_count'] == 32 and new['reported_count'] == 0
for result in (old, new):
    e = result['execution']
    assert e['returncode'] == 0 and not e['timed_out'] and e['seconds'] < e['wall_limit'] == 1200
old_findings = findings((out / 'original-macro/reports/drc.magic.rpt').read_text(encoding='utf-8'))
assert len(old_findings) == 32 and sum('SRAM exception' in c for c,_ in old_findings) == 20
assert not findings((out / 'correction-4/macro/reports/drc.magic.rpt').read_text(encoding='utf-8'))
assert read(out / 'original-macro/previous-result.json')['execution']['timed_out']
for label in ['original-macro', *(f'correction-{n}' for n in range(1,5)), 'controls-1', 'controls-2', 'wrapper-1', 'wrapper-2']:
    runtime = read(out / label / 'runtime.json')
    assert runtime['image_id'] == runtime['configured_image'] == 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
    assert runtime['state']['Status'] == 'exited'
    assert runtime['state']['ExitCode'] == (1 if label in ('correction-1','correction-2','correction-3','wrapper-1') else 0)
    assert any(m['Destination'] == '/pdk' and not m['RW'] for m in runtime['mounts'])
geometry = read(out / 'geometry/result.json')
assert geometry['status'] == 'PASS_ALL_32_REFERENCE_ENCLOSURES' and len(geometry['observations']) == 32
assert geometry['gds_sha256'] == 'e77a4d177e02541fe6c58351008455f9a05a715b504f8e318599f3d41bf5f959'
for observation in geometry['observations']:
    if observation['marker_coverage']['sram']:
        assert observation['minimum_activ_enclosure_nm'] == 10 and observation['reference_limit_nm'] == 6
    else:
        assert observation['marker_coverage']['digital'] and observation['minimum_activ_enclosure_nm'] == 60 and observation['reference_limit_nm'] == 50
controls = read(out / 'controls-2/result.json')
assert controls['status'] == 'PASS_CONTACT_BOUNDARY_CONTROLS'
sites = read(out / 'controls-2/sites.json')
assert len(sites['sites']) == 48
for label in ('controls-1', 'controls-2'):
    result = read(out / label / 'result.json')
    assert sha((out / label / 'controls.gds').read_bytes()) == result['gds_sha256']
    for kind in ('original', 'proposed'):
        report = findings((out / label / kind / 'reports/drc.magic.rpt').read_text(encoding='utf-8'))
        actual = set()
        for category, coordinates in report:
            if '(Cnt.c' in category:
                a,b,c,d = [float(v.removesuffix('um'))*1000 for v in coordinates.split()]
                matched = [s['name'] for s in sites['sites'] if abs(s['x_nm']+80-(a+c)/2)<500 and abs(s['y_nm']+80-(b+d)/2)<500]
                assert len(matched) == 1
                actual.add(matched[0])
        run = result['runs'][kind]
        assert sorted(actual) == run['observed_failing_cases']
        if label == 'controls-2':
            assert run['observed_failing_cases'] == run['expected_failing_cases']
        elif kind == 'proposed':
            assert actual - set(run['expected_failing_cases']) == {'ndc_sram_006','pdc_sram_006','nsc_sram_006'}
        assert sum('(M2.d)' in c for c,_ in report) == 1 and sum('(M2.a)' in c for c,_ in report) == 2
assert read(out / 'controls-1/result.json')['status'] == 'REJECTED_CONTACT_BOUNDARY_CONTROLS'
assert read(out / 'wrapper-2/result.json')['status'] == 'PASS_PORTABLE_MAGIC_WRAPPER'
for kind in ('original','proposed'):
    assert findings((out / 'wrapper-2' / kind / 'reports/drc.magic.rpt').read_text(encoding='utf-8')) == findings((out / 'controls-2' / kind / 'reports/drc.magic.rpt').read_text(encoding='utf-8'))

spec = importlib.util.spec_from_file_location('retained_alignment', out / 'portable/align_sram_magic.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for name, expected in module.REFERENCE_SHA256.items():
    assert sha((out / 'reference' / name).read_bytes()) == expected
for name, expected in module.ALIGNED_SHA256.items():
    assert sha((out / 'aligned' / name).read_bytes()) == expected
assert sha((out / 'reference/SG13CMOS5L_os_layout_rules.pdf').read_bytes()) == '6c921a403b30c30950b43664204ee6a567e7a33166a74a0e48cabd2a0c7bbc1d'
native = 'NOT_REPEATED'
if args.native:
    pdk = Path('/pdk/ciel/ihp-sg13/versions/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008/ihp-sg13cmos5l')
    for kind, step in [('proposed','Magic.DRC'),('original','Magic.StreamOut')]:
        work = out / ('native-' + kind)
        work.mkdir()
        (work / 'reports').mkdir()
        text = (out / 'controls-2' / kind / '_env.tcl').read_text(encoding='utf-8')
        for key, value in [('STEP_DIR',str(work)),('CURRENT_GDS',str(out / 'controls-2/controls.gds')),('STEP_ID',step)]:
            text, count = re.subn(r'^set ::env\(' + key + r'\) .*$', 'set ::env(' + key + ') ' + value, text, flags=re.M)
            assert count == 1
        env_file = work / '_env.tcl'
        env_file.write_bytes(text.encode())
        command = ['magic','-dnull','-noconsole','-rcfile',str(out / 'portable/sram_magicrc.tcl'), str(out / 'reference/native/wrapper.tcl')]
        with (work / 'run.log').open('wb') as log:
            done = subprocess.run(command, cwd=work, env=dict(os.environ,_TCL_ENV_IN=str(env_file),_MAGIC_SCRIPT=str(out / 'reference/native/drc.tcl')), stdout=log, stderr=subprocess.STDOUT, timeout=60)
        assert done.returncode == 0
        assert findings((work / 'reports/drc.magic.rpt').read_text()) == findings((out / 'controls-2' / kind / 'reports/drc.magic.rpt').read_text())
        assert (work / 'sram-magic-aligned/alignment.json').exists() == (kind == 'proposed')
    # A changed reference must be rejected before any aligned output is created.
    bad = out / 'wrong-reference/pdk'
    for name in module.REFERENCE_SHA256:
        target = bad / name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(pdk / name,target)
    changed = bad / 'libs.tech/magic/ihp-sg13cmos5l-cifin.tech'
    changed.write_bytes(changed.read_bytes()+b'\n# deliberate wrong reference\n')
    bad_out = out / 'wrong-reference/should-not-exist'
    try:
        module.align(bad / 'libs.tech/magic/ihp-sg13cmos5l.tech', bad_out)
    except ValueError as error:
        assert str(error) == 'pinned contact-rule input changed: libs.tech/magic/ihp-sg13cmos5l-cifin.tech'
    else:
        raise AssertionError('changed source was accepted')
    assert not bad_out.exists()
    native = 'PASS_EXACT_CONTROL_FINDINGS_SCOPE_AND_CHANGED_REFERENCE_REJECTION'
summary = {'status':'PASS_RETAINED_CONTACT_RULE_DIAGNOSIS','files':len(index['files']),
    'original_macro_violations':32,'aligned_macro_violations':0,'contact_cases':48,
    'all_original_markers_measured':32,'native_replay':native,'full_physical_qualification':'OPEN'}
(out / 'verification.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(summary['status'], native)
