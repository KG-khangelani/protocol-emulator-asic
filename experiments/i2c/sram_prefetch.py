# SPDX-License-Identifier: Apache-2.0
"""Generate isolated SRAM-screen inputs from the hash-checked D39 parent."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT / 'evidence/E0038-shared-program-read/sources'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parent_sources():
    manifest = json.loads((PARENT / 'source-manifest.json').read_bytes())['od128']['source_sha256']
    sources = {name:(PARENT / 'od128' / name).read_bytes() for name in manifest}
    assert {name:digest(raw) for name,raw in sources.items()} == manifest
    return sources


def engine_with_next_pc(raw):
    source = raw.decode()
    start = source.index('    task automatic abort_to(')
    stop = source.index('endmodule',start)
    prefix,body,suffix = source[:start],source[start:stop],source[stop:]
    # These are the only <= comparisons; protect them from assignment rewriting.
    guard = "(pc <= 8'd253)"
    assert body.count(guard) == 2
    protected = body.replace(guard,'(PC_SKIP_GUARD)')
    assignments = list(re.finditer(r'\b([A-Za-z_]\w*)\s*<=',protected))
    names = sorted({m.group(1) for m in assignments})
    declarations = {m.group(2):m.group(1) or '' for m in re.finditer(r'\breg\s*(\[[^\]]+\])?\s*([A-Za-z_]\w*)',prefix)}
    assert set(names) <= set(declarations)
    assert len(assignments) == 163 and len(names) == 26
    body = re.sub(r'\b([A-Za-z_]\w*)\s*<=',lambda m:m.group(1)+'_next =',protected)
    body = body.replace('(PC_SKIP_GUARD)',guard)
    clocked = '    always @(posedge clk) begin\n'
    assert body.count(clocked) == 1
    defaults = ''.join('        '+name+'_next = '+name+';\n' for name in names)
    body = body.replace(clocked,'    always @* begin\n'+defaults,1)
    port = '    output wire shift_result_write, output wire [7:0] shift_result_data\n'
    assert prefix.count(port) == 1
    prefix = prefix.replace(port,port.rstrip() + ',\n    output wire [7:0] prefetch_pc\n')
    prefix += ''.join('    reg '+(declarations[name]+' ' if declarations[name] else '')+name+'_next;\n' for name in names)
    prefix += '    assign prefetch_pc = pc_next;\n\n'
    commit = clocked + ''.join('        '+name+' <= '+name+'_next;\n' for name in names) + '    end\n'
    result = (prefix+body+commit+suffix).encode()
    return result, {'state_registers':names,'rewritten_assignments':len(assignments),
                    'protected_relational_guards':2,'source_sha256':digest(raw),'result_sha256':digest(result)}
