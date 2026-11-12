# SPDX-License-Identifier: Apache-2.0
"""Keep the timed-out diagnostic distinct from a physical result."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda path: json.loads(path.read_bytes())
for line in (HERE / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert sha((HERE / name).read_bytes()) == expected, name
result = read(HERE / 'attempt-1200s/result.json')
summary = read(HERE / 'verification.json')
assert result['status'] == 'FAILED_OR_INCOMPLETE' and result['returncode'] == 124 and result['timed_out'] is True
assert result['wall_limit_seconds'] == 1200 and len(result['removed_ndr_nets']) == 16
assert summary['status'] == 'INCOMPLETE_CLOCK_NDR_ABLATION' and summary['qualification'] == 'NOT_QUALIFIED'
assert summary['source_odb_sha256'] == result['source_odb_sha256']
assert result['runner_sha256'] == sha((HERE / 'attempt-1200s/runner.py').read_bytes())
assert result['spec_sha256'] == sha((HERE / 'attempt-1200s/spec-at-start.md').read_bytes())
before, after = (gzip.decompress((HERE / 'attempt-1200s' / n).read_bytes()) for n in ('before.def.gz', 'after.def.gz'))
marker = b' + NONDEFAULTRULE CTS_NDR_0'
assert before.count(marker) == 16 and before.replace(marker, b'') == after
assert sha(before) == summary['before_def_sha256'] and sha(after) == summary['after_def_sha256']
audit = read(HERE / 'attempt-1200s/input-audit.json')
assert audit['status'] == 'PASS_ISOLATED_ROUTING_INPUTS'
assert audit['original_def_sha256'] == sha(before) and audit['ablated_def_sha256'] == sha(after)
log = gzip.decompress((HERE / 'attempt-1200s/run.log.gz').read_bytes())
assert b'Start extra iteration 40/50' in log and b'Final congestion report' not in log
assert 'openroad -exit -threads 4' in (HERE / 'attempt-1200s/COMMANDS').read_text()
assert json.loads(gzip.decompress((HERE / 'runtime-image.json.gz').read_bytes()))[0]['Id'] == 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
for name, source in read(HERE / 'upstream/sources.json').items():
    raw = gzip.decompress((HERE / 'upstream' / (name+'.gz')).read_bytes())
    assert sha(raw) == source['sha256'] and len(raw) == source['bytes']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == source['git_blob']
    assert 'dcf36133a369abc8f3c5e5738cd4d82e4903c0e0' in source['url']
print('PASS: exact NDR-only edit and retained 1200-second timeout; NOT_QUALIFIED')
