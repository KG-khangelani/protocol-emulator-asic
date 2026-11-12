# SPDX-License-Identifier: Apache-2.0
"""Replay the actual integrated power stages and retained database bindings."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
read=lambda p:json.loads(p.read_bytes())
digest=lambda b:hashlib.sha256(b).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True,type=Path)
    out=p.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    out.mkdir(parents=True)
    for line in (HERE/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1)
        assert digest((HERE/name).read_bytes())==expected
    index=read(HERE/'archive.json')
    packed=(HERE/'pilot.tar.gz').read_bytes()
    assert len(packed)==index['bytes'] and digest(packed)==index['sha256']
    with tarfile.open(HERE/'pilot.tar.gz') as archive:
        members=archive.getmembers()
        assert len(members)==len(index['files']) and {m.name for m in members}==set(index['files'])
        for member in members:
            path=(out/member.name).resolve()
            assert member.isfile() and path.is_relative_to(out)
            raw=archive.extractfile(member).read()
            assert digest(raw)==index['files'][member.name]
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
    original=read(out/'pilot/verification.json')
    path=out/'pilot/inputs/audit_sram_power_pilot.py'
    nodes=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='audit']
    assert len(nodes)==1
    namespace={'read':read,'digest':digest,'json':json,'ROOT':ROOT}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    namespace['audit'](out/'pilot')
    assert read(out/'pilot/verification.json')==original==read(HERE/'verification.json')
    assert original['output_odb_sha256']=='db9b16aa65fb52722a7de25efe81aacc2e6a4ddf7c9634ef1a5e3f8ccc916995'
    print('PASS_RETAINED_INTEGRATED_SRAM_POWER_PILOT',len(members))


if __name__=='__main__':
    main()
