# SPDX-License-Identifier: Apache-2.0
"""Independent external pin/time mathematics; no VM, encoder or RTL imports."""

from bisect import bisect_right
import hashlib
import json

PERIOD_PS=20000
LOW=[2+50*j for j in range(8)]
RISING=[n+25 for n in LOW]
FALLING=[n+50 for n in LOW]
CAPTURE=[n+2 for n in RISING]
RELEASE=402
HALT=403


def bit(byte,index,order):
    if not 0<=byte<=255 or order not in (0,1) or not 0<=index<8:
        raise ValueError('byte/index/order out of range')
    return (byte>>(7-index if order else index))&1


def assemble(values,order):
    if len(values)!=8 or any(v not in (0,1) for v in values): raise ValueError('eight binary values required')
    return sum(v<<(7-j if order else j) for j,v in enumerate(values))


def literal_image(order,*,early=False):
    if order not in (0,1): raise ValueError('binary order required')
    return [0x65000008,0xA0486000|(order<<28),0x40000017,0x00040404,
            (0xA0500000 if early else 0xA0500008)|(order<<28),
            0x40000016 if early else 0x40000015,0x000C0C08,0x80000000]


def gpio(edge,tx,order):
    if edge<2: return 0,0
    index=min((edge-2)//50,7)
    clock=int(edge<RELEASE and (edge-2)%50>=25)
    return bit(tx,index,order)|(clock<<2)|(int(edge>=RELEASE)<<3),13


def normalize_event(time):
    # Coincident raw changes are placed explicitly before the sampled edge.
    return time-1 if time%PERIOD_PS==0 else time


def events(rx,order,responses,*,noise=False,hold_ps=1):
    if len(responses)!=8 or any(type(d) is not int or d<1 for d in responses):
        raise ValueError('eight positive picosecond responses required')
    changes=[]
    for j,(low,rise,delay) in enumerate(zip(LOW,RISING,responses)):
        value=bit(rx,j,order)
        changes.append((normalize_event(low*PERIOD_PS+delay),value))
        if noise:
            changes.extend([(rise*PERIOD_PS-2,1-value),
                            (rise*PERIOD_PS-1,value),
                            (rise*PERIOD_PS+hold_ps+1,1-value)])
    changes.append((RELEASE*PERIOD_PS+5000,1))
    merged={t:v for t,v in changes}
    result=[]; previous=1
    for t,v in sorted(merged.items()):
        if t<0: raise ValueError('negative event')
        if v!=previous: result.append([t,v]); previous=v
    return result


def level(changes,time):
    index=bisect_right([e[0] for e in changes],time)-1
    return changes[index][1] if index>=0 else 1


def envelope_errors(changes,rx,order,*,setup_ps=1,hold_ps=1):
    errors=[]
    for j,rise in enumerate(RISING):
        start,end=rise*PERIOD_PS-setup_ps,rise*PERIOD_PS+hold_ps
        intended=bit(rx,j,order)
        if level(changes,start)!=intended or any(start<t<=end and v!=intended for t,v in changes):
            errors.append(j)
    return errors


def wire_word(changes,order):
    return assemble([level(changes,n*PERIOD_PS) for n in RISING],order)


def transport_word(changes,order,*,early=False):
    # Two ideal stages: capture on R+2 consumes raw R; early capture R+1 raw R-1.
    return assemble([level(changes,(n-int(early))*PERIOD_PS) for n in RISING],order)


def event_hash(changes):
    return hashlib.sha256(json.dumps(changes,separators=(',',':')).encode()).hexdigest()
