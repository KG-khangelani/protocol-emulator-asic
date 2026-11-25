# SPDX-License-Identifier: Apache-2.0
"""Route the isolated FabricFox SPI fixture with the public production RTL."""
import argparse
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


def build(out):
    profile = verify(ROOT)
    sources = [HERE/'fabricfox.v', ROOT/'experiments/fpga_uart/program_ram.v']
    sources += [ROOT/'src'/n for n in profile['source_sha256']]
    (out/'build.ys').write_text('read_verilog -sv ' + ' '.join(map(str, sources)) +
                               '\nsynth_ice40 -top tt_fpga_top -json design.json\n')
    command(out, 'synth', ['yosys', '-s', 'build.ys'])
    design = json.loads((out/'design.json').read_bytes())['modules']['tt_fpga_top']
    pads = design['ports']['uio']['bits']
    ios = {c['connections']['PACKAGE_PIN'][0]: c for c in design['cells'].values() if c['type'] == 'SB_IO'}
    require(set(ios) == set(pads), 'missing board pad')
    for i, p in enumerate(pads):
        mode = '000001' if i in (0, 1, 2, 7) else '101001'
        require(ios[p]['parameters']['PIN_TYPE'] == mode, f'wrong direction capability on UIO{i}')
    require(ios[pads[3]]['connections']['OUTPUT_ENABLE'] == ios[pads[4]]['connections']['D_OUT_0'],
            'monitor differs from physical MISO enable')
    require(ios[pads[6]]['connections']['D_OUT_0'] == design['ports']['clk']['bits'], 'wrong clock witness')
    require(sum(c['type'] == 'SB_RAM40_4K' for c in design['cells'].values()) == 4, 'four memory byte lanes')
    result = dict(source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in [*sources, PCF]},
                  production_profile_sha256=profile['profile_sha256'], seed=SEED, routes=[])
    for mhz in (50, 12.5):
        d = out / f'route-{mhz:g}'
        d.mkdir()
        rc = command(d, 'route', ['nextpnr-ice40', '--up5k', '--package', 'sg48', '--seed', str(SEED),
                     '--freq', str(mhz), '--pcf', PCF, '--json', out/'design.json',
                     '--asc', 'design.asc', '--report', 'timing.json'], allow_failure=True)
        timing = json.loads((d/'timing.json').read_bytes())
        clock, = timing['fmax'].values()
        require(clock['constraint'] == mhz, 'clock constraint')
        result['routes'].append(dict(mhz=mhz, exit=rc, clock=clock, utilization=timing['utilization']))
        if rc:
            errors = [s for s in (d/'route.log').read_text().splitlines() if s.startswith('ERROR:')]
            require(errors and all('Max frequency for clock' in e for e in errors) and clock['achieved'] < mhz,
                    'route failed outside internal timing')
        else:
            require(clock['achieved'] >= mhz, 'internal timing')
            command(d, 'pack', ['icepack', 'design.asc', out/'image.bin'])
            result.update(target_mhz=mhz, image_sha256=sha(out/'image.bin'), bytes=(out/'image.bin').stat().st_size)
            break
    require('image_sha256' in result and verify(ROOT) == profile, 'no strictly routed image')
    (out/'result.json').write_bytes(json_bytes(result))
    print(result['target_mhz'], result['image_sha256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    build(fresh_directory(parser.parse_args().out))
