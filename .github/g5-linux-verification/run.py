# SPDX-License-Identifier: Apache-2.0
"""Run anonymous publication verification against the exact G5 release checkout."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'build/g5-linux-proof'
REQUEST = json.loads((HERE / 'request.json').read_bytes())


def encoded(value): return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, name, timeout=900, cwd=ROOT):
    log = OUT / (name + '.log')
    receipt = {'command': command, 'cwd': str(cwd), 'started_utc': datetime.now(timezone.utc).isoformat()}
    started = time.monotonic()
    try:
        with log.open('wb') as stream:
            result = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        receipt['returncode'] = result.returncode
        if result.returncode:
            raise RuntimeError(name + ' failed: ' + str(result.returncode))
        return log.read_bytes()
    except Exception as error:
        receipt['error'] = str(error)
        raise
    finally:
        receipt.update(log_sha256=sha(log), elapsed_seconds=time.monotonic() - started)
        (OUT / (name + '.json')).write_bytes(encoded(receipt))


def main():
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    (OUT / 'runner.py').write_bytes(Path(__file__).read_bytes())
    (OUT / 'request.json').write_bytes(encoded(REQUEST))
    auditor = HERE / 'verify_publication.py'
    assert sha(auditor) == REQUEST['auditor_sha256']
    (OUT / 'verify_publication.py').write_bytes(auditor.read_bytes())
    result = {'schema': 'protocol-emulator-g5-linux-publication-v1', 'status': 'RUNNING',
              'source_commit': REQUEST['source_commit'], 'ci_source_commit': os.environ['GITHUB_SHA'],
              'run_id': os.environ['GITHUB_RUN_ID'], 'job': os.environ['GITHUB_JOB'],
              'started_utc': datetime.now(timezone.utc).isoformat()}
    source = Path(os.environ['RUNNER_TEMP']) / 'g5-release-source'
    image = REQUEST['image']
    base = source / 'build/g5-publication'
    try:
        for name, expected in REQUEST['inputs_sha256'].items():
            assert sha(HERE / 'publication-inputs' / name) == expected, name
        run(['git', 'clone', '--branch', 'main', '--single-branch',
             'https://github.com/KG-khangelani/protocol-emulator-asic.git', str(source)], 'clone-source')
        run(['git', 'checkout', '--detach', REQUEST['source_commit']], 'checkout-source', cwd=source)
        assert run(['git', 'rev-parse', 'HEAD'], 'source-head', cwd=source).decode().strip() == REQUEST['source_commit']
        assert not run(['git', 'status', '--porcelain'], 'source-status', cwd=source).strip()
        run(['docker', 'version'], 'docker-version')
        run(['docker', 'pull', image], 'image-pull')
        before = json.loads(run(['docker', 'image', 'inspect', image], 'image-inspect-before'))
        assert len(before) == 1 and before[0]['Id'] == REQUEST['image_id'] and image in before[0]['RepoDigests']
        assert before[0]['Os'] == 'linux' and before[0]['Architecture'] == 'amd64'
        assert before[0]['Config']['Labels']['org.opencontainers.image.revision'] == REQUEST['image_source']
        result['audit_runtime'] = {'ref': image, 'id': before[0]['Id'], 'source': REQUEST['image_source']}
        command = ['docker', 'run', '--rm', '--pull=never', '--init', '--user', f'{os.getuid()}:{os.getgid()}',
                   '--env', 'HOME=/tmp', '--mount', f'type=bind,source={source},target=/workspace',
                   '--mount', f'type=bind,source={HERE},target=/audit,readonly', '--workdir', '/workspace', image, 'python3']
        run(command + ['evidence/E0048-waveform-replay/release-tools/package.py', '--source', REQUEST['source_commit'],
                       '--out', 'build/g5-assets'], 'package')
        base.mkdir(parents=True)
        for name in REQUEST['inputs_sha256']:
            shutil.copy2(HERE / 'publication-inputs' / name, base / name)
        run(command + ['/audit/verify_publication.py', '--repository', '/workspace',
                       '--directory', '/workspace/build/g5-publication', '--assets', '/workspace/build/g5-assets'], 'publication')
        checked = json.loads((base / 'verification.json').read_bytes())
        assert checked['status'] == 'PASS_G5_RELEASE_AND_PACKAGE' and checked['source_commit'] == REQUEST['source_commit']
        after = json.loads(run(['docker', 'image', 'inspect', image], 'image-inspect-after'))
        assert before == after
        result.update(status='PASS_G5_PUBLICATION_IN_PINNED_LINUX', verification_sha256=sha(base / 'verification.json'))
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        # Preserve downloaded originals and small audit outputs, including any
        # failed attempt. Generated extraction/source copies stay in CI scratch.
        if base.exists():
            retained = OUT / 'publication'
            retained.mkdir()
            for path in base.iterdir():
                if path.is_file():
                    shutil.copy2(path, retained / path.name)
                elif path.name in ('downloaded', 'downloaded-smoke'):
                    shutil.copytree(path, retained / path.name)
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (OUT / 'result.json').write_bytes(encoded(result))


if __name__ == '__main__':
    main()
