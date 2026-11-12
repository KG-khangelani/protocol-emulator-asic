import difflib
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import odb

ROOT = Path('/workspace')
OUT = ROOT / 'build/g2-routing-diagnostic-02'
BASE = ROOT / 'build/g2-physical-shared/13966350208'
PDK_HASH = '89d42ee6d2fd9b50b86a1aada6fee6673c3e6008'
SOURCE = BASE / 'runs/wokwi/37-openroad-resizertimingpostcts/tt_um_khangelani_protocol_emulator.odb'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def write(path, value):
    path.write_bytes((json.dumps(value, indent=2)+'\n').encode())

assert not (OUT / 'ablation-result.json').exists()
result = {'status': 'RUNNING', 'scope': 'CLOCK_NDR_ABLATION_GLOBAL_ROUTING_ONLY',
          'source_odb_sha256': sha(SOURCE), 'runner_sha256': sha(Path(__file__)),
          'spec_sha256': sha(ROOT / 'docs/specs/g2-clock-routing-diagnostic.md'),
          'wall_limit_seconds': 1200, 'physical_qualification': 'NOT_EVALUATED'}
write(OUT / 'ablation-result.json', result)
try:
    db = odb.dbDatabase.create()
    odb.read_db(db, str(SOURCE))
    block = db.getChip().getBlock()
    odb.write_def(block, str(OUT / 'before.def'))
    removed = []
    for net in block.getNets():
        rule = net.getNonDefaultRule()
        if rule:
            assert rule.getName() == 'CTS_NDR_0'
            removed.append(net.getName())
            net.setNonDefaultRule(None)
    assert len(removed) == 16
    odb.write_def(block, str(OUT / 'after.def'))
    before = (OUT / 'before.def').read_text().splitlines(keepends=True)
    after = (OUT / 'after.def').read_text().splitlines(keepends=True)
    marker = ' + NONDEFAULTRULE CTS_NDR_0'
    expected = [line.replace(marker, '') for line in before]
    assert sum(line.count(marker) for line in before) == 16 and expected == after
    (OUT / 'ndr-only.patch').write_bytes(''.join(difflib.unified_diff(before, after, fromfile='original', tofile='no-clock-ndr')).encode())
    modified = OUT / 'no-clock-ndr.odb'
    odb.write_db(db, str(modified))
    result.update(removed_ndr_nets=removed, modified_odb_sha256=sha(modified),
                  def_comparison='EXACTLY_16_NDR_ASSIGNMENTS_REMOVED', patch_sha256=sha(OUT / 'ndr-only.patch'))
    old_prefix = '/home/runner/work/protocol-emulator-asic/protocol-emulator-asic'
    old_pdk = '/home/runner/.ciel/ciel/ihp-sg13/versions/' + PDK_HASH
    def relocate(value):
        if isinstance(value, dict):
            return {k: relocate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [relocate(v) for v in value]
        if isinstance(value, str):
            return value.replace(old_prefix, str(BASE)).replace(old_pdk, '/pdk/ihp-sg13/versions/' + PDK_HASH)
        return value
    original_state = BASE / 'runs/wokwi/39-openroad-globalrouting/state_in.json'
    state = relocate(json.loads(original_state.read_bytes()))
    state['odb'] = str(modified)
    write(OUT / 'initial-state.json', state)
    config_source = BASE / 'src/config_merged.json'
    config = json.loads(config_source.read_bytes())
    config['VERILOG_FILES'] = [str(BASE / 'src' / Path(name).name.replace('dir::', '')) for name in config['VERILOG_FILES']]
    config['FP_DEF_TEMPLATE'] = str(ROOT / 'build/g1-upstream/support/tt_block_8x4_pgvdd.def')
    config['OPENROAD_THREADS'] = 4
    write(OUT / 'config.json', config)
    result.update(original_state_sha256=sha(original_state), original_config_sha256=sha(config_source),
                  initial_state_sha256=sha(OUT / 'initial-state.json'), config_sha256=sha(OUT / 'config.json'))
    command = ['librelane', '--pdk-root', '/pdk', '--pdk', 'ihp-sg13cmos5l',
               '--from', 'OpenROAD.GlobalRouting', '--to', 'OpenROAD.GlobalRouting',
               '--with-initial-state', str(OUT / 'initial-state.json'), '--run-tag', 'no-clock-ndr',
               '--design-dir', str(OUT), str(OUT / 'config.json')]
    result['command'] = command
    result['start_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    write(OUT / 'ablation-result.json', result)
    start = time.monotonic()
    with (OUT / 'ablation.log').open('w') as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=1200)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code, timed_out = 124, True
    result.update(returncode=code, timed_out=timed_out, seconds=round(time.monotonic()-start, 3),
                  status='GLOBAL_ROUTING_COMMAND_SUCCEEDED_REQUIRES_AUDIT' if code == 0 else 'FAILED_OR_INCOMPLETE')
    assert sha(SOURCE) == result['source_odb_sha256']
except Exception as error:
    result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
    raise
finally:
    write(OUT / 'ablation-result.json', result)
print(result['status'], flush=True)
