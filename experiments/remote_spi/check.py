# SPDX-License-Identifier: Apache-2.0
"""Decode the physical requester, MISO, output-enable witness, HALT and clock."""
import argparse
from bisect import bisect_right
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_spi.remote import PROGRAM_SHA
from experiments.remote_spi.gaps import gap_schedule, gap_trials
from experiments.remote_spi.schedules import schedule, tick, trials
from experiments.spi_target.requester import scenario, REPLIES


def need(ok, why):
    if not ok:
        raise ValueError(why)


def records(raw):
    need(raw.startswith(b'OK') and raw.endswith(b'\x04\x04>'), 'missing clean MicroPython completion')
    return [json.loads(line[7:]) for line in raw[2:-3].splitlines() if line.startswith(b'SPILAB ')]


def unpack(r):
    data = bytes.fromhex(r['data'])
    n = r['count']
    need(10 < n <= 65535 and n%4 == 0, 'capture length')
    if not r['packed']:
        need(len(data)==n and max(data)<128, 'raw pin length or bits')
        return data
    need(len(data)%3==0 and data[:2]==bytes(2), 'transition encoding')
    result = bytearray(n)
    last, value = 0, data[2]
    for p in range(3,len(data),3):
        index = data[p] + (data[p+1]<<8)
        need(last<index<n and data[p+2]<128, 'transition order')
        result[last:index] = bytes([value])*(index-last)
        last, value = index, data[p+2]
    result[last:] = bytes([value])*(n-last)
    for phase in range(10):
        if r['template'] & (1<<phase):
            result[phase::10] = bytes(s ^ 64 for s in result[phase::10])
    return result


def transitions(samples, bit):
    mask = 1<<bit
    return [i for i in range(1,len(samples)) if (samples[i]^samples[i-1]) & mask]


