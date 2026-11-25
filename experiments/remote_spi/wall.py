# SPDX-License-Identifier: Apache-2.0
"""Original requester nanoseconds on the safely routed 12.5 MHz target."""


def wall_tick(t):
    return (t+4)//8


def wall_trials(base_trials):
    for descriptor in base_trials('matrix'):
        if descriptor[4]!='short':
            yield descriptor


def wall_schedule(base_schedule, scenario, descriptor):
    case=base_schedule(scenario,descriptor)
    case['finish']+=12000
    return case
