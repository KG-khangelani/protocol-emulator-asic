"""Read two archived runs, independent contact threshold probes and the rule observation."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tarfile
from zipfile import ZipFile

import klayout.db as db


ROOT = Path('evidence/E0047-g4-submission-candidate')
FAST_REPORT = 'runs/wokwi/60-openroad-stapostpnr/nom_fast_1p32V_m40C/min.rpt'
GDS = 'tt_submission/tt_um_khangelani_protocol_emulator.gds'
HISTORICAL = Path('evidence/E0043-sram-physical-integration/contact-rules')
NUMBERS = (6, 7, 10, 11, 15, 50, 60, 61)


def load(path):
    return json.loads(path.read_bytes())


def read_member(directory, result, index, archive_name, member):
    ref = result['archives'][archive_name]
    path = directory / (str(ref['id']) + '.zip')
    with path.open('rb') as stream:
        digest = sha256()
        while block := stream.read(1 << 20):
            digest.update(block)
    assert digest.hexdigest() == ref['sha256']
    with ZipFile(path) as archive:
        raw = archive.read(member)
    assert sha256(raw).hexdigest() == index[archive_name][member]
    return raw


def historical_markers():
    archive = HISTORICAL / 'diagnostic.tar.gz'
    index = load(HISTORICAL / 'archive.json')
    assert sha256(archive.read_bytes()).hexdigest() == index['sha256']
    name = 'original-macro/reports/drc.magic.rpt'
    with tarfile.open(archive) as bundle:
        raw = bundle.extractfile(name).read()
    assert sha256(raw).hexdigest() == index['files'][name]
    boxes = []
    for line in raw.decode().splitlines():
        fields = re.findall(r'([0-9.]+)um', line)
        if len(fields) == 4:
            boxes.append(db.Box(*(int(Decimal(n) * 1000) for n in fields)))
    assert len({str(box) for box in boxes}) == 32
    return boxes


def threshold_counts(gds, markers):
    with os.fdopen(os.memfd_create('council-readonly.gds'), 'w+b') as temporary:
        temporary.write(gds)
        temporary.seek(0)
        layout = db.Layout()
        layout.read('/proc/self/fd/' + str(temporary.fileno()))
    assert layout.dbu == .001
    macro = layout.cell('RM_IHPSG13_1P_256x32_c2_bm_bist')
    counts = {'sram': Counter(), 'digital': Counter()}
    sites = Counter()
    for marker in markers:
        iterator = macro.begin_shapes_rec_overlapping(layout.layer(6, 0), marker)
        boxes = {}
        while not iterator.at_end():
            rectangle = iterator.shape().bbox().transformed(iterator.trans())
            if not (db.Region(marker) & db.Region(rectangle)).is_empty():
                boxes[str(rectangle)] = rectangle
            iterator.next()
        assert len(boxes) == 1
        contact = next(iter(boxes.values()))
        nearby = contact.enlarged(max(NUMBERS) + 10)
        def covered(layer_number, box):
            region = db.Region(macro.begin_shapes_rec_overlapping(layout.layer(layer_number, 0), nearby))
            return (db.Region(box) - region).is_empty()
        assert covered(16, contact)
        group = 'sram' if covered(25, contact) else 'digital'
        sites[group] += 1
        for required_nm in NUMBERS:
            counts[group][required_nm] += int(covered(1, contact.enlarged(required_nm)))
    return {'site_count': sites, 'covered_at_requirement_nm': counts}


def held_path(raw):
    section = raw.decode().split('slack (MET)', 1)[0]
    assert '_7350_/Q' in section and 'store.program_memory/A_ADDR[6]' in section
    def value(pattern):
        return Decimal(re.search(pattern, section, re.M)[1])
    arrival = value(r'^\s*(\d+\.\d+)\s+data arrival time')
    clock = value(r'^.*\s(\d+\.\d+) \^ store\.program_memory/A_CLK')
    hold = value(r'^\s*(\d+\.\d+)\s+\d+\.\d+\s+library hold time')
    baseline = value(r'^\s*(\d+\.\d+)\s+\d+\.\d+\s+clock uncertainty')
    limit = arrival - clock - hold
    return {'arrival_ns': str(arrival), 'capture_clock_ns': str(clock), 'library_hold_ns': str(hold),
            'uncertainty_ns': str(baseline), 'zero_slack_uncertainty_ns': str(limit),
            'baseline_hold_ns': str(limit-baseline), 'hold_at_0p375_ns': str(limit-Decimal('.375'))}


def main():
    result = {'started_utc': datetime.now(timezone.utc).isoformat(), 'klayout': db.__version__, 'runs': {}}
    markers = historical_markers()
    windows = []
    total = 0
    for run_id in (43543626249, 43543629839):
        directory = ROOT / f'ci-{run_id}'
        run = load(directory / 'result.json')
        index = load(directory / 'zip-files.json')
        rows = load(directory / 'jobs.json')['jobs']
        starts = [datetime.fromisoformat(row['started_at']) for row in rows]
        ends = [datetime.fromisoformat(row['completed_at']) for row in rows]
        durations = {row['name']: int((end-start).total_seconds()) for row, start, end in zip(rows,starts,ends)}
        windows.append((min(starts), max(ends)))
        total += sum(durations.values())
        result['runs'][run_id] = {'job_start_utc': windows[-1][0].isoformat(), 'job_end_utc': windows[-1][1].isoformat(),
                                 'job_seconds': durations, 'one_run_span_seconds': int((max(ends)-min(starts)).total_seconds()),
                                 'hold': held_path(read_member(directory, run, index, 'GDS_logs', FAST_REPORT)),
                                 'contacts': threshold_counts(read_member(directory, run, index, 'tt_submission', GDS), markers)}
    assert result['runs'][43543626249]['contacts'] == result['runs'][43543629839]['contacts']
    assert result['runs'][43543626249]['hold'] == result['runs'][43543629839]['hold']
    result['job_seconds_sum'] = total
    result['both_runs_first_start_to_last_finish_s'] = int((max(e for s,e in windows)-min(s for s,e in windows)).total_seconds())
    observation = load(Path('docs/research/rule-reviews/2026-11-24.json'))
    closure = load(ROOT / 'rules-closure-observation.json')
    assert observation['retrieval']['sha256'] == closure['retrieval']['sha256']
    result['organizer'] = {'observed_utc': observation['observed_utc'], 'sha256': observation['retrieval']['sha256'],
                           'final_form': observation['final_submission_form'], 'deadline': closure['deadline'],
                           'material': closure['required_material'], 'max_tiles': closure['maximum_tiles'],
                           'fixed_rate': closure['fixed_clock_or_protocol_speed_required'], 'video': closure['video_required']}
    result['ended_utc'] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
