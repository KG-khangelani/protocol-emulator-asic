# SPDX-License-Identifier: Apache-2.0
"""Run the SPI program through the public, reversible FabricFox gallery and terminal."""
import argparse
import gzip
import hashlib
from http.cookiejar import CookieJar
import inspect
import json
from pathlib import Path
import sys
import time
from urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_uart.run import SITE, WHEEL, WHEEL_URL, WHEEL_SHA, clock, receive_until
from experiments.spi_target.requester import scenario
from tools.assembler import assemble, load_plan
from tools.cold_load import fresh_directory
from tools.production_sram import verify

FIRMWARE = ROOT/'experiments/spi_target/watchdog/target.asm'
PROGRAM_SHA = 'e5d25fc51d17684ede5615ece99501084c69380091c61c9ea58aba65b23c9e58'
IMAGE_SHA = 'd4b9201641f0781757510db4defe28bd43300c9329a708944865a8a3d6fdae5b'
NAME = 'tt_um_khangelani_spi_' + IMAGE_SHA[:8]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def board_code(suite):
    image = assemble(FIRMWARE.read_text(encoding='utf-8'))
    if image['binary_sha256'] != PROGRAM_SHA:
        raise ValueError('wrong SPI program')
    rows = bytearray()
    for step in load_plan(image)['steps']:
        e = step['expected']
        flags = int(step['host_drives_uio']) | (('uo_out' in e) << 1) | (('uio_out' in e) << 2) | ((step['action']=='flush_idle') << 3)
        rows.extend((step['rst_n'], step['ui_in'], step['uio_in'], flags, e.get('uo_out',0), e.get('uio_out',0)))
    extension = ''
    if suite in ('gaps','settled'):
        extension = (HERE/'gaps.py').read_text() + '\ntrials=gap_trials\nschedule=gap_schedule\n'
    return ('import binascii\nPLAN=binascii.unhexlify("' + rows.hex() + '")\nSUITE=' + repr(suite) + '\n' +
            inspect.getsource(scenario) + '\n' + (HERE/'schedules.py').read_text() + '\n' +
            (HERE/'on_board.py').read_text() + '\n' + extension + 'run_experiment()\n').encode()


def terminal(connect, board, code, out):
    with connect(SITE.replace('https:', 'wss:')+'/ws/board/'+board+'/serial', origin=SITE, open_timeout=15) as ws:
        ws.send(b'\r')
        receive_until(ws, b'>>> ', 12)
        ws.send(b'\x01')
        receive_until(ws, b'CTRL-B to exit\r\n>', 8)
        data = bytearray()
        try:
            for i in range(0, len(code), 128):
                ws.send(code[i:i+128])
                time.sleep(.035)
            ws.send(b'\x04')
            deadline = time.monotonic()+360
            while not data.endswith(b'\x04>'):
                msg = ws.recv(timeout=max(1, min(100, deadline-time.monotonic())))
                if isinstance(msg, bytes):
                    data.extend(msg)
                if time.monotonic() > deadline:
                    raise TimeoutError('SPI campaign timed out')
        finally:
            (out/'terminal.bin.gz').write_bytes(gzip.compress(bytes(data), mtime=0))
            ws.send(b'\x02')
    if not data.startswith(b'OK'):
        raise ValueError('MicroPython did not accept the experiment')
    stdout, stderr = data[2:-2].split(b'\x04', 1)
    if stderr:
        raise ValueError(stderr[-1800:].decode(errors='replace'))
    records = [json.loads(line[7:]) for line in stdout.splitlines() if line.startswith(b'SPILAB ')]
    if not records or records[-1].get('event') != 'finish' or records[-1]['host_uio_oe'] != 0:
        raise ValueError('missing board cleanup')
    return len([r for r in records if r['event']=='trace'])


