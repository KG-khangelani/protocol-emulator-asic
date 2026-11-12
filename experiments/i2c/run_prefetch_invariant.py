# SPDX-License-Identifier: Apache-2.0
"""Prove that the actual prefetch port predicts the next registered PC."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from run_program_sensitivity import execute, vcd_frames

PROPERTY = """
    // Observe the unmodified engine; only the proof observer is initialized.
    reg f_prefetch_past = 1'b0;
    always @(posedge clk) begin
        f_prefetch_past <= 1'b1;
        if (f_prefetch_past)
            assert (pc == $past(prefetch_pc));
        cover (f_prefetch_past && rst_n && ena && pc != $past(pc));
    end
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_counterexample(directory):
    observations = []
    for witness in sorted((directory / 'proof/engine_0').glob('trace*.vcd')):
        raw = witness.read_bytes()
        assert raw.count(b'$scope module m1_engine $end') == 1
        parsed = directory / ('parsed-' + witness.name)
        parsed.write_bytes(raw.replace(b'$scope module m1_engine $end', b'$scope module public_spi $end'))
        rows = [row for row in vcd_frames(parsed) if row['time'] % 10 == 0]
        for before, after in zip(rows, rows[1:]):
            if after.get('f_prefetch_past') and after.get('pc') != before.get('prefetch_pc'):
                assert None not in (after.get('pc'), before.get('prefetch_pc'))
                observations.append({'edge': after['time'], 'predicted_pc': before['prefetch_pc'],
                                     'actual_pc': after['pc']})
    assert observations, 'negative control must show the actual wrong prediction'
    return observations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sources, out = args.sources.resolve(), args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    manifest = json.loads((ROOT / 'evidence/E0042-sram-prefetch-screen/candidate.json').read_bytes())
    expected = manifest['source_sha256']
    assert {name: digest(sources / name) for name in expected} == expected
    (out / 'inputs').mkdir(parents=True)
    original = (sources / 'm1_engine.v').read_text()
    assert original.count('endmodule') == 1
    (out / 'inputs/m1_engine.v').write_bytes((sources / 'm1_engine.v').read_bytes())
    (out / 'inputs' / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (out / 'inputs/property.vh').write_text(PROPERTY)
    result = {'status': 'RUNNING', 'sources': expected, 'runner_sha256': digest(Path(__file__)),
              'property_sha256': digest(out / 'inputs/property.vh'), 'tasks': [],
              'scope': 'All engine inputs arbitrary, including reset/enable/instruction. After one observed edge, the actual registered PC equals the previous prefetch output. No protocol, memory-array or physical claim.',
              'assumptions': [], 'observer_initialization': 'One proof-valid flag; no design state is initialized.'}
    save = lambda: (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    save()
    try:
        for name, mode, expected_status in [('prediction', 'prove', 'PASS'), ('moving-pc', 'cover', 'PASS'),
                                            ('wrong-low-bit', 'bmc', 'FAIL')]:
            task = out / name
            task.mkdir()
            text = original
            if mode == 'bmc':
                assert text.count('assign prefetch_pc = pc_next;') == 1
                text = text.replace('assign prefetch_pc = pc_next;', "assign prefetch_pc = pc_next ^ 8'h01;")
            text = text.replace('endmodule', PROPERTY + '\nendmodule')
            (task / 'engine.v').write_text(text)
            config = f'[options]\nmode {mode}\ndepth 8\nexpect {expected_status.lower()}\n\n[engines]\nsmtbmc z3\n\n[script]\n'
            config += 'read -formal -sv engine.v\nprep -top m1_engine\n\n[files]\n' + str(task / 'engine.v') + '\n'
            (task / 'proof.sby').write_text(config)
            stage = execute(['sby', '-f', '-d', str(task / 'proof'), str(task / 'proof.sby')], task / 'run.log', 120)
            status = (task / 'proof/status').read_text().split()[0] if (task / 'proof/status').exists() else 'MISSING'
            log = (task / 'run.log').read_text()
            witnesses = {p.relative_to(task).as_posix(): digest(p) for p in (task / 'proof/engine_0').glob('trace*.vcd')}
            accepted = stage['returncode'] == 0 and not stage['timed_out'] and status == expected_status
            if mode == 'prove':
                accepted &= 'successful proof by k-induction' in log
            else:
                accepted &= bool(witnesses)
            item = {'name': name, 'mode': mode, 'expected': expected_status, 'status': status,
                    'execution': stage, 'accepted': accepted, 'engine_sha256': digest(task / 'engine.v'),
                    'witnesses': witnesses}
            result['tasks'].append(item)
            save()
            assert accepted, (name, status)
            if mode == 'bmc':
                item['counterexample'] = inspect_counterexample(task)
            model = json.loads((task / 'proof/model/design.json').read_bytes())['modules']
            assert len(model) == 1
            checks = [c for sort in model[0]['cell_sorts'] if sort['type'] == '$check' for c in sort['cells']]
            assert [c['parameters']['FLAVOR'] for c in checks].count('assert') == 1
            assert [c['parameters']['FLAVOR'] for c in checks].count('assume') == 0
            assert [c['parameters']['FLAVOR'] for c in checks].count('cover') == 1
        assert {name: digest(sources / name) for name in expected} == expected
        result['status'] = 'PASS_PREFETCH_PREDICTION_INVARIANT_AND_ACTUAL_COUNTEREXAMPLE'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'])


if __name__ == '__main__':
    main()
