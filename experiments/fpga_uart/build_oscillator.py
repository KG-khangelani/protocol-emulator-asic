# SPDX-License-Identifier: Apache-2.0
"""Build the D56 bench image and trace every mapped storage clock to the FPGA HFOSC."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.fpga_uart.run import PCF, SEED, command, require
from tools.assembler import json_bytes
from tools.cold_load import fresh_directory
from tools.production_sram import verify


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clock_roots(design, divider):
    cells = design['cells']
    oscillators = [c for c in cells.values() if c['type'] == 'SB_HFOSC']
    require(len(oscillators) == 1 and oscillators[0]['parameters']['CLKHF_DIV'].strip() == divider,
            'oscillator primitive or divider differs')
    ports = oscillators[0]['connections']
    root = ports['CLKHF']
    require(ports['CLKHFEN'] == ports['CLKHFPU'] == ['1'], 'receiver oscillator not always enabled')
    counts = Counter()
    for name, cell in cells.items():
        for port, direction in cell['port_directions'].items():
            if direction == 'input' and port in ('C', 'RCLK', 'WCLK'):
                require(cell['connections'][port] == root, 'storage clock outside HFOSC domain: ' + name)
                counts[port] += 1
    require(counts['C'] > 100 and counts['RCLK'] == counts['WCLK'] == 4, 'missing receiver logic or RAM')
    require(design['ports']['clk']['bits'] != root, 'controller request is the receiver clock')
    return dict(counts)


def build(directory):
    profile = verify(ROOT)
    sources = [HERE / 'independent_clock.v', HERE / 'program_ram.v']
    sources += [ROOT / 'src' / name for name in profile['source_sha256']]
    result = {'profile_sha256': profile['profile_sha256'],
              'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in [*sources, PCF]},
              'seed': SEED, 'routes': []}
    require(sha(PCF) == '98ee191f249b6fd9d09d95e9c51374c8ec1429210a4c2b0e0dae9ce51c24a747', 'pin map changed')
    for nominal, divider, screen in ((12, '0b10', 13.2), (6, '0b11', 6.6)):
        stage = directory / ('nominal-%d' % nominal)
        stage.mkdir()
        filenames = ' '.join(f'"{p}"' for p in sources)
        script = f'read_verilog -sv -DRX_OSC_DIV="{divider}" {filenames}\nsynth_ice40 -top tt_fpga_top -json design.json\n'
        (stage / 'build.ys').write_text(script)
        command(stage, 'synth', ['yosys', '-s', 'build.ys'])
        design = json.loads((stage / 'design.json').read_bytes())['modules']['tt_fpga_top']
        roots = clock_roots(design, divider)
        # nextpnr infers the nameplate oscillator frequency unless this net is constrained explicitly.
        (stage / 'constraint.py').write_text(f'ctx.addClock("receiver_clock", {screen})\n')
        rc = command(stage, 'route', ['nextpnr-ice40', '--up5k', '--package', 'sg48', '--seed', str(SEED),
                                     '--freq', str(screen), '--pre-pack', 'constraint.py', '--pcf', PCF, '--json', 'design.json',
                                     '--asc', 'routed.asc', '--report', 'timing.json'], allow_failure=True)
        timing = json.loads((stage / 'timing.json').read_bytes())
        require(len(timing['fmax']) == 1, 'expected exactly one timed domain')
        name, clock = next(iter(timing['fmax'].items()))
        require(abs(clock['constraint']-screen) < 0.001, 'router did not apply the declared oscillator screen')
        info = {'nominal_mhz': nominal, 'divider': divider, 'screen_mhz': screen, 'clock': name,
                'timing': clock, 'clock_pins': roots, 'route_exit': rc, 'utilization': timing['utilization']}
        result['routes'].append(info)
        if rc or clock['achieved'] < screen:
            errors = [s for s in (stage/'route.log').read_text().splitlines() if s.startswith('ERROR:')]
            require(clock['achieved'] < screen and all('Max frequency for clock' in s for s in errors),
                    'route failed outside the timing screen')
            continue
        require(timing['utilization']['SB_IO']['used'] == 26, 'package pin count differs')
        command(stage, 'pack', ['icepack', 'routed.asc', 'image.bin'])
        command(stage, 'unpack', ['iceunpack', 'image.bin', 'unpacked.asc'])
        command(stage, 'repack', ['icepack', 'unpacked.asc', 'repacked.bin'])
        require(sha(stage/'image.bin') == sha(stage/'repacked.bin'), 'bitstream round trip differs')
        result.update(status='PASS_OSCILLATOR_BUILD', nominal_mhz=nominal, image_sha256=sha(stage/'image.bin'),
                      length=(stage/'image.bin').stat().st_size)
        break
    require(verify(ROOT) == profile, 'qualified inputs changed during the build')
    (directory/'result.json').write_bytes(json_bytes(result))
    require('image_sha256' in result, 'neither oscillator divider met the timing screen')
    print(result['status'], result['nominal_mhz'], 'MHz', result['image_sha256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    build(fresh_directory(parser.parse_args().out))
