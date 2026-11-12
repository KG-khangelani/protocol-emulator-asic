# SPDX-License-Identifier: Apache-2.0
"""Validate both archived outcomes and extract the actual OpenDB replay inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
read=lambda path:json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    out=p.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    out.mkdir(parents=True)
    for line in (HERE/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1)
        assert sha((HERE/name).read_bytes())==expected
    index=read(HERE/'archive.json')
    raw=(HERE/'power-trials.tar.gz').read_bytes()
    assert sha(raw)==index['sha256'] and len(raw)==index['bytes']
    with tarfile.open(HERE/'power-trials.tar.gz') as archive:
        members=archive.getmembers()
        assert len(members)==len(index['files']) and {m.name for m in members}==set(index['files'])
        for member in members:
            path=(out/member.name).resolve()
            assert member.isfile() and path.is_relative_to(out)
            raw=archive.extractfile(member).read()
            assert sha(raw)==index['files'][member.name]
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
    native=read(out/'native/geometry.json')
    assert native['status']=='FAIL_UNPOWERED_SRAM' and native['supply_rectangles']==native['missing_overlaps']==104
    assert all(not r['same_net_overlaps'] and not r['opposite_net_overlaps'] for r in native['observations'])
    assert native['first_vdd_column_external_shapes_dbu']==[[24775,0,26875,301920],[24775,421660,26875,710640]]
    trial=read(out/'native/run-result.json')['execution']
    assert trial['returncode']==0 and not trial['timed_out'] and trial['wall_limit']==300
    runtime=read(out/'native/runtime-observation.json')
    assert runtime['image_id']==runtime['configured_image']=='sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
    prepared=read(out/'native/preparation.json')
    assert prepared['candidate']==read(ROOT/'evidence/E0042-sram-prefetch-screen/candidate.json')
    assert {n:sha((out/'native/src'/n).read_bytes()) for n in prepared['source_sha256']}==prepared['source_sha256']
    assert sha((out/'native/src/config_merged.json').read_bytes())==prepared['config_sha256']
    state=read(out/'native/runs/native-pdn/06-yosys-synthesis/state_out.json')['metrics']
    assert state['design__instance__count']==4201 and state['design__instance__area']==53089.7598
    assert all(state[k]==0 for k in ('design__lint_error__count','design__lint_warning__count','design__lint_timing_construct__count','design__inferred_latch__count','design__instance_unmapped__count','synthesis__check_error__count'))
    result=read(out/'edge-connections/result.json')
    assert result['status']=='PASS_GEOMETRY_CONNECTIONS_GRID_CHECK_PENDING'
    assert len(result['added_rectangles'])==144 and len(result['supply_rectangles'])==104
    assert sha((out/'edge-connections/before.odb').read_bytes())==result['input_database_sha256']
    assert sha((out/'edge-connections/after.odb').read_bytes())==result['output_database_sha256']
    native_db=next((out/'native/runs/native-pdn/21-openroad-generatepdn').glob('*.odb'))
    assert sha(native_db.read_bytes())==result['input_database_sha256']
    grid=read(out/'edge-connections/gridcheck.json')
    assert grid['status']=='PASS_BOTH_POWER_GRIDS' and grid['database_sha256']==result['output_database_sha256']
    assert grid['execution']['returncode']==0 and not grid['execution']['timed_out'] and grid['execution']['wall_limit']==120
    for filename,key in [('check-grid.tcl','script_sha256'),('gridcheck.log','log_sha256')]:
        assert sha((out/'edge-connections'/filename).read_bytes())==grid[key]
    log=(out/'edge-connections/gridcheck.log').read_text()
    assert all('All shapes on net '+n+' are connected.' in log and 'PASS_SRAM_GRID '+n in log for n in ('VPWR','VGND'))
    report={'status':'PASS_RETAINED_POWER_TRIALS','files':len(index['files']),
            'native_result':'FAIL_UNPOWERED_SRAM','added_edge_connections':144,'covered_supply_rectangles':104,
            'actual_database_replay':'RUN_REPLAY_ODB_NEXT','physical_qualification':'NOT_EVALUATED'}
    (out/'archive-check.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(report))


if __name__=='__main__':
    main()
