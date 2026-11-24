# SPDX-License-Identifier: Apache-2.0
"""Load a program into a continuously selected digital ASIC and start it."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.assembler import artifacts, assemble, json_bytes
from tools.host_transport.controller import read_image
from tools.production_sram import verify
from tools.run_program_examples import digest, run

FIXTURE = ROOT / 'tools/host_transport'
UART_BINARY = '47f0f1b86828840ec671579b6042334995267eb6e6167d88e737c499f82c0c39'
UART_SOURCE = '15c3b49fa57f7dc7c771df0f2d087fcb450c2a828136d9a281f572f1a2de353c'


def fresh_directory(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT / 'build'):
        raise ValueError('choose a new output directory under build/')
    path.mkdir(parents=True, exist_ok=False)
    return path


def prepare_models(output, production):
    directory = output / 'models'
    directory.mkdir()
    for name, expected in production['model_sha256'].items():
        archive = ROOT / 'evidence/E0042-sram-prefetch-screen/feasibility/verilog' / (name + '.gz')
        raw = gzip.decompress(archive.read_bytes())
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f'SRAM model digest differs for {name}')
        (directory / name).write_bytes(raw)
    return directory


def simulate(output, simulator, module, test_names, models, settings, *, netlist=None, pdk=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('COCOTB_', 'G1_', 'G2_')) and k not in
           ('GATES', 'MAKEFLAGS', 'MAKEOVERRIDES', 'COMPILE_ARGS', 'EXTRA_ARGS', 'M0_LEARNING', 'LEARNING_VCD',
            'PYTHONOPTIMIZE')}
    env.update(GENERAL_IO='yes', G2_CURRENT='yes', G2_SRAM='yes', SRAM_MODEL_DIR=str(models),
               PYTHONPATH=os.pathsep.join(map(str, (ROOT / 'test', ROOT))),
               COCOTB_RANDOM_SEED='20261124', PYTHONHASHSEED='0', **settings)
    command = ['make', '-C', str(FIXTURE), '-f', str(ROOT / 'test/Makefile'), 'SIM=' + simulator,
               'SRC_DIR=' + str(ROOT / 'src'), 'SIM_BUILD=' + str(output / 'sim'),
               'COCOTB_TEST_MODULES=' + module, 'COCOTB_RESULTS_FILE=' + str(output / 'results.xml'),
               'FST=', 'COCOTB_PLUSARGS=+NO_DUMP']
    if netlist:
        command.extend(('GATES=yes', 'GATE_LEVEL_NETLIST=' + str(netlist), 'PDK_ROOT=' + str(pdk)))
    run(command, output, 'simulator', 1800, env)
    cases = ET.parse(output / 'results.xml').findall('.//testcase')
    if (len(cases) != len(test_names) or {c.get('name') for c in cases} != set(test_names)
            or any(list(c) for c in cases)):
        raise RuntimeError('a required simulator case failed, was skipped or did not execute')
    return command


def stage_image(directory, source_dir):
    directory.mkdir()
    if source_dir is None:
        source = (ROOT / 'programs/od128-sram-v1/uart_rx.asm').read_text(encoding='utf-8')
        image = assemble(source)
        if (image['source_sha256'], image['binary_sha256']) != (UART_SOURCE, UART_BINARY):
            raise ValueError('default UART receiver differs from the released image')
        for name, contents in artifacts(image).items():
            (directory / name).write_bytes(contents)
    else:
        for name in ('program.json', 'program.bin', 'load-plan.json'):
            shutil.copyfile(source_dir / name, directory / name)
    return read_image(directory)


def execute(output, backend, image_dir=None):
    output = fresh_directory(output)
    result = {'status': 'INCOMPLETE', 'backend': backend, 'scope': 'digital public-pin RTL simulation'}
    try:
        image, _ = stage_image(output / 'image', image_dir)
        result.update(source_sha256=image['source_sha256'], binary_sha256=image['binary_sha256'],
                      inputs_sha256={p.name: digest(p) for p in (output / 'image').iterdir()})
        production = verify(ROOT)
        result['production_profile_sha256'] = production['profile_sha256']
        models = prepare_models(output, production)
        simulate(output, backend, 'run_image', ['load_and_start'], models,
                 {'COLD_LOAD_OUT': str(output)})
        receipt = json.loads((output / 'transcript.json').read_bytes())
        if receipt['status'] != 'PASS' or not receipt['launched'] or receipt['verified_bytes'] != len(image['words']) * 4:
            raise RuntimeError('incomplete loader receipt')
        result.update(status='PASS', verified_bytes=receipt['verified_bytes'],
                      runtime=receipt['runtime'], transcript_sha256=digest(output / 'transcript.json'))
    except Exception as error:
        result.update(status='FAILED', error=str(error))
        raise
    finally:
        (output / 'result.json').write_bytes(json_bytes(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, help='assembler artifact directory (default: released UART receiver)')
    parser.add_argument('--backend', choices=('icarus', 'verilator'), default='icarus')
    parser.add_argument('--out', type=Path, help='new output directory under build/')
    args = parser.parse_args()
    output = args.out or ROOT / 'build/cold-load' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    result = execute(output, args.backend, args.image)
    runtime = result['runtime']
    if 'uart_received' in runtime:
        received = ' '.join(f'0x{byte:02X}' for byte in runtime['uart_received'])
        observation = f"UART received {received} (status 0x{runtime['terminal']})"
    else:
        observation = f"first runtime edge {runtime['first_edge']}"
    print(f"PASS {args.backend}, verified {result['verified_bytes']} bytes, {observation}. {output}")


if __name__ == '__main__':
    main()
