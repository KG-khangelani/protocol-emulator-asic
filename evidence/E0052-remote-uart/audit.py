# SPDX-License-Identifier: Apache-2.0
"""Validate retained raw board terminals, producing GPIO code and the matching offline FPGA image."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_uart.check import check_evidence, require

SOURCE = '3959d6a06b68b5ff2c214bdd4016357e74d52edd'


def load(name):
    return json.loads((HERE / name).read_bytes())


def blob(name):
    return subprocess.check_output(['git', 'show', SOURCE + ':' + name], cwd=ROOT)


def check_terminal(directory):
    raw = gzip.decompress((directory / 'terminal.bin.gz').read_bytes())
    require(raw.startswith(b'OK') and raw.endswith(b'\x04>'), 'invalid raw MicroPython response')
    stdout, stderr = raw[2:-2].split(b'\x04', 1)
    require((stdout + stderr).replace(b'\r\n', b'\n') == (directory / 'terminal.log').read_bytes(),
            'raw board bytes disagree with the readable transcript')
    return stderr


def main():
    loader = json.loads(gzip.decompress(blob('evidence/E0050-powered-cold-loader/uart-transcript.json.gz')))['loader']
    steps = [(r['ui_in'], r['rst_n'], r['raw'] if r['host_drives_uio'] else -1,
              r['expected'].get('uo_out', -1), r['expected'].get('uio_out', -1)) for r in loader]
    payload = ('STEPS = ' + repr(steps) + '\n').encode() + blob('experiments/remote_uart/on_board.py')
    host_hash = hashlib.sha256(blob('experiments/remote_uart/run.py')).hexdigest()
    offline = load('offline-result.json')
    old = json.loads((HERE.parent/'E0051-fabricfox-uart/result.json').read_bytes())
    for key in ('status', 'bitstream_sha256', 'decoded_sha256', 'pins', 'routes', 'inputs_sha256'):
        require(offline[key] == old[key], 'offline FPGA replay differs in ' + key)

    devices, bounds, releases = set(), [], []
    for name in ('board-1', 'board-4'):
        directory = HERE / name
        require(not check_terminal(directory), name + ' terminal contains an exception')
        r = check_evidence(directory)
        require(r['source_commit'] == SOURCE and r['board_code_sha256'] == hashlib.sha256(payload).hexdigest()
                and r['controller_sha256'] == host_hash, 'producing GPIO or host source differs')
        require(r['image_sha256'] == offline['bitstream_sha256'], 'board and offline configuration differ')
        devices.add(r['board_identity_sha256'])
        for observation in r['observations']:
            if observation.get('event') == 'uart' and observation['configured_hz'] == 12500000:
                bounds.append(observation['service_upper_us'])
            if observation.get('event') == 'cold':
                bias = observation['uio1_pull_down_up']
                require(bias['driven_high'] == [1, 1] and bias['driven_low'] == [0, 0], 'driven control differs')
                releases.append(bias['released'])
    require(len(devices) == 2 and len(bounds) == 10, 'missing board or target-rate trial')
    require(len(releases) == 12 and all(row == [1, 1] for row in releases), 'release observations differ')
    require(load('first-host/result.json')['status'] == 'FAILED' and b'AssertionError' in check_terminal(HERE/'first-host'),
            'original failed service test missing')
    print('PASS_REMOTE_EVIDENCE boards=2 target_trials=10 max_service_us=%d release=unresolved' % max(bounds))


if __name__ == '__main__':
    main()
