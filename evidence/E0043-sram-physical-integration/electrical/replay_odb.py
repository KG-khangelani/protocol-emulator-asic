# SPDX-License-Identifier: Apache-2.0
"""Rerun the actual connectivity audit and both retained wiring faults."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--directory',required=True,type=Path)
    base=p.parse_args().directory.resolve()
    read=lambda p:json.loads(p.read_bytes())
    assert read(base/'verification.json')['status']=='PASS_RETAINED_ELECTRICAL_REJECTIONS_AND_BOUNDED_SCREENS'
    before=base/'full-01/runs/integrated/41-openroad-globalrouting/tt_um_khangelani_protocol_emulator.odb'
    screen=base/'buffer-screen'
    controls=screen/'controls'
    after=screen/'runs/screen/01-project-buffersraminputs/tt_um_khangelani_protocol_emulator.odb'
    out=base/'replayed-controls';out.mkdir(exist_ok=False)
    for name in ('baseline','crossed-address-loads','wrong-buffer-input'):
        directory=out/name;directory.mkdir()
        target=after if name=='baseline' else controls/name/'mutated.odb'
        command=['openroad','-no_init','-exit','-python',str(controls/'auditor.py'),
                 '--before',str(before),'--after',str(target),'--output',str(directory/'result.json')]
        with (directory/'run.log').open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        if name=='baseline':
            assert result.returncode==0
            assert read(directory/'result.json')==read(controls/name/'result.json')
        else:
            marker='TARGET_NET_IDENTITY_CHANGED' if name=='crossed-address-loads' else 'BUFFER_INPUT_CHANGED'
            assert result.returncode!=0 and marker in (directory/'run.log').read_text()
    print('PASS_ACTUAL_BUFFER_CONNECTIVITY_AND_TWO_FAULT_REPLAY')


if __name__=='__main__':
    main()
