# SPDX-License-Identifier: Apache-2.0
"""Keep initial bounded full-layout attempts explicitly incomplete."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tarfile

here=Path(__file__).resolve().parent
read=lambda raw:json.loads(raw)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
index=read((here/'full-layout-incomplete-index.json').read_bytes())
raw=(here/'full-layout-incomplete.tar.gz').read_bytes()
assert sha(raw)==index['sha256'] and len(raw)==index['bytes']
with tarfile.open(here/'full-layout-incomplete.tar.gz') as bundle:
    assert len(bundle.getmembers())==len(index['files'])
    files={m.name:bundle.extractfile(m).read() for m in bundle if m.isfile()}
assert {n:sha(v) for n,v in files.items()}==index['files']
for label in ('original','aligned'):
    review=read(files[label+'/completion-review.json'])
    assert review['status']=='INCOMPLETE_AFTER_DECLARED_BOUND_WITH_REPORTING_ERROR'
    assert sha(files[label+'/result.json'])==review['original_result_sha256']
    assert read(files[label+'/result.json'])['status']=='RUNNING_DIAGNOSTIC'
    assert not files[label+'/reports/drc.magic.rpt'] and review['report_bytes']==0
    assert b'DIAGNOSTIC FULL DRC START' in files[label+'/run.log']
    assert b'DIAGNOSTIC FULL DRC FINISHED' not in files[label+'/run.log']
    assert b'IndexError: list index out of range' in files[label+'/container.log']
    runtime=review['runtime']
    assert runtime['image_id']==runtime['configured_image']=='sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
    state=runtime['state']
    assert state['Status']=='exited' and state['ExitCode']==1
    elapsed=(datetime.fromisoformat(state['FinishedAt'])-datetime.fromisoformat(state['StartedAt'])).total_seconds()
    assert 1200<=elapsed<1210 and review['declared_bound_seconds']==1200
    declaration=read(files['followup-declarations/'+label+'/declared-decision.json'])
    assert declaration['wall_limit']==3600
    assert declaration['gds_sha256']==read(files[label+'/result.json'])['gds_sha256']=='b2a09ed14fd1676e954e494c03e7d5d5ef74468d269a5b81bfb0ebe0c8382c3f'
print('PASS_RETAINED_INCOMPLETE_FULL_DRC',len(files),'NO_MANUFACTURING_RESULT')