def assess(descriptor, r):
    name = descriptor[0]
    need(name==r['name'], 'case name')
    mode = descriptor[4]
    case = (gap_schedule if mode in ('gaps','settled') else schedule)(scenario, descriptor)
    raw = unpack(r)
    need(len(raw)==4*((tick(case['finish'])+67)//4), 'capture does not span full case')
    # Align to the observed CS fall, then check every input change by pin. Two pins
    # commanded at once can reach the digital sampler on neighboring ticks.
    actual = [transitions(raw,i) for i in range(3)]
    first, *remaining = case['frames']
    need(actual[2] and (raw[0]&7)==4, 'missing idle or selection')
    shift = actual[2][0]-tick(first['select'])
    edge = {}
    for i in range(3):
        exp = [t for (prev, old),(t,new) in zip(case['events'],case['events'][1:]) if (old^new)&(1<<i)]
        got = actual[i]
        need(len(got)==len(exp), 'input transition count on pin '+str(i))
        for t, observed in zip(exp,got):
            need(abs(observed-tick(t)-shift)<=2, 'requester edge moved')
            edge[(i,t)] = observed
    clock_edges = transitions(raw,6)
    widths = [b-a for a,b in zip(clock_edges,clock_edges[1:])]
    need(widths and min(widths)>=4 and max(widths)<=6 and clock_edges[0]<=8 and len(raw)-clock_edges[-1]<=8,
         'continuous physical project clock')
    period = 2*(clock_edges[-1]-clock_edges[0])/(len(clock_edges)-1)
    need(abs(period-10)<0.02, 'project clock ratio')
    oe = transitions(raw,4)
    halts = transitions(raw,5)
    need(not raw[0]&0x30 and len(halts)==1 and raw[-1]&32 and not raw[-1]&16, 'HALT and released ending')
    halt = halts[0]
    metrics = dict(project_period_ticks=round(period,5), capture_samples=len(raw), status=r['status'])
    errors = []
    def test(ok,msg):
        if not ok:
            errors.append(msg)
    def active_value(t):
        return ((raw[t]>>3)&1) if raw[t]&16 else None
    def check_frame(frame, limit=None):
        setup, hold, bits = [], [], []
        rises = [edge[(0,t)] for t in frame['rises'][8:] if limit is None or t<=limit]
        for i,rise in enumerate(rises):
            level = (REPLIES[frame['command']]>>(7-i))&1
            test(active_value(rise)==level, 'sampled reply bit')
            lo,hi = rise,rise
            while lo and active_value(lo-1)==level:
                lo-=1
            while hi<len(raw) and active_value(hi)==level:
                hi+=1
            # One sample of interval uncertainty at each observed transition pair.
            setup.append((rise-lo-1)*8)
            hold.append((hi-rise-1)*8)
            bits.append((raw[rise]>>3)&1)
        if bits:
            test(min(setup)>=240 and min(hold)>=160, 'reply setup/hold')
        if len(bits)==8:
            byte = sum(v<<(7-i) for i,v in enumerate(bits))
            test(byte==REPLIES[frame['command']], 'decoded reply')
            metrics.update(reply=byte, min_setup_lower_ns=min(setup), min_hold_lower_ns=min(hold))

    def quiet(lo, hi):
        return not any(v&16 for v in raw[lo:hi])
    def disabled_after(origin):
        return next((i for i in oe if i>=origin and not raw[i]&16),None)
    start = edge[(2,first['select'])]
    if first['command'] not in REPLIES:
        test(quiet(start,len(raw)) and r['status']==0xba,'invalid command terminal or drive')
    else:
        test(quiet(start,edge[(0,first['falls'][7])]),'driven command prefix')
        if remaining:
            fresh, = remaining
            abort = edge[(2,first['abort'])]
            new_cs = edge[(2,fresh['select'])]
            bit = (REPLIES[first['command']]>>(7-first['bit']))&1
            test(active_value(abort-1)==bit, 'expected driven bit at abort')
            if active_value(abort-1)!=bit:
                first_match = next((t for t in range(abort,new_cs) if active_value(t)==bit),None)
                metrics['preabort_bit_late_ns'] = None if first_match is None else (first_match-abort)*8
            disabled = disabled_after(abort)
            need(disabled is not None,'no output disable after abort')
            delta = (disabled-abort)*8
            metrics.update(abort_ns=delta, handoff_ns=(new_cs-abort)*8, enabled_at_fresh=bool(raw[new_cs]&16),
                           release_to_fresh_lower_ns=(new_cs-disabled-1)*8)
            test(delta+8<=640,'scaled abort deadline')
            test(disabled<=new_cs and quiet(disabled,edge[(0,fresh['falls'][7])]),'fresh command did not stay released')
            check_frame(fresh)
            test(r['status']==0xb9,'fresh success terminal')
        elif mode=='pause':
            origin=edge[(0,first['lost_clock'])]
            delta=(halt-origin)*8
            metrics.update(timeout_ns=delta)
            test(0<=delta and delta+8<=8000 and r['status']==0xbb,'selected timeout')
            test(quiet(halt,len(raw)) and not any(v&4 for v in raw[origin:halt+1]),'released timeout while selected')
            check_frame(first,first['lost_clock'])
        else:
            check_frame(first)
            release=disabled_after(edge[(0,first['falls'][-1])])
            test(release is not None and (release-edge[(0,first['falls'][-1])]+1)*8<=640,'normal release')
            test(r['status']==0xb9,'normal terminal')
    metrics['errors']=sorted(set(errors))
    return metrics


def audit(raw,suite,strict=True):
    rows=records(raw)
    need(rows[0]['event']=='start' and rows[0]['suite']==suite and rows[-1]['event']=='finish' and
         rows[-1]['restored_hz']==rows[0]['original_hz'] and rows[-1]['host_uio_oe']==0,'session boundaries')
    bad, cold = rows[1:3]
    need(bad['event']=='readback_error' and bad['selector']==0x81 and bad['observed']==(bad['expected']^1),
         'wrong-byte control')
    need(cold['event']=='cold' and cold['rows']==1050 and cold['registers']==[[160,126],[161,60],[164,167]]
         and hashlib.sha256(bytes.fromhex(cold['image'])).hexdigest()==PROGRAM_SHA,'full program and register readback')
    wanted=list(gap_trials(suite) if suite in ('gaps','settled') else trials(suite))
    captures=rows[3:-1]
    need([r['name'] for r in captures]==[d[0] for d in wanted], 'case inventory')
    measured={}
    groups=defaultdict(list)
    for desc,r in zip(wanted,captures):
        try:
            m=assess(desc,r)
        except (ValueError,KeyError,IndexError) as exc:
            raise ValueError(desc[0]+': '+str(exc)) from exc
        measured[desc[0]]=m
        groups[desc[4]].append(m)
    failures=[n for n,m in measured.items() if m['errors'] and not n.startswith('short-')]
    if strict:
        need(not failures,'failed case '+str([(k,measured[k]['errors']) for k in failures[:3]]))
    def span(group, field):
        values=[m[field] for m in groups[group] if field in m]
        return [min(values),max(values)] if values else []
    summary=dict(cases=len(wanted),failures=failures,groups={k:len(v) for k,v in groups.items()},
                 abort_ns=span('reselect','abort_ns'),timeout_ns=span('pause','timeout_ns'),
                 handoff_ns=span('reselect','handoff_ns'), samples=sum(m['capture_samples'] for m in measured.values()),
                 short_controls={k:v for k,v in measured.items() if k.startswith('short-')})
    return summary,measured


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    p.add_argument('--report-only',action='store_true')
    a=p.parse_args()
    rec=json.loads((a.directory/'result.json').read_bytes())
    summary,measured=audit(gzip.decompress((a.directory/'terminal.bin.gz').read_bytes()),rec['suite'],not a.report_only)
    print(json.dumps(summary,indent=2))
