# SPDX-License-Identifier: Apache-2.0
"""Run the product cold loader against the archived G3/G5 cases and handoff controls."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
COUNCIL = ROOT / 'evidence/E0049-review-council/powered-netlist'
sys.path[:0] = [str(COUNCIL), str(ROOT)]
from cross_release import WAVE_GROUPS, compare_g5
from run import G4, archive_member, library_hashes
from experiments.waveform_replay.run import build as build_waveforms
from tools.assembler import json_bytes
from tools.cold_load import digest, fresh_directory, prepare_models, simulate
from tools.current_profile import verification_inputs
from tools.production_sram import verify
from tools.program_examples import build
from tools.run_program_examples import GROUPS, audit_records


def qualify(output, simulator, pdk):
    if Path.cwd().resolve() != ROOT:
        raise ValueError('run from the repository root')
    output = fresh_directory(output)
    result = {'status': 'INCOMPLETE', 'backend': simulator, 'model': 'submitted netlist' if pdk else 'RTL',
              'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()}
    try:
        production = verify(ROOT)
        inputs = verification_inputs()
        for extra in (Path(__file__).resolve(), COUNCIL / 'run.py', COUNCIL / 'cross_release.py'):
            inputs[extra.relative_to(ROOT).as_posix()] = digest(extra)
        manifest = output / 'inputs.json'
        manifest.write_bytes(json_bytes(inputs))
        result['inputs_sha256'] = digest(manifest)
        result['input_files'] = len(inputs)
        result['physical_inputs'] = len(production['files_sha256'])
        result['production_profile_sha256'] = production['profile_sha256']
        models = prepare_models(output, production)
        netlist = None
        if pdk:
            for rel, expected in library_hashes().items():
                if digest(pdk / rel) != expected:
                    raise ValueError('PDK model differs: ' + rel)
            netlist = output / 'submitted.v'
            netlist.write_bytes(archive_member(G4 / 'ci-43543626249', 14094673928,
                                               'tt_submission/tt_um_khangelani_protocol_emulator.v'))
            result['netlist_sha256'] = digest(netlist)
            for run_id in (43543626249, 43543629839):
                recorded = json.loads((G4 / f'ci-{run_id}/result.json').read_bytes())
                if recorded['netlist_sha256'] != result['netlist_sha256']:
                    raise ValueError('submitted netlist identity differs')
        g3_dir = output / 'g3-images'
        g5_dir = output / 'g5-images'
        build(g3_dir)
        build_waveforms(g5_dir)
        reference = G4 / 'program-tools'
        for path in (g3_dir / 'uart_rx').iterdir():
            if path.read_bytes() != archive_member(reference, 14094030144, 'examples/uart_rx/' + path.name):
                raise ValueError('UART receiver release artifact differs: ' + path.name)
        stage_env = dict(COLD_LOAD_OUT=str(output), G3_PROGRAM_BUILD=str(g3_dir),
                         G3_PROGRAM_RECORDS=str(output / 'g3-records'), G5_PROGRAM_BUILD=str(g5_dir),
                         G5_RECORDS=str(output / 'g5-records'))
        tests = GROUPS | WAVE_GROUPS | {'adverse_handoffs'}
        result['command'] = simulate(output, simulator, 'qualification_cases,test_program_examples_public,'
                                     'test_waveform_replay_public', tests, models, stage_env, netlist=netlist, pdk=pdk)
        actual = audit_records(output / 'g3-records')
        reference_bytes = archive_member(reference, 14094030144, simulator + '/records/records.jsonl')
        archived = sorted(map(json.loads, reference_bytes.splitlines()), key=lambda r: r['name'])
        if actual != archived:
            raise ValueError('G3 public record mismatch: ' + str([r['name'] for r in actual if r not in archived]))
        result['g3'] = {'cases': len(actual), 'observations': sum(row['observations'] for row in actual),
                        'expected_rejections': sum(not row['expected_acceptance'] for row in actual),
                        'archive_records_sha256': hashlib.sha256(reference_bytes).hexdigest()}
        result['g5'] = compare_g5(output / 'g5-records')
        result['controls'] = json.loads((output / 'controls.json').read_bytes())
        result['junit_sha256'] = digest(output / 'results.xml')
        if any(digest(ROOT / name) != expected for name, expected in inputs.items()):
            raise RuntimeError('an input changed during qualification')
        result['status'] = 'PASS'
    except Exception as error:
        result.update(status='FAILED', error=str(error))
        raise
    finally:
        (output / 'qualification.json').write_bytes(json_bytes(result))
    print(f"PASS {simulator} {result['model']}: {len(actual)} G3, {result['g5']['cases']} G5, four rejected handoffs and a clean retry")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=('icarus', 'verilator'), default='icarus')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pdk', type=Path, help='use the submitted netlist and this pinned PDK model tree')
    args = parser.parse_args()
    if args.pdk and args.backend != 'icarus':
        parser.error('the submitted-netlist reference uses Icarus')
    qualify(args.out, args.backend, args.pdk.resolve() if args.pdk else None)
