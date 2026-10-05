// SPDX-License-Identifier: Apache-2.0
import { useEffect, useRef, useState } from 'react';
import { atlas, moduleById, relationById, short } from './data';
import type { Module, Relation } from './data';
import type { Location } from './navigation';

type Props = { location: Location; navigate: (patch: Partial<Location>) => void };
const regions: Record<string, { x: number; y: number; w: number; h: number }> = {
  top: { x: 18, y: 16, w: 782, h: 86 },
  program: { x: 18, y: 148, w: 224, h: 230 },
  engine: { x: 314, y: 148, w: 270, h: 270 },
  data: { x: 650, y: 148, w: 150, h: 224 },
  sync: { x: 314, y: 474, w: 270, h: 100 },
};
const paths: Record<string, { d: string; x: number; y: number; label: string; vertical?: boolean }> = {
  'raw-sync': { d: 'M 272 102 L 272 524 L 314 524', x: 264, y: 487, label: 'uio_in · raw input', vertical: true },
  'sync-engine': { d: 'M 448 474 L 448 418', x: 458, y: 451, label: 'sampled_inputs[7:0]' },
  'program-engine': { d: 'M 242 238 L 314 238', x: 278, y: 229, label: 'instruction' },
  'engine-program': { d: 'M 314 328 L 242 328', x: 278, y: 319, label: 'pc[4:0]' },
  'data-engine': { d: 'M 650 224 L 584 224', x: 617, y: 210, label: 'TX A / B' },
  'engine-data': { d: 'M 584 330 L 650 330', x: 617, y: 316, label: 'raw RX' },
  'engine-output': { d: 'M 532 148 L 532 102', x: 542, y: 126, label: 'GPIO + OE' },
};
const hex = (hash: string) => hash.match(/.{1,16}/g)?.join(' ') ?? hash;

function ModuleFields({ module }: { module: Module }) {
  return <dl className="field-list">{module.fields.length ? module.fields.map((field) => <div key={field.label}><dt>{field.label}</dt><dd>{field.bits} bits</dd></div>) : <div><dt>Routing only</dt><dd>0 state bits</dd></div>}</dl>;
}

