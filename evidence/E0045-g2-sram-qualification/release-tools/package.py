"""Package the exact qualified G2 sources, complete research trail and original archives."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.production_sram import verify

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def write(path, data):
    path.write_bytes((json.dumps(data, indent=2) + '\n').encode())

def check_verification_inputs(inputs, head):
    """Compare actual committed bytes; Windows checkout line endings are not Git blobs."""
    names = sorted(inputs)
    for offset in range(0, len(names), 100):
        selected = names[offset:offset + 100]
        packed = git('archive', '--format=tar', head, '--', *selected)
        seen = set()
        with tarfile.open(fileobj=io.BytesIO(packed)) as archive:
            for entry in archive:
                if entry.isdir():
                    continue
                assert entry.isfile() and entry.name in selected and entry.name not in seen
                seen.add(entry.name)
                assert sha(archive.extractfile(entry).read()) == inputs[entry.name], entry.name
        assert seen == set(selected)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--normal-ci', type=Path, required=True)
    args = parser.parse_args()
    ci = args.normal_ci.resolve()
    assert ci.is_relative_to(ROOT / 'evidence/E0045-g2-sram-qualification')
    assert not git('diff', '--name-only', 'HEAD')
    untracked = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
    assert set(untracked) <= {'.devcontainer/devcontainer-lock.json'}, untracked
    production = verify(ROOT)
    profile = read(ROOT / 'tools/production-profile.json')
    physical = read(ROOT / profile['qualification']['path'])
    normal = read(ci / 'verification.json')
    assert normal['status'] == 'PASS_DEFAULT_PRODUCTION_COMMAND_CI_ORIGINAL_ARCHIVE'
    assert normal['production'] == production
    inputs = read(ci / 'inputs.json')['files']
    head = git('rev-parse', 'HEAD').decode().strip()
    # Qualified physical files are also checked byte-for-byte in verify(ROOT).
    # Every other input must match the clean CI Git bytes, without normalizing it.
    check_verification_inputs(inputs, head)
    out = ROOT / 'build/g2-release-assets' / head
    assert not out.exists()
    out.mkdir(parents=True)
    assets = []
    physical_dir = ROOT / profile['qualification']['path']
    physical_dir = physical_dir.parent
    for name, meta in sorted(physical['archives'].items()):
        raw = (physical_dir / (str(meta['id']) + '.zip')).read_bytes()
        assert sha(raw) == meta['sha256'] and len(raw) == meta['bytes']
        target = out / ('g2-sram-' + name + '.zip')
        target.write_bytes(raw)
        assets.append({'name': target.name, 'sha256': sha(raw), 'bytes': len(raw),
                       'artifact_id': meta['id'], 'run_id': physical['run_id'],
                       'original_archive_unchanged': True})
    raw = (ci / (str(normal['artifact_id']) + '.zip')).read_bytes()
    assert sha(raw) == normal['original_zip_sha256'] and len(raw) == normal['original_zip_bytes']
    target = out / 'g2-production-current.zip'
    target.write_bytes(raw)
    assets.append({'name': target.name, 'sha256': sha(raw), 'bytes': len(raw),
                   'artifact_id': normal['artifact_id'], 'run_id': normal['run_id'],
                   'original_archive_unchanged': True})
    paths = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'evidence').iterdir()
                   if p.is_dir() and ((p.name.startswith('E00') and 32 <= int(p.name[3:5]) <= 45)
                                     or p.name == 'UI0002-sram-atlas-preparation'))
    paths += ['docs/decisions', 'docs/specs/g2-production-profile.md', 'tools/production-profile.json']
    names = git('ls-tree', '-r', '--name-only', head, '--', *paths).decode().splitlines()
    expected_names = set(names)
    assert len(names) == len(expected_names) and len(names) > 1000
    bundle = out / 'g2-sram-evidence.zip'
    members = {}
    # Stream committed bytes rather than a mutable working tree; preserve every failed trial.
    process = subprocess.Popen(['git', 'archive', '--format=tar', head, '--', *paths], cwd=ROOT, stdout=subprocess.PIPE)
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zipped:
        with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
            for entry in archive:
                if entry.isdir():
                    continue
                assert entry.isfile() and entry.name in expected_names and entry.name not in members
                raw = archive.extractfile(entry).read()
                info = zipfile.ZipInfo(entry.name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED if entry.name.endswith(('.gz', '.zip', '.png')) else zipfile.ZIP_DEFLATED
                zipped.writestr(info, raw)
                members[entry.name] = sha(raw)
    assert process.wait() == 0 and set(members) == expected_names
    raw = bundle.read_bytes()
    assets.append({'name': bundle.name, 'sha256': sha(raw), 'bytes': len(raw), 'files': len(members),
                   'scope': 'Complete committed E0032-E0045 research trail, UI0002 and decisions, including original failures, frozen inputs and replay tools.'})
    manifest = {'schema': 'protocol-emulator-g2-release-artifacts-v1', 'status': 'QUALIFIED_PRODUCTION_PACKAGE',
                'release_source_commit': head, 'tag': profile['release_tag'],
                'physical_source_commit': physical['source_commit'], 'physical_run_id': physical['run_id'],
                'normal_command_source_commit': normal['source_commit'], 'normal_command_run_id': normal['run_id'],
                'normal_command_record': ci.relative_to(ROOT).as_posix() + '/verification.json',
                'normal_command_verification_input_files': len(inputs),
                'all_verification_inputs_unchanged_at_release': True,
                'production': production, 'decision_file': profile['decision'],
                'decision_sha256': profile['decision_sha256'], 'profile_sha256': sha((ROOT / 'tools/production-profile.json').read_bytes()),
                'gds_sha256': physical['gds_sha256'], 'netlist_sha256': physical['netlist_sha256'],
                'artifacts': assets, 'evidence_members_sha256': members,
                'scope': 'Qualified shared-core UART TX/bounded RX, held-input four-mode SPI and Standard-mode digital I2C production. Physical source differs from publication source; all twenty design/flow inputs and all clean-CI verification inputs are byte-identical. Not silicon, analog compliance, measured Fmax, unrestricted interoperability or owner fluency.'}
    write(out / 'g2-sram-publication.json', manifest)
    (out / 'g2-sram-SHA256SUMS').write_bytes(''.join(sha(p.read_bytes()) + '  ' + p.name + '\n'
        for p in sorted(out.iterdir()) if p.is_file() and p.name != 'g2-sram-SHA256SUMS').encode())
    print(json.dumps({'output': str(out), 'assets': len(list(out.iterdir())), 'evidence_files': len(members),
                      'bytes': sum(p.stat().st_size for p in out.iterdir())}, indent=2))

if __name__ == '__main__':
    main()
