# SPDX-License-Identifier: Apache-2.0
"""Build the versioned examples and enforce their independently reviewed words."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.assembler import TARGET, artifacts, assemble, json_bytes
from tools.production_sram import verify

EXAMPLES = ROOT / 'programs' / TARGET


def build(output):
    production = verify(ROOT)
    manifest = json.loads((EXAMPLES / 'examples.json').read_bytes())
    if manifest['schema'] != 'protocol-emulator-examples-v1' or manifest['target'] != TARGET:
        raise ValueError('unsupported example catalog')
    prepared = {}
    records = {}
    for entry in manifest['examples']:
        name = entry['name']
        if name in prepared or entry['file'] != name + '.asm' or Path(name).name != name or name in ('.', '..'):
            raise ValueError('invalid or duplicate example path')
        source = (EXAMPLES / entry['file']).read_text(encoding='utf-8')
        image = assemble(source)
        if image['words'] != entry['expected_words'] or image['binary_sha256'] != entry['binary_sha256']:
            raise ValueError(f'{name}: example bytes changed; review the ISA/example version and migration note')
        files = artifacts(image)
        prepared[name] = files
        records[name] = {'protocol': entry['protocol'], 'words': len(image['words']),
                         'source_sha256': image['source_sha256'], 'binary_sha256': image['binary_sha256'],
                         'artifact_sha256': {file: hashlib.sha256(raw).hexdigest() for file, raw in files.items()}}
    if output.exists():
        raise ValueError('output directory already exists; choose a new --out path')
    output.mkdir(parents=True)
    for name, files in prepared.items():
        folder = output / name
        folder.mkdir()
        for file, raw in files.items():
            (folder / file).write_bytes(raw)
    result = {'schema': 'protocol-emulator-example-build-v1', 'status': 'PASS_BUILD_AND_FROZEN_WORDS',
              'target': TARGET, 'qualified_source_sha256': production['source_sha256'],
              'examples': records, 'scope': 'Assembly and reference-byte identity only; public-pin simulation is separate.'}
    (output / 'manifest.json').write_bytes(json_bytes(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.out)
    except (OSError, ValueError) as error:
        parser.exit(2, f'error: {error}\n')
    print(result['status'], len(result['examples']), 'examples')
