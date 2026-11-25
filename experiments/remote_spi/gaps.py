# SPDX-License-Identifier: Apache-2.0
"""Follow-up requester timing matrix. Offset and gap are physical nanoseconds."""


def gap_trials(suite):
    for op in (0xa4, 0xa5):
        for half in ((250, 500, 1000) if suite=='settled' else (250,)):
            for phase in (1, 7, 13, 19):
                for bit in range(8):
                    for pol in (0, 1):
                        for extra in ((32,) if suite=='settled' else (0,32)):
                            for gap in ((640,) if suite=='settled' else (160,240,320,400,480,560,640)):
                                name='%s-%02x-%d-%d-%d-%d-%d-%d' % (suite,op,half,phase,bit,pol,extra,gap)
                                yield name,op,half,phase,suite,bit,pol,extra,gap


def gap_schedule(scenario, descriptor):
    name,op,half,phase,mode,bit,pol,extra,gap=descriptor
    case=scenario(op,half,phase,'reselect',bit,pol)
    first,fresh=case['frames']
    old=first['abort']
    start=fresh['select']
    move=(extra+gap)//4-160
    events=[]
    for t,v in case['events']:
        if t==old:
            t+=extra//4
        elif pol and t==old+80:
            t=old+extra//4+gap//8
        elif t>=start:
            t+=move
        events.append((t,v))
    case['events']=events
    first['abort']+=extra//4
    first['end']+=extra//4
    for key in ('select','end'):
        fresh[key]+=move
    for key in ('rises','falls'):
        fresh[key]=[t+move for t in fresh[key]]
    case['finish']+=move
    return case
