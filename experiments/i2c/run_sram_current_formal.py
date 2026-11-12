# SPDX-License-Identifier: Apache-2.0
"""Bind SRAM composition, prediction, instruction and support proofs to real sources."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from current_profile import describe, digest
from current_sram import materialize_candidate
from run_program_sensitivity import execute


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sources, out = args.sources.resolve(), args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    profile = describe(sources)
    assert profile['profile'] == 'od128-sram'
    candidate = out / 'candidate'
    manifest = materialize_candidate(sources, candidate)
    (out / 'inputs').mkdir()
    for name in ('experiments/i2c/run_sram_current_formal.py', 'experiments/i2c/run_sram_store_controls.py',
                 'test/sram_program_store.sv'):
        target = out / 'inputs' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    result = {'status': 'RUNNING', 'source_directory': str(sources), 'sources': profile['source_sha256'],
              'candidate': manifest, 'stages': [], 'units': [],
              'scope': 'Source-bound engine composition/reset, actual digital SRAM induction and controls, prefetch prediction, current instruction and support assertions. Historical formal remains a separate baseline.'}
    save = lambda: (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

    def run(name, command, limit):
        item = execute(command, out / (name + '.log'), limit)
        result['stages'].append(dict(name=name, **item, log_sha256=digest(out / (name + '.log'))))
        save()
        assert item['returncode'] == 0 and not item['timed_out'], name

    save()
    try:
        for name, script, arguments, limit, expected in (
            ('engine', 'run_prefetch_core_proof.py', [], 240, 'PASS_COMPOSITIONAL_NEXT_STATE_ENGINE_EQUIVALENCE'),
            ('store-controls', 'run_sram_store_controls.py', ['--candidate', str(candidate)], 600, 'PASS_SRAM_STORE_PORTS_AND_FOUR_CHECKED_CONTROLS'),
            ('store-formal', 'run_sram_store_formal.py', ['--candidate', str(candidate)], 1000, 'PASS_ARBITRARY_LOGICAL_STORE_AND_REAL_MODEL_CONTROL'),
            ('prediction', 'run_prefetch_invariant.py', ['--sources', str(candidate / 'src')], 400, 'PASS_PREFETCH_PREDICTION_INVARIANT_AND_ACTUAL_COUNTEREXAMPLE'),
        ):
            run(name, [sys.executable, str(ROOT / 'experiments/i2c' / script), *arguments,
                       '--output', str(out / name)], limit)
            child = json.loads((out / name / 'result.json').read_bytes())
            assert child['status'] == expected
            if 'candidate' in child:
                assert child['candidate'] == manifest
        assert digest(out / 'engine/gate.v') == profile['source_sha256']['m1_engine.v']
        variants = out / 'variants/od128/src'
        variants.mkdir(parents=True)
        (variants / 'm1_engine.v').write_bytes((sources / 'm1_engine.v').read_bytes())
        run('instructions', [sys.executable, str(ROOT / 'experiments/i2c/run_general_formal.py'),
                             '--variants', str(out / 'variants'), '--variant', 'od128', '--engine-style', 'next-state',
                             '--output', str(out / 'instructions')], 800)
        instructions = json.loads((out / 'instructions/result.json').read_bytes())
        assert instructions['status'] == 'PASS_SCOPED_INSTRUCTION_PROOFS'
        assert instructions['sources'] == {'od128': profile['source_sha256']['m1_engine.v']}
        for filename, tasks in (('m1_data_store', ('prove', 'cover')), ('m1_input_sync', ('prove', 'cover')),
                                ('m1_public_readout', (None,))):
            raw = (ROOT / 'formal' / (filename + '.sby')).read_text()
            script, files = raw.split('[files]\n')
            inputs = [candidate / 'src' / Path(name).name if name.startswith('src/') else ROOT / name
                      for name in files.splitlines() if name.strip()]
            if filename == 'm1_public_readout':
                # Compile the actual macro models, with no substituted memory.
                models = [candidate / 'models' / name for name in manifest['model_sha256']]
                old = 'read -formal -sv project.v m1_engine.v m1_program_store.v m1_data_store.v m1_input_sync.v'
                assert script.count(old) == 1
                script = script.replace(old, 'read -formal -sv -D FUNCTIONAL -D SYNTHESIS ' +
                                        ' '.join(p.name for p in [*models, *inputs]))
                # Resolve the actual top-level BIST tie-offs before clock
                # analysis, as in the separately verified SRAM-store proof.
                script = script.replace('prep -top tt_um_khangelani_protocol_emulator',
                                        'prep -top tt_um_khangelani_protocol_emulator -flatten')
                inputs = [*models, *inputs]
            config = out / (filename + '.sby')
            config.write_text(script + '[files]\n' + '\n'.join(str(p) for p in inputs) + '\n')
            for task in tasks:
                name = filename + ('-' + task if task else '')
                directory = out / name
                run(name, ['sby', '-f', '-d', str(directory), str(config)] + ([task] if task else []), 300)
                status = (directory / 'status').read_text().split()[0]
                assert status == 'PASS'
                log = (out / (name + '.log')).read_text()
                witnesses = {p.relative_to(directory).as_posix(): digest(p) for p in directory.glob('engine_*/trace*.vcd')}
                assert witnesses if task == 'cover' else 'successful proof by k-induction' in log
                for source in inputs:
                    assert (directory / 'src' / source.name).read_bytes() == source.read_bytes()
                result['units'].append({'name': name, 'status': status, 'inputs': {p.name: digest(p) for p in inputs},
                                        'proof_sby_sha256': digest(config), 'witnesses': witnesses})
                save()
        run('host-deadline', [sys.executable, str(ROOT / 'tools/check_host_deadline.py')], 120)
        assert describe(sources) == profile
        assert {name: digest(candidate / 'src' / name) for name in profile['source_sha256']} == profile['source_sha256']
        result['status'] = 'PASS_CURRENT_SRAM_COMPOSITION_INSTRUCTIONS_AND_SUPPORT_FORMAL'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'])


if __name__ == '__main__':
    main()
