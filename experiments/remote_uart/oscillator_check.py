# SPDX-License-Identifier: Apache-2.0
"""Decode simultaneous external UART data and FPGA clock samples for the D56 fixture."""

from bisect import bisect_left
import hashlib
import math

from experiments.remote_uart.check import check_cold, check_setup, require
from experiments.remote_uart.margin_check import decode_levels

NOMINAL_MHZ = 12
REF_MHZ = 125
CASES = ('preset', 'calibration', 'matched', 'distinct', 'fast', 'slow', 'bad-first', 'bad-second')


def capture(records, idx, name, length):
    raw = bytearray()
    while idx < len(records) and records[idx].get('event') == 'samples':
        row = records[idx]
        data = bytes.fromhex(row['data'])
        require(row['case'] == name and row['offset'] == len(raw)
                and len(data) == min(1024, length-len(raw)) and data, 'missing or reordered capture chunk')
        raw.extend(data)
        idx += 1
    require(len(raw) == length, 'incomplete pad capture: ' + name)
    return raw, idx


def clock_trace(raw, nominal):
    levels = [(byte >> shift) & 3 for byte in raw for shift in (0, 2, 4, 6)]
    rising = [i for i in range(1, len(levels)) if levels[i] & 2 and not levels[i-1] & 2]
    require(len(rising) > 100, 'receiver clock absent')
    periods = len(rising) - 1
    span = rising[-1]-rising[0]
    period = span / periods
    gaps = [b-a for a, b in zip(rising, rising[1:])]
    require(rising[0] <= math.ceil(period)+1 and len(levels)-rising[-1] <= math.ceil(period)+1
            and min(gaps) >= math.floor(period)-1 and max(gaps) <= math.ceil(period)+1,
            'receiver clock has an interruption or an extra edge')
    mhz = REF_MHZ / (2*period)
    require(0.8*nominal <= mhz <= 1.1*nominal, 'observed clock outside fixture timing screen')
    measured = {'first_rise': rising[0], 'last_rise': rising[-1], 'rising': len(rising),
                'receiver_mhz_relative_to_rp': round(mhz, 6), 'max_period_ticks': 2*max(gaps),
                'samples': len(levels), 'sha256': hashlib.sha256(raw).hexdigest()}
    return [v & 1 for v in levels], rising, measured


def check_oscillator(records, image_hash):
    check_setup(records)
    nominal_ticks = (REF_MHZ*434 + NOMINAL_MHZ//2)//NOMINAL_MHZ
    matched = None
    summary = {}
    idx = 2
    for name in CASES:
        check_cold(records[idx], name, image_hash)
        idx += 1
        ticks = nominal_ticks if name == 'preset' else matched
        if name == 'fast':
            ticks = (100*matched+51)//102
        if name == 'slow':
            ticks = (100*matched+49)//98
        length = 4096 if name == 'calibration' else 4*((20*ticks+2048+31)//32)
        raw, idx = capture(records, idx, name, length)
        data, rising, info = clock_trace(raw, NOMINAL_MHZ)
        row = records[idx]
        idx += 1
        require(row['case'] == name and row['cpu_hz'] == REF_MHZ*1000000, 'wrong case or reference')
        if name == 'calibration':
            require(row['event'] == 'clock' and row['request_level'] == 0 and all(data),
                    'calibration did not observe the oscillator with idle UART and run held low')
            n = len(rising)-1
            matched = (2*434*(rising[-1]-rising[0])+n//2)//n
            require(row['matched_ticks'] == matched and all(row[k] == info[k] for k in ('first_rise','last_rise','rising')),
                    'independent idle-clock recount differs')
            summary[name] = dict(info, matched_ticks=matched)
            continue
        require(row['event'] == 'oscillator_uart' and row['cell_ticks'] == ticks
                and (row['request_level'], row['early_fall'], row['final_fall']) == (1, 0, 1),
                'transmitter setting or steady run-enable control differs: ' + name)
        pair = (0x96, 0x69) if name == 'distinct' else (0x55, 0xaa)
        stops = (int(name != 'bad-first'), int(name != 'bad-second'))
        wire = decode_levels(data, ticks, pair, stops)
        rx_ticks = 2*(rising[-1]-rising[0])/(len(rising)-1)
        offset = (434*rx_ticks/ticks - 1)*100
        wire_ticks = wire['second_start_spacing_ticks']
        if wire_ticks is not None:
            first = wire['first_fall_sample']
            count = bisect_left(rising, first+wire_ticks//2)-bisect_left(rising, first)
            require(abs(count-wire_ticks/rx_ticks) <= 2, 'clock count between starts differs')
            info['receiver_edges_between_starts'] = count
        if name != 'preset':
            expected_offset = {'fast': 2, 'slow': -2}.get(name, 0)
            require(abs(offset-expected_offset) <= 0.5, 'measured baud offset differs: ' + name)
        good = stops == (1, 1)
        delivered = row['terminal'] == 0xa7 and row['accepted'] == list(pair) and row['tentative'] == pair[0]
        if name != 'preset':
            if good:
                require(delivered, 'two-frame delivery failed: ' + name)
            else:
                require(row['terminal'] == 0xe6 and row['accepted'] is None, 'framing fault escaped')
                if stops[0]:
                    require(row['tentative'] == pair[0], 'second-stop fault lost the tentative first byte')
        bound = row['max_poll_gap_us']+row['max_read_sequence_us']+2
        # Reserve one full observed RX clock and one sample for edge quantization.
        interval = min(10*ticks, wire_ticks) if wire_ticks is not None else 10*ticks
        budget = interval-info['max_period_ticks']-2
        require(row['polls'] >= 2 and min(row['max_poll_gap_us'], row['max_read_sequence_us']) > 0
                and row['service_upper_us'] == bound and bound*REF_MHZ < budget,
                'host missed measured service budget: ' + name)
        summary[name] = dict(info, wire=wire, cell_ticks=ticks, delivered=delivered, terminal=row['terminal'],
                             observed_bytes=row['accepted'], measured_offset_pct=round(offset, 5),
                             service_upper_us=bound, conservative_budget_us=budget/REF_MHZ)
    require(idx == len(records)-1, 'extra board observations')
    return summary
