# SPDX-License-Identifier: Apache-2.0
"""Check host-visible UART observations and the physical clock-counter measurements."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.cold_load import UART_BINARY

CASES = {'slow-good': [0x96, 0x69], 'target-good': [0x96, 0x69],
         'target-bad-first': None, 'target-bad-second': None,
         'target-distinct': [0x3c, 0xa5], 'target-fresh': [0x96, 0x69]}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check(records, image_hash):
    require(len(records) == 3 + 2 * len(CASES), 'missing or extra physical observations')
    require(records[0].get('event') == 'controller' and records[-1].get('status') == 'PASS'
            and records[0]['original_hz'] == records[-1]['restored_cpu_hz']
            and records[-1]['host_uio_oe'] == 0, 'controller cleanup or identity missing')
    damaged = records[1]
    require((damaged['case'], damaged['event'], damaged['edge'], damaged['selector'],
             damaged['expected'], damaged['observed']) == ('damaged', 'readback_failure', 38, 0x81, 0, 1),
            'corrupt image escaped')
    for idx, (name, expected) in enumerate(CASES.items()):
        cold, run = records[2 + idx*2:4 + idx*2]
        require((cold['case'], cold['event'], cold['identity'], cold['status'], cold['edges'])
                == (name, 'cold', 0x22, 0x20, 76), 'invalid cold start: ' + name)
        data = bytes.fromhex(cold['image'])
        require(len(data) == 32 and hashlib.sha256(data).hexdigest() == image_hash
                and cold['registers'] == [[0xa0, 8], [0xa1, 255], [0xa4, 255]], 'readback differs: ' + name)
        bias = cold['uio1_pull_down_up']
        require(all(len(bias[k]) == 2 and all(v in (0, 1) for v in bias[k])
                    for k in ('driven_low', 'driven_high', 'released')), 'missing bias readings: ' + name)
        require((run['case'], run['event'], run['accepted']) == (name, 'uart', expected)
                and run['terminal'] == (0xa7 if expected else 0xe6), 'wrong delivery or terminal: ' + name)
        if expected or name == 'target-bad-second':
            require(run['tentative'] == (expected[0] if expected else 0x96), 'first byte differs: ' + name)
        hz = 1000000 if name == 'slow-good' else 12500000
        bound = run['max_poll_gap_us'] + run['max_read_sequence_us'] + 2
        require(run['configured_hz'] == hz and run['cpu_hz'] == 125000000 and run['polls'] >= 2
                and run['service_upper_us'] == bound and bound * hz < 4340 * 1000000,
                'physical service bound missed: ' + name)
        nominal_us = 100000 * 1000000 // hz
        require(run['pad_clock_periods'] == 100000 and abs(run['pad_count_elapsed_us'] - nominal_us) <= nominal_us/50,
                'physical clock pad disagrees: ' + name)


def check_evidence(directory):
    result = json.loads((directory / 'result.json').read_bytes())
    archive = ROOT / 'evidence/E0051-fabricfox-uart'
    expected_image = json.loads((archive/'result.json').read_bytes())['bitstream_sha256']
    require(result['image_sha256'] == expected_image == hashlib.sha256(
            (archive/'fabricfox-v2-12p5mhz.bin').read_bytes()).hexdigest(), 'FPGA image identity differs')
    require(result['uart_sha256'] == UART_BINARY and result['before']['present']
            and result['before']['kind'] == 'fpga' and result['before']['clients'] == 0,
            'incomplete board or program identity')
    require(result['upload']['size'] == 104090 and not result['upload']['evicted']
            and result['upload']['name'] == result['enable']['enabled'], 'gallery receipts differ')
    records = [json.loads(line[8:]) for line in (directory / 'terminal.log').read_bytes().splitlines()
               if line.startswith(b'UARTLAB ')]
    require(result['status'] == 'PASS_REMOTE_UART_DIGITAL' and records == result['observations'],
            'terminal and host receipt differ')
    check(records, UART_BINARY)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories', nargs='+', type=Path)
    for folder in parser.parse_args().directories:
        print('PASS_VERIFIED_REMOTE_UART', check_evidence(folder)['board'])
