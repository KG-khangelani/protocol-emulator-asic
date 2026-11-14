# SPDX-License-Identifier: Apache-2.0
"""Build deterministic G4 assets from committed, qualified evidence and source."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
from types import ModuleType
import zipfile

ROOT = Path(__file__).resolve().parents[3]
TAG = 'v0.1.0'
EVIDENCE = 'evidence/E0047-g4-submission-candidate'
G3 = 'evidence/E0046-program-toolchain/ci-0297655'
G2 = 'evidence/E0045-g2-sram-qualification/ci-94a3082'
RUNS = {'candidate': 43543626249, 'reproduction': 43543629839}
PHYSICAL_ARCHIVES = {'GDS_logs', 'tt_submission', 'sram-physical-candidate',
                     'precheck_reports', 'gatelevel_test_results', 'sram-netlist-check'}
RESTORE_SCRIPT = '''# SPDX-License-Identifier: Apache-2.0
"""Restore exact retained archive parts from the separately downloaded G4 assets."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--assets', type=Path, default=ROOT)
args = parser.parse_args()
manifest = json.loads((ROOT / 'g4-submission.json').read_bytes())
require(manifest['schema'] == 'protocol-emulator-g4-release-package-v1', 'wrong manifest')
restored = 0
for archive in manifest['original_archives']:
    name = archive['asset']
    require(bool(name) and PurePosixPath(name).name == name and '\\\\' not in name,
            'asset must be a basename')
    source = args.assets.resolve() / name
    require(source.stat().st_size == archive['bytes'] and digest(source) == archive['sha256'],
            'original asset identity differs: ' + name)
    require(sum(part['bytes'] for part in archive['storage']) == archive['bytes'], 'part lengths differ')
    with source.open('rb') as stream:
        for part in archive['storage']:
            relative = PurePosixPath(part['path'])
            require(not relative.is_absolute() and '..' not in relative.parts and
                    '\\\\' not in part['path'] and part['path'].startswith((
                        'evidence/E0047-g4-submission-candidate/ci-',
                        'evidence/E0046-program-toolchain/ci-0297655/')), 'unsafe retained path')
            target = (ROOT / relative).resolve()
            require(target.is_relative_to(ROOT), 'retained path escapes the bundle')
            raw = stream.read(part['bytes'])
            require(len(raw) == part['bytes'] and hashlib.sha256(raw).hexdigest() == part['sha256'],
                    'original part identity differs: ' + part['path'])
            if target.exists():
                require(target.is_file() and target.stat().st_size == part['bytes'] and
                        digest(target) == part['sha256'], 'existing file differs: ' + part['path'])
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    output.write(raw)
            restored += 1
        require(not stream.read(1), 'unexpected trailing original bytes')
print('RESTORED_EXACT_ORIGINAL_PARTS', restored)
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def relative(name):
    path = PurePosixPath(name)
    require(bool(name) and not path.is_absolute() and '..' not in path.parts and
            '\\' not in name and ':' not in name, 'unsafe repository path: ' + name)
    return path


def blob(source, name):
    relative(name)
    return git('show', source + ':' + name)


def read(source, name):
    return json.loads(blob(source, name))


def names_at(source, path):
    relative(path)
    return git('ls-tree', '-r', '--name-only', source, '--', path).decode().splitlines()


def blobs(source, names):
    names = sorted(set(names))
    for name in names:
        relative(name)
    files = {}
    for offset in range(0, len(names), 100):
        selected = names[offset:offset + 100]
        with tarfile.open(fileobj=io.BytesIO(git('archive', '--format=tar', source, '--', *selected))) as archive:
            for entry in archive:
                if entry.isdir():
                    continue
                require(entry.isfile() and entry.name in selected and entry.name not in files,
                        'unexpected archived Git entry: ' + entry.name)
                files[entry.name] = archive.extractfile(entry).read()
    require(set(files) == set(names), 'incomplete committed source file set')
    return files


