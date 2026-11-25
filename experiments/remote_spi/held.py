# SPDX-License-Identifier: Apache-2.0
"""Original E0055 held-abort schedules with no SCK or CS edge after abort."""


def held_trials(suite):
    offsets = (0, 32) if suite == 'held' else (0,)
    for op in (0xa4, 0xa5):
        for bit in range(8):
            for polarity in (0, 1):
                for offset in offsets:
                    name = '%s-%02x-%d-%d-%d' % (suite, op, bit, polarity, offset)
                    yield name, op, 250, 7, suite, bit, polarity, offset


def held_schedule(scenario, descriptor):
    _, op, half, phase, suite, bit, polarity, offset = descriptor
    case = scenario(op, half, phase, 'hold', bit, polarity)
    frame = case['frames'][0]
    abort, pins = case['events'][-1]
    assert abort == frame['abort']
    offset_units = offset // 4
    case['events'][-1] = (abort + offset_units, pins)
    frame['abort'] += offset_units
    frame['end'] += offset_units
    case['finish'] += offset_units
    if suite == 'heldwall':
        case['finish'] += 12000
    return case
