# SPDX-License-Identifier: Apache-2.0
"""Verify G5 public downloads, original publisher execution and registry identity."""
import argparse
import ast
import concurrent.futures
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

REPO = 'KG-khangelani/protocol-emulator-asic'
TAG = 'v0.1.1'
SOURCE = '022834146efcb5f388a4d6ec23b3b705a0df7ef8'
WORKFLOWS = {'test', 'docs', 'atlas', 'i2c-general', 'sram-candidate',
             'spi-program-sensitivity', 'spi-timed-gpio', 'program-tools', 'waveform-replay', 'publish'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(urllib.parse.urlsplit(newurl).scheme == 'https', 'refuse a non-HTTPS redirect')
        same = urllib.parse.urlsplit(req.full_url).netloc == urllib.parse.urlsplit(newurl).netloc
        forwarded = {key: value for key, value in req.headers.items()
                     if key.lower() not in ('content-length', 'content-type') and
                     (same or key.lower() != 'authorization')}
        require(req.get_method() in ('GET', 'HEAD'), 'unexpected public verification request method')
        return urllib.request.Request(newurl, headers=forwarded, method=req.get_method())


def fetch(url, *, headers=None, method='GET'):
    # Tokens are held only in memory; never forward them to a different host.
    request = urllib.request.Request(url, headers={'User-Agent': 'protocol-emulator-g5-audit', **(headers or {})}, method=method)
    with urllib.request.build_opener(Redirect).open(request, timeout=90) as response:
        require(response.status == 200, 'public request failed')
        return (response.read() if method == 'GET' else b''), dict(response.headers)


def audit(root, base, assets):
    require(sys.platform.startswith('linux'), 'replay the publisher waveform parsers in pinned Linux')
    require(base.is_relative_to(root / 'build') and assets.is_relative_to(root / 'build'), 'outputs must remain under build/')
    git = lambda *args: subprocess.check_output(['git', *args], cwd=root)
    require(git('rev-parse', 'HEAD').decode().strip() == SOURCE, 'audit must use the exact release checkout')
    run, jobs, release, tag_ref, tag_object, tag_runs = [read(base / name) for name in
        ('run.json', 'jobs.json', 'release.json', 'tag-ref.json', 'tag-object.json', 'tag-workflows.json')]
    require(run['head_sha'] == SOURCE and run['head_branch'] == TAG and run['event'] == 'push' and
            run['path'] == '.github/workflows/publish.yaml' and run['status'] == 'completed' and
            run['conclusion'] == 'success', 'wrong or incomplete publisher')
    require(len(jobs['jobs']) == 1, 'expected one publisher job')
    job = jobs['jobs'][0]
    require(job['name'] == 'workbench' and job['run_id'] == run['id'] and job['head_sha'] == SOURCE and
            job['run_attempt'] == run['run_attempt'] and job['conclusion'] == 'success' and
            all(step['conclusion'] == 'success' for step in job['steps']), 'publisher job did not fully pass')
    require({item['name'] for item in tag_runs['runs']} == WORKFLOWS and len(tag_runs['runs']) == len(WORKFLOWS),
            'tag workflow set differs')
    tag_jobs = {}
    for item in tag_runs['runs']:
        require(item['head_sha'] == SOURCE and item['head_branch'] == TAG and item['event'] == 'push' and
                item['status'] == 'completed' and item['conclusion'] == 'success', 'tag workflow incomplete: ' + item['name'])
        entries = tag_runs['jobs'][str(item['id'])]['jobs']
        require(entries and all(j['run_id'] == item['id'] and j['head_sha'] == SOURCE and
                j['run_attempt'] == item['run_attempt'] and j['status'] == 'completed' and j['conclusion'] == 'success'
                for j in entries), 'tag job failed or missing: ' + item['name'])
        tag_jobs[item['name']] = {'run_id': item['id'], 'jobs': {j['name']: j['id'] for j in entries}}
    require(tag_jobs['publish']['run_id'] == run['id'], 'publisher run differs from tag evidence')
    require(release['tag_name'] == TAG and not release['draft'] and not release['prerelease'], 'release is not stable/public')
    require(tag_ref['ref'] == 'refs/tags/' + TAG and tag_ref['object']['type'] == 'tag' and
            tag_ref['object']['sha'] == tag_object['sha'] and tag_object['tag'] == TAG and
            tag_object['object']['type'] == 'commit' and tag_object['object']['sha'] == SOURCE, 'tag source differs')
    notes = git('show', SOURCE + ':docs/releases/' + TAG + '.md').decode().strip()
    require(release['body'].replace('\r\n', '\n').strip().startswith(notes), 'release notes do not preserve the qualified source account')
    matches = [a for a in read(base / 'artifacts.json')['artifacts'] if a['name'] == 'publication-' + SOURCE]
    require(len(matches) == 1, 'publisher artifact missing or ambiguous')
    artifact = matches[0]
    require(artifact['workflow_run']['id'] == run['id'] and artifact['workflow_run']['head_sha'] == SOURCE,
            'publisher artifact source differs')
    original = base / (str(artifact['id']) + '.zip')
    raw = original.read_bytes()
    require(len(raw) == artifact['size_in_bytes'] and 'sha256:' + sha(raw) == artifact['digest'], 'publisher transport differs')
    spec = importlib.util.spec_from_file_location('g5_publication_retained_audit', root / 'evidence/E0048-waveform-replay/verify.py')
    retained = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(retained)
    members = retained.zip_members(raw)
    ci = base / 'original'
    require(not ci.exists(), 'preserve old extraction; use a fresh audit directory')
    for name, data in members.items():
        path = ci / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    write(base / 'zip-files.json', {name: sha(data) for name, data in sorted(members.items())})
    pubdirs = list(ci.rglob('publication.json'))
    require(len(pubdirs) == 1, 'publisher output location is ambiguous')
    pubdir = pubdirs[0].parent
    pipeline = ci / 'build/current'
    evidence = read(pipeline / 'evidence.json')
    inputs = evidence['verification_inputs']
    profile_source = git('show', SOURCE + ':tools/current_profile.py')
    function = next(node for node in ast.parse(profile_source).body if isinstance(node, ast.FunctionDef) and node.name == 'verification_inputs')
    constants = {node.targets[0].id: ast.literal_eval(node.value) for node in function.body
                 if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id in ('prefixes', 'singles')}
    selection = json.loads(git('show', SOURCE + ':tools/production-profile.json'))
    required = set(constants['singles']) | set(selection['files_sha256']) | {selection['decision']}
    required.update(selection[key]['path'] for key in
                    ('qualification', 'combined_regression', 'normal_command_verification', 'corrected_netlist_pair'))
    paths = set(git('ls-tree', '-r', '--name-only', SOURCE).decode().splitlines())
    expected = {name for name in paths if name.startswith(constants['prefixes']) or name in required}
    require(required <= expected and set(inputs) == expected, 'publisher input membership differs from source contract')
    frozen = base / 'inputs'
    require(not frozen.exists(), 'preserve previous frozen source')
    source_files = retained.git_bytes(SOURCE, sorted(inputs))
    require({name: sha(data) for name, data in source_files.items()} == inputs, 'publisher inputs differ from release Git blobs')
    for name, data in source_files.items():
        path = frozen / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    sys.path[:0] = [str(frozen / 'tools'), str(frozen)]
    from current_run import STAGES, retained_files, semantic_check
    from current_profile import describe
    from tools.production_sram import verify
    require(Path(sys.modules['current_run'].__file__).resolve().is_relative_to(frozen), 'wrong verification implementation imported')
    production = verify(frozen)
    profile = describe(frozen / 'src')
    require(evidence['status'] == 'PASS' and evidence['profile'] == profile and set(evidence['stages']) == set(STAGES),
            'normal-command publisher verification incomplete')
    require(read(pubdir / 'production-verification.json') == evidence, 'published default-command evidence differs')
    runtime = None
    stages = {}
    for action in STAGES:
        receipt = read(pipeline / 'receipts' / (action + '.json'))
        require(receipt == evidence['stages'][action] and receipt['status'] == 'PASS' and receipt['action'] == action and
                receipt['profile'] == profile and receipt['git_head'] == SOURCE and
                receipt['source_directory'] == '/workspace/src' and receipt['verification_inputs'] == inputs,
                'normal-command source identity differs: ' + action)
        relative = PurePosixPath(receipt['directory']).relative_to('build/current')
        stage = (pipeline / relative).resolve()
        require(stage.is_relative_to(pipeline) and receipt['commands'] and all(c['returncode'] == 0 for c in receipt['commands']),
                'normal-command receipt incomplete: ' + action)
        require(receipt['artifact_sha256'] == retained_files(stage), 'normal-command artifact bytes differ: ' + action)
        stages[action] = semantic_check(action, stage, profile)
        require(stages[action] == receipt['summary'] and receipt['artifact_sha256'] == retained_files(stage),
                'normal-command semantic replay differs: ' + action)
        if action == 'doctor':
            runtime = sha((stage / 'run.log').read_bytes())
        require(receipt['runtime_identity'] == runtime, 'stage workbench identity differs')
    checks = sorted((pipeline / 'runs').glob('*-check'))
    require(len(checks) == 2 and len(list((pipeline / 'runs').iterdir())) == 9, 'publisher stage executions incomplete')
    for check in checks:
        log = (check / 'run.log').read_text()
        counts = re.findall(r'^Ran (\d+) tests? in ', log, re.M)
        require(sum(map(int, counts)) == 159 and len(re.findall(r'^OK$', log, re.M)) == len(counts) and
                not re.search(r'^(FAILED|ERROR|FAIL:)', log, re.M), 'publisher repository tests incomplete')
    local = {path.name: path for path in assets.iterdir() if path.is_file()}
    published = {path.name: path for path in pubdir.iterdir() if path.is_file()}
    inventory = {asset['name']: asset for asset in release['assets']}
    require(set(local).isdisjoint(published) and set(inventory) == set(local) | set(published) and
            len(inventory) == len(release['assets']) == 22, 'release asset set is incomplete')
    downloaded = base / 'downloaded'
    require(not downloaded.exists(), 'use a fresh public download directory')
    downloaded.mkdir()
    def download(meta):
        name = meta['name']
        require(re.fullmatch(r'[A-Za-z0-9_.-]+', name) and name not in ('.','..'), 'unsafe asset name')
        require(meta['browser_download_url'].startswith('https://github.com/' + REPO + '/releases/download/' + TAG + '/'), 'wrong public asset URL')
        data, headers = fetch(meta['browser_download_url'])
        require(len(data) == meta['size'] and 'sha256:' + sha(data) == meta['digest'], 'anonymous asset digest differs: ' + name)
        require(data == (local.get(name) or published[name]).read_bytes(), 'download differs from qualified original: ' + name)
        (downloaded / name).write_bytes(data)
        return name, {'id': meta['id'], 'bytes': len(data), 'sha256': sha(data), 'anonymous_download': True, 'url': meta['browser_download_url']}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        download_records = dict(pool.map(download, inventory.values()))
    for checksum, names in (('SHA256SUMS', set(published)), ('g5-SHA256SUMS', set(local))):
        listed = set()
        for line in (downloaded / checksum).read_text().splitlines():
            digest, name = line.split('  ', 1)
            require(name not in listed and re.fullmatch('[0-9a-f]{64}', digest) and download_records[name]['sha256'] == digest,
                    'downloaded checksum manifest differs')
            listed.add(name)
        require(listed == names - {checksum}, 'checksum manifest membership differs')
    publication = read(downloaded / 'publication.json')
    require(publication['source_commit'] == SOURCE and publication['ref'] == 'refs/tags/' + TAG and
            publication['production_qualification'] == production and
            publication['verification_run'].endswith('/' + str(run['id'])), 'publication manifest source/production differs')
    spec = importlib.util.spec_from_file_location('g5_downloaded_package', root / 'evidence/E0048-waveform-replay/release-tools/package.py')
    packager = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = packager
    spec.loader.exec_module(packager)
    bundle = read(downloaded / 'g5-waveform-replay.json')
    require(bundle['release_source_commit'] == SOURCE and bundle['verification_inputs_unchanged'] == 366 and
            bundle['production'] == production, 'downloaded G5 package source/production differs')
    require({name: sha(data) for name, data in retained.git_bytes(SOURCE, sorted(bundle['qualified_inputs_sha256'])).items()} ==
            bundle['qualified_inputs_sha256'], 'downloaded G5 input map differs from release source')
    require(inputs.items() <= bundle['qualified_inputs_sha256'].items(), 'publisher input map differs from G5 qualification')
    smoke = packager.smoke(downloaded, base / 'downloaded-smoke')
    require(smoke['status'] == 'PASS_G5_STANDALONE_DISTRIBUTION', 'downloaded standalone bundle failed')
    original_g5 = root / 'evidence/E0048-waveform-replay/ci-66743b6/14155007514.zip'
    require((downloaded / 'g5-original-ci.zip').read_bytes() == original_g5.read_bytes(), 'downloaded G5 CI archive differs')
    registry = 'kg-khangelani/protocol-emulator-asic-workbench'
    prefix = 'ghcr.io/' + registry + '@'
    require(publication['image'].startswith(prefix), 'wrong image registry')
    digest = publication['image'].removeprefix(prefix)
    token_url = 'https://ghcr.io/token?' + urllib.parse.urlencode({'service':'ghcr.io','scope':'repository:' + registry + ':pull'})
    token = json.loads(fetch(token_url)[0])['token']
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json'}
    registry_get = lambda path: fetch('https://ghcr.io/v2/' + registry + '/' + path, headers=headers)[0]
    raw = registry_get('manifests/' + digest)
    require('sha256:' + sha(raw) == digest, 'registry manifest digest differs')
    (base / 'registry-manifest.json').write_bytes(raw)
    manifest = json.loads(raw)
    for tag in (TAG, 'sha-' + SOURCE):
        require('sha256:' + sha(registry_get('manifests/' + tag)) == digest, 'published image tag differs: ' + tag)
    child = digest
    if 'manifests' in manifest:
        matches = [m for m in manifest['manifests'] if m.get('platform',{}).get('os') == 'linux' and m.get('platform',{}).get('architecture') == 'amd64']
        require(len(matches) == 1, 'ambiguous Linux image platform')
        child = matches[0]['digest']; raw = registry_get('manifests/' + child)
        require('sha256:' + sha(raw) == child, 'Linux image manifest digest differs')
        (base / 'registry-linux-amd64.json').write_bytes(raw)
        manifest = json.loads(raw)
    raw = registry_get('blobs/' + manifest['config']['digest'])
    require('sha256:' + sha(raw) == manifest['config']['digest'], 'registry config digest differs')
    (base / 'registry-config.json').write_bytes(raw)
    config = json.loads(raw); labels = config['config']['Labels']
    require(config['os'] == 'linux' and config['architecture'] == 'amd64' and
            labels['org.opencontainers.image.revision'] == labels['org.opencontainers.image.version'] == SOURCE and
            labels['org.opencontainers.image.source'] == 'https://github.com/' + REPO, 'registry image source differs')
    inspection = read(downloaded / 'image-inspect.json')
    require(len(inspection) == 1 and inspection[0]['Id'] == manifest['config']['digest'] and
            inspection[0]['Config']['Labels'] == labels, 'published image differs from actual verified local image')
    joblog = gzip.decompress((base / 'job.log.gz').read_bytes()).decode('utf-8-sig')
    require(re.findall(r'"containerimage.config.digest": "(sha256:[0-9a-f]{64})"', joblog) == [inspection[0]['Id']] and
            artifact['digest'].removeprefix('sha256:') in joblog and str(artifact['id']) in joblog,
            'actual publisher log does not bind image and artifact')
    def head_layer(layer):
        data, returned = fetch('https://ghcr.io/v2/' + registry + '/blobs/' + layer['digest'], headers=headers, method='HEAD')
        length = next(value for name, value in returned.items() if name.lower() == 'content-length')
        require(not data and int(length) == layer['size'], 'public layer access or size differs')
        return {'digest': layer['digest'], 'bytes': layer['size'], 'anonymous_head_status': 200}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        layers = list(pool.map(head_layer, manifest['layers']))
    result = {'schema': 'protocol-emulator-g5-publication-verification-v1', 'status': 'PASS_G5_RELEASE_AND_PACKAGE',
              'observed_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': SOURCE, 'tag': TAG,
              'release_id': release['id'], 'url': release['html_url'], 'publish_run': run['id'], 'publish_job': job['id'],
              'publisher_artifact': {'id': artifact['id'], 'bytes': original.stat().st_size, 'sha256': sha(original.read_bytes()), 'members': len(members)},
              'publisher_input_count': len(inputs), 'g5_qualified_input_count': 366, 'production': production,
              'stages': stages, 'metadata_tests_each': 159, 'tag_workflows': tag_jobs, 'assets': download_records,
              'standalone': {'programs': 2, 'compiled_files': 8, 'oracle_tests': 12, 'outside_repository': True},
              'bundle_members': len(bundle['bundle_members_sha256']), 'image': publication['image'],
              'config_digest': manifest['config']['digest'], 'linux_manifest': child, 'layers': layers,
              'registry_scope': 'Manifest/config bodies downloaded and hashed; public layer access and sizes checked by anonymous HEAD. No claim of a full pull of the new image.',
              'scope': 'Software publication on unchanged G4-qualified physical inputs; no new silicon, analog, Fmax or owner-fluency result.'}
    write(base / 'verification.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.repository.resolve(), args.directory.resolve(), args.assets.resolve())
    print(result['status'], len(result['assets']), 'public assets')
