# SPDX-License-Identifier: Apache-2.0
"""Replay the two mapped netlists, exact inputs and fixed-condition comparison."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(p.read_bytes())


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, str):
        value = value.replace('/home/runner/work/protocol-emulator-asic/protocol-emulator-asic', '<design>')
        for label in ('gold', 'gate'):
            value = value.replace('/workspace/build/g2-banked-mapped-01/' + label, '<design>')
        for prefix in ('/home/runner/.ciel', '/pdk'):
            value = value.replace(prefix + '/ciel/ihp-sg13/versions/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008', '<pdk>')
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    out.mkdir(parents=True)
    for line in (HERE.parent / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert sha((HERE.parent / name).read_bytes()) == expected
    index = read(HERE / 'archive.json')
    archive_path = HERE / 'mapping.tar.gz'
    assert sha(archive_path.read_bytes()) == index['sha256']
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
        for member in members:
            path = (out / member.name).resolve()
            assert member.isfile() and path.is_relative_to(out)
            raw = archive.extractfile(member).read()
            assert sha(raw) == index['files'][member.name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    report, run = read(HERE / 'verification.json'), read(out / 'result.json')
    assert report['status'] == 'PASS_MATCHED_MAPPED_COST_SCREEN'
    assert run['status'] == 'MAPPING_COMMANDS_SUCCEEDED_REQUIRES_AUDIT'
    assert run['runner_sha256'] == sha((out / 'inputs/run_g2_banked_mapping.py').read_bytes())
    assert run['spec_sha256'] == sha((out / 'inputs/g2-banked-mapped-screen.md').read_bytes())
    assert read(out / 'image-inspect.json')[0]['Id'] == report['runtime_image_id'] == 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
    profiles = read(HERE.parent / 'result.json')['sources']
    configs = {}
    for label, count, area in (('gold', 34683, 477788.2578), ('gate', 32160, 502643.5722)):
        job = run['runs'][label]
        assert job['returncode'] == 0 and job['timed_out'] is False and job['wall_limit_seconds'] == 300
        assert job['command'][job['command'].index('--to')+1] == 'Yosys.Synthesis'
        assert job['sources'] == profiles[label]
        assert {n: sha((out / label / 'src' / n).read_bytes()) for n in job['sources']} == profiles[label]
        configs[label] = normalize(read(out / label / 'runs/mapped-screen/resolved.json'))
        step = out / label / 'runs/mapped-screen/06-yosys-synthesis'
        measured = report['measurements'][label]
        metrics = read(step / 'state_out.json')['metrics']
        assert metrics == measured['metrics'] and metrics['design__instance__count'] == count and metrics['design__instance__area'] == area
        for key in ('design__inferred_latch__count', 'design__instance_unmapped__count', 'synthesis__check_error__count', 'design__lint_error__count'):
            assert metrics[key] == 0
        cells = read(step / 'tt_um_khangelani_protocol_emulator.nl.v.json')['modules']['tt_um_khangelani_protocol_emulator']['cells']
        counts = Counter(c['type'] for c in cells.values())
        assert dict(counts) == measured['cell_types'] and sum(counts.values()) == count
        assert counts['sg13cmos5l_dfrbpq_1'] == measured['sequential_cells'] == 4278
        assert sha((step / 'tt_um_khangelani_protocol_emulator.nl.v').read_bytes()) == measured['netlist_sha256']
        log = (step / 'yosys-synthesis.log').read_text()
        assert float(re.findall(r'of which used for sequential elements: ([\d.]+)', log)[-1]) == measured['sequential_area_um2'] == 209574.0864
        assert float(re.findall(r'Chip area for module .*?: ([\d.]+)', log)[-1]) == area
        assert 'Yosys 0.69' in log and '9f75ca1f9834a39a863915b5dae0c7b1e33533bc' in log
    assert configs['gold'] == configs['gate']
    original = normalize(read(out / 'inputs/original-d39-resolved.json'))
    diff = {k: [original.get(k), configs['gold'].get(k)] for k in set(original)|set(configs['gold'])
            if original.get(k) != configs['gold'].get(k)}
    assert set(diff) == {'OPENROAD_THREADS', 'FP_DEF_TEMPLATE', 'DESIGN_DIR'}, sorted(diff)
    assert diff['OPENROAD_THREADS'] == [None, 4] and diff['DESIGN_DIR'] == ['<design>/src', '<design>']
    result = {'status': 'PASS_RETAINED_MATCHED_MAPPING', 'files': len(index['files']),
              'mapped_area_change_percent': (502643.5722/477788.2578-1)*100,
              'configuration_differences_from_original_after_path_relocation': diff,
              'routed_or_timing_qualification': 'NOT_EVALUATED'}
    (out / 'verification.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(result))


if __name__ == '__main__':
    main()
