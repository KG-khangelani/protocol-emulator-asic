# SPDX-License-Identifier: Apache-2.0
"""Build and qualify the bounded G5 waveform experiment on unchanged production RTL."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.assembler import artifacts, assemble, json_bytes, program_bytes, load_plan
from tools.current_profile import verification_inputs
from tools.production_sram import verify

HERE = Path(__file__).resolve().parent
PROGRAMS = ('control', 'timing_fault')
PASS = 'PASS_G5_BOTH_PUBLIC_SIMULATORS'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fresh_output(output):
    output = output.resolve()
    require(output.is_relative_to((ROOT / 'build').resolve()), 'output must be under repository build/')
    require(not output.exists(), 'output exists; choose a new path to preserve earlier results')
    output.mkdir(parents=True)
    return output


def run(command, directory, label, timeout, env=None):
    """A failed or timed-out command still leaves its actual receipt and output."""
    log = directory / (label + '.log')
    receipt = {'command': command, 'cwd': str(ROOT), 'timeout_seconds': timeout,
               'started_utc': datetime.now(timezone.utc).isoformat()}
    started = time.monotonic()
    try:
        with log.open('wb') as stream:
            completed = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, timeout=timeout)
        receipt['returncode'] = completed.returncode
        require(completed.returncode == 0, f'{label} failed ({completed.returncode}); see {log}')
        receipt['status'] = 'PASS_COMMAND'
    except Exception as error:
        receipt.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        receipt['elapsed_seconds'] = round(time.monotonic() - started, 6)
        receipt['log_sha256'] = digest(log) if log.is_file() else None
        (directory / (label + '.json')).write_bytes(json_bytes(receipt))
    return receipt


def freeze_sources(output, inputs):
    """Retain actual producing bytes and independently check their Git identities."""
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', 'HEAD'], cwd=ROOT)
    blobs = {}
    for entry in tree.split(b'\0'):
        if entry:
            header, name = entry.split(b'\t', 1)
            mode, kind, oid = header.split()
            if kind == b'blob':
                blobs[name.decode('utf-8')] = oid.decode('ascii')
    mismatches = []
    with zipfile.ZipFile(output / 'source-inputs.zip', 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, expected in sorted(inputs.items()):
            raw = (ROOT / name).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == expected, 'input changed while freezing: ' + name)
            actual_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            if blobs.get(name) != actual_blob:
                mismatches.append(name)
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw, compresslevel=9)
    result = {'inputs_sha256': inputs, 'source_zip_sha256': digest(output / 'source-inputs.zip'),
              'matches_committed_input_bytes': not mismatches, 'uncommitted_inputs': mismatches}
    (output / 'source-inputs.json').write_bytes(json_bytes(result))
    return result


def build(output):
    output.mkdir()
    programs = {}
    images = {}
    for name in PROGRAMS:
        image = assemble((HERE / (name + '.asm')).read_text(encoding='utf-8'))
        files = artifacts(image)
        require(len(image['words']) == 20, name + ': expected the frozen twenty-word experiment')
        folder = output / name
        folder.mkdir()
        for filename, raw in files.items():
            (folder / filename).write_bytes(raw)
        programs[name] = {'words': len(image['words']), 'bytes': len(files['program.bin']),
                          'binary_sha256': image['binary_sha256'],
                          'artifact_sha256': {file: hashlib.sha256(raw).hexdigest() for file, raw in files.items()}}
        images[name] = image
    differences = [pc for pc, (a, b) in enumerate(zip(images['control']['words'], images['timing_fault']['words'])) if a != b]
    require(differences == [9, 11], 'fault variant must change only the two compensating WAIT words')
    result = {'schema': 'protocol-emulator-g5-build-v1', 'programs': programs, 'changed_word_indices': differences}
    (output / 'manifest.json').write_bytes(json_bytes(result))
    return result


def preregistration():
    path = ROOT / 'evidence/E0048-waveform-replay/preregistration.json'
    frozen = json.loads(path.read_bytes())
    require(frozen['status'] == 'FROZEN_BEFORE_EXECUTION', 'missing frozen experiment')
    amendment_path = path.with_name('amendment-01.json')
    amendment = json.loads(amendment_path.read_bytes())
    require(amendment['original_manifest_sha256'] == digest(path), 'amendment does not bind original declaration')
    require(set(amendment['changes']) == {'experiments/waveform_replay/' + name + '.asm' for name in PROGRAMS},
            'only the two program comment corrections are authorized')
    effective = dict(frozen['files_sha256'])
    for name, change in amendment['changes'].items():
        original = path.parent / 'assembly-rejection' / Path(name).name
        require(digest(original) == change['before_sha256'] == effective[name], 'original rejected source differs')
        require(original.read_bytes().replace(b'#', b';', 2) == (ROOT / name).read_bytes(),
                'comment amendment changed more than the two comment markers')
        effective[name] = change['after_sha256']
    for name, expected in effective.items():
        require(digest(ROOT / name) == expected, 'preregistered input changed: ' + name)
    return {'manifest_sha256': digest(path), 'amendment_sha256': digest(amendment_path), 'files_sha256': effective,
            'budget_start_utc': frozen['budget_start_utc'], 'budget_stop_utc': frozen['budget_stop_utc']}


def producing_inputs():
    inputs = verification_inputs()
    declaration = preregistration()
    names = set(declaration['files_sha256']) | {
        'evidence/E0048-waveform-replay/preregistration.json',
        'evidence/E0048-waveform-replay/amendment-01.json',
        'evidence/E0048-waveform-replay/assembly-rejection/control.asm',
        'evidence/E0048-waveform-replay/assembly-rejection/timing_fault.asm'}
    inputs.update({name: digest(ROOT / name) for name in names})
    return dict(sorted(inputs.items()))


def audit_loader(rows, case, record):
    """Recheck actual writes/readbacks and the precommit rejection boundary."""
    require(rows and all(row['step'] == n for n, row in enumerate(rows)), 'loader steps missing or duplicated')
    image = assemble((HERE / (case['program'] + '.asm')).read_text(encoding='utf-8'))
    expected = bytearray(program_bytes(image))
    if case.get('mutation') == 'uncompensated':
        require(expected[36] == 5, 'uncompensated control precondition')
        expected[36] = 7
    elif case.get('mutation') == 'missing_release':
        require(expected[73] == 0, 'missing-release control precondition')
        expected[73] = 7
    require(hashlib.sha256(expected).hexdigest() == record['binary_sha256'], 'case binary identity differs')
    corrupted = case['name'] == 'loader-corrupt-readback'
    written = bytearray(row['raw'] for row in rows if row['action'] == 'write_byte')
    actual = bytearray(expected)
    if corrupted:
        actual[40] ^= 1
    image = dict(image, words=[f'{int.from_bytes(expected[n:n+4], "little"):08x}' for n in range(0, 80, 4)],
                 binary_sha256=hashlib.sha256(expected).hexdigest())
    steps = load_plan(image, idle_inputs=case.get('idle', 0))['steps']
    canonical = []
    write_index = read_index = 0
    for index, step in enumerate(steps):
        raw = step['uio_in']
        if step['action'] == 'write_byte':
            raw = actual[write_index]
            write_index += 1
        observed = dict(step['expected'])
        if step['action'] == 'read_byte_after_edge':
            observed['uio_out'] = actual[read_index]
            read_index += 1
        canonical.append({'step': index, 'action': step['action'], 'raw': raw,
                          'ui_in': step['ui_in'], 'rst_n': step['rst_n'], 'ena': step['ena'],
                          'host_drives_uio': step['host_drives_uio'], 'expected': step['expected'], 'actual': observed})
        if corrupted and observed != step['expected']:
            break
    require(rows == canonical, 'public reset/bank/address/write/read/commit sequence differs')
    require(written == actual and len(written) == 80, 'actual public loaded bytes differ')
    reads = [row for row in rows if row['action'] == 'read_byte_after_edge']
    require(len(reads) == (41 if corrupted else 80), 'not all required public readbacks observed')
    for offset, row in enumerate(reads):
        require(row['expected'] == {'uio_oe': 255, 'uio_out': expected[offset]}, 'wrong readback expectation')
        require(row['actual'] == {'uio_oe': 255, 'uio_out': actual[offset]}, 'wrong observed readback')
        require(row['ui_in'] == 0x80 | (offset % 32) and row['ena'] == 0 and not row['host_drives_uio'],
                'readback must clock the public read address with host released')
    mismatches = [n for n, row in enumerate(rows) if row['expected'] != row['actual']]
    require(mismatches == ([len(rows) - 1] if corrupted else []), 'unexpected loader mismatch boundary')
    require(all(not row['host_drives_uio'] or row['actual'].get('uio_oe') == 0 for row in rows),
            'loader pin ownership conflict')
    identity = [row for row in rows if row['action'] == 'identify']
    require(len(identity) == 1 and identity[0]['actual'] == {'uio_oe': 0, 'uo_out': 0x22},
            'public interface identity missing')
    commits = [row for row in rows if row['action'] == 'commit_length']
    if corrupted:
        require(not commits and rows[-1]['action'] == 'read_byte_after_edge', 'corruption continued past rejection')
    else:
        require(len(commits) == 1 and commits[0]['raw'] == 20 and commits[0]['ui_in'] == 0xE0,
                'wrong public committed length')
        length = [row for row in rows if row['action'] == 'read_length']
        require(len(length) == 1 and length[0]['actual'] == {'uio_oe': 255, 'uio_out': 20}, 'length readback absent')
        require([row['action'] for row in rows[-2:]] == ['flush_idle', 'flush_idle'] and
                all(row['ena'] == 0 and row['raw'] == case.get('idle', 0) and
                    row['actual'] == {'uio_oe': 0, 'uo_out': 0x20} for row in rows[-2:]), 'invalid host handoff')


def audit_records(directory):
    # Membership comes from preregistration, never from whatever happened to run.
    from experiments.waveform_replay.oracle import assess
    expected = json.loads((HERE / 'expected.json').read_bytes())
    cases = {case['name']: case for case in expected['cases']}
    records = [json.loads(line) for line in (directory / 'records.jsonl').read_text(encoding='utf-8').splitlines()]
    require(len(records) == len(cases) == 21 and {record['name'] for record in records} == set(cases),
            'missing, extra or duplicate public cases')
    require({path.name for path in directory.iterdir()} == {'records.jsonl', *(name + '.json.gz' for name in cases)},
            'unexpected or missing public trace files')
    for record in records:
        case = cases[record['name']]
        require(record['group'] == case['group'], 'case group differs: ' + record['name'])
        require(record['expected_acceptance'] is case['accepted'] and record['accepted'] is case['accepted'],
                'case acceptance differs: ' + record['name'])
        raw = gzip.decompress((directory / (record['name'] + '.json.gz')).read_bytes())
        require(hashlib.sha256(raw).hexdigest() == record['trace_sha256'], 'trace hash differs: ' + record['name'])
        trace = json.loads(raw)
        require(set(trace) == {'loader', 'runtime'} and isinstance(trace['loader'], list) and isinstance(trace['runtime'], list),
                'invalid retained trace structure: ' + record['name'])
        require(record['observations'] == len(trace['loader']) + len(trace['runtime']) and record['observations'] > 0,
                'trace observation count differs: ' + record['name'])
        audit_loader(trace['loader'], case, record)
        if record['name'] == 'loader-corrupt-readback':
            require(record.get('rejected') is True and not trace['runtime'] and record['errors'],
                    'corrupted readback must reject before runtime')
        else:
            errors = assess(trace['runtime'], case)
            require(errors == record['errors'] and (not errors) is case['accepted'],
                    'retained runtime fails independent reassessment: ' + record['name'])
            if case.get('pause_edges'):
                require(not assess(trace['runtime'], case, paused=True), 'paused case does not match accepted-edge timing')
    require(sum(not record['accepted'] for record in records) == 5, 'expected five rejection controls')
    return sorted(records, key=lambda record: record['name'])


def compare_trace_bytes(left, right, records):
    for record in records:
        name = record['name'] + '.json.gz'
        require(gzip.decompress((left / name).read_bytes()) == gzip.decompress((right / name).read_bytes()),
                'retained trace bytes differ: ' + record['name'])


def execute(output, simulators, build_only=False, require_clean=False):
    output = fresh_output(output)
    result = {'schema': 'protocol-emulator-g5-verification-v1', 'status': 'RUNNING',
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'runtime': {'python': sys.version, 'platform': platform.platform()}, 'stages': []}
    save = lambda: (output / 'result.json').write_bytes(json_bytes(result))
    save()
    try:
        result['production'] = verify(ROOT)
        result['preregistration'] = preregistration()
        result['inputs_sha256'] = producing_inputs()
        result['source'] = freeze_sources(output, result['inputs_sha256'])
        if require_clean:
            require(result['source']['matches_committed_input_bytes'], 'qualification requires committed producing inputs')
        result['build'] = build(output / 'programs')
        if build_only:
            result['status'] = 'PASS_G5_BUILD_ONLY'
            return result
        strict = dict(os.environ, PROTOCOL_EMULATOR_LOCKED_WORKBENCH='1')
        result['stages'].append(run([sys.executable, 'tools/doctor.py'], output, 'doctor', 120, strict))
        result['stages'].append(run([sys.executable, '-m', 'unittest', 'discover', '-s', 'test',
                                     '-p', 'test_waveform_replay_oracle.py'], output, 'oracle-tests', 180, strict))
        models = output / 'models'
        models.mkdir()
        for name, expected in result['production']['model_sha256'].items():
            raw = gzip.decompress((ROOT / 'evidence/E0042-sram-prefetch-screen/feasibility/verilog' / (name + '.gz')).read_bytes())
            require(hashlib.sha256(raw).hexdigest() == expected, 'SRAM model differs: ' + name)
            (models / name).write_bytes(raw)
        observed = {}
        for simulator in simulators:
            stage = output / simulator
            stage.mkdir()
            env = dict(strict)
            for key in ('GATES', 'G1_PHYSICAL', 'G2_PHYSICAL', 'COCOTB_TESTCASE', 'COCOTB_TEST_FILTER',
                        'MAKEFLAGS', 'MFLAGS', 'COMPILE_ARGS', 'LEARNING_VCD', 'M0_LEARNING', 'COCOTB_PLUSARGS',
                        'COCOTB_TEST_MODULES', 'SIM', 'SRC_DIR', 'SIM_BUILD', 'PYTHONPATH'):
                env.pop(key, None)
            env.update(GENERAL_IO='yes', G2_CURRENT='yes', G2_SRAM='yes', SRAM_MODEL_DIR=str(models),
                       G5_PROGRAM_BUILD=str(output / 'programs'), G5_RECORDS=str(stage / 'records'),
                       COCOTB_RANDOM_SEED='20261115', PYTHONHASHSEED='0')
            command = ['make', '-C', 'test', 'SIM=' + simulator, 'SRC_DIR=' + str(ROOT / 'src'),
                       'SIM_BUILD=' + str(stage / 'sim'), 'COCOTB_TEST_MODULES=test_waveform_replay_public',
                       'COCOTB_RESULTS_FILE=' + str(stage / 'results.xml'), 'FST=', 'COCOTB_PLUSARGS=+NO_DUMP']
            result['stages'].append(run(command, stage, 'public-pins', 900, env))
            cases = ET.parse(stage / 'results.xml').getroot().findall('.//testcase')
            TEST_GROUPS = ('replay_waveforms', 'replay_falsification', 'replay_loader')
            require(len(cases) == len(TEST_GROUPS) and {case.get('name') for case in cases} == set(TEST_GROUPS),
                    'public suite group membership differs from frozen contract')
            require(all(not list(case) for case in cases), 'failure, error or skipped public test')
            log = (stage / 'public-pins.log').read_text(encoding='utf-8')
            require(('Running on Icarus Verilog' if simulator == 'icarus' else 'Running on Verilator') in log,
                    'simulator identity not observed in actual log')
            observed[simulator] = audit_records(stage / 'records')
            result[simulator] = {'groups': len(cases), 'junit_sha256': digest(stage / 'results.xml'),
                                 'records': observed[simulator]}
            save()
            print(simulator, 'PASS_G5_PUBLIC_TRACES', flush=True)
        if len(observed) == 2:
            require(observed['icarus'] == observed['verilator'], 'simulators disagree on complete public records')
            compare_trace_bytes(output / 'icarus/records', output / 'verilator/records', observed['icarus'])
            result['status'] = PASS
        else:
            result['status'] = 'PASS_G5_ONE_PUBLIC_SIMULATOR'
        require(verify(ROOT) == result['production'], 'production inputs changed during qualification')
        require(preregistration() == result['preregistration'], 'preregistration changed during qualification')
        require(producing_inputs() == result['inputs_sha256'], 'producing inputs changed during qualification')
        result['scope'] = 'Firmware-only digital simulation on unchanged G4-qualified RTL; no new physical, silicon, analog or owner-fluency claim.'
        return result
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()


def compare(first, second, output):
    output = fresh_output(output)
    result = {'schema': 'protocol-emulator-g5-reproduction-v1', 'status': 'RUNNING'}
    try:
        left, right = [json.loads((path / 'result.json').read_bytes()) for path in (first, second)]
        require(left['status'] == right['status'] == PASS, 'both runs must pass both simulators')
        require(left['source']['matches_committed_input_bytes'] and right['source']['matches_committed_input_bytes'],
                'both runs must use actual committed input bytes')
        for key in ('source_commit', 'inputs_sha256', 'production', 'preregistration', 'build'):
            require(left[key] == right[key], 'reproduction differs: ' + key)
        for simulator in ('icarus', 'verilator'):
            a, b = [audit_records(path / simulator / 'records') for path in (first, second)]
            require(a == b == left[simulator]['records'] == right[simulator]['records'],
                    simulator + ': retained original records do not reproduce')
            compare_trace_bytes(first / simulator / 'records', second / simulator / 'records', a)
        result.update(status='PASS_G5_COMMITTED_SOURCE_REPRODUCTION', source_commit=left['source_commit'],
                      first_result_sha256=digest(first / 'result.json'), second_result_sha256=digest(second / 'result.json'),
                      inputs=len(left['inputs_sha256']), programs=left['build'])
        return result
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        (output / 'result.json').write_bytes(json_bytes(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--require-clean', action='store_true')
    parser.add_argument('--simulator', choices=('icarus', 'verilator'), action='append')
    parser.add_argument('--compare', nargs=2, type=Path)
    args = parser.parse_args()
    simulators = args.simulator or ['icarus', 'verilator']
    if len(simulators) != len(set(simulators)):
        parser.error('simulators must be unique')
    if args.compare and (args.build_only or args.require_clean or args.simulator):
        parser.error('--compare cannot be combined with execution options')
    result = compare(*args.compare, args.out) if args.compare else execute(args.out, simulators, args.build_only, args.require_clean)
    print(result['status'], args.out)


if __name__ == '__main__':
    main()