def sealed_files(source, directory, external_parts=()):
    """Read sealed metadata from Git; original bulk parts are streamed later."""
    prefix = directory + '/'
    seal_path = prefix + 'SHA256SUMS'
    raw_seal = blob(source, seal_path)
    seal = {}
    for line in raw_seal.decode('utf-8').splitlines():
        digest, name = line.split('  ', 1)
        relative(name)
        require(re.fullmatch('[0-9a-f]{64}', digest) and name not in seal,
                'invalid or duplicate seal entry: ' + name)
        seal[name] = digest
    tracked = set(names_at(source, directory))
    require(tracked == {prefix + name for name in seal} | {seal_path},
            'seal does not cover the committed evidence tree: ' + directory)
    external_parts = dict(external_parts)
    for name, digest in external_parts.items():
        require(name.startswith(prefix) and seal.get(name.removeprefix(prefix)) == digest,
                'original part disagrees with evidence seal: ' + name)
    files = blobs(source, sorted(tracked - set(external_parts)))
    for name, raw in files.items():
        if name != seal_path:
            require(sha(raw) == seal[name.removeprefix(prefix)], 'evidence seal mismatch: ' + name)
    return files


def check_g3(source):
    frozen = sealed_files(source, G3)
    # The historical auditor reads its retained directory and original Git revision.
    # Require those local bytes to equal the selected committed evidence first.
    for name, raw in frozen.items():
        require((ROOT / name).read_bytes() == raw, 'local frozen G3 record differs: ' + name)
    module = ModuleType('g4_frozen_g3_audit')
    module.__file__ = str(ROOT / G3 / 'verify.py')
    exec(compile(frozen[G3 + '/verify.py'], module.__file__, 'exec'), module.__dict__)
    checked = module.audit(ROOT / G3)
    require(checked == json.loads(frozen[G3 + '/verification.json']), 'historical G3 audit differs')
    public = module.zip_files(ROOT / G3 / '14022181491.zip')
    compiled = module.zip_files(ROOT / G3 / '14022515054.zip')
    inputs = json.loads(public['result.json'])['inputs_sha256']
    require(len(inputs) == 351, 'historical G3 input membership changed')
    actual = {name: sha(raw) for name, raw in blobs(source, sorted(inputs)).items()}
    changed = sorted(name for name in inputs if actual.get(name) != inputs[name])
    require(not changed, 'G3 producing inputs changed: ' + ', '.join(changed))
    require(len(compiled) == 53, 'compiled program membership changed')
    archives = []
    for role, artifact_id in (('public', 14022181491), ('windows', 14022515054)):
        metadata = checked['artifacts'][role]
        name = G3 + '/' + str(artifact_id) + '.zip'
        require(metadata['id'] == artifact_id and sha(frozen[name]) == metadata['sha256'],
                'G3 original identity changed')
        archives.append({'role': 'g3-' + role, 'run_id': module.RUN, 'artifact_id': artifact_id,
                         'asset': 'g4-' + role + '-programs.zip', 'bytes': metadata['bytes'],
                         'sha256': metadata['sha256'],
                         'storage': [{'path': name, 'bytes': metadata['bytes'], 'sha256': metadata['sha256']}]})
        del frozen[name]
    record = {'qualification_source_commit': module.SOURCE, 'run_id': module.RUN,
              'verification_record': G3 + '/verification.json',
              'verification_record_sha256': sha(frozen[G3 + '/verification.json']),
              'verification_inputs_unchanged': len(inputs), 'inputs_sha256': inputs,
              'production': checked['production'], 'examples': 13,
              'public_cases_each_simulator': 55, 'expected_rejections_each': 15}
    return record, compiled, frozen, archives


