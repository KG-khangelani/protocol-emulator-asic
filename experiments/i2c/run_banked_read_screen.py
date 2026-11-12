# SPDX-License-Identifier: Apache-2.0
"""One bounded D39 read-network experiment; no production or physical claims."""
import argparse
import json
from pathlib import Path
import sys

from shared_read import EVIDENCE as PARENT, ROOT, digest

sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from run_comparison import cell_counts
from run_program_sensitivity import execute

TOP = 'tt_um_khangelani_protocol_emulator'
STORE = 'm1_program_store.v'
SPEC = ROOT / 'docs/specs/g2-banked-read-screen.md'
STORE_PORTS = {
    'clk': ('input', 1), 'rst_n': ('input', 1), 'ena': ('input', 1),
    'load_mode': ('input', 1), 'load_write': ('input', 1),
    'load_length': ('input', 1), 'load_bank': ('input', 1),
    'byte_address': ('input', 5), 'data_in': ('input', 8), 'pc': ('input', 8),
    'data_out': ('output', 8), 'program_length': ('output', 8),
    'program_ready': ('output', 1), 'program_bank': ('output', 4),
    'instruction': ('output', 32), 'instruction_valid': ('output', 1),
}


def read(path):
    return json.loads(path.read_bytes())


def generate():
    expected = read(PARENT / 'sources/source-manifest.json')['od128']['source_sha256']
    parent = {name: (PARENT / 'sources/od128' / name).read_bytes() for name in expected}
    assert {name: digest(raw) for name, raw in parent.items()} == expected
    original = parent[STORE].decode()
    start = original.index('    always @(*) begin')
    end = original.index('        data_out = instruction', start)
    assert original[start:end].count(': instruction = word') == 128
    lines = [f'    reg [31:0] read_bank{bank};' for bank in range(16)]
    lines += ['    always @(*) begin', '        case (read_address[2:0])']
    for low in range(8):
        lines += [f"            3'd{low}: begin"]
        lines += [f'                read_bank{bank} = word{8*bank+low};' for bank in range(16)]
        lines += ['            end']
    lines += ['            default: begin']
    lines += [f"                read_bank{bank} = 32'd0;" for bank in range(16)]
    lines += ['            end', '        endcase', '        case (read_address[7:3])']
    lines += [f"            5'd{bank}: instruction = read_bank{bank};" for bank in range(16)]
    lines += ["            default: instruction = 32'd0;", '        endcase']
    candidate = dict(parent)
    candidate[STORE] = (original[:start] + '\n'.join(lines) + '\n' + original[end:]).encode()
    assert candidate[STORE].split(b'    reg [31:0] read_bank0;')[0] == parent[STORE][:start]
    assert candidate[STORE][candidate[STORE].index(b'        data_out = instruction'):] == parent[STORE][end:]
    return parent, candidate


def state_coverage(models):
    states, names = {}, set()
    for label, module in models.items():
        assert {n: (p['direction'], len(p['bits'])) for n, p in module['ports'].items()} == STORE_PORTS
        assert not any('latch' in c['type'].lower() or c['type'] in ('$assume', '$anyseq', '$anyconst')
                       for c in module['cells'].values())
        qbits = {b for c in module['cells'].values() if 'dff' in c['type'].lower()
                 for b in c['connections']['Q'] if isinstance(b, int)}
        assert len(qbits) == 4109
        visible = {n: w['bits'] for n, w in module['netnames'].items() if not n.startswith('$')}
        states[label] = {n: bits for n, bits in visible.items()
                         if any(b in qbits for b in bits) and all(b in qbits for b in bits)}
        names |= set(visible)
    common = sorted(set(states['gold']) & set(states['gate']))
    for label in models:
        assert len({b for n in common for b in states[label][n]}) == 4109
    return common, sorted(names - set(common) - set(STORE_PORTS))


def check_comparisons(before, after, state_names):
    equiv = {n: c for n, c in before['cells'].items() if c['type'] == '$equiv'}
    pairs = {(c['connections']['A'][0], c['connections']['B'][0]) for c in equiv.values()}
    output_bits = {b for p in before['ports'].values() if p['direction'] == 'output' for b in p['bits']}
    assert len(output_bits) == 54
    assert output_bits <= {b for c in equiv.values() for b in c['connections']['Y']}
    for name in state_names:
        a, b = (before['netnames'][name + suffix]['bits'] for suffix in ('_gold', '_gate'))
        assert len(a) == len(b)
        assert all((x, y) in pairs or (y, x) in pairs for x, y in zip(a, b)), name
    assert equiv and all(after['cells'][n]['connections']['A'] == after['cells'][n]['connections']['B']
                         for n in equiv)
    return len(equiv)


