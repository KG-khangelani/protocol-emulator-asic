# SPDX-License-Identifier: Apache-2.0
"""Audit the explicit integrated power stages and their actual file bindings."""
import argparse
import json
from pathlib import Path

from sram_prefetch import ROOT, digest

read = lambda path: json.loads(path.read_bytes())


def audit(base):
    run = base / 'runs/integrated'
    preparation = read(base / 'preparation.json')
    execution = read(base / 'run-result.json')
    assert execution['status'] == 'COMMAND_SUCCEEDED_REQUIRES_ARTIFACT_AUDIT'
    assert execution['mode'] == 'power-pilot'
    assert execution['execution']['wall_limit'] == 300
    assert execution['execution']['returncode'] == 0 and not execution['execution']['timed_out']
    runtime = read(base / 'runtime-observation.json')
    assert runtime['image_id'] == 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
    assert len(runtime['pdk_volume_mounts']) == 1
    assert runtime['pdk_volume_mounts'][0]['Name'] == 'protocol-emulator-g1-pdk-89d42ee6'
    assert not runtime['pdk_volume_mounts'][0]['RW']
    for name, sha in preparation['plugin_sha256'].items():
        assert digest((base / name).read_bytes()) == sha
    for name, sha in preparation['source_sha256'].items():
        assert digest((base / 'src' / name).read_bytes()) == sha
    assert digest((base / 'src/config_merged.json').read_bytes()) == preparation['config_sha256']
    native = read(run / '21-openroad-generatepdn/state_out.json')
    geometry = read(run / '23-project-connectsrampower/power-connections.json')
    assert geometry['status'] == 'PASS_GEOMETRY_CONNECTIONS_GRID_CHECK_PENDING'
    assert len(geometry['added_rectangles']) == 144 and len(geometry['supply_rectangles']) == 104
    assert geometry['preparation_sha256'] == digest((base / 'preparation.json').read_bytes())
    connected = read(run / '23-project-connectsrampower/state_out.json')
    checked = read(run / '24-project-checksrampower/state_out.json')
    source = read(run / '23-project-connectsrampower/state_in.json')
    check_in = read(run / '24-project-checksrampower/state_in.json')
    assert source['odb'] == read(run / '22-odb-removepdnobstructions/state_out.json')['odb']
    def local(path):
        command = execution['execution']['command']
        prefix = command[command.index('--design-dir') + 1] + '/'
        assert path.startswith(prefix)
        target = (base / path[len(prefix):]).resolve()
        assert target.is_relative_to(base.resolve())
        return target
    assert digest(local(source['odb']).read_bytes()) == geometry['input_odb_sha256']
    assert check_in['odb'] == connected['odb']
    metrics = checked['metrics']
    for suffix in ('', '__net:VPWR', '__net:VGND'):
        key = 'design__power_grid_violation__count' + suffix
        assert native['metrics'][key] > 0 and metrics[key] == 0
    log = (run / '24-project-checksrampower/project-checksrampower.log').read_text()
    for net in ('VPWR', 'VGND'):
        assert f'All shapes on net {net} are connected.' in log and f'PASS_SRAM_GRID {net}' in log
    assert '[ERROR' not in log and '[WARNING' not in log
    assert metrics['design__instance__count__class:macro'] == 1
    result = {'status': 'PASS_INTEGRATED_SRAM_POWER_PILOT', 'seconds': execution['execution']['seconds'],
              'added_rectangles': 144, 'supply_rectangles': 104,
              'native_violations': native['metrics']['design__power_grid_violation__count'],
              'fresh_violations': 0, 'output_odb_sha256': digest(local(checked['odb']).read_bytes()),
              'physical_qualification': 'NOT_EVALUATED'}
    (base / 'verification.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps(result))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--directory', required=True, type=Path)
    audit(p.parse_args().directory.resolve())
