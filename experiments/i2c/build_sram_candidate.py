# SPDX-License-Identifier: Apache-2.0
"""Build the explicitly revised 0x22 candidate without editing production."""
import argparse
import gzip
import json
from pathlib import Path
from sram_prefetch import ROOT, digest, parent_sources, engine_with_next_pc


def build(out):
    out=out.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    source=parent_sources()
    source['m1_engine.v'],transformation=engine_with_next_pc(source['m1_engine.v'])
    source['m1_program_store.v']=(ROOT/'experiments/i2c/sram_program_store.v').read_bytes()
    top=source['project.v'].decode()
    assert top.count("8'h21")==2
    top=top.replace("8'h21","8'h22")
    assert top.count('    wire [7:0] pc;')==1
    top=top.replace('    wire [7:0] pc;','    wire [7:0] pc;\n    wire [7:0] prefetch_pc;')
    needle='.byte_address(byte_address), .data_in(uio_in), .pc(pc),'
    assert top.count(needle)==1
    top=top.replace(needle,needle+' .prefetch_pc(prefetch_pc),')
    needle='.pc(pc), .state(state), .wait_left(wait_left),'
    assert top.count(needle)==1
    top=top.replace(needle,'.pc(pc), .prefetch_pc(prefetch_pc), .state(state), .wait_left(wait_left),')
    source['project.v']=top.encode()
    (out/'src').mkdir(parents=True)
    for name,raw in source.items():
        (out/'src'/name).write_bytes(raw)
    recorded=ROOT/'evidence/E0042-sram-prefetch-screen/feasibility'
    inspection=json.loads((recorded/'inspection.json').read_bytes())
    (out/'models').mkdir()
    models={}
    for name,metadata in inspection['macro_inputs'].items():
        if not name.startswith('verilog/'):
            continue
        raw=gzip.decompress((recorded/(name+'.gz')).read_bytes())
        assert digest(raw)==metadata['sha256'] and len(raw)==metadata['bytes']
        (out/'models'/Path(name).name).write_bytes(raw)
        models[Path(name).name]=digest(raw)
    manifest={'status':'BUILT_UNQUALIFIED_SRAM_CANDIDATE','profile':'od128-sram','interface_id':'0x22',
              'source_sha256':{name:digest(raw) for name,raw in source.items()},'model_sha256':models,
              'engine_transformation':transformation,'physical_capacity_bits':8192,'logical_program_words':128,
              'builder_sha256':digest(Path(__file__).read_bytes()),
              'store_template_sha256':digest((ROOT/'experiments/i2c/sram_program_store.v').read_bytes()),
              'prefetch_builder_sha256':digest((ROOT/'experiments/i2c/sram_prefetch.py').read_bytes())}
    (out/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(build(parser.parse_args().output)))
