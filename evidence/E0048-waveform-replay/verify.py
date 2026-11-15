# SPDX-License-Identifier: Apache-2.0
"""Replay the bounded G5 audit from the original authenticated CI artifact."""
import argparse
from datetime import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = '66743b60b93508d2f00f23fa2cc2ac7db244bc3a'
IMAGE = 'ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:a22fc6626bc4f61b52cd6a32793cec86f718f0943d078ad03cfbf8dc7932af88'
IMAGE_ID = 'sha256:21502b121379e64bf296ca06cceb96cf31d7e33c6b40a9152af5d472287fd06a'
IMAGE_SOURCE = '5bdc0e6b6449a829a5da1f8f9a8060257e974843'
G5_GROUPS = {'replay_waveforms', 'replay_falsification', 'replay_loader'}
G3_GROUPS = {'assembled_loader_controls', 'assembled_uart_examples', 'assembled_spi_examples', 'assembled_i2c_examples'}
EXTRA_INPUTS = {
    'docs/decisions/0050-bounded-firmware-waveform-replay.md',
    'evidence/E0048-waveform-replay/preregistration.json',
    'evidence/E0048-waveform-replay/amendment-01.json',
    'evidence/E0048-waveform-replay/assembly-rejection/control.asm',
    'evidence/E0048-waveform-replay/assembly-rejection/timing_fault.asm',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def read(path):
    return json.loads(path.read_bytes())


def utc(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00'))


def zip_members(raw):
    """Read bounded plain files; reject traversal, links and ambiguous names."""
    result = {}
    folded = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        require(len(archive.infolist()) <= 10000, 'archive contains too many members')
        for item in archive.infolist():
            name = item.filename
            path = PurePosixPath(name)
            require(name and not path.is_absolute() and '..' not in path.parts and
                    '\\' not in name and ':' not in name and '\n' not in name and '\r' not in name,
                    'unsafe archive path: ' + name)
            require((item.external_attr >> 16) & 0o170000 != 0o120000, 'archive link is forbidden')
            if item.is_dir():
                continue
            require(name.casefold() not in folded, 'duplicate or case-colliding archive member: ' + name)
            folded.add(name.casefold())
            total += item.file_size
            require(item.file_size <= 64 * 1024 * 1024 and total <= 256 * 1024 * 1024,
                    'archive exceeds bounded audit size')
            result[name] = archive.read(item)
    require(result, 'empty original archive')
    return result


def git_bytes(commit, names):
    """Compare snapshots to immutable Git blobs without a full repository export."""
    require(re.fullmatch('[0-9a-f]{40}', commit), 'invalid source commit')
    request = ''.join(f'{commit}:{name}\n' for name in names).encode('utf-8')
    completed = subprocess.run(['git', 'cat-file', '--batch'], input=request, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, cwd=ROOT, timeout=60, check=True)
    stream = io.BytesIO(completed.stdout)
    values = {}
    for name in names:
        header = stream.readline().split()
        require(len(header) == 3 and header[1] == b'blob', 'missing immutable Git input: ' + name)
        size = int(header[2])
        raw = stream.read(size)
        require(len(raw) == size and stream.read(1) == b'\n', 'truncated Git blob: ' + name)
        values[name] = raw
    require(not stream.read(), 'unexpected Git source output')
    return values


def file_map(directory):
    return {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


def source_snapshot(folder, result, commit):
    inputs = result['inputs_sha256']
    snapshot = read(folder / 'source-inputs.json')
    require(result['source'] == snapshot and snapshot['inputs_sha256'] == inputs,
            'source snapshot metadata differs from result')
    require(snapshot['matches_committed_input_bytes'] is True and snapshot['uncommitted_inputs'] == [],
            'producing source was not committed')
    raw = (folder / 'source-inputs.zip').read_bytes()
    require(sha(raw) == snapshot['source_zip_sha256'], 'source archive digest differs')
    files = zip_members(raw)
    require(set(files) == set(inputs), 'source archive membership differs')
    require({name: sha(data) for name, data in files.items()} == inputs, 'frozen producing bytes differ')
    require(files == git_bytes(commit, sorted(files)), 'producing bytes differ from committed Git blobs')
    return files


def bind_audit_code(files):
    # Reused checks execute only repository code whose actual bytes were frozen
    # in this run. Do not import or execute untrusted artifact contents.
    names = {name for name in files if name.startswith('programs/')}
    names.update({
        'experiments/waveform_replay/run.py', 'experiments/waveform_replay/oracle.py',
        'experiments/waveform_replay/expected.json', 'experiments/waveform_replay/control.asm',
        'experiments/waveform_replay/timing_fault.asm', 'tools/assembler.py',
        'tools/run_program_examples.py', 'tools/program_examples.py',
        'tools/production_sram.py', 'tools/production-profile.json',
        'tools/current_profile.py', *EXTRA_INPUTS,
    })
    require(names <= set(files), 'missing audit dependency in producing source')
    for name in names:
        require((ROOT / name).read_bytes() == files[name], 'current audit dependency differs from producer: ' + name)


def junit(path, groups):
    cases = ET.parse(path).getroot().findall('.//testcase')
    require(len(cases) == len(groups) and {case.get('name') for case in cases} == groups,
            'JUnit group selection differs: ' + str(path))
    require(all(not list(case) for case in cases), 'failed, skipped or errored JUnit group')


def command_checks(folder, result, *, g3=False):
    require(len(result['stages']) == 4, 'expected doctor, unit tests and both simulators')
    labels = ('doctor', 'unit-tests' if g3 else 'oracle-tests', 'icarus/public-pins', 'verilator/public-pins')
    tests = 'test_program_tools.py' if g3 else 'test_waveform_replay_oracle.py'
    groups = G3_GROUPS if g3 else G5_GROUPS
    for index, (label, receipt) in enumerate(zip(labels, result['stages'])):
        log_path = folder / (label + '.log')
        log = log_path.read_text(encoding='utf-8')
        require(receipt['returncode'] == 0 and receipt['log_sha256'] == digest(log_path), 'command/log identity differs: ' + label)
        command = receipt['command']
        if not g3:
            require(receipt == read(folder / (label + '.json')) and receipt['status'] == 'PASS_COMMAND',
                    'actual command receipt missing or unsuccessful: ' + label)
            require(receipt['cwd'] == '/workspace' and receipt['elapsed_seconds'] >= 0, 'invalid runtime command context')
        if index == 0:
            require(command[1:] == ['tools/doctor.py'] and 'RESULT: PASS' in log and 'RESULT: REPORT' not in log,
                    'locked workbench doctor did not pass')
        elif index == 1:
            require(command[1:] == ['-m', 'unittest', 'discover', '-s', 'test', '-p', tests], 'wrong unit command')
            count = 20 if g3 else 12
            require(re.search(r'Ran ' + str(count) + r' tests? in ', log) and re.search(r'\nOK\s*$', log),
                    'unit test count or result differs')
        else:
            simulator = ('icarus', 'verilator')[index - 2]
            module = 'test_program_examples_public' if g3 else 'test_waveform_replay_public'
            require(command[:3] == ['make', '-C', 'test'] and 'SIM=' + simulator in command and
                    'SRC_DIR=/workspace/src' in command and 'COCOTB_TEST_MODULES=' + module in command and
                    'COCOTB_PLUSARGS=+NO_DUMP' in command, 'wrong public simulation command')
            marker = 'Running on Icarus Verilog' if simulator == 'icarus' else 'Running on Verilator'
            require(marker in log, 'actual simulator identity missing')
            junit_path = folder / simulator / 'results.xml'
            require(digest(junit_path) == result[simulator]['junit_sha256'], 'JUnit digest differs')
            junit(junit_path, groups)


def audit(directory, *, expected_source=SOURCE, windows_build=None):
    directory = Path(directory).resolve()
    run, jobs, artifacts = [read(directory / name) for name in ('run.json', 'jobs.json', 'artifacts.json')]
    require(run['head_sha'] == expected_source and run['path'] == '.github/workflows/waveform-replay.yaml' and
            run['status'] == 'completed' and run['conclusion'] == 'success', 'CI source, workflow or conclusion differs')
    require(run['repository']['full_name'] == 'KG-khangelani/protocol-emulator-asic', 'wrong repository')
    require(jobs['total_count'] == len(jobs['jobs']) == 1, 'expected one complete workflow job')
    job = jobs['jobs'][0]
    require(job['name'] == 'public-waveforms' and job['run_id'] == run['id'] and job['head_sha'] == expected_source and
            job['run_attempt'] == run['run_attempt'] and job['status'] == 'completed' and job['conclusion'] == 'success',
            'job identity or conclusion differs')
    require('ubuntu-24.04' in job['labels'] and all(step['conclusion'] == 'success' for step in job['steps']),
            'job contains skipped or failed steps')
    required_steps = {'Pull and identify the immutable G4 workbench',
                      'Load and check the frozen experiment in both simulators',
                      'Reproduce from a distinct clean clone of the committed source',
                      'Preserve the mandatory G3 program behavior',
                      'Retain original experiment records and source identities'}
    require(required_steps <= {step['name'] for step in job['steps']}, 'required workflow step missing')
    require(artifacts['total_count'] == len(artifacts['artifacts']) == 1, 'expected one original workflow artifact')
    artifact = artifacts['artifacts'][0]
    require(artifact['name'] == 'waveform-replay-' + expected_source and artifact['workflow_run']['id'] == run['id'] and
            artifact['workflow_run']['head_sha'] == expected_source, 'artifact source/run identity differs')
    archive_path = directory / (str(artifact['id']) + '.zip')
    raw = archive_path.read_bytes()
    require(len(raw) == artifact['size_in_bytes'] and 'sha256:' + sha(raw) == artifact['digest'],
            'original archive differs from authenticated GitHub artifact metadata')
    log = gzip.decompress((directory / 'job.log.gz').read_bytes()).decode('utf-8')
    require(sha(raw) in log and str(artifact['id']) in log and expected_source in log and IMAGE in log,
            'actual job log does not bind artifact, source and pinned image')
    for marker in ('PASS_G5_BOTH_PUBLIC_SIMULATORS', 'PASS_G5_COMMITTED_SOURCE_REPRODUCTION',
                   'PASS_ASSEMBLER_AND_BOTH_PUBLIC_SIMULATORS'):
        require(marker in log, 'job log is missing successful execution: ' + marker)
    members = zip_members(raw)
    require('runtime.json' in members and 'primary/result.json' in members, 'unexpected artifact root')
    build_root = (ROOT / 'build').resolve()
    build_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='g5-audit-', dir=build_root) as temporary:
        temporary = Path(temporary).resolve()
        require(temporary.is_relative_to(build_root), 'temporary extraction escaped build directory')
        for name, value in members.items():
            target = temporary / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(value)
        runtime = read(temporary / 'runtime.json')
        require(runtime['source_commit'] == expected_source and int(runtime['run_id']) == run['id'] and
                int(runtime['run_attempt']) == run['run_attempt'] and runtime['job'] == 'public-waveforms',
                'container runtime is not bound to actual job')
        before, after = [read(temporary / name) for name in ('workbench-image.json', 'workbench-image-after.json')]
        require(before == after and len(before) == 1, 'runtime image changed during execution')
        image = before[0]
        require(image['Id'] == runtime['image_id'] == IMAGE_ID and runtime['image_ref'] == IMAGE and
                IMAGE in image['RepoDigests'] and image['Os'] == 'linux' and image['Architecture'] == 'amd64',
                'actual pulled image manifest/config/platform identity differs')
        require(image['Config']['Labels'] == runtime['image_labels'] and
                image['Config']['Labels']['org.opencontainers.image.revision'] == IMAGE_SOURCE,
                'runtime image source label differs')
        primary, reproduction = [read(temporary / name / 'result.json') for name in ('primary', 'reproduction')]
        require(primary['source_commit'] == reproduction['source_commit'] == expected_source, 'execution source differs')
        frozen = source_snapshot(temporary / 'primary', primary, expected_source)
        require(frozen == source_snapshot(temporary / 'reproduction', reproduction, expected_source), 'clean-clone source bytes differ')
        bind_audit_code(frozen)
        sys.path.insert(0, str(ROOT))
        from experiments.waveform_replay import run as g5
        from tools import run_program_examples as g3
        from tools.program_examples import build as build_examples
        require(primary['status'] == reproduction['status'] == g5.PASS, 'both original runs must pass both simulators')
        for key in ('inputs_sha256', 'production', 'preregistration', 'build'):
            require(primary[key] == reproduction[key], 'clean-clone result differs: ' + key)
        require(primary['production'] == g5.verify(ROOT) and primary['preregistration'] == g5.preregistration(),
                'production or preregistration identity differs')
        stop = utc(primary['preregistration']['budget_stop_utc'])
        require(utc(primary['started_utc']) <= utc(primary['finished_utc']) <= stop and
                utc(reproduction['started_utc']) <= utc(reproduction['finished_utc']) <= stop,
                'experiment exceeded the frozen investigation cap')
        rebuilt = g5.build(temporary / 'rebuilt-g5')
        require(rebuilt == primary['build'], 'independent program rebuild differs')
        program_files = file_map(temporary / 'rebuilt-g5')
        require(len(program_files) == 9, 'expected eight program artifacts and their manifest')
        for label, result in (('primary', primary), ('reproduction', reproduction)):
            folder = temporary / label
            require(result['runtime']['platform'].startswith('Linux-'), 'qualification did not run on Linux')
            require(file_map(folder / 'programs') == program_files, 'compiled program files differ')
            command_checks(folder, result)
            for simulator in ('icarus', 'verilator'):
                records = g5.audit_records(folder / simulator / 'records')
                require(records == result[simulator]['records'] == primary['icarus']['records'],
                        'actual public records disagree across source clones or simulators')
                g5.compare_trace_bytes(temporary / 'primary/icarus/records', folder / simulator / 'records', records)
        comparison = read(temporary / 'comparison/result.json')
        require(comparison['status'] == 'PASS_G5_COMMITTED_SOURCE_REPRODUCTION' and
                comparison['source_commit'] == expected_source and comparison['inputs'] == len(frozen) and
                comparison['programs'] == rebuilt and
                comparison['first_result_sha256'] == sha(members['primary/result.json']) and
                comparison['second_result_sha256'] == sha(members['reproduction/result.json']), 'reproduction receipt differs')
        continuity = read(temporary / 'g3-continuity/result.json')
        require(continuity['status'] == 'PASS_ASSEMBLER_AND_BOTH_PUBLIC_SIMULATORS' and
                continuity['source_commit'] == expected_source and continuity['production'] == primary['production'],
                'mandatory G3 continuity did not pass on the same production source')
        require(continuity['inputs_sha256'] == {name: digest for name, digest in primary['inputs_sha256'].items()
                                               if name not in EXTRA_INPUTS}, 'G3 producing-input map differs')
        command_checks(temporary / 'g3-continuity', continuity, g3=True)
        examples = build_examples(temporary / 'rebuilt-g3')
        require(len(examples['examples']) == 13 and examples == continuity['build'], 'frozen G3 example rebuild differs')
        example_files = file_map(temporary / 'rebuilt-g3')
        require(len(example_files) == 53 and example_files == file_map(temporary / 'g3-continuity/examples'),
                'G3 generated files differ')
        for simulator in ('icarus', 'verilator'):
            records = g3.audit_records(temporary / 'g3-continuity' / simulator / 'records')
            require(records == continuity[simulator]['records'] == continuity['icarus']['records'] and
                    len(records) == 55 and sum(not row['expected_acceptance'] for row in records) == 15,
                    'G3 actual public records disagree')
            g5.compare_trace_bytes(temporary / 'g3-continuity/icarus/records',
                                   temporary / 'g3-continuity' / simulator / 'records', records)
        windows = None
        if windows_build is not None:
            windows_build = Path(windows_build).resolve()
            result = read(windows_build / 'result.json')
            require(result['status'] == 'PASS_G5_BUILD_ONLY' and result['source_commit'] == expected_source and
                    result['runtime']['platform'].startswith('Windows-') and result['build'] == rebuilt,
                    'native Windows source/build identity differs')
            snapshot = read(windows_build / 'source-inputs.json')
            raw_snapshot = (windows_build / 'source-inputs.zip').read_bytes()
            require(snapshot == result['source'] and sha(raw_snapshot) == snapshot['source_zip_sha256'],
                    'native Windows producing snapshot differs')
            native = zip_members(raw_snapshot)
            require({name: sha(raw) for name, raw in native.items()} == result['inputs_sha256'] == snapshot['inputs_sha256']
                    and set(native) == set(frozen), 'native Windows source membership or identity differs')
            differing = sorted(name for name in native if native[name] != frozen[name])
            require(differing == snapshot['uncommitted_inputs'] and
                    snapshot['matches_committed_input_bytes'] is (not differing) and
                    all(native[name].replace(b'\r\n', b'\n') == frozen[name] for name in differing),
                    'native Windows source differs beyond retained CRLF line endings')
            exact_native_inputs = {'tools/assembler.py', 'experiments/waveform_replay/control.asm',
                                   'experiments/waveform_replay/timing_fault.asm'}
            require(not exact_native_inputs.intersection(differing) and
                    file_map(windows_build / 'programs') == program_files, 'Windows/Linux actual program bytes differ')
            windows = {'program_files': 8, 'manifest_files': 1, 'result_sha256': digest(windows_build / 'result.json'),
                       'source_zip_sha256': sha(raw_snapshot), 'source_eol_differences': differing,
                       'scope': 'Native assembly only; all eight compiled files match Linux. Listed source files differ only by CRLF; this is not a clean Windows RTL run.'}
    retained = ['run.json', 'jobs.json', 'artifacts.json', 'job.log.gz', archive_path.name]
    result = {'schema': 'protocol-emulator-g5-retained-audit-v1', 'status': 'PASS_G5_RETAINED_ORIGINALS',
              'source_commit': expected_source, 'run_id': run['id'], 'job_id': job['id'],
              'artifact': {'id': artifact['id'], 'sha256': sha(raw), 'bytes': len(raw), 'members': len(members)},
              'runtime': {'image_ref': IMAGE, 'image_id': IMAGE_ID, 'image_source': IMAGE_SOURCE},
              'inputs': len(frozen), 'simulators': {name: {'cases': 21, 'rejections': 5} for name in ('icarus', 'verilator')},
              'reproduction': True,
              'g3': {'examples': 13, 'cases_per_simulator': 55, 'rejections_per_simulator': 15, 'compiled_files': 53},
              'files_sha256': {name: digest(directory / name) for name in retained}}
    if windows is not None:
        result['windows_build'] = windows
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source', default=SOURCE)
    parser.add_argument('--windows-build', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to((ROOT / 'build').resolve()) and not output.exists(),
            'audit output must be a fresh file under build/')
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = audit(args.directory, expected_source=args.expected_source, windows_build=args.windows_build)
    except Exception as error:
        result = {'schema': 'protocol-emulator-g5-retained-audit-v1', 'status': 'FAILED_OR_INCOMPLETE', 'error': str(error)}
        output.write_bytes((json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
        raise
    output.write_bytes((json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    print(result['status'], output)


if __name__ == '__main__':
    main()
