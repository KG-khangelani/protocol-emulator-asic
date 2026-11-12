import hashlib
import json
from pathlib import Path
import odb

base = Path('/workspace/build/g2-physical-shared/13966350208/runs/wokwi')
source = base / '37-openroad-resizertimingpostcts/tt_um_khangelani_protocol_emulator.odb'
db = odb.dbDatabase.create()
odb.read_db(db, str(source))
block = db.getChip().getBlock()
units = block.getDbUnitsPerMicron()
records = []
for net in block.getNets():
    ndr = net.getNonDefaultRule()
    if not ndr:
        continue
    pins = []
    for pin in net.getITerms():
        inst = pin.getInst()
        box = inst.getBBox()
        pins.append({'instance': inst.getName(), 'cell': inst.getMaster().getName(),
                     'pin': pin.getMTerm().getName(), 'direction': str(pin.getMTerm().getIoType()),
                     'center_um': [(box.xMin()+box.xMax())/(2*units), (box.yMin()+box.yMax())/(2*units)]})
    ports = [{'name': pin.getName(), 'boxes_um': [[b.xMin()/units, b.yMin()/units,
              b.xMax()/units, b.yMax()/units] for p in pin.getBPins() for b in p.getBoxes()]}
             for pin in net.getBTerms()]
    records.append({'name': net.getName(), 'rule': ndr.getName(), 'pins': pins, 'ports': ports})
rules = []
for rule in block.getNonDefaultRules():
    rules.append({'name': rule.getName()})
result = {'scope': 'READ_ONLY_PRE_ROUTING_DATABASE_INSPECTION', 'source': str(source),
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'instances': len(block.getInsts()), 'nets': len(block.getNets()),
          'ndr_rules': rules, 'ndr_nets': records}
out = Path('/workspace/build/g2-routing-diagnostic-01/database.json')
out.write_bytes((json.dumps(result, indent=2)+'\n').encode())
print(json.dumps({'instances': result['instances'], 'nets': result['nets'], 'ndr_net_count': len(records),
                  'rules': rules, 'first_ndr_nets': [n['name'] for n in records[:12]]}))