def check_fresh_program_toolchain(source, production, compiled):
    directory = EVIDENCE + '/program-tools'
    frozen = sealed_files(source, directory)
    for name, raw in frozen.items():
        require((ROOT / name).read_bytes() == raw, 'local frozen G4 program record differs: ' + name)
    module = ModuleType('g4_frozen_fresh_program_audit')
    module.__file__ = str(ROOT / directory / 'verify.py')
    exec(compile(frozen[directory + '/verify.py'], module.__file__, 'exec'), module.__dict__)
    checked = module.audit(ROOT / directory)
    reference_path = directory + '/verification.json'
    require(checked == json.loads(frozen[reference_path]), 'fresh G4 program audit differs')
    require(checked['status'] == 'PASS_G4_FRESH_PROGRAM_TOOLCHAIN_CI' and
            checked['source_commit'] == 'ae2ac7bf800bd02d83fe62677a56bc4131e98b06' and
            checked['run_id'] == 43544749692, 'fresh G4 program qualification identity differs')
    producer = json.loads(frozen[directory + '/producer.json'])
    inputs = producer['verification_inputs_sha256']
    require(len(inputs) == checked['committed_verification_inputs'] == 352 and
            len(producer['files']) == checked['frozen_producer']['files'] == 356,
            'fresh G4 program input membership changed')
    actual = {name: sha(raw) for name, raw in blobs(source, sorted(inputs)).items()}
    changed = sorted(name for name in inputs if actual.get(name) != inputs[name])
    require(not changed, 'fresh G4 producing inputs changed: ' + ', '.join(changed))
    require(checked['production'] == production, 'fresh G4 program production identity differs')
    windows_id = checked['artifacts']['windows']['id']
    observed = module.zip_files(ROOT / directory / (str(windows_id) + '.zip'))
    require(observed == compiled and len(observed) == 53, 'fresh G4 compiled program artifacts changed')
    record = {'status': checked['status'], 'source_commit': checked['source_commit'],
              'run_id': checked['run_id'], 'verification_record': reference_path,
              'verification_record_sha256': sha(frozen[reference_path]),
              'verification_inputs_sha256': inputs, 'committed_verification_inputs': len(inputs),
              'frozen_producer_files': len(producer['files']), 'examples': checked['examples'],
              'assembler_tests': checked['assembler_tests'], 'public_cases_each': checked['public_cases_each'],
              'expected_rejections_each': checked['expected_rejections_each'],
              'compiled_artifact_files_identical': len(observed),
              'actual_ci_image_config_digest': checked['actual_ci_image_config_digest'],
              'original_artifacts': checked['artifacts']}
    return record, frozen


