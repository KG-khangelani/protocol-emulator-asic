# SPDX-License-Identifier: Apache-2.0
"""Stage the declared native power-grid pilot without changing candidate RTL."""
import argparse
from decimal import Decimal
import gzip
import json
from pathlib import Path
import re
import tarfile

from sram_prefetch import ROOT, digest
from run_sram_mapping import blackbox, MACRO

read=lambda path:json.loads(path.read_bytes())


def power_rectangles(raw):
    text=raw.decode()
    found={}
    for name in ('VDD!','VDDARRAY!','VSS!'):
        match=re.search(r'\bPIN '+re.escape(name)+r'\s+(.*?)\bEND '+re.escape(name),text,re.S)
        assert match and set(re.findall(r'\bLAYER\s+(\S+)\s*;',match[1]))=={'Metal4'}
        found[name]=[tuple(Decimal(v) for v in values.split())
                     for values in re.findall(r'\bRECT\s+([^;]+);',match[1])]
    assert {n:len(v) for n,v in found.items()}=={'VDD!':36,'VDDARRAY!':32,'VSS!':36}
    assert {r[0:3:2] for r in found['VDDARRAY!']} <= {r[0:3:2] for r in found['VDD!']}
    assert all(r[2]-r[0]==Decimal('2.81') for rows in found.values() for r in rows)
    return found


