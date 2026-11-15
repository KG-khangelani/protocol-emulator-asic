# SPDX-License-Identifier: Apache-2.0
"""Package the qualified G5 firmware example from immutable Git and CI bytes."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import platform
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
QUALIFICATION = ROOT / 'evidence/E0048-waveform-replay/ci-66743b6'
SOURCE = '66743b60b93508d2f00f23fa2cc2ac7db244bc3a'
TAG = 'v0.1.1'
PROGRAMS = ('control', 'timing_fault')
PROGRAM_FILES = ('load-plan.json', 'program.bin', 'program.json', 'program.lst')
SOURCES = (
    'LICENSE', 'THIRD_PARTY_NOTICES.md', 'tools/assembler.py',
    'experiments/waveform_replay/control.asm', 'experiments/waveform_replay/timing_fault.asm',
    'experiments/waveform_replay/expected.json', 'experiments/waveform_replay/oracle.py',
    'test/test_waveform_replay_oracle.py', 'docs/waveform-replay.md', 'docs/programming.md',
    'docs/isa.md', 'docs/submission.md', 'docs/specs/g5-waveform-replay.md',
    'docs/decisions/0050-bounded-firmware-waveform-replay.md', 'docs/releases/' + TAG + '.md',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def blobs(source, names):
    names = sorted(set(names))
    files = {}
    for offset in range(0, len(names), 80):
        selected = names[offset:offset + 80]
        with tarfile.open(fileobj=io.BytesIO(git('archive', '--format=tar', source, '--', *selected))) as archive:
            for item in archive:
                if item.isdir():
                    continue
                require(item.isfile() and item.name in selected and item.name not in files,
                        'invalid or duplicate Git archive member')
                files[item.name] = archive.extractfile(item).read()
    require(set(files) == set(names), 'release source is missing required files')
    return files


def zip_files(path):
    files = {}
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            name = item.filename
            parts = PurePosixPath(name)
            require(name not in files and not parts.is_absolute() and '..' not in parts.parts
                    and '\\' not in name and ':' not in name and str(parts) == name,
                    'unsafe or duplicate ZIP member')
            require(item.file_size <= 100_000_000, 'unexpectedly large ZIP member')
            files[name] = archive.read(item)
    return files


def fresh_output(output):
    output = output.resolve()
    require(output.is_relative_to((ROOT / 'build').resolve()), 'output must be under repository build/')
    require(not output.exists(), 'output exists; preserve it and choose a fresh directory')
    return output


def package(output, source='HEAD', qualification=QUALIFICATION):
    output = fresh_output(output)
    qualification = qualification.resolve()
    require(qualification.is_relative_to(ROOT), 'qualification must be retained inside this repository')
    head = git('rev-parse', '--verify', source + '^{commit}').decode().strip()
    require(subprocess.run(['git', 'merge-base', '--is-ancestor', SOURCE, head], cwd=ROOT).returncode == 0,
            'release source does not descend from qualified implementation')
    audit_path = HERE.parent / 'verify.py'
    bound_names = [Path(__file__).relative_to(ROOT).as_posix(), audit_path.relative_to(ROOT).as_posix(),
                   (qualification / 'verification.json').relative_to(ROOT).as_posix()]
    bound = blobs(head, bound_names)
    for name, raw in bound.items():
        require(raw == (ROOT / name).read_bytes(), 'commit the actual packaging/audit inputs before packaging: ' + name)
    spec = importlib.util.spec_from_file_location('g5_retained_package_audit', audit_path)
    audit = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = audit
    spec.loader.exec_module(audit)
    checked = audit.audit(qualification, expected_source=SOURCE)
    require(checked['status'] == 'PASS_G5_RETAINED_ORIGINALS', 'retained qualification did not pass')
    recorded = json.loads((qualification / 'verification.json').read_bytes())
    require({key: recorded.get(key) for key in checked} == checked, 'retained verification no longer reproduces')
    require(set(recorded) <= set(checked) | {'windows_build'}, 'unexpected fields in recorded verification')
    original = qualification / (str(checked['artifact']['id']) + '.zip')
    original_raw = original.read_bytes()
    require(sha(original_raw) == checked['artifact']['sha256'], 'original CI transport changed')
    original_name = original.relative_to(ROOT).as_posix()
    require(blobs(head, [original_name])[original_name] == original_raw, 'release does not retain the exact original CI ZIP')
    ci = zip_files(original)
    result = json.loads(ci['primary/result.json'])
    require(result['status'] == 'PASS_G5_BOTH_PUBLIC_SIMULATORS' and result['source_commit'] == SOURCE,
            'wrong original qualification result')
    inputs = result['inputs_sha256']
    require({name: sha(raw) for name, raw in blobs(head, inputs).items()} == inputs,
            'qualified producing input bytes changed in release source')
    source_files = blobs(head, SOURCES)
    compiled = {}
    for program in PROGRAMS:
        data = result['build']['programs'][program]
        require(data['words'] == 20 and data['bytes'] == 80, 'wrong frozen program footprint')
        require(set(data['artifact_sha256']) == set(PROGRAM_FILES), 'unexpected compiled file set')
        for filename in PROGRAM_FILES:
            raw = ci['primary/programs/' + program + '/' + filename]
            require(sha(raw) == data['artifact_sha256'][filename], 'compiled artifact identity differs')
            require(raw == ci['reproduction/programs/' + program + '/' + filename], 'compiled artifacts do not reproduce')
            compiled['compiled/' + program + '/' + filename] = raw
    manifest = {
        'schema': 'protocol-emulator-g5-release-package-v1', 'tag': TAG,
        'release_source_commit': head, 'qualification_source_commit': SOURCE,
        'qualification_run_id': checked['run_id'], 'target': 'od128-sram-v1', 'interface_id': '0x22',
        'verification_inputs_unchanged': len(inputs), 'qualified_inputs_sha256': inputs,
        'qualification_record': bound_names[-1], 'qualification_record_sha256': sha(bound[bound_names[-1]]),
        'original_artifact': checked['artifact'], 'runtime': checked['runtime'],
        'production': result['production'], 'programs': result['build']['programs'],
        'public_cases_per_simulator': 21, 'expected_rejections_per_simulator': 5,
        'clean_reproduction': True, 'g3_continuity': checked['g3'],
        'source_members_sha256': {name: sha(raw) for name, raw in sorted(source_files.items())},
        'compiled_members_sha256': {name: sha(raw) for name, raw in sorted(compiled.items())},
        'scope': 'Firmware-only digital stimulus and timing-fault example on unchanged G4-qualified hardware. No new physical, silicon, analog, Fmax or owner-fluency result.',
    }
    files = {**source_files, **compiled, 'g5-waveform-replay.json': encoded(manifest)}
    files['README.md'] = f'''# Triggered waveform replay ({TAG})

Two 20-word / 80-byte programs for interface 0x22, od128-sram-v1.
The fault program moves one rising edge by two clocks while preserving later
output transitions. Both programs explicitly release all outputs before HALT.

Build with Python 3.11 or later, using new output directories:

```
python tools/assembler.py experiments/waveform_replay/control.asm --out build/my-control
python tools/assembler.py experiments/waveform_replay/timing_fault.asm --out build/my-fault
```

`compiled/` contains the eight original qualified program artifacts. Start with
`docs/waveform-replay.md` for the pin assignment, load/readback procedure and
timing limits. `docs/programming.md` documents the assembler. The independent
literal trace checker and its tests are included; run from this bundle root:

```
python -m unittest discover -s test -p test_waveform_replay_oracle.py
```

The bundle supports standalone assembly and checker tests. Complete public-pin
simulation uses a repository checkout and the pinned workbench:
https://github.com/KG-khangelani/protocol-emulator-asic/tree/{head}

Qualification source: {SOURCE}
Qualification run: https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/{checked['run_id']}
Release source: {head}

The separate `g5-original-ci.zip` asset preserves the original CI transport:
two simulator runs, clean-clone reproduction and the existing G3 protocol
guard. The external manifest and `g5-SHA256SUMS` bind the downloadable assets.
This ZIP uses stored entries, fixed metadata and lexical filename order.

Hardware and physical evidence remain the stable G4 candidate:
https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0

This is a digital simulation example, not a physical fixture, analog glitch
generator, unrestricted timing guarantee or fabricated-chip measurement.
'''.encode('utf-8')
    output.mkdir(parents=True)
    with zipfile.ZipFile(output / 'g5-waveform-replay.zip', 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    (output / 'g5-original-ci.zip').write_bytes(original_raw)
    manifest['bundle_members_sha256'] = {name: sha(raw) for name, raw in sorted(files.items())}
    manifest['artifacts'] = {path.name: {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
                             for path in sorted(output.glob('*.zip'), key=lambda path: path.name)}
    (output / 'g5-waveform-replay.json').write_bytes(encoded(manifest))
    paths = sorted(output.iterdir(), key=lambda path: path.name)
    (output / 'g5-SHA256SUMS').write_bytes(''.join(sha(path.read_bytes()) + '  ' + path.name + '\n'
                                                for path in paths).encode('utf-8'))
    return manifest


def smoke(assets, output):
    """Rebuild from the shipped bundle with isolated, standard-library Python."""
    output = fresh_output(output)
    assets = assets.resolve()
    manifest = json.loads((assets / 'g5-waveform-replay.json').read_bytes())
    for name, item in manifest['artifacts'].items():
        raw = (assets / name).read_bytes()
        require(len(raw) == item['bytes'] and sha(raw) == item['sha256'], 'asset checksum differs: ' + name)
    files = zip_files(assets / 'g5-waveform-replay.zip')
    require({name: sha(raw) for name, raw in files.items()} == manifest['bundle_members_sha256'],
            'bundle member checksums differ')
    output.mkdir(parents=True)
    commands, compiled = [], {}
    # Keep Windows work on H:; Linux uses its local temporary directory. Both
    # locations are outside the repository and are unique to this smoke run.
    parent = ROOT.parent if sys.platform == 'win32' else None
    with tempfile.TemporaryDirectory(prefix='g5-distribution-', dir=parent) as isolated:
        isolated = Path(isolated).resolve()
        require(not isolated.is_relative_to(ROOT), 'standalone run must be outside the repository')
        if parent is not None:
            require(isolated.parent == parent.resolve(), 'Windows scratch escaped the selected H: parent')
        bundle = isolated / 'bundle'
        for name, raw in files.items():
            path = bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        for program in PROGRAMS:
            built = isolated / ('rebuilt-' + program)
            command = [sys.executable, '-I', '-S', str(bundle / 'tools/assembler.py'),
                       str(bundle / 'experiments/waveform_replay' / (program + '.asm')), '--out', str(built)]
            completed = subprocess.run(command, cwd=isolated, capture_output=True, timeout=60)
            log = completed.stdout + completed.stderr
            (output / (program + '.log')).write_bytes(log)
            require(completed.returncode == 0, 'standalone assembly failed: ' + program)
            require({path.name for path in built.iterdir()} == set(PROGRAM_FILES), 'standalone file set differs')
            for filename in PROGRAM_FILES:
                raw = (built / filename).read_bytes()
                require(raw == files['compiled/' + program + '/' + filename],
                        'standalone compiled bytes differ: ' + program + '/' + filename)
                compiled[program + '/' + filename] = sha(raw)
            commands.append({'command': command, 'cwd': str(isolated), 'returncode': completed.returncode,
                             'log_sha256': sha(log)})
        # Add only the shipped bundle path to isolated Python's standard library
        # search path, then execute the included independent checker tests.
        code = "import runpy,sys;sys.path.insert(0,sys.argv[1]);sys.argv=[sys.argv[2]];runpy.run_path(sys.argv[0],run_name='__main__')"
        command = [sys.executable, '-I', '-S', '-c', code, str(bundle), str(bundle / 'test/test_waveform_replay_oracle.py')]
        completed = subprocess.run(command, cwd=isolated, capture_output=True, timeout=60)
        log = completed.stdout + completed.stderr
        (output / 'oracle-tests.log').write_bytes(log)
        require(completed.returncode == 0 and b'Ran 12 tests' in completed.stderr,
                'standalone independent checker tests failed or were not all executed')
        commands.append({'command': command, 'cwd': str(isolated), 'returncode': completed.returncode,
                         'log_sha256': sha(log)})
    result = {'schema': 'protocol-emulator-g5-distribution-smoke-v1', 'status': 'PASS_G5_STANDALONE_DISTRIBUTION',
              'release_source_commit': manifest['release_source_commit'], 'programs': 2, 'compiled_files': 8,
              'oracle_tests': 12, 'bundle_sha256': sha((assets / 'g5-waveform-replay.zip').read_bytes()),
              'runtime': {'python': sys.version, 'platform': platform.platform()},
              'compiled_sha256': compiled, 'outside_repository': True,
              'commands': commands}
    (output / 'result.json').write_bytes(encoded(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source', default='HEAD')
    parser.add_argument('--qualification', type=Path, default=QUALIFICATION)
    parser.add_argument('--smoke', type=Path, help='test an existing four-asset package instead of packaging')
    args = parser.parse_args()
    if args.smoke:
        result = smoke(args.smoke, args.out)
        print(result['status'], result['compiled_files'], 'compiled files')
    else:
        result = package(args.out, args.source, args.qualification)
        print('PACKAGED_G5_WAVEFORM_REPLAY', result['release_source_commit'], len(result['bundle_members_sha256']), 'members')


if __name__ == '__main__':
    main()
