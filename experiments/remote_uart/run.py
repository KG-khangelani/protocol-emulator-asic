# SPDX-License-Identifier: Apache-2.0
"""Use the public FabricFox gallery and its MicroPython terminal to run the pin test."""

import argparse
import gzip
import hashlib
from http.cookiejar import CookieJar
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen
from uuid import uuid4
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.assembler import json_bytes
from tools.cold_load import fresh_directory, UART_BINARY
from tools.production_sram import verify
from experiments.remote_uart.check import check
from experiments.remote_uart.margin_check import check_margin
from experiments.remote_uart.oscillator_check import check_oscillator, NOMINAL_MHZ

SITE = 'https://tinytapeout.fpgas.online'
IMAGE = ROOT / 'evidence/E0051-fabricfox-uart/fabricfox-v2-12p5mhz.bin'
IMAGE_SHA = '89fa89607e0eac4468d11257b4b46296f9122115e0995c888274d31387fb4163'
NAME = 'tt_um_khangelani_uart_89fa8960'
OSC_IMAGE = ROOT / 'evidence/E0054-separate-oscillators/fabricfox-hfosc.bin'
OSC_SHA = '27945dd4aa26dc48e123a93dd6502fdde44a7c4c82e19557740edef0fa26461e'
OSC_NAME = 'tt_um_khangelani_osc_' + OSC_SHA[:8]
WHEEL = 'websockets-15.0.1-py3-none-any.whl'
WHEEL_URL = 'https://files.pythonhosted.org/packages/fa/a8/5b41e0da817d64113292ab1f8247140aac61cbf6cfd085d6a0fa77f4984f/' + WHEEL
WHEEL_SHA = 'f7a866fbc1e97b5c617ee4116daaa09b722101d4a3c170c787450ba409f9736f'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def clock():
    return datetime.now(timezone.utc).isoformat()


def board_code(suite='delivery'):
    archive = ROOT / 'evidence/E0050-powered-cold-loader/uart-transcript.json.gz'
    raw = gzip.decompress(archive.read_bytes())
    require(hashlib.sha256(raw).hexdigest() == 'c660d0d69282094b6999c4b5ce83303e77c0307be5571762ec64ebb7ffb0a188',
            'E0050 loader changed')
    rows = json.loads(raw)['loader']
    program = bytes(r['expected']['uio_out'] for r in rows if r['action'] == 'read_byte_after_edge')
    require(len(rows) == 76 and hashlib.sha256(program).hexdigest() == UART_BINARY, 'wrong released program')
    steps = [(r['ui_in'], r['rst_n'], r['raw'] if r['host_drives_uio'] else -1,
              r['expected'].get('uo_out', -1), r['expected'].get('uio_out', -1)) for r in rows]
    code = 'STEPS = ' + repr(steps) + '\n' + (HERE / 'on_board.py').read_text()
    if suite == 'oscillator':
        code += f'\nNOMINAL_MHZ = {NOMINAL_MHZ}\n' + (HERE / 'independent_peer.py').read_text()
        code += '\nrun_suite(oscillator_trials, (xtal_peer, clock_and_data, idle_clock_and_data, watch_enable), 3)\n'
    elif suite == 'margin':
        code += '\n' + (HERE / 'baud_margin.py').read_text()
        code += '\nrun_suite(margin_trials, (project_clock, serial_peer, pad_sampler, count_clock), 3)\n'
    else:
        code += '\nrun_suite(delivery_trials, (wire_pair, count_clock), 2)\n'
    return code.encode()


def receive_until(ws, suffix, timeout):
    data = bytearray()
    end = time.monotonic() + timeout
    while not data.endswith(suffix):
        remaining = end - time.monotonic()
        require(remaining > 0, 'board terminal timed out')
        msg = ws.recv(timeout=remaining)
        if isinstance(msg, bytes):
            data.extend(msg)
    return bytes(data)


def run_terminal(connect, slug, code, out):
    address = SITE.replace('https:', 'wss:') + '/ws/board/' + slug + '/serial'
    with connect(address, origin=SITE, open_timeout=15, close_timeout=3) as ws:
        ws.send(b'\r')
        receive_until(ws, b'>>> ', 10)
        ws.send(b'\x01')
        receive_until(ws, b'CTRL-B to exit\r\n>', 8)
        try:
            for start in range(0, len(code), 128):
                ws.send(code[start:start+128])
                time.sleep(0.035)
            ws.send(b'\x04')
            data = receive_until(ws, b'\x04>', 90)
        finally:
            ws.send(b'\x02')  # Return the public terminal to its normal prompt.
        (out / 'terminal.bin').write_bytes(data)
        require(data.startswith(b'OK'), 'board did not accept the test source')
        stdout, stderr = data[2:-2].split(b'\x04', 1)
        (out / 'terminal.log').write_bytes(stdout.replace(b'\r\n', b'\n') + stderr.replace(b'\r\n', b'\n'))
        records = [json.loads(line[8:]) for line in stdout.splitlines() if line.startswith(b'UARTLAB ')]
        return records, stderr


