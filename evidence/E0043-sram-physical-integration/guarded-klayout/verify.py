# SPDX-License-Identifier: Apache-2.0
"""Audit the complete KLayout diagnostic and its original precheck command."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from types import SimpleNamespace
import xml.etree.ElementTree as ET

here = Path(__file__).resolve().parent
root = here.parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--native', action='store_true')
args = parser.parse_args()
out = args.output.resolve()
assert not out.exists() and out.is_relative_to(root / 'build')
out.mkdir()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(p.read_bytes())
result = read(here / 'result.json')
assert result['status'] == 'PASS_SCOPED_KLAYOUT_RULE_DECK' and result['violations'] == 0 and not result['categories']
assert result['execution']['returncode'] == 0 and not result['execution']['timed_out']
assert result['execution']['seconds'] < result['execution']['wall_limit'] == 900
assert result['full_physical_qualification'] == 'OPEN'
for name in ('runner.py', 'precheck-reference.py', 'run.log', 'drc.xml'):
    (out / name).write_bytes(gzip.decompress((here / (name + '.gz')).read_bytes()))
assert sha((out / 'drc.xml').read_bytes()) == result['report_sha256']
reference = (out / 'precheck-reference.py').read_bytes()
assert sha(reference) == result['precheck_source_sha256']
identity = read(here / 'source-reference.json')
assert sha(reference) == identity['retained_reference_sha256']
assert reference.endswith(b'\n\n') and sha(reference[:-1]) == identity['primary_source_sha256']
runtime = read(here / 'runtime.json')
assert runtime['image_id'] == runtime['configured_image'] == 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
assert runtime['state']['Status'] == 'exited' and runtime['state']['ExitCode'] == 0
assert any(m['Destination'] == '/pdk' and not m['RW'] for m in runtime['mounts'])
database = ET.parse(out / 'drc.xml').getroot()
assert database.tag == 'report-database' and database.find('items') is not None
assert len(database.find('items')) == 0 and len(database.find('categories')) == 332
assert [c.findtext('name') for c in database.findall('./cells/cell')] == ['tt_um_khangelani_protocol_emulator']
log = (out / 'run.log').read_text(encoding='utf-8')
assert "KLayout DRC run for tables 'main' completed" in log
assert 'Executing rule CMOS5L.FORB.Vmim' in log
command = result['execution']['command']
deck = Path(command[3])
gds_argument = next(v for v in command if v.startswith('input=')).removeprefix('input=')
original_report = next(v for v in command if v.startswith('report=')).removeprefix('report=')
calls = []
scope = {'PDK_ROOT': command[3].split('/ihp-sg13cmos5l/')[0], 'PDK_NAME': 'ihp-sg13cmos5l',
    'REPORTS_PATH': '/audit', 'logging': SimpleNamespace(info=lambda *a: None),
    'subprocess': SimpleNamespace(run=lambda c: (calls.append(c), SimpleNamespace(returncode=0))[1]),
    'check_drc_report': lambda *a: None}
names = {'klayout_sg13cmos5l', 'klayout_drc', 'klayout_custom_drc'}
nodes = [n for n in ast.parse(reference).body if isinstance(n, ast.FunctionDef) and n.name in names]
assert len(nodes) == 3
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'pinned-precheck-functions', 'exec'), scope)
scope['klayout_sg13cmos5l'](gds_argument)
assert calls == [[part.replace(original_report, '/audit/drc_sg13cmos5l.xml') for part in command]]
layout_archive = here.parent / 'guarded-lvs/diagnostic.tar.gz'
archive_index = read(here.parent / 'guarded-lvs/archive.json')
assert sha(layout_archive.read_bytes()) == archive_index['sha256']
member = 'passed/run/final/gds/tt_um_khangelani_protocol_emulator.gds'
with tarfile.open(layout_archive) as bundle:
    gds = bundle.extractfile(member).read()
assert sha(gds) == archive_index['files'][member] == result['gds_sha256']
(out / 'tt_um_khangelani_protocol_emulator.gds').write_bytes(gds)
if args.native:
    import klayout.rdb as rdb
    assert subprocess.check_output(['klayout', '-v'], text=True).strip() == result['klayout_version']
    for name, expected in result['rule_files'].items():
        assert sha((deck.parent / name).read_bytes()) == expected
    native = rdb.ReportDatabase('DRC')
    native.load(str(out / 'drc.xml'))
    assert native.num_items() == 0
summary = {'status': 'PASS_RETAINED_KLAYOUT_DIAGNOSTIC', 'rule_categories': 332, 'violations': 0,
    'gds_sha256': result['gds_sha256'], 'seconds': result['execution']['seconds'],
    'original_precheck_command': 'PASS_EXACT_ARGUMENTS_EXCEPT_OUTPUT_PATHS',
    'native_report_reader_and_pinned_rule_hashes': 'PASS' if args.native else 'NOT_REPEATED',
    'full_physical_qualification': 'OPEN'}
(out / 'verification.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode())
print(summary['status'], summary['violations'])
