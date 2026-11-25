"""Rebuild the SPI measurement tables from the archived physical captures."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_spi.check import assess, audit, need, records, transitions, unpack
from experiments.remote_spi.held import held_trials
from experiments.remote_spi.remote import board_code, IMAGE_SHA, NAME, PROGRAM_SHA, WHEEL_SHA
from experiments.remote_spi.schedules import trials
from tools.production_sram import verify

SUITES = ('pilot', 'matrix', 'settled', 'gaps', 'wall', 'fine', 'held', 'heldwall')


def read(path):
    return json.loads(path.read_bytes())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def group(rows, family):
    def count(field):
        return sum(row.get(field) is True for row in rows)

    def span(field):
        values = [r[field] for r in rows if field in r]
        return [min(values), max(values)] if values else []

    result = dict(cases=len(rows), strict_pass=sum(not r['errors'] for r in rows),
                  terminal_status=dict(sorted(Counter(f"0x{r['status']:02x}" for r in rows).items())),
                  failures_by_check=dict(sorted(Counter(e for r in rows for e in r['errors']).items())))
    if family in ('short', 'reselect', 'settled', 'gaps', 'fine'):
        result.update(active_before_abort=count('active_before_abort'),
                      expected_bit_before_abort=count('bit_correct_before_abort'),
                      enable_low_by_deadline=count('released_by_deadline'),
                      enable_high_at_reselection=count('enabled_at_fresh'),
                      quiet_until_fresh_reply=count('quiet_through_fresh_prefix'),
                      correct_fresh_byte_and_setup_hold=count('valid_fresh_byte'),
                      first_observed_disable_ns=span('abort_ns'), measured_cs_high_ns=span('handoff_ns'),
                      release_to_select_lower_ns=span('release_to_fresh_lower_ns'),
                      strict_with_positive_margin=sum(not r['errors'] and
                          r.get('release_to_fresh_lower_ns', 0)>0 for r in rows),
                      fresh_setup_lower_ns=span('min_setup_lower_ns'), fresh_hold_lower_ns=span('min_hold_lower_ns'))
    if family=='pause':
        result.update(selected_stall_timeouts=sum('timeout_ns' in r for r in rows),
                      selected_stall_ns=span('timeout_ns'), timeout_marker_ns=span('timeout_marker_ns'))
    if family in ('held','heldwall'):
        result.update(active_before_abort=count('active_before_abort'),
                      expected_bit_before_abort=count('bit_correct_before_abort'),
                      enable_low_by_deadline=count('released_by_deadline'),
                      stayed_disabled=count('quiet_after_release'),
                      first_observed_disable_ns=span('abort_ns'),
                      fixed_clock_observation_ns=span('held_after_abort_ns'))
    return result


def campaign(suite, profile, identity):
    folder = HERE/'board-4'/suite
    receipt = read(folder/'result.json')
    raw = gzip.decompress((folder/'terminal.bin.gz').read_bytes())
    need(receipt['suite']==suite and receipt['board']=='fpga-4' and receipt['clients_before']==0 and
         receipt['board_identity_sha256']==identity and receipt['profile_sha256']==profile and
         receipt['program_sha256']==PROGRAM_SHA and receipt['image_sha256']==IMAGE_SHA and
         receipt['board_code_sha256']==sha(board_code(suite)), 'capture provenance: '+suite)
    need(receipt['upload']==dict(name=NAME, size=104090, evicted=[]) and
         receipt['enable']['enabled']==NAME, 'gallery receipt')
    if suite=='pilot':
        need(receipt['status']=='INCOMPLETE' and '404' in receipt['error'], 'original restoration failure')
    else:
        need(receipt['status']=='CAPTURED' and receipt['restore_via']==receipt['after']=='tt_um_factory_test',
             'board restoration: '+suite)
    summary, measurements = audit(raw,suite,strict=False)
    need(receipt['observations']==summary['cases'], 'live observation count')
    output = dict(trials=summary['cases'], samples=summary['samples'], groups={})
    for family, size in summary['groups'].items():
        cases = [row for name,row in measurements.items() if name.startswith(family+'-')]
        need(size==len(cases), 'group size')
        output['groups'][family]=group(cases,family)
    if suite=='matrix':
        output['preabort_counterexamples'] = {
            name:m['preabort_bit_late_ns'] for name,m in measurements.items() if name in summary['failures']}
    if suite in ('held','heldwall'):
        output['by_abort_offset_ns']={}
        for offset in sorted({d[-1] for d in held_trials(suite)}):
            selected=[d for d in held_trials(suite) if d[-1]==offset]
            output['by_abort_offset_ns'][str(offset)] = {
                label:group([measurements[d[0]] for d in selected if pol is None or d[6]==pol],suite)
                for label,pol in (('both',None),('sck_low',0),('sck_high',1))}
    if suite in ('gaps','fine'):
        grid = {}
        for name, row in measurements.items():
            _,extra,gap = name.rsplit('-',2)
            grid.setdefault(extra,{}).setdefault(int(gap),[]).append(row)
        output['gap_sweep']={}
        for offset, intervals in grid.items():
            scores = {gap:group(rows,suite) for gap,rows in sorted(intervals.items())}
            candidates = [gap for gap in scores if all(s['strict_with_positive_margin']==s['cases']
                          for g,s in scores.items() if g>=gap)]
            output['gap_sweep'][offset]=dict(shortest_passing_tested_ns=min(candidates,default=None),
                                              by_requested_gap_ns={str(g):s for g,s in scores.items()})
    return output


def adverse_controls():
    raw = gzip.decompress((HERE/'board-4/pilot/terminal.bin.gz').read_bytes())
    trace = next(r for r in records(raw) if r.get('name','').startswith('reselect-'))
    descriptor = next(d for d in trials('pilot') if d[0]==trace['name'])
    pins = unpack(trace)
    need(not assess(descriptor,trace)['errors'], 'baseline for adverse controls')
    new_cs = [i for i in transitions(pins,2) if not pins[i]&4][1]
    first_reply = [i for i in transitions(pins,0) if i>new_cs and pins[i]&1][8]
    def check_pins(samples):
        return assess(descriptor, dict(trace,packed=False,data=samples.hex()))
    for mask, expected in ((1,'input transition count'), (64,'continuous physical project clock')):
        try:
            check_pins(bytes(v & ~mask for v in pins))
        except ValueError as exc:
            need(expected in str(exc), 'wrong capture rejection')
        else:
            raise ValueError('absent channel was accepted')
    samples=bytearray(pins)
    samples[new_cs] |= 16
    need('fresh command did not stay released' in check_pins(samples)['errors'], 'stale drive control')
    samples=bytearray(pins)
    samples[first_reply] ^= 8
    need('sampled reply bit' in check_pins(samples)['errors'], 'wrong physical bit control')
    need('success terminal after deselection' in assess(descriptor,dict(trace,status=0xbb))['errors'],
         'wrong terminal control')
    program=records(raw)[2]['image'].encode()
    damaged=(b'00' if program[:2]!=b'00' else b'01')+program[2:]
    try:
        audit(raw.replace(program,damaged,1),'pilot')
    except ValueError as exc:
        need('full program and register readback' in str(exc), 'wrong readback rejection')
    else:
        raise ValueError('altered archived program accepted')
    held_raw=gzip.decompress((HERE/'board-4/held/terminal.bin.gz').read_bytes())
    descriptor=next(d for d in held_trials('held') if d[-1]==32)
    trace=next(r for r in records(held_raw) if r.get('name')==descriptor[0])
    samples=bytearray(unpack(trace))
    abort=transitions(samples,2)[-1]
    release=next(t for t in transitions(samples,4) if t>abort and not samples[t]&16)
    samples[release+4] |= 16
    result=assess(descriptor,dict(trace,packed=False,data=samples.hex()))
    need('MISO enable reasserted after held abort' in result['errors'], 'held enable reassertion')


def main(output):
    profile=verify(ROOT)
    need(len(profile['files_sha256'])==20, 'qualified input inventory')
    for tag in ('v0.1.0','v0.1.1'):
        for path,digest in profile['files_sha256'].items():
            data=subprocess.check_output(['git','show',tag+':'+path],cwd=ROOT)
            need(sha(data)==digest, tag+' '+path)
    route=read(HERE/'route-a.json')
    need(route==read(HERE/'route-b.json') and route['production_profile_sha256']==profile['profile_sha256'] and
         route['image_sha256']==sha((HERE/'fabricfox-spi.bin').read_bytes())==IMAGE_SHA, 'repeated route')
    need(sha((ROOT/'evidence/E0056-spi-target-watchdog/program.bin').read_bytes())==PROGRAM_SHA,
         'E0056 selected binary')
    for path,digest in route['source_sha256'].items():
        need(sha((ROOT/path).read_bytes())==digest,'route input '+path)
    need([(r['mhz'],r['exit']) for r in route['routes']]==[(50,1),(12.5,0)], 'timing outcomes')
    for r in route['routes']:
        rate=r['mhz']
        timing=json.loads(gzip.decompress((HERE/f'route-{rate}-timing.json.gz').read_bytes()))
        clock,=timing['fmax'].values()
        need(clock==r['clock'] and timing['utilization']==r['utilization'] and
             (clock['achieved']>=rate)==(r['exit']==0), 'router timing report')
    access=read(HERE/'access.json')
    restored=read(HERE/'restoration.json')
    for board in ('fpga-4','fpga-1'):
        need(access[board]['present'] and access[board]['reachable'] and
             access[board]['identity']==restored[board]['identity'], 'board identity')
    need(access['fpga-4']['clients']==0 and access['fpga-1']['clients']>0 and
         restored['fpga-4']['idle_display']['state']=='loaded', 'fixture access and final service state')
    measured={s:campaign(s,profile['profile_sha256'],access['fpga-4']['identity']) for s in SUITES}
    adverse_controls()
    if output:
        output.write_bytes((json.dumps(measured,indent=2)+'\n').encode())
        return
    need(read(HERE/'summary.json')==measured,'recomputed physical measurements')
    final=read(HERE/'held-restoration.json')['fpga-4']
    need(final['identity']==access['fpga-4']['identity'] and final['clients']==0 and
         final['selection']=='idle_display' and final['idle_display']['state']=='loaded',
         'service state after fixed-clock sessions')
    manifest=read(HERE/'manifest.json')
    artifacts={f.relative_to(HERE).as_posix() for f in HERE.rglob('*') if f.is_file() and
               f.name not in ('manifest.json','audit.py','README.md') and '__pycache__' not in f.parts}
    need(set(manifest['sha256'])==artifacts and manifest['wheel_sha256']==WHEEL_SHA, 'artifact inventory')
    for path,digest in manifest['sha256'].items():
        need(sha((HERE/path).read_bytes())==digest,'artifact '+path)
    for path,digest in manifest['source_sha256'].items():
        need(sha((ROOT/path).read_bytes())==digest,'experiment source '+path)
    checks=read(HERE/'checks.json')
    need([c['status'] for c in checks]==['PASS','FAILED_OR_INCOMPLETE','PASS'] and
         checks[1]['error']=='AssertionError: inputs changed during execution', 'repository check records')
    log=gzip.decompress((HERE/'check.log.gz').read_bytes())
    need(sum(map(int,re.findall(rb'Ran ([0-9]+) tests?',log)))==163, 'repository check count')
    print(f"PASS: {sum(s['trials'] for s in measured.values()):,} physical trials reproduced, "
          "seven altered-capture controls rejected, two release profiles checked")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-summary',type=Path,help='export independently decoded measurements as JSON')
    main(parser.parse_args().write_summary)