def check_physical(source, role, run_id, reproduction, production):
    directory = EVIDENCE + '/ci-' + str(run_id)
    result_path = directory + '/result.json'
    result_raw = blob(source, result_path)
    result = json.loads(result_raw)
    binding = reproduction['runs'][role]
    require(binding == {'run_id': run_id, 'result_path': result_path, 'result_sha256': sha(result_raw)},
            'reproduction result binding differs: ' + role)
    require(result['status'] == 'PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES' and
            result['run_id'] == run_id and result['source_commit'] == reproduction['source_commit'],
            'physical qualification identity differs: ' + role)
    require(result['workflow_path'] == '.github/workflows/gds.yaml', 'wrong physical workflow')
    require(set(result['jobs']) == {'gds', 'precheck', 'gl_test'} and
            all(job['conclusion'] == 'success' for job in result['jobs'].values()), 'incomplete physical jobs')
    require(result['staged_sha256'] == production['files_sha256'] and len(result['staged_sha256']) == 20,
            'final physical inputs differ from production')
    require(result['metadata_sha256_lf'] == production['metadata_sha256'], 'physical metadata changed')
    require(result['candidate']['source_sha256'] == production['source_sha256'] and
            result['candidate']['model_sha256'] == production['model_sha256'], 'physical source or models changed')
    require(result['physical_metrics']['status'] == 'PASS' and
            result['precheck']['status'] == 'PASS' and result['precheck']['test_count'] == 10 and
            len(set(result['precheck']['tests'])) == 10, 'physical or precheck gate missing')
    require(result['netlist_tests']['status'] == 'PASS' and
            result['netlist_tests']['public_test_groups'] == 18, 'public netlist gate missing')
    require(set(result['archives']) == PHYSICAL_ARCHIVES, 'physical archive membership changed')
    storage = read(source, directory + '/storage.json')
    metadata = read(source, directory + '/artifacts.json')['artifacts']
    indexed = read(source, directory + '/zip-files.json')
    require(set(indexed) == PHYSICAL_ARCHIVES, 'physical member index is incomplete')
    archives, external_parts = [], {}
    for name in sorted(PHYSICAL_ARCHIVES):
        matches = [item for item in metadata if item['name'] == name]
        require(len(matches) == 1, 'missing or duplicate original archive: ' + name)
        item = matches[0]
        archive = result['archives'][name]
        require(archive == {'id': item['id'], 'sha256': item['digest'].removeprefix('sha256:'),
                            'bytes': item['size_in_bytes']}, 'audited archive metadata differs: ' + name)
        require(item['workflow_run']['id'] == run_id and
                item['workflow_run']['head_sha'] == result['source_commit'], 'original archive producer differs')
        pieces = storage[str(item['id']) + '.zip']
        require(bool(pieces) and sum(piece['bytes'] for piece in pieces) == item['size_in_bytes'],
                'original archive storage length differs')
        stored = []
        for piece in pieces:
            require(relative(piece['name']).name == piece['name'], 'archive part must be a basename')
            path = directory + '/' + piece['name']
            require(path not in external_parts and piece['bytes'] > 0, 'invalid or repeated original part')
            external_parts[path] = piece['sha256']
            stored.append({'path': path, 'bytes': piece['bytes'], 'sha256': piece['sha256']})
        archives.append({'role': role, 'run_id': run_id, 'artifact_id': item['id'], 'name': name,
                         'asset': 'g4-' + str(run_id) + '-' + name + '.zip',
                         'bytes': item['size_in_bytes'], 'sha256': archive['sha256'], 'storage': stored})
    require(set(storage) == {str(item['artifact_id']) + '.zip' for item in archives},
            'unexpected original archive storage entry')
    frozen = sealed_files(source, directory, external_parts)
    for platform in ('windows', 'linux'):
        replay = json.loads(frozen[directory + '/verification-' + platform + '.json'])
        require(replay['status'].startswith('PASS_') and replay['run_id'] == run_id and
                replay['source_commit'] == result['source_commit'], 'retained replay missing: ' + platform)
    controls = json.loads(frozen[directory + '/controls-result.json'])
    require(controls['status'].startswith('PASS_') and controls['run_id'] == run_id and
            controls['source_commit'] == result['source_commit'] and bool(controls['cases']) and
            all(case['status'].startswith('PASS_') for case in controls['cases']), 'corruption controls missing')
    for name in ('audit.py', 'verify.py', 'controls.py', 'producer.tar.gz', 'producer.json'):
        require(directory + '/' + name in frozen, 'frozen replay dependency missing: ' + name)
    record = {'run_id': run_id, 'source_commit': result['source_commit'],
              'result_path': result_path, 'result_sha256': sha(result_raw),
              'gds_sha256': result['gds_sha256'], 'netlist_sha256': result['netlist_sha256'],
              'physical_metrics': result['physical_metrics'], 'area': result['area'],
              'precheck': result['precheck'], 'public_test_groups': result['netlist_tests']['public_test_groups']}
    return record, frozen, archives, indexed


