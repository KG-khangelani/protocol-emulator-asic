# SPDX-License-Identifier: Apache-2.0
"""Replay final public-netlist acceptance without erasing the pin rejection."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(PRIOR))
from sram_official_frozen_support import load

read = lambda p: json.loads(p.read_bytes())
sha = lambda b: hashlib.sha256(b).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
out = args.output.resolve()
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
for directory in (HERE, PRIOR):
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert sha((directory / name).read_bytes()) == expected, name
out.mkdir(parents=True)
run, jobs = read(HERE / 'run.json'), read(HERE / 'jobs.json')['jobs']
assert run['id'] == 43337581691 and run['head_sha'] == '232ee20e1eb35726f785225ecfc1a2641e10af33'
assert run['status'] == 'completed' and run['conclusion'] == 'failure'
assert run['path'] == '.github/workflows/gds-sram.yaml'
assert len(jobs) == 3 and {j['name'] for j in jobs} == {'gds', 'precheck', 'gl_test'}
assert all(j['status'] == 'completed' and j['run_id'] == run['id'] and j['head_sha'] == run['head_sha'] for j in jobs)
jobs = {j['name']: j for j in jobs}
assert {n:j['conclusion'] for n,j in jobs.items()} == {'gds':'success', 'precheck':'failure', 'gl_test':'success'}
producer = load(run['head_sha'], out / 'producer')
rejected = False
try:
    producer.audit.require_finished(run, list(jobs.values()))
except (AssertionError, ValueError, RuntimeError, SystemExit):
    rejected = True
assert rejected, 'failed complete run must not qualify'
metadata = read(HERE / 'artifacts.json')['artifacts']
indexed = read(HERE / 'zip-files.json')
archives = {}
for a in metadata:
    if a['name'] not in indexed:
        continue
    path = HERE / (str(a['id']) + '.zip')
    assert path.stat().st_size == a['size_in_bytes'] and 'sha256:' + sha(path.read_bytes()) == a['digest']
    z = zipfile.ZipFile(path)
    assert indexed[a['name']] == {n: sha(z.read(n)) for n in z.namelist() if not n.endswith('/')}
    archives[a['name']] = z
assert set(archives) == {'sram-netlist-check', 'gatelevel_test_results'}
submission = next(a for a in metadata if a['name'] == 'tt_submission')
assert submission['digest'] == 'sha256:' + sha((PRIOR / (str(submission['id']) + '.zip')).read_bytes())
log = gzip.decompress((HERE / 'gl_test-job.log.gz').read_bytes())
consumer = producer.runtime.inspect_consumed_artifact(log, submission, producer.common.candidate_lock(), jobs['gl_test']['id'], 'gl_test')
with zipfile.ZipFile(PRIOR / (str(submission['id']) + '.zip')) as z:
    netlist = z.read('tt_submission/tt_um_khangelani_protocol_emulator.v')
assert sha(netlist) == read(PRIOR / 'physical-review.json')['netlist_sha256']
staged = next(a for a in metadata if a['name'] == 'sram-physical-candidate')
with zipfile.ZipFile(PRIOR / (str(staged['id']) + '.zip')) as z:
    original_inputs = json.loads(z.read('build/sram-physical/inputs.json'))
netcheck, tests = archives['sram-netlist-check'], archives['gatelevel_test_results']
inputs = json.loads(netcheck.read('build/sram-physical/inputs.json'))
assert {k:v for k,v in inputs.items() if k != 'created_utc'} == {k:v for k,v in original_inputs.items() if k != 'created_utc'}
checked = json.loads(netcheck.read('test/output/physical-result.json'))
assert checked['status'] == 'PASS' and checked['variant'] == 'od128-sram'
assert checked['evidence_kind'] == 'FUNCTIONAL_ZERO_DELAY_NETLIST' and checked['netlist_sha256'] == sha(netlist)
assert checked['source_sha256'] == inputs['candidate']['source_sha256'] and checked['model_sha256'] == inputs['candidate']['model_sha256']
(out / 'results.xml').write_bytes(tests.read('results.xml'))
for name in ('spi/cases.jsonl', 'i2c/cases.jsonl', 'i2c/boundaries.jsonl', 'i2c/aborts.jsonl'):
    p = out / 'records' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(tests.read('output/' + name))
producer.physical_g2.check_tests(SimpleNamespace(junit=out/'results.xml', records=out/'records', output=out/'public-audit.json', require_netlist=False))
observed = read(out / 'public-audit.json')
for key in ('public_test_groups', 'excluded_discovered_tests', 'records', 'junit_sha256'):
    assert checked[key] == observed[key], key
result = {'status': 'PASS_FINAL_NETLIST_TESTS_WITH_PHYSICAL_REJECTION_PRESERVED',
    'run_id': run['id'], 'source_commit': run['head_sha'], 'jobs': {n:j['conclusion'] for n,j in jobs.items()},
    'physical_qualification': 'REJECTED_POWER_PORT_PRECHECK', 'aggregate_rejection_checked': rejected,
    'netlist_sha256': sha(netlist), 'consumer': consumer, 'public_checks': checked,
    'additional_original_archive_files': sum(map(len, indexed.values())),
    'scope': 'All eighteen public groups pass on the actual submitted netlist. Earlier nine-of-ten precheck and its 148 pin errors are unchanged; no production promotion.'}
(out / 'verification.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
for z in archives.values():
    z.close()
print(result['status'], result['additional_original_archive_files'])
