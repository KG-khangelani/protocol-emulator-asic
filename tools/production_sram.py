# SPDX-License-Identifier: Apache-2.0
"""Require production files to match the independently qualified SRAM inputs."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'tools/production-profile.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def relative_file(root, name):
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and '..' not in relative.parts and '\\' not in name,
            'production reference must be repository relative: ' + name)
    path = (root / relative).resolve()
    require(path.is_relative_to(root) and path.is_file(), 'missing production input: ' + name)
    return path


def verify(root=ROOT):
    root = Path(root).resolve()
    profile_path = relative_file(root, PROFILE)
    profile = json.loads(profile_path.read_bytes())
    require(profile['schema'] == 'protocol-emulator-production-profile-v1' and
            profile['profile'] == 'od128-sram', 'unsupported production profile')
    qualification = profile['qualification']
    result_path = relative_file(root, qualification['path'])
    require(sha(result_path.read_bytes()) == qualification['sha256'], 'qualified physical result changed')
    result = json.loads(result_path.read_bytes())
    require(result['status'] == 'PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES', 'physical candidate is not qualified')
    for key in ('source_commit', 'run_id', 'gds_sha256', 'netlist_sha256'):
        require(result[key] == qualification[key], 'qualified physical identity changed: ' + key)
    require(set(result['jobs']) == {'gds', 'precheck', 'gl_test'} and
            all(j['conclusion'] == 'success' for j in result['jobs'].values()), 'incomplete physical gates')
    require(result['physical_metrics']['status'] == 'PASS', 'physical metrics failed')
    require(result['precheck']['status'] == 'PASS' and result['precheck']['test_count'] == 10 and
            len(set(result['precheck']['tests'])) == 10, 'complete official precheck missing')
    require(result['power_port_selection']['status'] == 'PASS_EXISTING_FULL_HEIGHT_POWER_PORT_SELECTION',
            'qualified external power ports missing')
    require(result['netlist_tests']['public_test_groups'] == 18 and result['netlist_tests']['status'] == 'PASS',
            'qualified public netlist tests missing')
    expected = result['staged_sha256']
    require(expected == profile['files_sha256'], 'production file set differs from qualification')
    require(len(expected) == 20, 'qualified physical input set is incomplete')
    for name, digest in expected.items():
        require(sha(relative_file(root, name).read_bytes()) == digest, 'production input differs: ' + name)
    candidate = result['candidate']
    require({n.removeprefix('src/'): h for n,h in expected.items() if n.endswith('.v')} == candidate['source_sha256'],
            'production RTL differs from qualified candidate')
    require(profile['model_sha256'] == candidate['model_sha256'], 'production SRAM models differ')
    for label, status in (
            ('combined_regression', 'PASS_SRAM_CURRENT_BOTH_SIMULATORS'),
            ('normal_command_verification', 'PASS_CURRENT_SRAM_COMMAND_CI_ORIGINAL_ARCHIVE'),
            ('corrected_netlist_pair', 'PASS_RETAINED_CORRECTED_NETLIST_PAIR_WITH_FROZEN_INPUTS')):
        reference = profile[label]
        path = relative_file(root, reference['path'])
        require(sha(path.read_bytes()) == reference['sha256'], 'production evidence changed: ' + label)
        evidence = json.loads(path.read_bytes())
        require(evidence['status'] == status, 'production evidence did not pass: ' + label)
        if label == 'combined_regression':
            require(evidence['candidate'] == candidate, 'combined regression used a different candidate')
        if label == 'normal_command_verification':
            require(evidence['profile']['source_sha256'] == candidate['source_sha256'] and
                    evidence['profile']['model_sha256'] == candidate['model_sha256'],
                    'normal verification used different source or memory models')
        if label == 'corrected_netlist_pair':
            require(evidence['netlist_sha256'] == result['netlist_sha256'], 'qualified netlist differs from both-simulator pair')
    metadata = relative_file(root, 'info.yaml').read_bytes()
    require(sha(metadata) == profile['metadata_sha256'], 'production metadata changed')
    info = metadata.decode('utf-8')
    require(re.search(r'^  tiles:\s+"8x4"\s*(?:#.*)?$', info, re.M) and
            re.search(r'^  clock_hz:\s+50000000\s*(?:#.*)?$', info, re.M), 'production footprint or clock changed')
    require(re.search(r'^  top_module:\s+"tt_um_khangelani_protocol_emulator"\s*(?:#.*)?$', info, re.M),
            'production top module changed')
    require(sha(relative_file(root, profile['decision']).read_bytes()) == profile['decision_sha256'],
            'production decision changed')
    return {'status': 'PASS_PRODUCTION_MATCHES_QUALIFIED_SRAM', 'profile': profile['profile'],
            'profile_sha256': sha(profile_path.read_bytes()), 'source_sha256': candidate['source_sha256'],
            'model_sha256': candidate['model_sha256'], 'qualified_run_id': result['run_id'],
            'qualified_source_commit': result['source_commit'], 'qualified_netlist_sha256': result['netlist_sha256'],
            'files_sha256': expected, 'metadata_sha256': sha(metadata)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(result['status'])


if __name__ == '__main__':
    main()