def stream_original(source, archive, output, expected_members=None):
    """Concatenate committed parts without changing a byte of the original ZIP."""
    target = output / archive['asset']
    total = hashlib.sha256()
    count = 0
    with target.open('xb') as destination:
        for part in archive['storage']:
            digest, length = hashlib.sha256(), 0
            process = subprocess.Popen(['git', 'show', source + ':' + part['path']], cwd=ROOT,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with process.stdout:
                while block := process.stdout.read(1024 * 1024):
                    destination.write(block)
                    digest.update(block)
                    total.update(block)
                    length += len(block)
            error = process.stderr.read()
            process.stderr.close()
            require(process.wait() == 0, 'cannot read committed original part: ' + error.decode(errors='replace'))
            require(length == part['bytes'] and digest.hexdigest() == part['sha256'],
                    'committed original part differs: ' + part['path'])
            count += length
    require(count == archive['bytes'] and total.hexdigest() == archive['sha256'],
            'reconstructed original archive differs: ' + archive['asset'])
    if expected_members is not None:
        with zipfile.ZipFile(target) as packed:
            entries = packed.infolist()
            require(len(entries) == len({entry.filename for entry in entries}), 'duplicate original ZIP member')
            observed = {}
            for entry in entries:
                relative(entry.filename)
                if entry.is_dir():
                    continue
                digest = hashlib.sha256()
                with packed.open(entry) as stream:
                    while block := stream.read(1024 * 1024):
                        digest.update(block)
                observed[entry.filename] = digest.hexdigest()
            require(observed == expected_members, 'original ZIP member index differs: ' + archive['asset'])


def package(output, source=None):
    require(not git('diff', '--name-only', 'HEAD'), 'commit tracked work before packaging')
    head = git('rev-parse', 'HEAD').decode().strip()
    source = head if source is None else source
    require(re.fullmatch('[0-9a-f]{40}', source), '--source must be a full commit SHA')
    require(git('rev-parse', source + '^{commit}').decode().strip() == source, 'source is not a commit')
    require(subprocess.run(['git', 'merge-base', '--is-ancestor', source, head], cwd=ROOT).returncode == 0,
            'source must be an ancestor of the current checkout')
    output = output.resolve()
    require(not output.exists() and output.is_relative_to((ROOT / 'build').resolve()),
            'use a new output directory under build/')
    self_path = Path(__file__).resolve().relative_to(ROOT).as_posix()
    require(blob(source, self_path) == Path(__file__).read_bytes(), 'executed packager differs from source commit')
    notes = blob(source, 'docs/releases/' + TAG + '.md').decode('utf-8')
    require(notes.strip() and not re.search(r'\bDRAFT\b', notes), 'finalize release notes before packaging')
    g3, compiled, frozen, originals = check_g3(source)
    fresh_programs, fresh_files = check_fresh_program_toolchain(source, g3['production'], compiled)
    frozen.update(fresh_files)
    historical = blobs(source, [G2 + '/' + name for name in
                               ('14004891901.zip', 'result.json', 'artifacts.json')])
    qualification = read(source, 'tools/production-profile.json')['qualification']
    require(qualification['path'] == G2 + '/result.json' and
            sha(historical[G2 + '/result.json']) == qualification['sha256'],
            'G2 continuity result differs from the adopted qualification')
    old_result = json.loads(historical[G2 + '/result.json'])
    old_metadata = json.loads(historical[G2 + '/artifacts.json'])['artifacts']
    old_matches = [item for item in old_metadata if item['id'] == 14004891901 and item['name'] == 'tt_submission']
    require(len(old_matches) == 1, 'G2 continuity archive metadata missing')
    old_archive = old_matches[0]
    old_raw = historical[G2 + '/14004891901.zip']
    require(old_archive['workflow_run']['id'] == g3['production']['qualified_run_id'] and
            old_archive['workflow_run']['head_sha'] == g3['production']['qualified_source_commit'] and
            len(old_raw) == old_archive['size_in_bytes'] == old_result['archives']['tt_submission']['bytes'] and
            'sha256:' + sha(old_raw) == old_archive['digest'] and
            sha(old_raw) == old_result['archives']['tt_submission']['sha256'],
            'G2 continuity original archive differs')
    frozen.update(historical)
    reproduction_path = EVIDENCE + '/reproduction.json'
    reproduction_raw = blob(source, reproduction_path)
    reproduction = json.loads(reproduction_raw)
    require(reproduction['schema'] == 'protocol-emulator-g4-reproduction-v1' and
            reproduction['status'] == 'PASS_REPRODUCED_G4_PHYSICAL_CANDIDATE', 'G4 reproduction is not qualified')
    require(set(reproduction['runs']) == set(RUNS), 'reproduction run membership differs')
    require({'normalized_gds', 'netlist', 'metrics', 'public_records', 'stages'} <= set(reproduction['comparisons'])
            and 'g2_continuity' in reproduction, 'reproduction comparison scope incomplete')
    dispatch = read(source, EVIDENCE + '/dispatches.json')
    require(dispatch['source_commit'] == reproduction['source_commit'] and
            {item['id'] for item in dispatch['runs']} == set(RUNS.values()) and
            all(item['head_sha'] == reproduction['source_commit'] for item in dispatch['runs']),
            'registered physical run identity changed')
    physical, indices = {}, {}
    for role, run_id in RUNS.items():
        record, files, archives, indexed = check_physical(source, role, run_id, reproduction, g3['production'])
        physical[role] = record
        frozen.update(files)
        originals.extend(archives)
        for archive in archives:
            indices[archive['asset']] = indexed[archive['name']]
    excluded = {part['path'] for archive in originals for part in archive['storage']}
    frozen.update(blobs(source, [name for name in names_at(source, EVIDENCE) if name not in excluded]))
    source_names = names_at(source, 'docs') + names_at(source, 'programs/od128-sram-v1')
    source_names += list(g3['production']['files_sha256'])
    source_names += ['LICENSE', 'info.yaml', 'tools/assembler.py', 'tools/production-profile.json',
                     'tools/workbench/toolchain.lock.json']
    source_files = blobs(source, source_names)
    manifest = {'schema': 'protocol-emulator-g4-release-package-v1', 'tag': TAG,
                'release_source_commit': source, 'target': 'od128-sram-v1', 'interface_id': '0x22',
                'g3': g3, 'fresh_program_toolchain': fresh_programs, 'physical_runs': physical,
                'reproduction': {'path': reproduction_path, 'sha256': sha(reproduction_raw), 'record': reproduction},
                'original_archives': originals,
                'source_members_sha256': {name: sha(raw) for name, raw in sorted(source_files.items())},
                'frozen_evidence_members_sha256': {name: sha(raw) for name, raw in sorted(frozen.items())},
                'compiled_members_sha256': {name: sha(raw) for name, raw in sorted(compiled.items())},
                'scope': 'Prepared G4 source, software and original physical qualification assets. Public-download, release-tag and image verification are separate; no actual competition submission, analog, silicon, Fmax or owner-fluency claim.'}
    files = {**source_files, **frozen, **{'compiled/' + name: raw for name, raw in compiled.items()}}
    require(len(files) == len(source_files) + len(frozen) + len(compiled), 'bundle path collision')
    files['g4-submission.json'] = encoded(manifest)
    files['restore-originals.py'] = RESTORE_SCRIPT.encode('utf-8')
    files['README.md'] = f'''# G4 submission candidate ({TAG})

Release source: {source}
Physical source: {reproduction['source_commit']}
Interface: 0x22 / od128-sram-v1 / 128 logical program words.

Start with docs/submission.md, docs/architecture.md, docs/isa.md and
docs/programming.md. The compiled/ directory contains the thirteen original
qualified program binaries, decoded images, timing listings and load plans.
The source assembler uses Python 3.11+ and its standard library:

```
python tools/assembler.py programs/od128-sram-v1/uart_tx.asm --out build/my-uart
```

Use a new output directory. Full simulation and source-history checks use a
complete repository checkout and its pinned workbench; this readable bundle
does not replace that checkout:

https://github.com/KG-khangelani/protocol-emulator-asic/tree/{source}

Download the fourteen separate g4-*.zip original-archive assets listed in
g4-submission.json. Verify them against g4-SHA256SUMS, then restore the exact
retained filenames/parts beside the frozen replay scripts:

```
python restore-originals.py --assets /path/to/downloaded-assets
```

The restore command checks full ZIP and part hashes and preserves existing
files. E0047's per-run README files give the frozen physical replay commands.
The G3 historical audit additionally requires the original repository Git
history. The source and each compiled/evidence member are individually hashed.
Stored ZIP entries with fixed metadata make this package platform independent.

Follow the documented host ownership, UART service, SPI hold and I2C pull-up
requirements. The physical timing target is not measured maximum frequency;
functional netlist simulation is not analog or fabricated-chip testing.
Publication verification is a separate recorded gate. No competition entry
has been sent by packaging these files.
'''.encode('utf-8')
    output.mkdir(parents=True)
    for archive in originals:
        stream_original(source, archive, output, indices.get(archive['asset']))
    with zipfile.ZipFile(output / 'g4-submission-bundle.zip', 'x', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    manifest['bundle_members_sha256'] = {name: sha(raw) for name, raw in sorted(files.items())}
    manifest['artifacts'] = {}
    for path in sorted(output.glob('*.zip')):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        manifest['artifacts'][path.name] = {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}
    (output / 'g4-submission.json').write_bytes(encoded(manifest))
    (output / 'g4-SHA256SUMS').write_bytes(''.join(
        (manifest['artifacts'][path.name]['sha256'] if path.suffix == '.zip' else sha(path.read_bytes()))
        + '  ' + path.name + '\n' for path in sorted(output.iterdir())).encode('utf-8'))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source', help='Full committed source SHA; defaults to HEAD')
    args = parser.parse_args()
    result = package(args.out, args.source)
    print('PACKAGED_G4_SUBMISSION', result['release_source_commit'],
          len(result['bundle_members_sha256']), 'members', len(result['artifacts']) + 2, 'assets')
