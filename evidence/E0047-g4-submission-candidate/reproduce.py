"""Compare two original G4 builds and the separate retained G2 qualification."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOP = 'tt_um_khangelani_protocol_emulator'
RUNS = {'candidate': 43543626249, 'reproduction': 43543629839}
SOURCE = '45c55f7cd95db2a883b0ffb5e864decd62d53601'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(p.read_bytes())
encoded = lambda value: (json.dumps(value, indent=2) + '\n').encode()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def checked_records(gds, path):
    data, parsed = gds.parse_records(path)
    require(all(length == 28 and datatype == 2 for length, kind, datatype, _ in parsed
                if kind in gds.TIMESTAMP_RECORDS), 'unexpected GDS timestamp record format')
    return data, parsed

def archived(base, record, name):
    metadata = read(base / 'artifacts.json')['artifacts']
    matches = [a for a in metadata if a['name'] == name]
    require(len(matches) == 1, 'missing/duplicate archive: ' + name)
    meta = matches[0]
    raw = (base / (str(meta['id']) + '.zip')).read_bytes()
    require(meta['workflow_run']['id'] == record['run_id'] and
            meta['workflow_run']['head_sha'] == record['source_commit'], 'archive source differs')
    require(len(raw) == meta['size_in_bytes'] and 'sha256:' + sha(raw) == meta['digest'], 'archive identity differs')
    require(meta['id'] == record['archives'][name]['id'] and sha(raw) == record['archives'][name]['sha256'],
            'archive differs from audited result')
    return zipfile.ZipFile(base / (str(meta['id']) + '.zip'))

def compare(candidate, reproduction, out):
    require(not out.exists() and out.is_relative_to((ROOT / 'build').resolve()), 'use a fresh directory under build')
    out.mkdir(parents=True)
    tool = HERE / 'reproduction-tools/compare_gds_records.py'
    require(sha(tool.read_bytes()) == 'ffe8827ab3d503cc7987e0265a9a0df55b348feac217db099db9346d7f8de1bf',
            'frozen GDS comparison helper differs')
    spec = importlib.util.spec_from_file_location('g4_frozen_gds_compare', tool)
    gds = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gds)
    results, layouts, records, landmarks, runs = {}, {}, {}, {}, {}
    for role, base in (('candidate', candidate), ('reproduction', reproduction)):
        retained = HERE / ('ci-' + str(RUNS[role]))
        record = read(retained / 'result.json')
        require(record['status'] == 'PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES' and
                record['run_id'] == RUNS[role] and record['source_commit'] == SOURCE, 'unqualified G4 result')
        require(read(base / 'audit/result.json') == record, 'run the retained audit before comparison')
        results[role] = record
        runs[role] = {'run_id': record['run_id'], 'result_path': (retained / 'result.json').relative_to(ROOT).as_posix(),
                      'result_sha256': sha((retained / 'result.json').read_bytes())}
        with archived(base, record, 'tt_submission') as z:
            raw = z.read('tt_submission/' + TOP + '.gds')
            require(sha(raw) == record['gds_sha256'], 'submitted layout differs')
            path = out / (role + '.gds')
            path.write_bytes(raw)
            layouts[role] = path
            require(sha(z.read('tt_submission/' + TOP + '.v')) == record['netlist_sha256'], 'submitted netlist differs')
        with archived(base, record, 'gatelevel_test_results') as z:
            records[role] = {}
            for name, item in record['netlist_tests']['records'].items():
                raw = z.read('output/' + name)
                require(sha(raw) == item['sha256'], 'public record bytes differ: ' + name)
                parsed = [json.loads(line) for line in raw.splitlines()]
                qualified = [r for r in parsed if 'trace_sha256' in r] if name.startswith('spi/') else parsed
                require(len(qualified) == item['count'], 'public record count differs')
                records[role][name] = {'all_retained_records': len(parsed), 'qualified_records': len(qualified),
                                      'sha256': sha(raw), 'semantic_sha256': sha(encoded(parsed))}
        raw = (base / 'audit/uart-landmarks.json').read_bytes()
        require(sha(raw) == record['uart_landmarks']['sha256'] and len(json.loads(raw)) == 97, 'UART landmarks differ')
        landmarks[role] = sha(raw)
    left, right = results['candidate'], results['reproduction']
    require(left['production'] == right['production'] and left['staged_sha256'] == right['staged_sha256'], 'production drift')
    for path in layouts.values():
        checked_records(gds, path)
    geometry = gds.compare(layouts['candidate'], layouts['reproduction'])
    for role, key in (('candidate', 'left'), ('reproduction', 'right')):
        geometry[key]['path'] = 'ci-' + str(RUNS[role]) + '/tt_submission/' + TOP + '.gds'
    require(geometry['equivalent_except_timestamps'], 'fresh G4 geometry does not reproduce')
    require(left['netlist_sha256'] == right['netlist_sha256'], 'fresh G4 netlist does not reproduce')
    require(left['physical_metrics'] == right['physical_metrics'] and left['area'] == right['area'], 'fresh G4 metrics differ')
    require(records['candidate'] == records['reproduction'] and landmarks['candidate'] == landmarks['reproduction'],
            'fresh public observations differ')
    flows = [r['flow_execution'] for r in results.values()]
    require(all(f['status'] == 'PASS_EXACT_CONFIGURED_EXECUTED_AND_SKIPPED_SEQUENCE' for f in flows), 'flow sequence failed')
    stage_differences = [name for name in flows[0]['stage_member_sha256']
                         if flows[0]['stage_member_sha256'][name] != flows[1]['stage_member_sha256'].get(name)]
    # G2 remains a distinct historical comparison, never silently overwritten.
    prior = ROOT / 'evidence/E0045-g2-sram-qualification/ci-94a3082'
    g2 = read(prior / 'result.json')
    require(sha((prior / 'result.json').read_bytes()) ==
            'af34f8debf3693461626d45782e6b74ca0390d2c6e8bc2106751a4c1ba1e1532', 'G2 reference differs')
    with archived(prior, g2, 'tt_submission') as z:
        raw = z.read('tt_submission/' + TOP + '.gds')
        require(sha(raw) == g2['gds_sha256'], 'G2 layout differs')
        prior_gds = out / 'g2.gds'
        prior_gds.write_bytes(raw)
        require(sha(z.read('tt_submission/' + TOP + '.v')) == g2['netlist_sha256'], 'G2 netlist differs')
    checked_records(gds, prior_gds)
    historical = gds.compare(prior_gds, layouts['candidate'])
    historical['left']['path'] = 'E0045/ci-94a3082/tt_submission/' + TOP + '.gds'
    historical['right']['path'] = geometry['left']['path']
    result = {'schema': 'protocol-emulator-g4-reproduction-v1', 'status': 'PASS_REPRODUCED_G4_PHYSICAL_CANDIDATE',
              'source_commit': SOURCE, 'runs': runs, 'physical_inputs_identical': len(left['staged_sha256']),
              'normalized_gds': geometry, 'netlist': {'identical': True, 'sha256': left['netlist_sha256']},
              'metrics': {'identical': True, 'physical_metrics': left['physical_metrics'], 'area': left['area']},
              'public_records': {'identical': True, 'records': records['candidate'], 'uart_retained_landmarks': 97,
                                 'uart_landmarks_sha256': landmarks['candidate'],
                                 'uart_scope': 'Seven UART groups execute assertions; retained RX landmarks compared, not complete TX traces.'},
              'stages': {'configured': 85, 'executed_top_level': 77, 'nested': 2, 'gate_disabled': 8,
                         'configuration_and_state_bytes_identical': not stage_differences,
                         'differing_stage_members': stage_differences},
              'g2_continuity': {'run_id': g2['run_id'], 'source_commit': g2['source_commit'], 'gds': historical,
                  'netlist_identical': g2['netlist_sha256'] == left['netlist_sha256'],
                  'physical_inputs_identical': g2['staged_sha256'] == left['staged_sha256'],
                  'physical_metrics_identical': g2['physical_metrics'] == left['physical_metrics'],
                  'area_identical': g2['area'] == left['area'],
                  'public_records_identical': g2['netlist_tests']['records'] == left['netlist_tests']['records']},
              'scope': 'Two clean official builds at one frozen source. Only standard BGNLIB/BGNSTR timestamps may be normalized. Zero-delay netlist tests and static timing, not hardware or analog measurements.'}
    (out / 'result.json').write_bytes(encoded(result))
    return result

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate-directory', type=Path, required=True)
    p.add_argument('--reproduction-directory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = compare(args.candidate_directory.resolve(), args.reproduction_directory.resolve(), args.output.resolve())
    print(result['status'])
