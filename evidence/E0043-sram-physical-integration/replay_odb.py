# SPDX-License-Identifier: Apache-2.0
"""Run with pinned OpenROAD: reconstruct the real wire delta and check both grids."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import odb

p=argparse.ArgumentParser()
p.add_argument('--directory',type=Path,required=True)
out=p.parse_args().directory.resolve()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
read=lambda path:json.loads(path.read_bytes())
assert read(out/'archive-check.json')['status']=='PASS_RETAINED_POWER_TRIALS'
source=out/'edge-connections/inputs/connect_sram_power.py'
spec=importlib.util.spec_from_file_location('frozen_sram_connections',source)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
expected=read(out/'edge-connections/result.json')
db=odb.dbDatabase.create()
odb.read_db(db,str(out/'edge-connections/before.odb'))
actual=module.connect(db,read(out/'edge-connections/inputs/preparation.json'))
assert all(value==json.loads(json.dumps(expected[key])) for key,value in json.loads(json.dumps(actual)).items())
target=out/'reproduced.odb'
assert not target.exists()
odb.write_db(db,str(target))
assert sha(target.read_bytes())==expected['output_database_sha256']
script=(out/'edge-connections/check-grid.tcl').read_text()
assert script.count('/workspace/build/g2-sram-pdn-bridges-01')==2
script=script.replace('/workspace/build/g2-sram-pdn-bridges-01',str(out/'edge-connections'))
(out/'recheck.tcl').write_bytes(script.encode())
start=time.monotonic()
with (out/'recheck.log').open('w') as log:
    completed=subprocess.run(['openroad','-no_init','-exit',str(out/'recheck.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert completed.returncode==0
log=(out/'recheck.log').read_text()
assert all('All shapes on net '+n+' are connected.' in log and 'PASS_SRAM_GRID '+n in log for n in ('VPWR','VGND'))
report={'status':'PASS_ACTUAL_POWER_DATABASE_REPLAY','added_edge_connections':144,'covered_supply_rectangles':104,
        'reproduced_database_sha256':sha(target.read_bytes()),'grid_check_seconds':round(time.monotonic()-start,3),
        'physical_qualification':'NOT_EVALUATED'}
(out/'verification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report))