export function Architecture({ location, navigate }: Props) {
  const [search, setSearch] = useState('');
  const [pointer, setPointer] = useState('');
  const [keyboard, setKeyboard] = useState('');
  const enterTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const exitTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const graph = useRef<HTMLDivElement>(null);
  const pinned = location.relation;
  const trace = pinned || keyboard || pointer;
  const active = relationById(trace);
  const selected = moduleById(location.module);
  const filteredModules = atlas.modules.filter((item) => `${item.label} ${item.name} ${item.file}`.toLowerCase().includes(search.toLowerCase()));
  const filteredRelations = atlas.relations.filter((item) => `${item.label} ${item.signals.join(' ')}`.toLowerCase().includes(search.toLowerCase()));
  const clearTimers = () => { if (enterTimer.current) clearTimeout(enterTimer.current); if (exitTimer.current) clearTimeout(exitTimer.current); };
  useEffect(() => () => clearTimers(), []);
  useEffect(() => { clearTimers(); setPointer(''); setKeyboard(''); }, [location.relation, location.module]);
  const clear = () => { clearTimers(); setPointer(''); setKeyboard(''); navigate({ relation: '' }); };
  const dwell = (id: string) => {
    clearTimers();
    enterTimer.current = setTimeout(() => { if (!pinned && !keyboard) setPointer(id); }, 150);
  };
  const leave = () => { clearTimers(); exitTimer.current = setTimeout(() => setPointer(''), 100); };
  const select = (id: string) => { clearTimers(); setPointer(''); setKeyboard(''); navigate({ module: id, relation: '' }); };
  const pin = (item: Relation) => { clearTimers(); navigate({ relation: item.id, module: item.to }); };
  const focus = (id: string) => { clearTimers(); setPointer(''); setKeyboard(id); };
  const fit = () => { navigate({ zoom: 1 }); graph.current?.scrollTo({ top: 0, left: 0 }); };
  const relationButton = (item: Relation) => <button key={item.id} type="button" className={`outline-item relation-item ${trace === item.id ? 'selected' : ''}`} data-relation={item.id}
    aria-pressed={pinned === item.id} onMouseEnter={() => dwell(item.id)} onMouseLeave={leave} onFocus={() => focus(item.id)} onBlur={() => setKeyboard('')} onClick={() => pin(item)}>
    <span>{item.label}</span><small>{moduleById(item.from).label} → {moduleById(item.to).label}</small>
  </button>;

  return <section className="workspace architecture" aria-label="Architecture" onKeyDown={(event) => { if (event.key === 'Escape') clear(); }}>
    <aside className="outline" aria-label="Architecture outline">
      <label className="eyebrow" htmlFor="find">Outline</label>
      <input id="find" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find module or signal" />
      <h2>Modules <span>{atlas.modules.length}</span></h2>
      {filteredModules.map((item) => <button key={item.id} className={`outline-item ${selected.id === item.id ? 'selected' : ''}`} aria-pressed={selected.id === item.id} onClick={() => select(item.id)}><span>{item.label}</span><small>{item.stateBits} declared state bits</small></button>)}
      <h2>Relationships <span>{atlas.relations.length}</span></h2>
      {filteredRelations.map(relationButton)}
      {filteredModules.length + filteredRelations.length === 0 && <p role="status">No matching source item.</p>}
    </aside>

    <div className="canvas-region">
      <div className="region-heading"><div><h1>Chip architecture</h1><p>CHIP_COMPLETE · logical wiring, not a floorplan</p></div><span className="metric">{atlas.totalStateBits} <small>state bits · DERIVED</small></span></div>
      <div className="toolbar" aria-label="Graph controls">
        <label><input type="checkbox" checked={location.signals} onChange={(event) => navigate({ signals: event.target.checked })} /> Signal labels</label>
        <div className="zoom-control"><button aria-label="Zoom out" disabled={location.zoom <= .8} onClick={() => navigate({ zoom: Math.max(.8, +(location.zoom - .1).toFixed(1)) })}>−</button><output aria-label="Zoom">{Math.round(location.zoom * 100)}%</output><button aria-label="Zoom in" disabled={location.zoom >= 1.4} onClick={() => navigate({ zoom: Math.min(1.4, +(location.zoom + .1).toFixed(1)) })}>+</button><button onClick={fit}>Fit</button></div>
        <button disabled={!trace} onClick={clear}>Clear trace</button>
      </div>
      <div className="graph-scroll" ref={graph}>
        <svg className="chip-graph" viewBox="0 0 820 598" style={{ width: `${location.zoom * 820}px` }} aria-label="Source-backed chip module relationships">
          <title>Five source modules and seven directed relationships. Accessible relationship controls are in the outline.</title>
          <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 9 5 L 0 9" className="arrow" /></marker></defs>
          {atlas.relations.map((item) => {
            const path = paths[item.id];
            return <g key={item.id} className={`connection ${trace === item.id ? 'traced' : ''}`} data-edge={item.id}>
              <path d={path.d} className={`wire ${trace && trace !== item.id ? 'deemphasized' : ''}`} markerEnd="url(#arrow)" />
              {trace === item.id && <path key={`${trace}-${pinned ? 'pin' : 'transient'}`} d={path.d} className="travel-cue" />}
              {location.signals && <text x={path.x} y={path.y} textAnchor={path.vertical ? 'start' : item.id.includes('engine') && !['sync-engine', 'engine-output'].includes(item.id) ? 'middle' : 'start'} transform={path.vertical ? `rotate(-90 ${path.x} ${path.y})` : undefined} className="signal-label">{path.label}</text>}
              <path d={path.d} className="wire-hit" aria-hidden="true" onMouseEnter={() => dwell(item.id)} onMouseLeave={leave} onClick={() => pin(item)} />
            </g>;
          })}
          {atlas.modules.map((item) => {
            const box = regions[item.id];
            const incident = active && (active.from === item.id || active.to === item.id);
            return <g key={item.id} className={`module ${selected.id === item.id ? 'is-selected' : ''} ${incident ? 'incident' : ''}`} data-module={item.id} onClick={() => select(item.id)}>
              <rect x={box.x} y={box.y} width={box.w} height={box.h} rx="3" className="module-surface" />
              {selected.id === item.id && <path d={`M ${box.x} ${box.y + 8} V ${box.y + box.h - 8}`} className="selection-rule" />}
              <text x={box.x + 10} y={box.y + 24} className="module-title">{item.label}</text>
              <text x={box.x + 10} y={box.y + 43} className="module-subtitle">{item.stateBits} declared state bits</text>
              {item.id === 'top' ? <><text x={box.x + 252} y={box.y + 24} className="module-subtitle">Shared pins · loader / runtime ownership</text><text x={box.x + 252} y={box.y + 47} className="module-subtitle">uo_out = status / selected register readback</text><text x={box.x + 10} y={box.y + 70} className="module-subtitle">engine reset: rst_n &amp;&amp; program_ready &amp;&amp; !load_mode</text></> : item.fields.map((field, index) => <g key={field.label}><text x={box.x + 10} y={box.y + 70 + 25 * index} className="module-field">{field.label}</text><text x={box.x + box.w - 10} y={box.y + 70 + 25 * index} textAnchor="end" className="module-number">{field.bits}</text></g>)}
              {item.id === 'engine' && <><text x={box.x + 10} y={box.y + 225} className="module-subtitle">RUN · WAIT · HALT · FAULT</text><text x={box.x + 10} y={box.y + 246} className="module-subtitle">ena freezes execution, not input sync</text></>}
              {item.id === 'program' && <text x={box.x + 10} y={box.y + 168} className="module-subtitle">8 × 32-bit writable words</text>}
              {item.id === 'data' && <text x={box.x + 10} y={box.y + 188} className="module-subtitle">Capture ≠ accept</text>}
            </g>;
          })}
        </svg>
      </div>
      <div className="mobile-module"><span className="eyebrow">Focused module</span><h2>{selected.label}</h2><p>{selected.note}</p><ModuleFields module={selected} /><h3>Connected relationships</h3>{atlas.relations.filter((item) => item.from === selected.id || item.to === selected.id).map(relationButton)}</div>
      <div className="trace-summary" role="status" aria-live="polite" aria-atomic="true"><span className="eyebrow">{pinned ? 'Pinned relationship' : active ? 'Relationship trace' : 'Inspect a connection'}</span>{active ? <><strong>{moduleById(active.from).label} → {moduleById(active.to).label}</strong><code>{active.signals.join(' · ')}</code><p>{active.note} <span className="muted">Navigation only; no simulated activity.</span></p></> : <p>Hover deliberately, focus or tap a relationship. Enter pins; Escape clears. Labels keep full contrast.</p>}</div>
    </div>

    <aside className="inspector" aria-label="Source inspector"><span className="eyebrow">{active ? 'Relationship' : 'Selected module'}</span><h2>{active?.label ?? selected.label}</h2>
      {active ? <><p>{moduleById(active.from).name}<br /><span className="muted">→</span> {moduleById(active.to).name}</p><dl className="field-list"><div><dt>From port</dt><dd><code>{active.sourcePort}</code></dd></div><div><dt>To port</dt><dd><code>{active.targetPort}</code></dd></div><div><dt>Top-level wire</dt><dd><code>{active.wire}</code></dd></div></dl><p>{active.note}</p><a href={moduleById('top').sourceUrl} target="_blank" rel="noreferrer">Inspect named connections ↗</a></> : <><p>{selected.note}</p><ModuleFields module={selected} /><code className="source-file">{selected.file}</code><a href={selected.sourceUrl} target="_blank" rel="noreferrer">Open qualified source ↗</a><h3>Declared sequential state</h3>{selected.registers.length ? <ul className="register-list">{selected.registers.map((item) => <li key={item.name}><code>{item.name}</code><span>{item.bits}</span></li>)}</ul> : <p>Combinational routing; no declared clocked state.</p>}<h3>Source fingerprint</h3><code className="hash">{hex(selected.sourceHash)}</code></>}
      <div className="inspector-note"><h3>Claim boundary</h3><p>{selected.evidenceSourceMatches ? `Source SHA-256 matches retained E0018 (${short(atlas.source.revision)}).` : 'Source does not match qualified evidence. No current-source PASS.'}</p><p>State attribution is DERIVED. Geometry is schematic, not area. Loader writes and raw capture do not imply protocol acceptance.</p><button onClick={() => navigate({ view: 'evidence', evidence: 'E0018' })}>Inspect qualification →</button></div>
    </aside>
  </section>;
}