def check_reset(model, state_names, count):
    assertions = [c for c in model['cells'].values() if c['type'] == '$assert']
    comparisons = [c for c in model['cells'].values() if c['type'] == '$eqx']
    assert all(c['connections']['EN'] == ['1'] for c in assertions)
    assert not any(c['type'] == '$assume' for c in model['cells'].values())
    assert {tuple(c['connections']['Y']) for c in comparisons} == {tuple(c['connections']['A']) for c in assertions}
    pairs = {(tuple(c['connections']['A']), tuple(c['connections']['B'])) for c in comparisons}
    for name in set(state_names) | {n for n, p in model['ports'].items() if p['direction'] == 'output'}:
        a, b = (tuple(model['netnames'][name + suffix]['bits']) for suffix in ('_gold', '_gate'))
        assert (a, b) in pairs or (b, a) in pairs, name
    assert sum(int(c['parameters']['A_WIDTH'], 2) for c in comparisons) == count
    return {'vector_assertions': len(assertions), 'compared_bits_including_aliases': count}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('new isolated build output required')
    out.mkdir(parents=True)
    sources = dict(zip(('gold', 'gate'), generate()))
    result = {'status': 'RUNNING', 'scope': 'GENERIC_AND_COMPLETE_STORE_EQUIVALENCE_ONLY',
              'spec_sha256': digest(SPEC.read_bytes()), 'runner_sha256': digest(Path(__file__).read_bytes()),
              'sources': {label: {n: digest(raw) for n, raw in files.items()} for label, files in sources.items()},
              'stages': {}, 'counts': {}}

    def save():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    def run(label, script, limit):
        path = out / (label + '.ys')
        path.write_bytes((script + '\n').encode())
        stage = execute(['yosys', '-Q', '-s', str(path)], out / (label + '.log'), limit)
        result['stages'][label] = stage
        save()
        assert stage['returncode'] == 0 and not stage['timed_out'], label

    save()
    try:
        version = execute(['yosys', '-V'], out / 'yosys-version.log', 10)
        assert version['returncode'] == 0
        result['tool_version'] = (out / 'yosys-version.log').read_text().strip()
        models = {}
        for label, files in sources.items():
            src = out / label / 'src'
            src.mkdir(parents=True)
            for name, raw in files.items():
                (src / name).write_bytes(raw)
            script = 'read_verilog ' + ' '.join(str(src / n) for n in files)
            script += f'; hierarchy -check -top {TOP}; synth -top {TOP}; check -assert; stat; write_json {out / (label + "-synth.json")}'
            run(label + '-synth', script, 300)
            counts = cell_counts(out / (label + '-synth.json'))
            assert counts['state_bits'] == 4278 and not any('latch' in n.lower() for n in counts['cell_types'])
            result['counts'][label] = counts
            script = f'read_verilog {src / STORE}; hierarchy -check -top m1_program_store; proc; opt; check -assert; rename m1_program_store {label}; '
            script += f'write_rtlil {out / (label + ".il")}; write_json {out / (label + ".json")}'
            run(label + '-model', script, 60)
            models[label] = read(out / (label + '.json'))['modules'][label]
        common, excluded = state_coverage(models)
        (out / 'blacklist.txt').write_bytes(('\n'.join(excluded) + '\n').encode())
        result.update(actual_store_state_bits=4109, common_state_names=common, excluded_combinational_names=excluded)
        inputs = f'read_rtlil {out / "gold.il"} {out / "gate.il"}; '
        miter = f'equiv_make -blacklist {out / "blacklist.txt"} gold gate equivalence; hierarchy -top equivalence; '
        run('temporal', inputs + miter + f'write_json {out / "before.json"}; equiv_simple; equiv_induct -seq 1; equiv_status -assert; write_json {out / "after.json"}', 240)
        assert 'Equivalence successfully proven!' in (out / 'temporal.log').read_text()
        count = check_comparisons(read(out / 'before.json')['modules']['equivalence'],
                                  read(out / 'after.json')['modules']['equivalence'], common)
        result.update(public_store_output_bits=54, proven_bit_comparisons_including_aliases=count)
        script = inputs + miter.replace('equiv_make ', 'equiv_make -make_assert ')
        script += f'dffunmap; opt_clean; write_json {out / "reset.json"}; '
        script += 'sat -verify -seq 2 -set-at 1 rst_n 0 -prove-asserts -prove-skip 1 -set-def-inputs -show-ports'
        run('reset', script, 90)
        assert 'SAT proof finished - no model found: SUCCESS!' in (out / 'reset.log').read_text()
        result['reset_base'] = check_reset(read(out / 'reset.json')['modules']['equivalence'], common, count)
        assert {label: {n: digest((out / label / 'src' / n).read_bytes()) for n in files}
                for label, files in sources.items()} == result['sources']
        result['status'] = 'PASS_BOUNDED_BANKED_READ_PROOF_AND_GENERIC_SCREEN'
        result['controls'] = 'PENDING_SEPARATE_PORT_DRIVEN_TEST'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'], result['counts'], flush=True)


if __name__ == '__main__':
    main()
