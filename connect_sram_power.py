# SPDX-License-Identifier: Apache-2.0
"""Connect existing outer stripes to SRAM power pins without crossing its interior."""
from collections import Counter
from decimal import Decimal
import hashlib
import json

import odb


def wire_rectangles(block, net_name):
    rows=[]
    for wire in block.findNet(net_name).getSWires():
        for shape in wire.getWires():
            if not shape.isVia() and shape.getTechLayer().getName()=='Metal4':
                rows.append((shape.xMin(),shape.yMin(),shape.xMax(),shape.yMax()))
    return rows


def overlaps(a,b):
    return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])


def logical_identity(block):
    instances=sorted((i.getName(),i.getMaster().getName(),i.getLocation(),str(i.getOrient()),str(i.getPlacementStatus())) for i in block.getInsts())
    nets=sorted((n.getName(),str(n.getSigType()),sorted(t.getInst().getName()+'/'+t.getMTerm().getName() for t in n.getITerms()),
                 sorted(t.getName() for t in n.getBTerms())) for n in block.getNets())
    pins=sorted((t.getName(),str(t.getIoType()),str(t.getSigType()),
                 sorted((b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax()) for p in t.getBPins() for b in p.getBoxes())) for t in block.getBTerms())
    return hashlib.sha256(json.dumps([instances,nets,pins],sort_keys=True).encode()).hexdigest()


def connect(db, preparation):
    block=db.getChip().getBlock()
    scale=block.getDbUnitsPerMicron()
    assert scale==1000
    inst=block.findInst('store.program_memory')
    assert inst and inst.getMaster().getName()=='RM_IHPSG13_1P_256x32_c2_bm_bist'
    bounds=inst.getBBox()
    box=(bounds.xMin(),bounds.yMin(),bounds.xMax(),bounds.yMax())
    assert box==(20160,302400,436800,421180) and str(inst.getOrient()) in ('MX','FS')
    original=logical_identity(block)
    before={n:wire_rectangles(block,n) for n in ('VPWR','VGND')}
    pins=[]
    for name,rows in preparation['power_rectangles'].items():
        net='VGND' if name=='VSS!' else 'VPWR'
        assert inst.findITerm(name).getNet().getName()==net
        for row in rows:
            r=[int(Decimal(v)*scale) for v in row]
            pins.append((name,net,(box[0]+r[0],box[3]-r[3],box[0]+r[2],box[3]-r[1])))
    additions=[]
    for net,columns in preparation['column_centres'].items():
        assert len(columns)==36
        for column in columns:
            centre=box[0]+int(Decimal(column)*scale)
            for side in ('lower','upper'):
                boundary=box[1] if side=='lower' else box[3]
                available=[r for r in before[net] if r[0]==centre-1050 and r[2]==centre+1050 and
                           ((r[3]<=boundary and boundary-r[3]<=2000) if side=='lower' else
                            (r[1]>=boundary and r[1]-boundary<=2000))]
                assert len(available)==1,(net,column,side,available)
                wire=available[0]
                bridge=(wire[0],wire[3]-1000,wire[2],boundary+1000) if side=='lower' else (wire[0],boundary-1000,wire[2],wire[1]+1000)
                assert overlaps(bridge,wire)
                own=[r for _,n,r in pins if n==net and overlaps(bridge,r)]
                assert own and all(bridge[0]>=r[0] and bridge[2]<=r[2] for r in own)
                assert not any(overlaps(bridge,r) for _,n,r in pins if n!=net)
                assert bridge[3]<=box[1]+1000 if side=='lower' else bridge[1]>=box[3]-1000
                additions.append({'net':net,'side':side,'rectangle_dbu':bridge,'existing_wire_dbu':wire})
    assert len(additions)==144 and len({(a['net'],a['rectangle_dbu']) for a in additions})==144
    layer=db.getTech().findLayer('Metal4')
    swires={n:odb.dbSWire_create(block.findNet(n),'ROUTED') for n in before}
    for item in additions:
        shape=odb.dbSBox_create(swires[item['net']],layer,*item['rectangle_dbu'],'STRIPE')
        assert shape is not None
    assert logical_identity(block)==original
    after={n:wire_rectangles(block,n) for n in before}
    for net in before:
        assert Counter(after[net])==Counter(before[net])+Counter(a['rectangle_dbu'] for a in additions if a['net']==net)
    observations=[]
    for pin,net,rectangle in pins:
        own=[r for r in after[net] if overlaps(rectangle,r)]
        other=[r for r in after['VGND' if net=='VPWR' else 'VPWR'] if overlaps(rectangle,r)]
        assert own and not other
        observations.append({'pin':pin,'net':net,'rectangle_dbu':rectangle,'overlaps':own})
    return {'status':'PASS_GEOMETRY_CONNECTIONS_GRID_CHECK_PENDING','logical_identity_before_and_after':original,
            'added_rectangles':additions,'supply_rectangles':observations,
            'before_wire_counts':{n:len(v) for n,v in before.items()},'after_wire_counts':{n:len(v) for n,v in after.items()},
            'physical_qualification':'NOT_EVALUATED'}