def pdn_script(rectangles):
    x=Decimal('20.16')
    width=Decimal('416.64')
    columns={net:sorted({(r[0]+r[2])/2 for r in rectangles[pin]})
             for net,pin in [('VPWR','VDD!'),('VGND','VSS!')]}
    globals_=[(net,x+centre) for net,centres in columns.items() for centre in centres]
    # Same core origin, offset, pair spacing and pitch as the pinned template.
    for k in range(35):
        for net,delta in [('VPWR',Decimal('0')),('VGND',Decimal('4.1'))]:
            centre=Decimal('2.88')+Decimal('10')+50*k+delta
            if centre+Decimal('1.05')>Decimal('1721.28'):
                continue
            if centre+Decimal('1.05')<x or centre-Decimal('1.05')>x+width:
                globals_.append((net,centre))
    lines=[
        '# SPDX-License-Identifier: Apache-2.0',
        '# Generated from the pinned macro Metal4 supply rectangles.',
        'source $::env(SCRIPTS_DIR)/openroad/common/io.tcl',
        'source $::env(SCRIPTS_DIR)/openroad/common/set_global_connections.tcl',
        'set_global_connections',
        'set_voltage_domain -name CORE -power $::env(VDD_NET) -ground $::env(GND_NET)',
        'set block [ord::get_db_block]',
        'set core_x [expr {double([[$block getCoreArea] xMin])/[$block getDbUnitsPerMicron]}]',
        'if {abs($core_x - 2.88) > 0.0001} {error "Unexpected core origin"}',
        'define_pdn_grid -name stdcell_grid -starts_with POWER -voltage_domains CORE -pins Metal4',
    ]
    for net,centre in sorted(globals_,key=lambda v:v[1]):
        lines.append(f'add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {{{centre} - $core_x}}] -number_of_straps 1 -nets {net} -extend_to_boundary')
    lines += [
        'add_pdn_stripe -grid stdcell_grid -layer $::env(PDN_RAIL_LAYER) -width $::env(PDN_RAIL_WIDTH) -followpins',
        'add_pdn_connect -grid stdcell_grid -layers "$::env(PDN_RAIL_LAYER) Metal4"',
        'define_pdn_grid -macro -name sram_grid -instances {store.program_memory} -grid_over_boundary -halo {0 0} -starts_with POWER',
    ]
    for net,centres in columns.items():
        for centre in centres:
            lines.append(f'add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset {centre} -number_of_straps 1 -nets {net} -extend_to_boundary')
    return ('\n'.join(lines)+'\n').encode(),columns


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--template',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--integrated',action='store_true',help='Stage the two explicit power steps in the unchanged Classic flow.')
    args=p.parse_args()
    candidate,out=args.candidate.resolve(),args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    manifest=read(candidate/'manifest.json')
    evidence=ROOT/'evidence/E0042-sram-prefetch-screen'
    assert manifest==read(evidence/'candidate.json')
    mapped=read(evidence/'mapped/verification.json')
    assert mapped['status']=='PASS_MATCHED_SRAM_MAPPED_SCREEN' and mapped['mapped_footprint_reduction_percent']>=20
    assert read(evidence/'regression/result.json')['status']=='PASS_SRAM_CURRENT_BOTH_SIMULATORS'
    (out/'src').mkdir(parents=True)
    (out/'inputs').mkdir()
    for name,expected in manifest['source_sha256'].items():
        raw=(candidate/'src'/name).read_bytes()
        assert digest(raw)==expected
        (out/'src'/name).write_bytes(raw)
    model=(candidate/'models'/(MACRO+'.v')).read_bytes()
    assert digest(model)==manifest['model_sha256'][MACRO+'.v']
    header=blackbox(model)
    assert header.count(b'`timescale 1ns/10ps\n')==1
    header=header.replace(b'`timescale 1ns/10ps\n',b'')
    (out/'src'/(MACRO+'.vh')).write_bytes(header)
    raw=gzip.decompress((evidence/'feasibility/lef'/(MACRO+'.lef.gz')).read_bytes())
    rectangles=power_rectangles(raw)
    script,columns=pdn_script(rectangles)
    (out/'src/sram_pdn.tcl').write_bytes(script)
    index=read(evidence/'mapped/archive.json')
    assert digest((evidence/'mapped/mapping.tar.gz').read_bytes())==index['sha256']
    with tarfile.open(evidence/'mapped/mapping.tar.gz') as archive:
        raw=archive.extractfile('sram/src/config_merged.json').read()
        assert digest(raw)==index['files']['sram/src/config_merged.json']
    (out/'inputs/mapped-config.json').write_bytes(raw)
    config=json.loads(raw)
    config['VERILOG_FILES']=[str(out/'src'/name) for name in manifest['source_sha256']]
    config['FP_DEF_TEMPLATE']=str(args.template.resolve())
    assert digest(args.template.read_bytes())=='64b52f2150f699edc7fb500c2f486a51eca66fd91d3efb7347200bd2cf83a2ee'
    macro=config['MACROS'][MACRO]
    macro['vh']=[str(out/'src'/(MACRO+'.vh'))]
    macro['instances']={'store.program_memory':{'location':[20.16,302.4],'orientation':'FS'}}
    config.update(PDN_CFG=str(out/'src/sram_pdn.tcl'),PDN_HORIZONTAL_HALO=0,PDN_VERTICAL_HALO=0,PDN_SKIPTRIM=True,
                  PDN_MACRO_CONNECTIONS=['^store\\.program_memory$ VPWR VGND VDD! VSS!',
                                         '^store\\.program_memory$ VPWR VGND VDDARRAY! VSS!'])
    plugin_files={}
    if args.integrated:
        config.setdefault('meta',{})['flow']='SramClassic'
        config['SRAM_POWER_MANIFEST']=str(out/'preparation.json')
        for name in ('librelane_plugin_sram.py','sram_power_step.py','connect_sram_power.py','check_sram_power.tcl'):
            body=(ROOT/'experiments/i2c'/name).read_bytes()
            (out/name).write_bytes(body)
            plugin_files[name]=digest(body)
    (out/'src/config_merged.json').write_bytes((json.dumps(config,indent=2)+'\n').encode())
    for path in (Path(__file__),ROOT/'experiments/i2c/run_sram_mapping.py',ROOT/'docs/specs/g2-sram-physical-integration.md'):
        (out/'inputs'/path.name).write_bytes(path.read_bytes())
    result={'status':'PREPARED_UNQUALIFIED_NATIVE_PDN_TRIAL','candidate':manifest,
            'config_sha256':digest((out/'src/config_merged.json').read_bytes()),
            'header_sha256':digest(header),'pdn_script_sha256':digest(script),
            'power_rectangles':{n:[[str(v) for v in r] for r in rows] for n,rows in rectangles.items()},
            'column_centres':{n:[str(v) for v in rows] for n,rows in columns.items()},
            'source_sha256':{n:digest((out/'src'/n).read_bytes()) for n in manifest['source_sha256']},
            'physical':'NOT_EVALUATED'}
    if args.integrated:
        result.update(status='PREPARED_UNQUALIFIED_INTEGRATED_PDN_TRIAL',plugin_sha256=plugin_files)
    (out/'preparation.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(result['status'])


if __name__=='__main__':
    main()
