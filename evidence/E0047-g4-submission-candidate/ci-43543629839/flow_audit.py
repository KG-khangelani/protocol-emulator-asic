"""Check configured flow, executed stages and explicit skips independently."""
import hashlib
import json
from pathlib import Path
import re

BASELINE_SHA256 = '0cd6994fe46e82d8c5466a95188896ded250ab8973c2a2c30552b8d1d5888f32'

def inspect_flow(logs, resolved, require):
    raw = (Path(__file__).resolve().parent / 'audit-baseline.json').read_bytes()
    sha = lambda value: hashlib.sha256(value).hexdigest()
    require(sha(raw) == BASELINE_SHA256, 'frozen G2 stage baseline differs')
    baseline = json.loads(raw)
    flow_raw = logs.bytes('runs/wokwi/flow.log')
    text = flow_raw.decode('utf-8')
    top, nested, sequence, skipped = [], [], [], []
    for line in text.splitlines():
        running = re.fullmatch(r"Running '([^']+)' at '(runs/wokwi/[^']+)'\u2026", line)
        disabled = re.fullmatch(r"Gating variable for step '([^']+)' set to 'False'- the step will be skipped\.", line)
        if running:
            step, path = running.groups()
            depth = len(path.split('/'))
            require(depth in (3, 4), 'unexpected stage nesting')
            entry = {'step_id': step, 'directory': path}
            (top if depth == 3 else nested).append(entry)
            if depth == 3:
                sequence.append((step, 'EXECUTED_TOP_LEVEL'))
        elif disabled:
            skipped.append(line)
            sequence.append((disabled[1], 'SKIPPED_FROZEN_GATE_FALSE'))
    require(sequence == [(r['step_id'], r['status']) for r in baseline['configured_sequence']],
            'configured G4 stage sequence differs')
    require(top == [{k:r[k] for k in ('step_id', 'directory')} for r in baseline['executed_top_level']],
            'executed G4 stage sequence differs')
    require(nested == [{k:r[k] for k in ('step_id', 'directory')} for r in baseline['nested_stages']],
            'nested G4 stage sequence differs')
    require(skipped == [r['message'] for r in baseline['gated_skips']], 'G4 gated skips differ')
    require({key: resolved[key] for key in baseline['resolved_run_controls']} == baseline['resolved_run_controls'],
            'G4 resolved flow controls differ')
    notices = [line for line in text.splitlines()
               if ('Skipping' in line or 'skipping' in line) and not line.startswith('Skipping step ')]
    require(notices == [r['message'] for r in baseline['in_step_noops_or_skip_notices']],
            'G4 in-step skip notices differ')
    expected_configs = {r['directory'] + '/config.json' for r in top + nested}
    actual_configs = {name for name in logs.file.namelist()
                      if re.fullmatch(r'runs/wokwi/\d+-[^/]+/(?:\d+-[^/]+/)?config.json', name)}
    require(actual_configs == expected_configs, 'G4 executed stage membership differs')
    stage_hashes = {}
    configuration_ids = {r['directory']: r['configuration_step_id']
                         for r in baseline['executed_top_level'] + baseline['nested_stages']}
    for record in top + nested:
        directory = record['directory']
        config = logs.json(directory + '/config.json')
        require(config['meta']['step'] == configuration_ids[directory], 'G4 executed stage configuration differs')
        stage_hashes[directory] = {}
        for name in ('config.json', 'state_in.json', 'state_out.json'):
            raw = logs.bytes(directory + '/' + name)
            json.loads(raw)
            stage_hashes[directory][name] = sha(raw)
    return {'status': 'PASS_EXACT_CONFIGURED_EXECUTED_AND_SKIPPED_SEQUENCE',
            'baseline_sha256': BASELINE_SHA256, 'flow_log_sha256': sha(flow_raw),
            'configured_stages': len(sequence), 'executed_top_level': len(top),
            'nested_stages': len(nested), 'gated_skips': len(skipped),
            'in_step_skip_notices': len(notices), 'resolved_run_controls': baseline['resolved_run_controls'],
            'stage_member_sha256': stage_hashes}
