# SPDX-License-Identifier: Apache-2.0
"""Bounded pinned mapping after the complete SRAM functional gate."""
import argparse
import json
from pathlib import Path
import re
import sys
import tarfile

from sram_prefetch import ROOT, digest, parent_sources
from run_current_regression import check_junit, check_controls, physical

sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from run_program_sensitivity import execute

PDK = Path('/pdk/ciel/ihp-sg13/versions/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008/ihp-sg13cmos5l')
MACRO = 'RM_IHPSG13_1P_256x32_c2_bm_bist'
read = lambda path: json.loads(path.read_bytes())


def write(path, value):
    path.write_bytes((json.dumps(value, indent=2) + '\n').encode())


def blackbox(model):
    marker = b'// ---- Simulation-only check:'
    assert model.count(marker) == 1
    declaration = model.split(marker)[0]
    assert declaration.count(b'module ') == 1
    return declaration.replace(b'module ', b'(* blackbox *) module ') + b'\nendmodule\n`endcelldefine\n'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--regression', type=Path, required=True)
    p.add_argument('--proof-controls', type=Path, required=True)
    p.add_argument('--template', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    candidate, regression, proof, out = (p.resolve() for p in
        (args.candidate, args.regression, args.proof_controls, args.output))
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    manifest = read(candidate / 'manifest.json')
    assert manifest == read(ROOT / 'evidence/E0042-sram-prefetch-screen/candidate.json')
    evidence = read(regression / 'result.json')
    assert evidence['status'] == 'PASS_SRAM_CURRENT_BOTH_SIMULATORS'
    assert evidence['candidate'] == manifest
    assert {s['simulator'] for s in evidence['stages']} == {'icarus', 'verilator'}
    for simulator in ('icarus', 'verilator'):
        path = regression / simulator
        checked = check_junit(path / 'results.xml')
        checked['records'] = physical.check_public_records(path / 'records')
        checked['current_bank_control'] = check_controls(path / 'records/spi/controls.jsonl')
        assert checked == read(path / 'check.json')
    gate = read(proof / 'result.json')
    assert gate['status'] == 'PASS_SRAM_GATE' and gate['gate'] == 'proof-controls'
    assert gate['candidate'] == manifest
    assert {name: digest((candidate / 'src' / name).read_bytes()) for name in manifest['source_sha256']} == manifest['source_sha256']
    assert {name: digest((candidate / 'models' / name).read_bytes()) for name in manifest['model_sha256']} == manifest['model_sha256']
    (out / 'inputs').mkdir(parents=True)
    for name, source in [('regression-result.json', regression / 'result.json'),
                         ('proof-result.json', proof / 'result.json'),
                         ('run_sram_mapping.py', Path(__file__)),
                         ('g2-sram-mapped-screen.md', ROOT / 'docs/specs/g2-sram-mapped-screen.md')]:
        (out / 'inputs' / name).write_bytes(source.read_bytes())
    result = {'status': 'RUNNING', 'scope': 'MATCHED_SYNTHESIS_ONLY_WITH_REAL_MACRO',
              'candidate': manifest, 'runner_sha256': digest(Path(__file__).read_bytes()),
              'spec_sha256': digest((out / 'inputs/g2-sram-mapped-screen.md').read_bytes()),
              'physical': 'NOT_EVALUATED', 'runs': {}}
    write(out / 'result.json', result)
    try:
        old = ROOT / 'evidence/E0040-banked-read-screen/mapped'
        index = read(old / 'archive.json')
        assert digest((old / 'mapping.tar.gz').read_bytes()) == index['sha256']
        with tarfile.open(old / 'mapping.tar.gz') as archive:
            name = 'gold/src/config_merged.json'
            raw = archive.extractfile(name).read()
            assert digest(raw) == index['files'][name]
        (out / 'inputs/reference-config.json').write_bytes(raw)
        original_config = json.loads(raw)
        template = args.template.resolve()
        assert digest(template.read_bytes()) == '64b52f2150f699edc7fb500c2f486a51eca66fd91d3efb7347200bd2cf83a2ee'
        base = PDK / 'libs.ref/sg13cmos5l_sram'
        installed = {}
        views = {}
        for folder, ext, key in [('gds', 'gds', 'gds'), ('lef', 'lef', 'lef'), ('cdl', 'cdl', 'spice')]:
            path = base / folder / (MACRO + '.' + ext)
            installed[str(path)] = {'sha256': digest(path.read_bytes()), 'bytes': path.stat().st_size}
            views[key] = [str(path)]
        view_map = {'nom_typ_1p20V_25C': 'typ_1p20V_25C',
                    'nom_fast_1p32V_m40C': 'fast_1p32V_m55C',
                    'nom_slow_1p08V_125C': 'slow_1p08V_125C'}
        views['lib'] = {}
        libraries = {}
        for corner, suffix in view_map.items():
            path = base / 'lib' / (MACRO + '_' + suffix + '.lib')
            raw = path.read_bytes()
            installed[str(path)] = {'sha256': digest(raw), 'bytes': len(raw)}
            libraries[corner] = {'path': str(path), 'nominal_temperature': re.findall(r'\bnom_temperature\s*:\s*([^;]+)', raw.decode()),
                                 'nominal_voltage': re.findall(r'\bnom_voltage\s*:\s*([^;]+)', raw.decode())}
            views['lib'][corner] = [str(path)]
        feasibility = read(ROOT / 'evidence/E0042-sram-prefetch-screen/feasibility/inspection.json')
        for relative, item in feasibility['macro_inputs'].items():
            if str(base / relative) in installed:
                assert installed[str(base / relative)] == item
        result.update(macro_views=installed, macro_corner_sets=libraries,
                      fast_boundary='Standard-cell -40 C with vendor SRAM -55 C; not an isothermal SRAM characterization.',
                      template_sha256=digest(template.read_bytes()))
        sources = {'gold': parent_sources(), 'sram': {n: (candidate / 'src' / n).read_bytes() for n in manifest['source_sha256']}}
        for label, files in sources.items():
            design = out / label
            src = design / 'src'
            src.mkdir(parents=True)
            for name, raw in files.items():
                (src / name).write_bytes(raw)
            config = dict(original_config)
            config.update(VERILOG_FILES=[str(src / name) for name in files],
                          FP_DEF_TEMPLATE=str(template), OPENROAD_THREADS=4)
            if label == 'sram':
                header = src / (MACRO + '.vh')
                header.write_bytes(blackbox((candidate / 'models' / (MACRO + '.v')).read_bytes()))
                config['MACROS'] = {MACRO: dict(views, vh=[str(header)], instances={}, nl=[], spef={})}
            write(src / 'config_merged.json', config)
            command = ['librelane', '--pdk-root', '/pdk', '--pdk', 'ihp-sg13cmos5l',
                       '--to', 'Yosys.Synthesis', '--run-tag', 'mapped-screen',
                       '--design-dir', str(design), str(src / 'config_merged.json')]
            item = {'sources': {n: digest(raw) for n, raw in files.items()},
                    'config_sha256': digest((src / 'config_merged.json').read_bytes())}
            result['runs'][label] = item
            write(out / 'result.json', result)
            item['execution'] = execute(command, design / 'run.log', 300)
            write(out / 'result.json', result)
            assert item['execution']['returncode'] == 0 and not item['execution']['timed_out'], label
            assert {n: digest((src / n).read_bytes()) for n in files} == item['sources']
        result['status'] = 'MAPPING_COMMANDS_SUCCEEDED_REQUIRES_AUDIT'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        write(out / 'result.json', result)
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