def run(args, out, rec):
    image = args.image.read_bytes()
    if sha(image) != IMAGE_SHA:
        raise ValueError('unexpected FPGA image')
    wheel = args.wheel or out/WHEEL
    if not args.wheel:
        with urlopen(WHEEL_URL, timeout=25) as response:
            wheel.write_bytes(response.read())
    if sha(wheel.read_bytes()) != WHEEL_SHA:
        raise ValueError('terminal library digest')
    sys.path.insert(0,str(wheel.resolve()))
    from websockets.sync.client import connect
    code = board_code(args.suite)
    rec.update(image_sha256=IMAGE_SHA, program_sha256=PROGRAM_SHA, board_code_sha256=sha(code))
    page = SITE+'/board/'+args.board+'/'
    api = SITE+'/api/board/'+args.board
    jar = CookieJar()
    http = build_opener(HTTPCookieProcessor(jar))
    with http.open(page,timeout=20) as response:
        if b'Upload your own bitstream' not in response.read():
            raise ValueError('public gallery unavailable')
    token = next(c.value for c in jar if c.name=='csrftoken')

    def request(url, body=None, content_type='application/json'):
        headers = {'User-Agent':'Protocol Emulator ASIC SPI experiment'}
        if body is not None:
            headers.update({'Origin':SITE,'Referer':page,'X-CSRFToken':token,'Content-Type':content_type})
        with http.open(Request(url,data=body,headers=headers),timeout=90) as response:
            return json.load(response)

    status = request(page+'status.json')
    gallery = request(api+'/designs')
    old = gallery['enabled']
    uploads = [r['name'] for r in gallery['designs'] if r['source']=='upload']
    rec.update(previous=old, clients_before=status['clients'], board_identity_sha256=sha(status['board']['usb_serial'].encode()))
    if not (status['reachable'] and status['board']['present'] and status['kind']=='fpga' and status['clients']==0):
        raise ValueError('board unavailable or in use')
    if old not in (None, 'idle_display', 'tt_um_factory_test', NAME):
        raise ValueError('another design is active')
    if len(uploads)>=16 and NAME not in uploads:
        raise ValueError('upload would evict another visitor')
    boundary = 'spibench'+uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="name"\r\n\r\n{NAME}\r\n--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file"; filename="{NAME}.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
    rec['upload'] = request(api+'/bitstream',body+image+f'\r\n--{boundary}--\r\n'.encode(),'multipart/form-data; boundary='+boundary)
    if rec['upload'].get('evicted') or rec['upload'].get('size')!=len(image) or rec['upload'].get('name')!=NAME:
        raise ValueError('gallery upload receipt')
    # idle_display is loaded privately by the site's idle controller and may
    # have no public gallery entry. The stock SDK start design re-arms it.
    listed = {d['name'] for d in gallery['designs']}
    intended = old if old in listed and old != NAME else 'tt_um_factory_test'
    if intended not in listed:
        raise ValueError('previous design and SDK startup demo unavailable for restoration')
    rec['restore_via'] = intended
    try:
        if request(page+'status.json')['clients'] != 0:
            raise ValueError('board occupied before programming')
        rec['enable'] = request(api+'/designs/'+NAME+'/enable',b'{}')
        if request(api+'/designs')['enabled'] != NAME:
            raise ValueError('bitstream selection')
        rec['observations'] = terminal(connect,args.board,code,out)
    finally:
        current = request(api+'/designs')['enabled']
        if current in (NAME,None) and current != intended and request(page+'status.json')['clients']==0:
            request(api+'/designs/'+intended+'/enable',b'{}')
        rec['after'] = request(api+'/designs')['enabled']
    if rec['after'] != intended and not (intended == 'tt_um_factory_test' and rec['after'] == 'idle_display'):
        raise ValueError('board selection after session: '+str(rec['after']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--board',choices=('fpga-1','fpga-4'),required=True)
    p.add_argument('--suite',choices=('pilot','matrix','gaps','settled'),required=True)
    p.add_argument('--image',type=Path,required=True)
    p.add_argument('--wheel',type=Path)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    out=fresh_directory(args.out)
    rec=dict(board=args.board,suite=args.suite,started_utc=clock(),profile_sha256=verify(ROOT)['profile_sha256'])
    try:
        run(args,out,rec)
        rec['status']='CAPTURED'
    except Exception as e:
        rec.update(status='INCOMPLETE',error=str(e))
        raise
    finally:
        rec['ended_utc']=clock()
        (out/'result.json').write_text(json.dumps(rec,indent=2)+'\n')
        print(rec['status'],out,flush=True)
