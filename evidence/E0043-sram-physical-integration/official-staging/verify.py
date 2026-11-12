# SPDX-License-Identifier: Apache-2.0
"""Verify retained portable configuration, native grid result and controls."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
read = lambda path: json.loads(path.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    index = read(HERE / 'archive.json')
    packed = (HERE / 'staging.tar.gz').read_bytes()
    assert len(packed) == index['bytes'] and sha(packed) == index['sha256']
    with tarfile.open(HERE / 'staging.tar.gz') as archive:
        members = archive.getmembers()
        assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
        for member in members:
            target = (out / member.name).resolve()
            assert member.isfile() and target.is_relative_to(out)
            raw = archive.extractfile(member).read()
            assert sha(raw) == index['files'][member.name]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    base = out / 'pilot'
    inputs = read(base / 'inputs.json')
    assert inputs['candidate'] == read(ROOT / 'evidence/E0042-sram-prefetch-screen/candidate.json')
    for name, expected in inputs['staged_sha256'].items():
        assert sha((base / 'workspace' / name).read_bytes()) == expected
    for name, expected in inputs['provenance_sha256'].items():
        assert sha((base / 'inputs' / name).read_bytes()) == expected
    result = read(base / 'pilot-verification.json')
    assert result == read(HERE / 'verification.json')
    assert result['status'] == 'PASS_PORTABLE_STAGING_POWER_AND_SIX_RESOLVED_CORRUPTION_CONTROLS'
    assert result['execution']['returncode'] == 0 and not result['execution']['timed_out']
    assert result['execution']['seconds'] < result['execution']['wall_limit'] == 300
    assert sha((out / 'current-inputs/tools/physical_sram.py').read_bytes()) == result['gate_sha256']
    assert sha((base / 'inputs/audit_sram_official_staging.py').read_bytes()) == result['audit_sha256']
    assert len(result['controls']) == 6 and len({c['fault'] for c in result['controls']}) == 6
    assert all(c['observed_rejection'] for c in result['controls'])
    runtime = read(base / 'runtime-observation.json')
    expected_image = 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
    assert runtime['image_id'] == runtime['configured_image'] == expected_image
    assert runtime['state'] == 'exited' and runtime['exit_code'] == 0
    assert any(m['Destination'] == '/pdk' and not m['RW'] for m in runtime['mounts'])
    run = base / 'workspace/runs/portable-pilot'
    state = read(run / '24-project-checksrampower/state_out.json')
    for suffix in ('', '__net:VPWR', '__net:VGND'):
        assert state['metrics']['design__power_grid_violation__count' + suffix] == 0
    odb = run / '24-project-checksrampower/tt_um_khangelani_protocol_emulator.odb'
    assert sha(odb.read_bytes()) == result['final_odb_sha256'] == 'db9b16aa65fb52722a7de25efe81aacc2e6a4ddf7c9634ef1a5e3f8ccc916995'
    power = read(run / '23-project-connectsrampower/power-connections.json')
    assert len(power['added_rectangles']) == 144
    assert power['preparation_sha256'] == sha((base / 'workspace/src/sram-preparation.json').read_bytes())
    # The first portable pilot used sorted geometry keys. It added the same
    # physical wires, but in the reverse net order; retain that failed byte audit.
    old = read(out / 'initial/workspace/runs/portable-pilot/23-project-connectsrampower/power-connections.json')
    assert old['input_odb_sha256'] == power['input_odb_sha256']
    assert old['logical_identity_before_and_after'] == power['logical_identity_before_and_after']
    assert sorted(old['added_rectangles'], key=str) == sorted(power['added_rectangles'], key=str)
    assert old['added_rectangles'] != power['added_rectangles']
    for filename, code in (('pilot-execution.json', 2), ('pilot-execution-02.json', 1), ('pilot-execution-03.json', 2)):
        assert read(out / 'initial' / filename)['returncode'] == code
    log = (out / 'repo-check.log').read_text()
    assert 'RESULT: PASS' in log and 'FAILED' not in log
    assert sum(map(int, re.findall(r'Ran (\d+) tests?', log))) == 114
    metrics = read(out / 'reference/post-pnr/state_out.json')['metrics']
    corners = ('nom_fast_1p32V_m40C', 'nom_slow_1p08V_125C', 'nom_typ_1p20V_25C')
    for corner in corners:
        for kind in ('slew', 'cap', 'fanout'):
            assert metrics[f'design__max_{kind}_violation__count__corner:{corner}'] == 0
        for kind in ('setup', 'hold'):
            assert metrics[f'timing__{kind}__ws__corner:{corner}'] > 0
    assert metrics['route__drc_errors'] == metrics['antenna__violating__nets'] == 0
    print('PASS_RETAINED_PORTABLE_SRAM_STAGING_AND_ROUTED_STAGE_SNAPSHOT', len(members))


if __name__ == '__main__':
    main()
