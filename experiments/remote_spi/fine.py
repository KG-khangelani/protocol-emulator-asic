# SPDX-License-Identifier: Apache-2.0
"""Repeat the settled fastest-rate cases across the measured gap boundary."""


def fine_trials(gap_trials):
    for gap in range(480, 399, -8):
        for _, op, half, phase, _, bit, pol, offset, coarse_gap in gap_trials('gaps'):
            if offset == 32 and coarse_gap == 480:
                name = 'fine-%02x-%d-%d-%d-%d-%d-%d' % (op, half, phase, bit, pol, offset, gap)
                yield name, op, half, phase, 'fine', bit, pol, offset, gap
