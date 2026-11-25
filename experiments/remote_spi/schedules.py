# SPDX-License-Identifier: Apache-2.0
"""Shared descriptors for the physical peer; scenario itself is frozen in E0055."""


def trials(suite):
    pilot = [('reselect-a4-250-7-3-0', 0xa4, 250, 7, 'reselect', 3, 0),
             ('reselect-a5-500-13-0-1', 0xa5, 500, 13, 'reselect', 0, 1),
             ('pause-a4-0-0', 0xa4, 250, 7, 'pause', 0, 0),
             ('pause-a5-7-1', 0xa5, 250, 7, 'pause', 7, 1)]
    for op in (0xa4, 0xa5, 0):
        yield ('normal-%02x' % op, op, 500, 7, 'normal', 0, 1)
    yield ('short-a4', 0xa4, 250, 7, 'short', 3, 0)
    yield ('short-a5', 0xa5, 250, 7, 'short', 4, 0)
    if suite == 'pilot':
        for item in pilot:
            yield item
        return
    for op in (0xa4, 0xa5):
        for half in (250, 500, 1000):
            for phase in (1, 7, 13, 19):
                for bit in range(8):
                    for pol in (0, 1):
                        name = 'reselect-%02x-%d-%d-%d-%d' % (op, half, phase, bit, pol)
                        yield name, op, half, phase, 'reselect', bit, pol
        for bit in range(8):
            for pol in (0, 1):
                yield 'pause-%02x-%d-%d' % (op, bit, pol), op, 250, 7, 'pause', bit, pol


def schedule(scenario, descriptor):
    name, op, half, phase, mode, bit, pol = descriptor
    case = scenario(op, half, phase, 'reselect' if mode == 'short' else mode, bit, pol)
    if mode == 'short':
        fresh = case['frames'][1]
        old = fresh['select']
        case['events'] = [(t - 120 if t >= old else t, v) for t, v in case['events']]
        for key in ('select', 'end'):
            fresh[key] -= 120
        for key in ('rises', 'falls'):
            fresh[key] = [t - 120 for t in fresh[key]]
        case['finish'] -= 120
    return case


def tick(t):
    # At 12.5 MHz one E0055 nanosecond scales to four nominal nanoseconds.
    # Quantize the absolute edge time to the nearest 8 ns RP2350 sample.
    return (t + 1) // 2
