# SPDX-License-Identifier: Apache-2.0
"""Build the FabricFox v2 FPGA image and rehearse the UART test at its package pins."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.assembler import json_bytes
from tools.cold_load import fresh_directory, prepare_models
from tools.production_sram import verify
from tools.run_program_examples import digest

MACRO = 'RM_IHPSG13_1P_256x32_c2_bm_bist'
TOP = 'tt_um_khangelani_protocol_emulator'
PCF = HERE / 'tt_fpga_fabricfoxv2.pcf'
TEMPLATE = HERE / 'tt_fpga_top.v.in'
UART_RECORD = ROOT / 'evidence/E0050-powered-cold-loader/uart-transcript.json.gz'
SEED = 10


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(out, name, argv, *, allow_failure=False, env=None, stdout=None):
    with (out / (name + '.log')).open('wb') as log:
        proc = subprocess.run(argv, cwd=out, env=env, stdout=stdout or log, stderr=log, timeout=600)
    if proc.returncode and not allow_failure:
        raise RuntimeError(f'{name} exited {proc.returncode}, see {out / (name + ".log")}')
    return proc.returncode


def verify_ram(out, cells, production):
    models = prepare_models(out, production)
    vendor = (models / (MACRO + '.v')).read_text()
    original = 'module ' + MACRO
    require(vendor.count(original) == 1, 'unexpected vendor wrapper')
    (out / 'vendor_reference.v').write_text(vendor.replace(original, 'module vendor_reference'))
    core = models / 'RM_IHPSG13_1P_core_behavioral_bm_bist.v'
    adapter = HERE / 'program_ram.v'
    args = ['iverilog', '-g2012', '-DFUNCTIONAL', '-DSYNTHESIS', '-DNO_ICE40_DEFAULT_ASSIGNMENTS']
    for fault in (False, True):
        source = adapter
        label = 'ram-bad' if fault else 'ram'
        if fault:
            text = adapter.read_text()
            old = 'write_data <= A_DIN[8*lane +: 8];'
            require(text.count(old) == 1, 'unexpected forwarding expression')
            source = out / 'bad_forwarding.v'
            source.write_text(text.replace(old, "write_data <= A_DIN[8*lane +: 8] ^ 8'h01;"))
        command(out, label + '-compile', [*args, '-s', 'compare_ram', '-o', label + '.vvp',
                cells, source, 'vendor_reference.v', core, HERE / 'compare_ram.sv'])
        code = command(out, label, ['vvp', label + '.vvp'], allow_failure=fault)
        log = (out / (label + '.log')).read_text()
        if fault:
            require(code != 0 and 'RAM_MISMATCH check=1 address=0' in log, 'broken forwarding escaped')
        else:
            require('PASS_RAM checks=16640' in log, 'incomplete memory comparison')
    command(out, 'store-compile', [*args, '-s', 'sram_program_store', '-o', 'store.vvp', cells,
            adapter, ROOT / 'src/m1_program_store.v', ROOT / 'test/sram_program_store.sv'])
    command(out, 'store', ['vvp', 'store.vvp'])
    match = re.search(r'PASS_SRAM_STORE_PORTS checks=(\d+) unknown_checks=(\d+)', (out / 'store.log').read_text())
    require(match and int(match[2]) == 2, 'store boundary test incomplete')
    return {'vendor_and_oracle_edges': 16640, 'bad_forwarding_rejected_at_edge': 1,
            'store_checks': int(match[1]), 'four_state_store_checks': int(match[2])}


def build(out, result, production):
    require(digest(PCF) == '98ee191f249b6fd9d09d95e9c51374c8ec1429210a4c2b0e0dae9ce51c24a747'
            and digest(TEMPLATE) == 'ca43fa063e4ec312e172f3e9f08441caebcafb8ed14ec50aa03d8a527c28fbcc',
            'pinned FabricFox wrapper or pin map differs')
    wrapper = TEMPLATE.read_text()
    require(wrapper.count('__tt_um_placeholder') == 1, 'unexpected FPGA wrapper')
    (out / 'tt_fpga_top.v').write_text(wrapper.replace('__tt_um_placeholder', TOP))
    ports = {'clk', 'rst_n'} | {f'{bus}[{n}]' for bus in ('ui_in', 'uo_out', 'uio') for n in range(8)}
    pins = [(name, pin) for name, pin in re.findall(r'^set_io -nowarn\s+(\S+)\s+(\d+)$', PCF.read_text(), re.M)
            if name in ports]
    require({name for name, _ in pins} == ports and len(pins) == len({p for _, p in pins}) == 26,
            'incomplete or repeated FPGA package pin')
    # IceStorm's reverse decoder accepts "set_io name pin". Route against the
    # unmodified upstream PCF, then give the decoder the same 26 name/pin pairs.
    decoder_pcf = out / 'decoder.pcf'
    decoder_pcf.write_text(''.join(f'set_io {name} {pin}\n' for name, pin in pins))
    result['package_pins'] = dict(pins)
    sources = [ROOT / 'src' / name for name in production['source_sha256']]
    script = ('read_verilog -sv "tt_fpga_top.v" ' + ' '.join(f'"{s}"' for s in [*sources, HERE/'program_ram.v'])
              + '\nsynth_ice40 -top tt_fpga_top -json design.json\n')
    (out / 'synth.ys').write_text(script)
    command(out, 'synth', ['yosys', '-s', 'synth.ys'])
    design = json.loads((out / 'design.json').read_bytes())['modules']['tt_fpga_top']
    counts = dict(Counter(cell['type'] for cell in design['cells'].values()))
    require(counts.get('SB_RAM40_4K') == 4 and counts.get('SB_IO') == 8, 'FPGA byte lanes or bidirectional pads missing')
    result['mapped_cells'] = counts
    result['routes'] = []
    for mhz in (50, 12.5):
        stage = out / f'route-{mhz:g}'
        stage.mkdir()
        argv = ['nextpnr-ice40', '--up5k', '--package', 'sg48', '--seed', str(SEED), '--freq', str(mhz),
                '--pcf', PCF, '--json', '../design.json', '--asc', 'routed.asc', '--report', 'timing.json']
        code = command(stage, 'nextpnr', argv, allow_failure=True)
        timing = json.loads((stage / 'timing.json').read_bytes())
        require(len(timing['fmax']) == 1, 'expected one constrained project clock')
        clock, = timing['fmax'].values()
        require(clock['constraint'] == mhz, 'project clock constraint missing')
        require(timing['utilization']['SB_IO']['used'] == len(ports)
                and timing['utilization']['ICESTORM_RAM']['used'] == 4, 'unexpected routed pin or memory count')
        result['routes'].append({'target_mhz': mhz, 'exit': code, 'clock': clock,
                                 'utilization': timing['utilization'], 'timing_sha256': digest(stage/'timing.json')})
        if code:
            log = (stage / 'nextpnr.log').read_text()
            errors = [line for line in log.splitlines() if line.startswith('ERROR:')]
            require(clock['achieved'] < mhz and errors and all('Max frequency for clock' in e for e in errors),
                    'route failed for a reason other than frequency, see ' + str(stage))
            continue
        require(clock['achieved'] >= mhz, 'failing timing at selected point')
        command(stage, 'pack', ['icepack', 'routed.asc', 'fabricfox.bin'])
        command(stage, 'unpack', ['iceunpack', 'fabricfox.bin', 'unpacked.asc'])
        command(stage, 'repack', ['icepack', 'unpacked.asc', 'repacked.bin'])
        require((stage/'fabricfox.bin').read_bytes() == (stage/'repacked.bin').read_bytes(), 'bitstream round trip differs')
        with (out / 'decoded.v').open('wb') as decoded:
            command(stage, 'decode', ['icebox_vlog', '-S', '-c', '-d', 'sg48', '-p', decoder_pcf,
                                      '-n', 'tt_fpga_top', 'unpacked.asc'], stdout=decoded,
                    env=dict(os.environ, PYTHONHASHSEED='0'))
        result.update(selected_mhz=mhz, bitstream_sha256=digest(stage/'fabricfox.bin'),
                      bitstream_bytes=(stage/'fabricfox.bin').stat().st_size, decoded_sha256=digest(out/'decoded.v'))
        return
    raise RuntimeError('neither clock closed timing')


def exercise(out, cells, result):
    command(out, 'pins-compile', ['iverilog', '-g2012', '-DNO_ICE40_DEFAULT_ASSIGNMENTS',
            '-s', 'tb', '-o', 'pins.vvp', cells, 'decoded.v', HERE / 'package_tb.v'])
    lib = subprocess.check_output(['cocotb-config', '--lib-dir'], text=True).strip()
    interpreter = subprocess.check_output(['cocotb-config', '--python-bin'], text=True).strip()
    clean = {k: v for k, v in os.environ.items() if k not in ('COCOTB_TEST_FILTER', 'TESTCASE', 'PYTHONOPTIMIZE')}
    env = dict(clean, COCOTB_TEST_MODULES='test_package', COCOTB_TOPLEVEL='tb', TOPLEVEL_LANG='verilog',
               COCOTB_RESULTS_FILE=str(out/'results.xml'), COCOTB_RANDOM_SEED='20261124',
               PYGPI_PYTHON_BIN=interpreter, PYTHONPATH=str(ROOT), FPGA_UART_ROOT=str(ROOT),
               FPGA_UART_OUT=str(out), FPGA_UART_MHZ=str(result['selected_mhz']))
    test = (HERE / 'test_package.py').read_text()
    (out / 'test_package.py').write_text(test)
    simulator = ['vvp', '-M', lib, '-m', 'libcocotbvpi_icarus', out / 'pins.vvp']
    # Remove the clock-low wait in a disposable driver. The separate Verilog
    # monitor must reject the overclock during loading, before any pin result.
    negative = out / 'short-clock'
    negative.mkdir()
    wait = "await Timer(2 * quarter_ps, unit='ps')  # loader low phase"
    require(test.count(wait) == 1, 'missing loader clock control point')
    (negative / 'test_package.py').write_text(test.replace(wait, "await Timer(1, unit='ps')"))
    command(negative, 'pins', simulator, allow_failure=True,
            env=dict(env, FPGA_UART_OUT=str(negative), COCOTB_RESULTS_FILE=str(negative/'results.xml')))
    mismatch = re.search(r'FPGA_CLOCK_TOO_FAST interval_ps=(\d+) minimum_ps=(\d+)',
                         (negative / 'pins.log').read_text())
    require(mismatch and int(mismatch[1]) < int(mismatch[2]) and not (negative/'observations.json').exists(),
            'short UART loader clock escaped')
    result['short_clock_control'] = {'rejected_period_ps': int(mismatch[1]), 'required_minimum_ps': int(mismatch[2])}
    command(out, 'pins', simulator, env=env)
    tests = ET.parse(out/'results.xml').findall('.//testcase')
    require(len(tests) == 1 and tests[0].get('name') == 'package_handoff' and not list(tests[0]), 'pin rehearsal failed')
    result['pins'] = json.loads((out/'observations.json').read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='new directory under build/')
    args = parser.parse_args()
    out = fresh_directory(args.out)
    result = {'status': 'INCOMPLETE', 'started_utc': datetime.now(timezone.utc).isoformat(), 'seed': SEED,
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    try:
        production = verify(ROOT)
        result['physical_input_count'] = len(production['files_sha256'])
        result['production_profile_sha256'] = production['profile_sha256']
        result['qualified_source_sha256'] = production['source_sha256']
        result['qualified_model_sha256'] = production['model_sha256']
        cells = Path(subprocess.check_output(['yosys-config', '--datdir'], text=True).strip())/'ice40/cells_sim.v'
        version_commands = {'yosys': ['yosys', '-V'], 'nextpnr': ['nextpnr-ice40', '--version'],
                            'iverilog': ['iverilog', '-V'], 'cocotb': ['cocotb-config', '--version']}
        result['tools'] = {name: subprocess.check_output(argv, text=True, stderr=subprocess.STDOUT).splitlines()[0]
                           for name, argv in version_commands.items()}
        files = [*HERE.glob('*.py'), *HERE.glob('*.v'), *HERE.glob('*.sv'), PCF, TEMPLATE, UART_RECORD,
                 UART_RECORD.parent/'uart-result.json', ROOT/'test/sram_program_store.sv',
                 ROOT/'programs/od128-sram-v1/uart_rx.asm',
                 *(ROOT/'tools'/f for f in ('assembler.py', 'cold_load.py', 'm1_contract_model.py',
                                            'production_sram.py', 'run_program_examples.py',
                                            'uart_rx_oracle.py', 'uart_rx_host_service.py'))]
        result['inputs_sha256'] = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(files)}
        result['cells_sim_sha256'] = digest(cells)
        result['ram'] = verify_ram(out, cells, production)
        build(out, result, production)
        exercise(out, cells, result)
        require(verify(ROOT) == production, 'production inputs changed')
        require(all(digest(ROOT/name) == expected for name, expected in result['inputs_sha256'].items()),
                'experiment input changed')
        result['status'] = 'PASS_FPGA_REHEARSAL'
    except Exception as error:
        result.update(status='FAILED', error=str(error))
        raise
    finally:
        result['ended_utc'] = datetime.now(timezone.utc).isoformat()
        (out/'result.json').write_bytes(json_bytes(result))
        print(result['status'], out, flush=True)


if __name__ == '__main__':
    main()
