# SPDX-License-Identifier: Apache-2.0
"""Actual reset/load/read store control with a checked high-bank alias witness."""
import argparse
import json
from pathlib import Path
import re

from run_banked_read_screen import ROOT, STORE, digest, execute, generate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('new isolated output required')
    out.mkdir(parents=True)
    parent, baseline = generate()
    original = baseline[STORE]
    before = b"5'd15: instruction = read_bank15;"
    after = b"5'd15: instruction = read_bank0;"
    assert original.count(before) == 1
    mutant = original.replace(before, after)
    bench = ROOT / 'test/banked_read_store.sv'
    result = {'status': 'RUNNING', 'scope': 'STORE_PORTS_ONLY_NOT_PUBLIC_CHIP_QUALIFICATION',
              'bench_sha256': digest(bench.read_bytes()), 'runner_sha256': digest(Path(__file__).read_bytes()),
              'baseline_store_sha256': digest(original), 'mutant_store_sha256': digest(mutant),
              'mutation': {'before': before.decode(), 'after': after.decode()}, 'runs': {}}

    def save():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    save()
    try:
        for simulator in ('icarus', 'verilator'):
            result['runs'][simulator] = {}
            for name, raw in (('parent', parent[STORE]), ('baseline', original), ('high-bank-alias', mutant)):
                work = out / simulator / name
                work.mkdir(parents=True)
                src = work / STORE
                src.write_bytes(raw)
                (work / bench.name).write_bytes(bench.read_bytes())
                executable = work / 'simulation'
                if simulator == 'icarus':
                    compile_cmd = ['iverilog', '-g2012', '-s', 'banked_read_store', '-o', str(executable), str(src), str(work / bench.name)]
                    run_cmd = ['vvp', str(executable)]
                else:
                    compile_cmd = ['verilator', '--binary', '--timing', '-Wno-fatal', '--top-module', 'banked_read_store',
                                   '--Mdir', str(work / 'sim'), '-o', str(executable), str(src), str(work / bench.name)]
                    run_cmd = [str(executable)]
                compile_result = execute(compile_cmd, work / 'compile.log', 120)
                item = {'compile': compile_result}
                result['runs'][simulator][name] = item
                save()
                assert compile_result['returncode'] == 0 and not compile_result['timed_out']
                run = execute(run_cmd, work / 'run.log', 30)
                item['simulation'] = run
                log = (work / 'run.log').read_text()
                assert not run['timed_out']
                if name == 'high-bank-alias':
                    witness = re.search(r'CHECK_FAILED fetch pc=120 bank=0 observed=([0-9a-f]{8}) expected=([0-9a-f]{8})', log)
                    assert run['returncode'] != 0 and witness and 'PORT_CHECK_FAILED' in log and 'PASS_STORE_PORT_TEST' not in log
                    def word(index):
                        return sum((((4*index+lane)*73 + ((4*index+lane)>>4)*19 + 41) & 255) << (8*lane) for lane in range(4))
                    assert int(witness[1], 16) == word(0) and int(witness[2], 16) == word(120) and word(0) != word(120)
                    item.update(status='EXPECTED_OBSERVABLE_FAILURE', witness={'pc': 120, 'observed': word(0), 'expected': word(120)})
                else:
                    match = re.search(r'PASS_STORE_PORT_TEST checks=(\d+) unknown_checks=(\d+)', log)
                    assert run['returncode'] == 0 and match and 'CHECK_FAILED' not in log
                    checks, unknown = map(int, match.groups())
                    assert unknown == (2 if simulator == 'icarus' else 0) and checks >= 1170
                    item.update(status='PASS', checks=checks, unknown_checks=unknown)
                item['store_sha256'] = digest(src.read_bytes())
                item['log_sha256'] = digest((work / 'run.log').read_bytes())
                assert item['store_sha256'] == digest(raw)
                save()
            a, b = (result['runs'][simulator][n] for n in ('parent', 'baseline'))
            assert (a['checks'], a['unknown_checks']) == (b['checks'], b['unknown_checks'])
        assert digest(bench.read_bytes()) == result['bench_sha256']
        result['status'] = 'PASS_BANKED_STORE_PORTS_AND_CHECKED_ALIAS_CONTROLS'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
