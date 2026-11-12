"""Read-only inspection of the exact installed PDK; no SRAM implementation claim."""
import hashlib
import json
from pathlib import Path
import re

PDK = Path('/pdk/ciel/ihp-sg13/versions/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008/ihp-sg13cmos5l')
BASE = PDK / 'libs.ref/sg13cmos5l_sram'
OUT = Path('/workspace/build/g2-sram-feasibility-01')
OUT.mkdir(parents=True, exist_ok=True)
name = 'RM_IHPSG13_1P_256x32_c2_bm_bist'
selected = [BASE / 'lef' / (name+'.lef'), BASE / 'doc' / (name+'.txt'),
            BASE / 'verilog' / (name+'.v'), BASE / 'verilog/RM_IHPSG13_1P_core_behavioral_bm_bist.v']
selected += sorted((BASE / 'lib').glob(name+'*.lib'))
result = {'status': 'READ_ONLY_FEASIBILITY_OBSERVATION',
          'pdk': '89d42ee6d2fd9b50b86a1aada6fee6673c3e6008', 'macro': name,
          'physical_capacity_bits': 256*32, 'proposed_logical_words': 128,
          'macro_inputs': {}, 'timing_libraries': {}, 'implementation': 'NOT_STARTED',
          'limits': ['Existing loader promises combinational readback; synchronous SRAM requires an explicit revised contract.',
                     'SRAM has no data-reset port; logical zero after reset needs a separately verified validity scheme.',
                     'Fast SRAM library is -55C, unlike the existing -40C standard-cell fast corner; do not relabel it silently.',
                     'Macro footprint is not complete-chip mapped/routed cost; placement, power and all signoff remain untested.']}
for source in selected:
    raw = source.read_bytes()
    rel = source.relative_to(BASE).as_posix()
    result['macro_inputs'][rel] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    if source.parent.name != 'lib':
        target = OUT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    else:
        text = raw.decode()
        result['timing_libraries'][source.name] = {
            'nom_voltage': re.findall(r'\bnom_voltage\s*:\s*([^;]+)', text),
            'nom_temperature': re.findall(r'\bnom_temperature\s*:\s*([^;]+)', text),
            'nom_process': re.findall(r'\bnom_process\s*:\s*([^;]+)', text)}
width, height = map(float, re.search(r'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)', selected[0].read_text()).groups())
result['lef_footprint_um'] = [width, height]
result['lef_area_um2'] = round(width*height, 4)
result['normal_port_pins'] = re.findall(r'^\s*(?:input|output)\s+(?:\[[^\]]+\]\s+)?(A_[A-Z]+)\s*;', selected[2].read_text(), re.M)
(OUT / 'inspection.json').write_bytes((json.dumps(result, indent=2)+'\n').encode())
print(json.dumps({k: result[k] for k in ('status','lef_footprint_um','lef_area_um2','physical_capacity_bits','timing_libraries')}))
