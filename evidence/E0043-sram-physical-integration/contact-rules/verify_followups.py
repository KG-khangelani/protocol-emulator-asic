# SPDX-License-Identifier: Apache-2.0
"""Check the one-hour follow-ups while rejecting missing manufacturing results."""
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
index = json.loads((HERE / 'full-layout-followups.json').read_bytes())
raw = (HERE / 'full-layout-followups.tar.gz').read_bytes()
assert sha(raw) == index['sha256'] and len(raw) == index['bytes']
with tarfile.open(HERE / 'full-layout-followups.tar.gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
    files = {m.name: archive.extractfile(m).read() for m in members if m.isfile()}
assert {n: sha(raw) for n, raw in files.items()} == index['files']
for label in ('original', 'aligned'):
    result = json.loads(files[label + '/result.json'])
    declared = json.loads(files[label + '/declared-decision.json'])
    assert result == index['outcomes'][label]
    assert result['status'] == 'INCONCLUSIVE_TIMEOUT' and result['execution']['timed_out']
    assert result['execution']['returncode'] == 124
    assert declared['wall_limit'] == result['execution']['wall_limit'] == 3600
    assert 3600 <= result['execution']['seconds'] < 3610
    assert result['gds_sha256'] == declared['gds_sha256'] == 'b2a09ed14fd1676e954e494c03e7d5d5ef74468d269a5b81bfb0ebe0c8382c3f'
    assert 'reported_count' not in result and files[label + '/reports/drc.magic.rpt'] == b''
    assert b'DIAGNOSTIC READ FINISHED' in files[label + '/run.log']
    assert b'DIAGNOSTIC FULL DRC START' in files[label + '/run.log']
    assert b'DIAGNOSTIC FULL DRC FINISHED' not in files[label + '/run.log']
assert files['original/drc-scheduled.tcl'] == files['aligned/drc-scheduled.tcl']
assert files['original/drc-original.tcl'] == files['aligned/drc-original.tcl']
assert sha(files['original/drc-original.tcl']) == '815c0ada08d55bb0b3b5c84cd80e0620590897b7f3e8e3c7c3d3f117bbe1f74b'
assert index['qualification'] == 'NO_MANUFACTURING_RESULT'
print('PASS_RETAINED_ONE_HOUR_TIMEOUTS_WITH_NO_MANUFACTURING_RESULT')
