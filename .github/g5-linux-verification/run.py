# SPDX-License-Identifier: Apache-2.0
"""Execute and retain G5 package verification in the actual pinned Linux image."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/g5-linux-proof'
REQUEST = json.loads(Path(__file__).with_name('request.json').read_bytes())


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, name, timeout=600, cwd=ROOT):
    path = OUT / (name + '.log')
    receipt = {'command': command, 'cwd': str(cwd), 'started_utc': datetime.now(timezone.utc).isoformat()}
    started = time.monotonic()
    try:
        with path.open('wb') as log:
            completed = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        receipt['returncode'] = completed.returncode
        if completed.returncode:
            raise RuntimeError(name + ' failed: ' + str(completed.returncode))
        return path.read_bytes()
    except Exception as error:
        receipt['error'] = str(error)
        raise
    finally:
        receipt.update(elapsed_seconds=time.monotonic() - started, log_sha256=sha(path))
        (OUT / (name + '.json')).write_bytes(encoded(receipt))


def main():
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    (OUT / 'runner.py').write_bytes(Path(__file__).read_bytes())
    (OUT / 'request.json').write_bytes(encoded(REQUEST))
    result = {'schema': 'protocol-emulator-g5-linux-package-v1', 'status': 'RUNNING',
              'source_commit': REQUEST['source_commit'], 'ci_source_commit': os.environ['GITHUB_SHA'],
              'run_id': os.environ['GITHUB_RUN_ID'], 'job': os.environ['GITHUB_JOB'],
              'started_utc': datetime.now(timezone.utc).isoformat()}
    source = Path(os.environ['RUNNER_TEMP']) / 'g5-release-source'
    image = REQUEST['image']
    try:
        run(['git', 'clone', '--branch', 'main', '--single-branch',
             'https://github.com/KG-khangelani/protocol-emulator-asic.git', str(source)], 'clone-source')
        run(['git', 'checkout', '--detach', REQUEST['source_commit']], 'checkout-source', cwd=source)
        assert run(['git', 'rev-parse', 'HEAD'], 'source-head', cwd=source).decode().strip() == REQUEST['source_commit']
        assert not run(['git', 'status', '--porcelain'], 'source-status', cwd=source).strip()
        run(['docker', 'version'], 'docker-version')
        run(['docker', 'pull', image], 'image-pull')
        before = json.loads(run(['docker', 'image', 'inspect', image], 'image-inspect-before'))
        assert len(before) == 1 and before[0]['Id'] == REQUEST['image_id']
        assert image in before[0]['RepoDigests'] and before[0]['Os'] == 'linux' and before[0]['Architecture'] == 'amd64'
        assert before[0]['Config']['Labels']['org.opencontainers.image.revision'] == REQUEST['image_source']
        result['image'] = {'ref': image, 'id': before[0]['Id'], 'source': REQUEST['image_source']}
        base = ['docker', 'run', '--rm', '--pull=never', '--network=none', '--init', '--user', f'{os.getuid()}:{os.getgid()}',
                '--env', 'HOME=/tmp', '--mount', f'type=bind,source={source},target=/workspace',
                '--workdir', '/workspace', image, 'python3']
        ev = 'evidence/E0048-waveform-replay/'
        run(base + [ev + 'verify.py', '--directory', ev + 'ci-66743b6', '--output', 'build/g5-audit.json'], 'audit')
        run(base + [ev + 'controls.py', '--directory', ev + 'ci-66743b6', '--output', 'build/g5-controls.json'], 'controls')
        run(base + [ev + 'release-tools/package.py', '--source', REQUEST['source_commit'], '--out', 'build/g5-assets'], 'package')
        run(base + [ev + 'release-tools/package.py', '--smoke', 'build/g5-assets', '--out', 'build/g5-smoke'], 'smoke')
        for name in ('g5-audit.json', 'g5-controls.json'):
            shutil.copy2(source / 'build' / name, OUT / name)
        shutil.copytree(source / 'build/g5-assets', OUT / 'assets')
        shutil.copytree(source / 'build/g5-smoke', OUT / 'smoke')
        actual = {path.name: {'bytes': path.stat().st_size, 'sha256': sha(path)} for path in sorted((OUT / 'assets').iterdir())}
        assert actual == REQUEST['windows_assets'], 'Linux and Windows package bytes differ'
        after = json.loads(run(['docker', 'image', 'inspect', image], 'image-inspect-after'))
        assert before == after
        result.update(status='PASS_G5_LINUX_PACKAGE_AND_WINDOWS_IDENTITY', assets=actual)
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (OUT / 'result.json').write_bytes(encoded(result))


if __name__ == '__main__':
    main()
