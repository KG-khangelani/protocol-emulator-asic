import sys
from pathlib import Path
sys.path.insert(0, '/workspace/experiments/spi_phase')
from run_program_sensitivity import execute
out=Path('/workspace/build/i2c-store-sat-02')
out.mkdir()
source=Path('/workspace/build/i2c-store-local-02/od128-prove/store.v')
(out/'store.v').write_bytes(source.read_bytes())
script=f'read -formal -sv {out}/store.v\nprep -top m1_program_store\nchformal -cover -remove\nchformal -lower\nsat -seq 1 -tempinduct -maxsteps 3 -prove-asserts -verify -timeout 180\n'
(out/'proof.ys').write_text(script)
result=execute(['yosys','-Q','-T','-s',str(out/'proof.ys')],out/'run.log',360)
import json
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(result, flush=True)
