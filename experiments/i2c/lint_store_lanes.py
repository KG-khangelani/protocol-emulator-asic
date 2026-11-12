# SPDX-License-Identifier: Apache-2.0
"""Apply D38's narrowly checked complete-byte-case style exception."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from store_lanes import MANIFEST, digest, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variants', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-revision', choices=('explicit-lanes', 'shared-read'), default='explicit-lanes')
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('new isolated build output required')
    out.mkdir(parents=True)
    sources = args.variants / 'od128/src'
    manifest = MANIFEST
    if args.source_revision == 'shared-read':
        from shared_read import MANIFEST as shared_manifest
        manifest = shared_manifest
    expected = json.loads(manifest.read_bytes())['od128']['source_sha256']
    assert {n: digest((sources / n).read_bytes()) for n in expected} == expected
    store = sources / 'm1_program_store.v'
    text = store.read_text()
    cases = re.findall(r'case \(byte_address\[1:0\]\)\n(.*?)\n\s*endcase', text, re.S)
    assert len(cases) == 128
    for word, body in enumerate(cases):
        statements = [line.strip() for line in body.splitlines()]
        assert statements == [f"2'd{lane}: word{word}[{lane*8+7}:{lane*8}] <= data_in;" for lane in range(4)]
    shared = args.source_revision == 'shared-read'
    rules = '--rules=-case-missing-default'
    if shared:
        # The measured source inserted the address wire between the inherited
        # line waiver and its sole combinational block. Preserve those bytes.
        assert text.count('    always @(*) begin') == 1
        assert "// verilog_lint: waive always-comb\n    wire [7:0] read_address" in text
        rules += ',-always-comb'
    stages = []
    for name, files, flags in (
        ('other-modules', [str(sources / n) for n in expected if n != store.name], []),
        ('store-unwaived', [str(store)], []),
        ('store-scoped', [str(store)], [rules]),
    ):
        command = ['verible-verilog-lint', '--rules_config_search', *flags, *files]
        process = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        (out / (name + '.log')).write_bytes(process.stdout)
        if name == 'store-unwaived':
            warnings = process.stdout.decode().splitlines()
            assert process.returncode == 1 and len(warnings) == 128 + int(shared)
            assert sum(line.endswith('[Style: case-statements] [case-missing-default]') for line in warnings) == 128
            assert sum(line.endswith('[Style: combinational-logic] [always-comb]') for line in warnings) == int(shared)
        else:
            assert process.returncode == 0, process.stdout.decode()
        stages.append({'name': name, 'command': command, 'returncode': process.returncode,
                       'log_sha256': digest(process.stdout)})
    result = {'status': 'PASS_SCOPED_STYLE_REVIEW', 'sources': expected, 'stages': stages,
              'exception': 'Only case-missing-default on the frozen program store: all four values of each two-bit byte selector are explicit and separately checked for all 128 words. An unknown simulation selector holds state. No RTL or physical threshold changes.',
              'unwaived_status': f'{128 + int(shared)} declared style warnings; all other modules/rules pass'}
    if shared:
        result['exception'] += ' D39 also preserves the inherited always-comb exception on its sole combinational read block; the inserted address wire separated the original line waiver from that block. The exact source and single block are checked before applying this exception.'
    (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(result['status'])


if __name__ == '__main__':
    main()
