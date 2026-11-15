# SPDX-License-Identifier: Apache-2.0
"""Check G5 closure against sealed execution, publication and source records.

Run after publication retention and final documentation updates. This checks
their linkage and unchanged bytes; it does not rerun RTL or physical design.
The resulting file records a historical closure snapshot, not future CI state.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
PREFIX = BASE.relative_to(ROOT).as_posix() + '/'
BASELINE = 'd664a4c227762f4c62fbbb703eec245fda2a60a9'
DECLARATION = 'e9f2eec26600e89bee790ce7a5b2f4af821de743'
QUALIFIED = '66743b60b93508d2f00f23fa2cc2ac7db244bc3a'
RELEASE = '022834146efcb5f388a4d6ec23b3b705a0df7ef8'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(path.read_bytes())
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def stamp(value): return datetime.fromisoformat(value.replace('Z', '+00:00'))


def audit():
    observed = datetime.now(timezone.utc)
    evidence_commit = git('rev-parse', 'HEAD').decode().strip()
    files = {}

    def record(path):
        relative = path.relative_to(ROOT).as_posix()
        files[relative] = sha(path.read_bytes())
        return relative

    def linked(names):
        return [{'path': record(ROOT / name), 'sha256': files[name]} for name in names]

    sealed = {}
    for manifest in sorted(BASE.glob('*/retention.json')):
        seal = read(manifest)
        require(seal.get('files_sha256'), 'empty retained record: ' + str(manifest))
        for name, digest in seal['files_sha256'].items():
            path = (manifest.parent / name).resolve()
            require(path.is_relative_to(manifest.parent.resolve()), 'retention path escaped its directory')
            require(sha(path.read_bytes()) == digest, 'changed retained bytes: ' + str(path))
            record(path)
        record(manifest)
        sealed[manifest.parent.name] = len(seal['files_sha256'])
    required_seals = {'assembly-rejection', 'host-startup', 'ci-66743b6', 'windows-build-66743b6',
                      'package-ci-43698190050', 'publication'}
    require(required_seals <= set(sealed), 'required retained proof is missing')
    public_ci = list(BASE.glob('publication-ci-*/verification.json'))
    require(len(public_ci) == 1 and public_ci[0].parent.name in sealed, 'publication execution is missing or ambiguous')
    continuity = read(BASE / 'g4-continuity/verification.json')
    for name, digest in continuity['files_sha256'].items():
        path = BASE / 'g4-continuity' / name
        require(sha(path.read_bytes()) == digest, 'G4 comparison source changed')
        record(path)

    for older, newer in ((BASELINE, DECLARATION), (DECLARATION, QUALIFIED), (QUALIFIED, RELEASE), (RELEASE, evidence_commit)):
        subprocess.run(['git', 'merge-base', '--is-ancestor', older, newer], cwd=ROOT, check=True)
    frozen_path = PREFIX + 'preregistration.json'
    frozen = read(BASE / 'preregistration.json')
    require((BASE / 'preregistration.json').read_bytes() == git('show', DECLARATION + ':' + frozen_path), 'original declaration changed')
    for name, digest in frozen['files_sha256'].items():
        require(sha(git('show', DECLARATION + ':' + name)) == digest, 'declaration source identity differs')
    amendment = read(BASE / 'amendment-01.json')
    require(amendment['original_manifest_sha256'] == sha((BASE / 'preregistration.json').read_bytes()), 'amendment binds a different declaration')
    for name, identity in amendment['changes'].items():
        old = (BASE / 'assembly-rejection' / Path(name).name).read_bytes()
        new = git('show', evidence_commit + ':' + name)
        require(sha(old) == identity['before_sha256'] == frozen['files_sha256'][name]
                and sha(new) == identity['after_sha256'] and old.replace(b'#', b';', 2) == new,
                'comment amendment changed instructions')
    unchanged_contract = set(frozen['files_sha256']) - set(amendment['changes'])
    for name in unchanged_contract:
        require(sha(git('show', evidence_commit + ':' + name)) == frozen['files_sha256'][name], 'frozen contract changed')
    failed = json.loads(gzip.decompress((BASE / 'assembly-rejection/result.json.gz').read_bytes()))
    declaration_time = stamp(git('show', '-s', '--format=%cI', DECLARATION).decode().strip())
    require(declaration_time < stamp(failed['started_utc']) < stamp(amendment['observed_utc']), 'declaration/correction chronology differs')
    require(failed['status'] == 'FAILED_OR_INCOMPLETE' and read(BASE / 'assembly-rejection/retention.json')['returncode'] == 2,
            'original failed attempt was not retained')
    started, deadline = stamp(frozen['budget_start_utc']), stamp(frozen['budget_stop_utc'])
    require((deadline - started).total_seconds() == frozen['budget_seconds'] == 57600 and started <= observed < deadline,
            'predeclared investigation cap exceeded')

    core = read(BASE / 'ci-66743b6/verification.json')
    require(core['status'] == 'PASS_G5_RETAINED_ORIGINALS' and core['source_commit'] == QUALIFIED
            and core['inputs'] == 366 and core['reproduction'], 'core qualification incomplete')
    require(core['simulators'] == {name: {'cases': 21, 'rejections': 5} for name in ('icarus', 'verilator')}, 'public cases incomplete')
    require(core['g3'] == {'examples': 13, 'cases_per_simulator': 55, 'rejections_per_simulator': 15, 'compiled_files': 53},
            'mandatory program guard incomplete')
    with zipfile.ZipFile(BASE / 'ci-66743b6' / (str(core['artifact']['id']) + '.zip')) as original:
        primary = json.loads(original.read('primary/result.json'))
        reproduction = json.loads(original.read('reproduction/result.json'))
        require(stamp(amendment['observed_utc']) < stamp(primary['started_utc']) < stamp(primary['finished_utc']) < deadline,
                'primary execution outside frozen conditions')
        require(stamp(primary['finished_utc']) < stamp(reproduction['started_utc']) < stamp(reproduction['finished_utc']) < deadline,
                'separate reproduction outside frozen conditions')
    controls = read(BASE / 'ci-66743b6/audit-controls.json')
    require(controls['status'] == 'PASS_FIVE_REHASHED_CONTROLS' and len(controls['controls']) == 5
            and all(item['rejected'] for item in controls['controls']), 'evidence controls incomplete')

    sys.path.insert(0, str(ROOT))
    from tools.production_sram import verify
    production = verify(ROOT)
    require(production == frozen['production'] and len(production['files_sha256']) == 20, 'qualified physical inputs changed')
    require(not git('diff', BASELINE, evidence_commit, '--', 'programs', 'src', 'info.yaml', 'tools/production-profile.json').strip(),
            'G3 programs or G4 production changed')
    changed_evidence = git('diff', '--name-only', BASELINE, evidence_commit, '--', 'evidence').decode().splitlines()
    require(changed_evidence and all(name.startswith(PREFIX) for name in changed_evidence), 'historical evidence changed')
    require(continuity['status'] == 'PASS_G4_RELEASE_AND_HISTORICAL_EVIDENCE_UNCHANGED'
            and len(continuity['assets']) == 35 and continuity['release_title_and_body_unchanged'], 'G4 publication continuity missing')

    package = read(BASE / 'package-ci-43698190050/verification.json')
    require(package['status'] == 'PASS_G5_WINDOWS_LINUX_PACKAGE_AND_SMOKE' and package['source_commit'] == RELEASE,
            'package qualification incomplete')
    require(package['standalone'] == {'programs': 2, 'compiled_files': 8, 'oracle_tests': 12,
            'platforms': ['Windows', 'Linux'], 'outside_repository': True}, 'standalone portability incomplete')
    public = read(BASE / 'publication/verification.json')
    execution = read(public_ci[0])
    require(execution['status'] == 'PASS_G5_PUBLICATION_RECEIPTS'
            and execution['publication_verification_sha256'] == sha((BASE / 'publication/verification.json').read_bytes()),
            'public audit does not bind actual execution')
    require(public['status'] == 'PASS_G5_RELEASE_AND_PACKAGE' and public['source_commit'] == RELEASE
            and public['production'] == production and len(public['assets']) == 22 and public['bundle_members'] == 25,
            'public distribution incomplete')
    require(len(public['tag_workflows']) == 10 and sum(len(item['jobs']) for item in public['tag_workflows'].values()) == 23,
            'mandatory tag workflows incomplete')
    require(public['publisher_input_count'] == 361 and public['g5_qualified_input_count'] == 366
            and public['metadata_tests_each'] == 159 and len(public['stages']) == 8, 'publisher verification incomplete')
    for name, identity in package['assets'].items():
        require(public['assets'][name]['sha256'] == identity['sha256'] and public['assets'][name]['bytes'] == identity['bytes'],
                'published G5 asset differs from portable package')
    notice = read(BASE / 'release-notice.json')
    require(notice['status'] == 'PASS_G5_RELEASE_NOTICE_AND_LATEST' and notice['release_id'] == public['release_id']
            and notice['source_commit'] == RELEASE and notice['asset_count'] == 22, 'final public release state not verified')
    require(notice.get('files_sha256'), 'final public observations are missing')
    for name, digest in notice['files_sha256'].items():
        path = (BASE / name).resolve()
        require(path.is_relative_to(BASE) and sha(path.read_bytes()) == digest, 'final public observation changed')
        record(path)

    docs = ['README.md', 'docs/state.md', 'docs/goals.md', 'docs/backlog.md', 'docs/research-ledger.md',
            'docs/waveform-replay.md', 'docs/verification.md', 'docs/ai-use.md', PREFIX + 'README.md']
    goal_text = (ROOT / 'docs/goals.md').read_text(encoding='utf-8')
    g5 = goal_text.split('## G5 -', 1)[1].split('## G6 -', 1)[0]
    require(g5.count('- [x]') == 3 and '- [ ]' not in g5 and 'Completed 2026-11-15' in g5, 'G5 goal record incomplete')
    require('M0 teach-back PENDING' in goal_text and '- [ ]' in goal_text.split('## G6 -', 1)[1], 'owner learning was promoted without evidence')
    row = next(line for line in (ROOT / 'docs/backlog.md').read_text(encoding='utf-8').splitlines() if line.startswith('| G5-T01 |'))
    require('DONE 2026-11-15' in row, 'backlog record incomplete')
    for name in docs:
        record(ROOT / name)
    record(Path(__file__))
    requirements = [
        {'requirement': 'Freeze one use case, control program, independent pin trace, measurements, timing assumptions and two-working-day cap before execution.',
         'status': 'PASS', 'evidence': linked([PREFIX + 'preregistration.json', PREFIX + 'amendment-01.json',
             'docs/decisions/0050-bounded-firmware-waveform-replay.md', 'docs/specs/g5-waveform-replay.md', PREFIX + 'assembly-rejection/retention.json']),
         'detail': 'Declaration precedes the first failed assembly. The retained prospective comment correction changes no instructions, traces, cases or budget.'},
        {'requirement': 'Demonstrate the capability through public-pin-loaded programs with zero new RTL, independent trace checks and explicit limits.',
         'status': 'PASS', 'evidence': linked([PREFIX + 'ci-66743b6/verification.json', PREFIX + 'ci-66743b6/audit-controls.json',
             PREFIX + 'ci-66743b6/windows-comparison.json', PREFIX + 'g4-continuity/verification.json', 'docs/waveform-replay.md']),
         'detail': 'Both simulators and a separate clone qualify 21 cases and five expected rejections. All 366 inputs, public loading/readback and complete G3 guard pass; twenty physical inputs and historical evidence remain unchanged.'},
        {'requirement': 'Keep a useful documented example, retain failures and stop on budget expiry or mandatory regression; publish a matching verified software milestone.',
         'status': 'PASS', 'evidence': linked([PREFIX + 'package-ci-43698190050/verification.json',
             PREFIX + 'publication/verification.json', public_ci[0].relative_to(ROOT).as_posix(), PREFIX + 'release-notice.json',
             PREFIX + 'host-startup/retention.json', 'docs/waveform-replay.md']),
         'detail': 'Windows/Linux standalone packages agree. Twenty-two public assets, ten tag workflows / twenty-three jobs, matching registry identity and original publisher execution pass within the frozen cap. G6 and competition entry remain separate.'},
    ]
    return {'schema': 'protocol-emulator-g5-completion-audit-v1', 'status': 'PASS_G5_COMPLETION_REQUIREMENTS',
            'observed_utc': observed.isoformat(), 'evidence_baseline_commit': evidence_commit,
            'declaration_commit': DECLARATION, 'qualified_commit': QUALIFIED, 'release_source_commit': RELEASE,
            'budget': {'start_utc': frozen['budget_start_utc'], 'stop_utc': frozen['budget_stop_utc'],
                       'maximum_seconds': 57600, 'elapsed_seconds': (observed - started).total_seconds()},
            'sealed_records': sealed, 'requirements': requirements, 'snapshot_files_sha256': dict(sorted(files.items())),
            'snapshot_scope': 'Historical closure file hashes. Execution evidence is bound to evidence_baseline_commit; final documentation, public release observations and this audit are committed together immediately after execution. Validate later against the commit holding this audit, not a changed future working tree.',
            'limits': ['No new RTL or physical acceptance', 'No fabricated silicon or analog characterization',
                       '50 MHz is an assumed target, not measured Fmax', 'No unrestricted asynchronous capture',
                       'No owner-fluency promotion or competition submission']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    require(output.is_relative_to(ROOT / 'build') and not output.exists(), 'use a fresh output under build/')
    output.write_bytes((json.dumps(audit(), indent=2, sort_keys=True) + '\n').encode())
    print('PASS_G5_COMPLETION_REQUIREMENTS', output)
