# SPDX-License-Identifier: Apache-2.0
"""Package G3's exact readable sources, compiled artifacts and original CI ZIPs."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
TAG = 'v0.1.0-alpha.7'
CI = ROOT / 'evidence/E0046-program-toolchain/ci-0297655'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def blobs(head, names):
    files = {}
    for offset in range(0, len(names), 100):
        selected = names[offset:offset + 100]
        with tarfile.open(fileobj=io.BytesIO(git('archive', '--format=tar', head, '--', *selected))) as archive:
            for entry in archive:
                if entry.isdir():
                    continue
                assert entry.isfile() and entry.name in selected and entry.name not in files
                files[entry.name] = archive.extractfile(entry).read()
    assert set(files) == set(names)
    return files


def package(output):
    assert not git('diff', '--name-only', 'HEAD'), 'commit tracked work before packaging'
    assert not output.exists() and output.resolve().is_relative_to((ROOT / 'build').resolve())
    head = git('rev-parse', 'HEAD').decode().strip()
    spec = importlib.util.spec_from_file_location('g3_frozen_audit', CI / 'verify.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    checked = audit.audit(CI)
    assert checked == json.loads((CI / 'verification.json').read_bytes())
    public = audit.zip_files(CI / '14022181491.zip')
    windows = audit.zip_files(CI / '14022515054.zip')
    inputs = json.loads(public['result.json'])['inputs_sha256']
    assert {name: sha(raw) for name, raw in blobs(head, sorted(inputs)).items()} == inputs
    notes = git('show', head + ':docs/releases/' + TAG + '.md')
    assert notes
    names = git('ls-tree', '-r', '--name-only', head, '--', 'programs/od128-sram-v1').decode().splitlines()
    names += ['tools/assembler.py', 'docs/programming.md', 'docs/specs/g3-program-toolchain.md']
    source_files = blobs(head, sorted(names))
    manifest = {'schema': 'protocol-emulator-g3-release-package-v1', 'tag': TAG, 'release_source_commit': head,
                'target': 'od128-sram-v1', 'interface_id': '0x22', 'qualification_source_commit': audit.SOURCE,
                'qualification_run_id': audit.RUN, 'verification_inputs_unchanged': len(inputs),
                'production': checked['production'],
                'qualification_record': 'evidence/E0046-program-toolchain/ci-0297655/verification.json',
                'qualification_record_sha256': sha((CI / 'verification.json').read_bytes()),
                'examples': 13, 'public_cases_each_simulator': 55, 'expected_rejections_each': 15,
                'source_members_sha256': {name: sha(raw) for name, raw in source_files.items()},
                'compiled_members_sha256': {name: sha(raw) for name, raw in windows.items()},
                'scope': 'Readable software tools and compiled programs for the unchanged alpha.6 G2-qualified core. No new physical, analog, silicon, Fmax or owner-fluency result.'}
    files = dict(source_files)
    files.update({'compiled/' + name: raw for name, raw in windows.items()})
    files['g3-toolchain.json'] = encoded(manifest)
    files['README.md'] = f'''# G3 program toolchain ({TAG})

Source: {head}
Qualified interface: 0x22 / od128-sram-v1 / 128 words.

`compiled/` contains thirteen ready-to-inspect program binaries, JSON images,
timing listings and public load/readback plans. `programs/` contains readable
sources and their frozen reference words. Compile a source with Python 3.11+:

```
python tools/assembler.py programs/od128-sram-v1/uart_tx.asm --out build/my-uart
```

Use a new output directory. See `docs/programming.md` and the example README
for pin ownership, UART host service, SPI input hold and I2C assumptions. This
small download contains the standalone assembler and prepared artifacts; full
simulation uses a checkout of the repository and its pinned workbench:

https://github.com/KG-khangelani/protocol-emulator-asic/tree/{head}

The original Windows and Linux CI ZIPs are separate release assets. All 351
producing inputs are unchanged from qualified source {audit.SOURCE}; compiled
files match both CI platforms and the clean-checkout replay. Hardware remains
the G2-qualified alpha.6 core, with its original physical archives retained at:

https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0-alpha.6

This ZIP stores uncompressed entries with fixed metadata for deterministic
packaging. Its internal manifest identifies every source and compiled member;
the separate release manifest/checksums bind the actual downloadable ZIPs.
'''.encode('utf-8')
    output.mkdir(parents=True)
    with zipfile.ZipFile(output / 'g3-program-toolchain.zip', 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    for original, name in (('14022181491.zip', 'g3-public-programs.zip'), ('14022515054.zip', 'g3-windows-programs.zip')):
        (output / name).write_bytes((CI / original).read_bytes())
    manifest['bundle_members_sha256'] = {name: sha(raw) for name, raw in sorted(files.items())}
    manifest['artifacts'] = {path.name: {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
                             for path in sorted(output.glob('*.zip'))}
    (output / 'g3-toolchain.json').write_bytes(encoded(manifest))
    files = sorted(output.iterdir())
    (output / 'g3-SHA256SUMS').write_text(''.join(sha(path.read_bytes()) + '  ' + path.name + '\n' for path in files), encoding='utf-8', newline='\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    result = package(parser.parse_args().out)
    print('PACKAGED_G3_TOOLCHAIN', result['release_source_commit'], len(result['bundle_members_sha256']), 'members')
