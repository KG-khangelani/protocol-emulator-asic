# SPDX-License-Identifier: Apache-2.0
"""Audit both bounded diagnostics without treating command success as qualification."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile

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

follow = HERE / 'attempt-2400s'
index = read(follow / 'archive.json')
packed = (follow / 'routing.tar.gz').read_bytes()
assert len(packed) == index['bytes'] and sha(packed) == index['sha256']
small = {}
with tarfile.open(follow / 'routing.tar.gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        raw = archive.extractfile(member).read()
        assert sha(raw) == index['files'][member.name]
        if member.size < 100000:
            small[member.name] = raw
get = lambda name: json.loads(small[name])
completed = get('ablation-result.json')
assert completed['returncode'] == 0 and completed['timed_out'] is False and completed['wall_limit_seconds'] == 2400
assert completed['source_odb_sha256'] == result['source_odb_sha256']
assert completed['modified_odb_sha256'] == result['modified_odb_sha256']
assert completed['removed_ndr_nets'] == result['removed_ndr_nets']
assert completed['runner_sha256'] == sha(small['run_ablation.py'])
assert completed['spec_sha256'] == sha(small['spec-at-start.md'])
assert get('input-audit.json')['original_def_sha256'] == sha(before)
assert get('input-audit.json')['ablated_def_sha256'] == sha(after)
resolved = get('runs/no-clock-ndr/resolved.json')
prior = json.loads((HERE / 'attempt-1200s/resolved.json').read_text().replace('diagnostic-02', 'diagnostic-03'))
assert resolved == prior
assert resolved['GRT_ALLOW_CONGESTION'] is True and resolved['GRT_OVERFLOW_ITERS'] == 50
step = 'runs/no-clock-ndr/01-openroad-globalrouting/'
assert 'openroad -exit -threads 4' in small[step+'COMMANDS'].decode()
log = small[step+'openroad-globalrouting.log'].decode()
assert 'Start extra iteration 50/50' in log and '[WARNING GRT-0115]' in log and '[ERROR GRT-0228]' not in log
rows = {}
for name,resource,demand,usage,h,v,total in re.findall(
        r'^(Metal[1-4]|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)$',log,re.M):
    rows[name] = dict(resource=int(resource),demand=int(demand),usage_percent=float(usage),
                      max_horizontal_overflow=int(h),max_vertical_overflow=int(v),total_overflow=int(total))
report = read(follow / 'verification.json')
assert report['status'] == 'COMPLETED_WITH_CONGESTION_NOT_QUALIFIED' and report['qualification'] == 'NOT_QUALIFIED'
assert report['decision'] == 'STOP_CLOCK_SPACING_ONLY_BRANCH'
assert report['final_congestion'] == rows and rows['Total']['total_overflow'] == 159781
assert rows['Metal3']['usage_percent'] == 152.09
assert get(step+'state_out.json')['metrics']['global_route__wirelength'] == report['global_wirelength_um'] == 6613869
assert get(step+'state_out.json')['metrics']['global_route__vias'] == report['global_vias'] == 387200
print('PASS: completed follow-up retains 159781 overflow and unchanged settings; NOT_QUALIFIED')
