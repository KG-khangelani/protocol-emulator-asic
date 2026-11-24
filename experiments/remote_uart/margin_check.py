# SPDX-License-Identifier: Apache-2.0
"""Reconstruct D55's physical serial traces and check the separately read FPGA results."""

import hashlib

from experiments.remote_uart.check import check_cold, check_setup, require


def matrix():
    for rate, cell in (('fast', 4254), ('nominal', 4340), ('slow', 4429)):
        for delay in (0, 4, 8):
            yield f'{rate}-{delay}', cell, delay, (0x55, 0xaa), (1, 1)
    yield 'fast-distinct', 4254, 4, (0xa5, 0x3c), (1, 1)
    yield 'fast-bad-first', 4254, 4, (0x55, 0xaa), (0, 1)
    yield 'slow-bad-second', 4429, 4, (0x55, 0xaa), (1, 0)


def decode_wire(encoded, cell_ticks, pair, stops):
    packed = bytes.fromhex(encoded)
    require(len(packed) == 5760, 'short digital capture')
    samples = [(byte >> bit) & 1 for byte in packed for bit in range(8)]
    result = decode_levels(samples, cell_ticks, pair, stops)
    result['samples_sha256'] = hashlib.sha256(packed).hexdigest()
    return result


def decode_levels(samples, cell_ticks, pair, stops):
    edges = [i for i in range(1, len(samples)) if samples[i] != samples[i-1]]
    require(samples[0] == samples[-1] == 1 and bool(edges), 'missing idle or frame start')
    start = edges[0]
    require(20 <= start <= 125 and len(samples)*2 > start*2 + 20*cell_ticks,
            'capture starts outside the arming window or ends within the pair')

    # Build the expected level in each UART cell from the published workload.
    # Compare all transitions against time measured from the actual first fall.
    levels = []
    for value, stop in zip(pair, stops):
        levels.extend([0] + [(value >> k) & 1 for k in range(8)] + [stop])
    levels.append(1)
    boundaries = [i for i, level in enumerate(levels) if level != (levels[i-1] if i else 1)]
    require(len(edges) == len(boundaries), 'missing or extra physical pad transition')
    errors = [2*(observed-start) - index*cell_ticks for observed, index in zip(edges, boundaries)]
    require(max(map(abs, errors)) <= 2, 'physical transition differs by more than one sample')
    centers = [samples[start + ((2*i+1)*cell_ticks)//4] for i in range(20)]
    decoded = [sum(centers[base+k+1] << k for k in range(8)) for base in (0, 10)]
    require(centers[0] == centers[10] == 0 and tuple(decoded) == pair
            and (centers[9], centers[19]) == stops, 'wire payload or stop differs')
    return {'first_fall_sample': start, 'transitions': len(edges), 'decoded': decoded,
            'stop_levels': [centers[9], centers[19]], 'max_edge_error_ticks': max(map(abs, errors)),
            'second_start_spacing_ticks': 2*(edges[boundaries.index(10)]-start) if 10 in boundaries else None}


def check_margin(records, image_hash):
    cases = list(matrix())
    require(len(records) == 3 + 2*len(cases), 'missing or extra baud-offset records')
    check_setup(records)
    summary = {}
    for idx, (name, ticks, delay, pair, stops) in enumerate(cases):
        cold, run = records[2+2*idx:4+2*idx]
        check_cold(cold, name, image_hash)
        require((run['case'], run['event'], run['cell_ticks'], run['delay_ticks'], run['cpu_hz'])
                == (name, 'margin', ticks, delay, 125000000), 'wrong trial settings: ' + name)
        summary[name] = decode_wire(run['samples_hex'], ticks, pair, stops)
        good = stops == (1, 1)
        require(run['terminal'] == (0xa7 if good else 0xe6)
                and run['accepted'] == (list(pair) if good else None), 'wrong FPGA delivery: ' + name)
        if stops[0]:
            require(run['tentative'] == pair[0], 'first capture lost: ' + name)
        bound = run['max_poll_gap_us'] + run['max_read_sequence_us'] + 2
        require(run['polls'] >= 2 and min(run['max_poll_gap_us'], run['max_read_sequence_us']) > 0
                and run['service_upper_us'] == bound and bound * 125 < 10*ticks,
                'host missed rate-specific service deadline: ' + name)
        require(run['pad_clock_periods'] == 100000 and abs(run['pad_count_elapsed_us']-8000) <= 160,
                'project clock pad count disagrees: ' + name)
    for rate in ('fast', 'nominal', 'slow'):
        starts = [summary[f'{rate}-{delay}']['first_fall_sample'] for delay in (0, 4, 8)]
        for earlier, later in zip(starts, starts[1:]):
            require(abs(later-earlier-2) <= 1, 'launch delay invisible on pad: ' + rate)
    return summary
