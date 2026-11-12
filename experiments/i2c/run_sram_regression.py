# SPDX-License-Identifier: Apache-2.0
"""The full current matrix with only the declared 0x22 loader adaptation."""
import argparse
import json
import os
from pathlib import Path
import sys
from sram_prefetch import ROOT, digest
from build_sram_candidate import build
from run_current_regression import INPUTS, check_junit, check_controls, physical
sys.path.insert(0,str(ROOT/'experiments/spi_phase'))
from run_program_sensitivity import execute


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--simulator',choices=('icarus','verilator'),action='append')
    args=p.parse_args()
    candidate,out=args.candidate.resolve(),args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    (out/'inputs').mkdir(parents=True)
    manifest=json.loads((candidate/'manifest.json').read_bytes())
    regenerated=build(out/'regenerated')
    assert regenerated==manifest
    for name,expected in manifest['source_sha256'].items():
        assert digest((candidate/'src'/name).read_bytes())==expected
    for name,expected in manifest['model_sha256'].items():
        assert digest((candidate/'models'/name).read_bytes())==expected
    names=set(INPUTS)|{'experiments/i2c/run_sram_regression.py','experiments/i2c/build_sram_candidate.py',
                      'experiments/i2c/sram_prefetch.py','experiments/i2c/sram_program_store.v',
                      'experiments/spi_phase/run_program_sensitivity.py'}
    inputs={n:digest((ROOT/n).read_bytes()) for n in sorted(names)}
    for name in inputs:
        path=out/'inputs'/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((ROOT/name).read_bytes())
    result={'status':'RUNNING','scope':'CURRENT_30_GROUPS_WITH_CLOCKED_PROGRAM_READ_0X22',
            'candidate':manifest,'verification_inputs':inputs,'stages':[],
            'contract_change':'Only program-byte readback waits for a rising edge; runtime ID 0x22. Public wire oracles, record references and instruction cadence unchanged.',
            'physical':'NOT_EVALUATED'}
    save=lambda:(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    save()
    simulators=args.simulator or ['icarus','verilator']
    assert len(simulators)==len(set(simulators))
    try:
        for simulator in simulators:
            stage=out/simulator
            stage.mkdir()
            env=dict(os.environ)
            for key in ('GATES','G1_PHYSICAL','G2_PHYSICAL','GENERAL_IO','MAKEFLAGS','COCOTB_TESTCASE',
                        'COCOTB_TEST_FILTER','COCOTB_TEST_MODULES','COMPILE_ARGS','LEARNING_VCD','M0_LEARNING'):
                env.pop(key,None)
            env.update(G2_CURRENT='yes',G2_SRAM='yes',SRAM_MODEL_DIR=str(candidate/'models'),
                       I2C_GENERAL_VARIANT='od128',I2C_GENERAL_SMOKE='0',I2C_GENERAL_RECORD_DIR=str(stage/'records/i2c'),
                       TIMED_GPIO_VARIANT='compact10',TIMED_GPIO_SMOKE='0',TIMED_GPIO_RECORD_DIR=str(stage/'records/spi'),
                       COCOTB_RANDOM_SEED='20261112')
            command=['make','-C','test','SIM='+simulator,'SRC_DIR='+str(candidate/'src'),
                     'SIM_BUILD='+str(stage/'sim'),'COCOTB_RESULTS_FILE='+str(stage/'results.xml'),
                     'FST=','COCOTB_PLUSARGS=+NO_DUMP']
            item={'simulator':simulator,'execution':execute(command,stage/'run.log',1800,env=env)}
            result['stages'].append(item)
            save()
            assert item['execution']['returncode']==0 and not item['execution']['timed_out'],simulator
            log=(stage/'run.log').read_text()
            assert ('Running on Icarus Verilog' if simulator=='icarus' else 'Running on Verilator') in log
            assert 'expects 8 bit(s), given 5' not in log
            checked=check_junit(stage/'results.xml')
            checked['records']=physical.check_public_records(stage/'records')
            checked['current_bank_control']=check_controls(stage/'records/spi/controls.jsonl')
            (stage/'check.json').write_bytes((json.dumps(checked,indent=2)+'\n').encode())
            item['check']=checked
            save()
            print(simulator,'PASS_CURRENT_30_GROUPS_AND_EXACT_REFERENCE_RECORDS',flush=True)
        assert {n:digest((ROOT/n).read_bytes()) for n in inputs}==inputs
        assert {n:digest((candidate/'src'/n).read_bytes()) for n in manifest['source_sha256']}==manifest['source_sha256']
        result['status']='PASS_SRAM_CURRENT_BOTH_SIMULATORS' if set(simulators)=={'icarus','verilator'} else 'PASS_SRAM_CURRENT_SIMULATOR'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE',error=str(error))
        raise
    finally:
        save()
    print(result['status'],flush=True)


if __name__=='__main__':
    main()