def run(args, out, receipt):
    wheel = args.wheel or out / WHEEL
    if args.wheel is None:
        with urlopen(WHEEL_URL, timeout=25) as r:
            wheel.write_bytes(r.read())
    require(hashlib.sha256(wheel.read_bytes()).hexdigest() == WHEEL_SHA, 'terminal dependency hash differs')
    sys.path.insert(0, str(wheel.resolve()))
    from websockets.sync.client import connect
    fixture = args.suite == 'oscillator'
    path, expected, name = (OSC_IMAGE, OSC_SHA, OSC_NAME) if fixture else (IMAGE, IMAGE_SHA, NAME)
    image = path.read_bytes()
    require(hashlib.sha256(image).hexdigest() == expected, 'FPGA image changed')
    code = board_code(args.suite)
    receipt.update(board=args.board, image_sha256=expected, uart_sha256=UART_BINARY,
                   board_code_sha256=hashlib.sha256(code).hexdigest(), websocket_wheel_sha256=WHEEL_SHA)
    page = SITE + '/board/' + args.board + '/'
    api = SITE + '/api/board/' + args.board
    jar = CookieJar()
    http = build_opener(HTTPCookieProcessor(jar))
    headers = {'User-Agent': 'Protocol-Emulator-ASIC FabricFox UART bench'}
    with http.open(Request(page, headers=headers), timeout=20) as r:
        require(b'Upload your own bitstream' in r.read(), 'public upload form is unavailable')
    token = next(c.value for c in jar if c.name == 'csrftoken')

    def request(url, body=None, content_type=None):
        h = dict(headers)
        if body is not None:
            h.update({'Origin': SITE, 'Referer': page, 'X-CSRFToken': token, 'Content-Type': content_type})
        with http.open(Request(url, data=body, headers=h), timeout=180) as r:
            return json.loads(r.read())

    status = request(page + 'status.json')
    gallery = request(api + '/designs')
    enabled = gallery['enabled']
    uploads = [d['name'] for d in gallery['designs'] if d['source'] == 'upload']
    receipt['before'] = {'reachable': status['reachable'], 'present': status['board']['present'],
                         'kind': status['kind'], 'clients': status['clients'], 'enabled': enabled,
                         'upload_count': len(uploads), 'daemon_version': status['version']}
    identity = status['board'].get('usb_serial')
    require(identity, 'board has no public device identity')
    receipt['board_identity_sha256'] = hashlib.sha256(identity.encode()).hexdigest()
    require(status['reachable'] and status['board']['present'] and status['kind'] == 'fpga'
            and status['clients'] == 0, 'board offline or in use')
    require(enabled in ('idle_display', NAME, name), 'another design is using the board')
    require(len(uploads) < 16 or name in uploads, 'upload would evict another visitor')
    boundary = 'uartlab' + uuid4().hex
    prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="name"\r\n\r\n{name}\r\n'
              f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}.bin"\r\n'
              'Content-Type: application/octet-stream\r\n\r\n').encode()
    try:
        response = request(api + '/bitstream', prefix + image + f'\r\n--{boundary}--\r\n'.encode(),
                           'multipart/form-data; boundary=' + boundary)
        receipt['upload'] = response
        require(response.get('name') == name and response.get('size') == len(image) and not response.get('evicted'),
                'unexpected public upload receipt')
        receipt['enable'] = request(api + '/designs/' + name + '/enable', b'{}', 'application/json')
        require(request(api + '/designs')['enabled'] == name, 'gallery did not select our design')
        records, errors = run_terminal(connect, args.board, code, out)
        receipt['observations'] = records
    finally:
        if fixture:
            current = request(api + '/designs')['enabled']
            if current == name and current != enabled:
                require(request(page + 'status.json')['clients'] == 0, 'board occupied before gallery restoration')
                request(api + '/designs/' + enabled + '/enable', b'{}', 'application/json')
            receipt['restored_design'] = request(api + '/designs')['enabled']
            require(receipt['restored_design'] == enabled, 'gallery selection changed during restoration')
    require(not errors, 'board test raised an exception, see terminal.log')
    require(records and records[-1].get('status') == 'PASS' and records[-1]['host_uio_oe'] == 0,
            'missing completion or controller still drives the bus')
    if fixture:
        receipt['digital_capture_summary'] = check_oscillator(records, UART_BINARY)
        receipt['status'] = 'PASS_REMOTE_UART_SEPARATE_OSCILLATORS'
    elif args.suite == 'margin':
        receipt['digital_capture_summary'] = check_margin(records, UART_BINARY)
        receipt['status'] = 'PASS_REMOTE_UART_BAUD_OFFSETS'
    else:
        check(records, UART_BINARY)
        receipt['status'] = 'PASS_REMOTE_UART_DIGITAL'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--board', required=True, help='public FabricFox slug, e.g. fpga-1')
    parser.add_argument('--suite', choices=('delivery', 'margin', 'oscillator'), default='delivery')
    parser.add_argument('--out', type=Path, required=True, help='fresh directory under build/')
    parser.add_argument('--wheel', type=Path, help='optional pre-fetched pinned terminal dependency')
    args = parser.parse_args()
    require(re.fullmatch(r'fpga-[1-9][0-9]*', args.board), 'expected a public FPGA board slug')
    out = fresh_directory(args.out)
    profile = verify(ROOT)
    receipt = {'status': 'INCOMPLETE', 'started_utc': clock(), 'production_profile_sha256': profile['profile_sha256'],
               'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        run(args, out, receipt)
        require(verify(ROOT) == profile, 'production inputs changed')
    except Exception as error:
        receipt.update(status='FAILED', error=str(error))
        raise
    finally:
        receipt['ended_utc'] = clock()
        (out/'result.json').write_bytes(json_bytes(receipt))
        print(receipt['status'], out, flush=True)


if __name__ == '__main__':
    main()
