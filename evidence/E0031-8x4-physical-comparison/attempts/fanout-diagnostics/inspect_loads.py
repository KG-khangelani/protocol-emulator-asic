import odb,json,hashlib
from pathlib import Path
base=Path('/workspace/build/g1/fanout-diagnostic/designs/P/runs/fanout8-distance100-route')
result={'variant':'P','net':'_0601_','scope':'read-only database inspection before and after detailed routing','stages':{}}
for rel in ('07-openroad-repairantennas/1-openroad-diodeinsertion/tt_um_khangelani_protocol_emulator.odb','09-openroad-detailedrouting/tt_um_khangelani_protocol_emulator.odb'):
    p=base/rel
    db=odb.dbDatabase.create()
    odb.read_db(db,str(p))
    net=db.getChip().getBlock().findNet('_0601_')
    pins=[{'instance':i.getInst().getName(),'cell':i.getInst().getMaster().getName(),'pin':i.getMTerm().getName(),'direction':str(i.getMTerm().getIoType())} for i in net.getITerms()]
    result['stages'][rel]={'odb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pins':pins,'load_count':sum(i['direction']=='INPUT' for i in pins)}
out=Path('/workspace/build/g1/fanout-diagnostic/antenna-loads.json')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v['load_count'] for k,v in result['stages'].items()}))
