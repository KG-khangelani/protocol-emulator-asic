# SPDX-License-Identifier: Apache-2.0
"""Audit the two independent clock paths, raw board terminals and retained early failures."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_uart.check import require
from experiments.remote_uart.oscillator_check import check_oscillator, NOMINAL_MHZ
from tools.cold_load import UART_BINARY
from tools.production_sram import verify


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(revision, path):
    return subprocess.check_output(['git', 'show', revision + ':' + path], cwd=ROOT)


def board_payload(revision):
    archive = blob(revision, 'evidence/E0050-powered-cold-loader/uart-transcript.json.gz')
    raw = gzip.decompress(archive)
    require(sha(raw) == 'c660d0d69282094b6999c4b5ce83303e77c0307be5571762ec64ebb7ffb0a188', 'loader differs')
    rows = json.loads(raw)['loader']
    steps = [(r['ui_in'], r['rst_n'], r['raw'] if r['host_drives_uio'] else -1,
              r['expected'].get('uo_out', -1), r['expected'].get('uio_out', -1)) for r in rows]
    return (('STEPS = ' + repr(steps) + '\n').encode() + blob(revision, 'experiments/remote_uart/on_board.py') +
            f'\nNOMINAL_MHZ = {NOMINAL_MHZ}\n'.encode() + blob(revision, 'experiments/remote_uart/independent_peer.py') +
            b'\nrun_suite(oscillator_trials, (xtal_peer, clock_and_data, idle_clock_and_data, watch_enable), 3, isolated_cold)\n')


def receipt(folder):
    path = folder / 'result.json.gz'
    data = gzip.decompress(path.read_bytes()) if path.exists() else (folder / 'result.json').read_bytes()
    row = json.loads(data)
    raw = gzip.decompress((folder/'terminal.bin.gz').read_bytes())
    require(raw.startswith(b'OK') and raw.endswith(b'\x04>'), 'incomplete terminal')
    stdout, stderr = raw[2:-2].split(b'\x04', 1)
    records = [json.loads(s[8:]) for s in stdout.splitlines() if s.startswith(b'UARTLAB ')]
    require(records == row['observations'], 'raw board response and host receipt differ')
    require(row['restored_design'] == row['before']['enabled'], 'gallery not restored')
    return row, stderr


def verify_build(revision):
    a, b = (json.loads((HERE/f'receiver-build-{i}.json').read_bytes()) for i in ('a', 'b'))
    require(a == b and a['status'] == 'PASS_OSCILLATOR_BUILD' and a['nominal_mhz'] == NOMINAL_MHZ,
            'clean builds differ')
    for path, expected in a['sources_sha256'].items():
        require(sha(blob(revision, path)) == expected, 'FPGA input differs: ' + path)
    timing = a['routes'][-1]
    require(timing['route_exit'] == 0 and abs(timing['timing']['constraint']-1.1*NOMINAL_MHZ) < 0.001
            and timing['timing']['achieved'] >= timing['screen_mhz'], 'timing screen failed')
    roots = timing['clock_pins']
    require(roots['C'] > 100 and roots['RCLK'] == roots['WCLK'] == 4, 'incomplete clock fanout')
    image = (HERE/'fabricfox-two-oscillators.bin').read_bytes()
    require(len(image) == a['length'] and sha(image) == a['image_sha256'], 'packed image differs')
    return a


def altered(records, changes, diagnostic):
    try:
        check_oscillator([dict(row, **changes(i, row)) for i, row in enumerate(records)], UART_BINARY)
    except ValueError as error:
        require(diagnostic in str(error), 'unexpected rejection: ' + str(error))
    else:
        raise ValueError('corrupted evidence escaped: ' + diagnostic)


def challenge(records):
    def erase_clock(i, row):
        if row.get('case') == 'matched' and row['event'] == 'samples':
            return {'data': bytes(b & 0x77 for b in bytes.fromhex(row['data'])).hex()}
        return {}

    altered(records, erase_clock, 'receiver clock absent')
    idx = next(i for i, row in enumerate(records) if row.get('case') == 'matched' and row['event'] == 'oscillator_uart')
    tree = records[idx]['clock_tree_before'][:]
    tree[2] = 1
    for fields, diagnostic in (({'clock_tree_before': tree}, 'PIO does not use undivided PLL_SYS'),
                               ({'early_fall': 1}, 'steady run-enable'),
                               ({'selector1_oe': 1}, 'linked selector OE'),
                               ({'accepted': [0xaa, 0xaa]}, 'two-frame delivery failed')):
        altered(records, lambda i, row: fields if i == idx else {}, diagnostic)


def main():
    devices, sources, bounds = set(), set(), []
    budgets = []
    valid = rejected = samples = 0
    for slot, archive in ((1, 'board-1'), (4, 'board-4'), (1, 'board-1-repeat')):
        r, stderr = receipt(HERE/archive)
        revision = r['source_commit']
        build = verify_build(revision)
        original = json.loads((HERE.parent/'E0052-remote-uart'/f'board-{slot}'/'result.json').read_bytes())
        require(not stderr and r['status'] == 'PASS_REMOTE_UART_SEPARATE_OSCILLATORS', 'board run failed')
        require(r['board'] == f'fpga-{slot}' and r['board_identity_sha256'] == original['board_identity_sha256']
                and r['before']['present'] and r['before']['reachable'] and r['before']['clients'] == 0,
                'wrong or occupied board')
        require(r['image_sha256'] == build['image_sha256'] and r['uart_sha256'] == UART_BINARY
                and r['production_profile_sha256'] == verify(ROOT)['profile_sha256']
                and r['controller_sha256'] == sha(blob(revision, 'experiments/remote_uart/run.py'))
                and r['board_code_sha256'] == sha(board_payload(revision))
                and r['websocket_wheel_sha256'] == original['websocket_wheel_sha256'], 'provenance differs')
        require(r['upload']['size'] == build['length'] and not r['upload']['evicted']
                and r['upload']['name'] == r['enable']['enabled'], 'unexpected gallery response')
        result = check_oscillator(r['observations'], UART_BINARY)
        require(result == r['digital_capture_summary'], 'independent terminal replay differs')
        require(result['preset']['delivered'], 'archived untrimmed preset failed')
        valid += sum(v.get('delivered') is True for v in result.values())
        rejected += sum(v.get('terminal') == 0xe6 and v.get('observed_bytes') is None for v in result.values())
        samples += sum(v['samples'] for v in result.values())
        bounds.extend(v['service_upper_us'] for v in result.values() if 'service_upper_us' in v)
        budgets.extend(v['conservative_budget_us'] for v in result.values() if 'conservative_budget_us' in v)
        devices.add(r['board_identity_sha256'])
        sources.add(revision)
        if archive == 'board-1':
            challenge(r['observations'])
        print(archive, 'preset delivered', result['preset']['delivered'],
              'idle receiver MHz', result['calibration']['receiver_mhz_relative_to_rp'])
    require(len(devices) == 2 and len(sources) == 1, 'boards or producing source differ')
    require((valid, rejected, samples, max(bounds), min(budgets)) == (15, 6, 1020240, 216, 353.648),
            'reported campaign totals differ')
    for name, error in (('initial-wiring', b'physical selector failed'), ('initial-selector', b'staged loader status'),
                        ('initial-handoff', b'AssertionError')):
        r, stderr = receipt(HERE/name)
        require(r['status'] == 'FAILED' and error in stderr, 'missing earlier failure: ' + name)
    print('PASS', valid, 'valid batches,', rejected, 'framing faults,', samples,
          'samples, maximum host bound', max(bounds), 'us, five altered records rejected')


if __name__ == '__main__':
    main()
