// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from 'react';
import { describe, exampleProgram, nextState, resetState, wordHex } from './model';
import type { Machine } from './model';
import { atlas } from './data';
type Row = { edge: number; accepted: number; mode: string; machine: Machine };
const initial = (): Row => ({ edge: 0, accepted: 0, mode: 'RESET MODEL', machine: resetState() });
const byte = (value: number) => value.toString(16).padStart(2, '0').toUpperCase();

export function Cycles() {
  const [count, setCount] = useState(1);
  const [scenario, setScenario] = useState('example');
  const [ena, setEna] = useState(true);
  const [rstN, setRstN] = useState(true);
  const [rows, setRows] = useState<Row[]>([initial()]);
  const [selected, setSelected] = useState(0);
  const [playing, setPlaying] = useState(false);
  const program = scenario === 'invalid' ? [0x80000001] : scenario === 'fallthrough' ? [0x00010101] : exampleProgram(count);
  const current = rows.at(-1)!;
  const viewed = rows[selected] ?? current;
  const terminal = current.machine.state === 'HALT' || current.machine.state === 'FAULT';
  const step = () => setRows((history) => {
    const previous = history.at(-1)!;
    const machine = nextState(previous.machine, program, rstN, ena);
    const next = { edge: previous.edge + 1, accepted: previous.accepted + (rstN && ena ? 1 : 0), mode: !rstN ? 'RESET' : !ena ? 'DISABLED' : 'ACCEPTED', machine };
    return [...history, next];
  });
  useEffect(() => { setSelected(rows.length - 1); }, [rows]);
  useEffect(() => { if (terminal || rows.length >= 65541) setPlaying(false); }, [terminal, rows.length]);
  useEffect(() => {
    if (!playing) return;
    const interval = setInterval(step, 250);
    return () => clearInterval(interval);
  }, [playing, ena, rstN, count, scenario]);
  const restart = () => { setPlaying(false); setRows([initial()]); setSelected(0); };
  const configure = (operation: () => void) => { operation(); restart(); };
  return <section className="workspace cycle-workspace" aria-label="Reference cycles">
    <aside className="outline"><span className="eyebrow">Specimen</span><h2>SET / WAIT / HALT</h2><label className="stacked">Scenario<select aria-label="Scenario" value={scenario} onChange={(event) => configure(() => setScenario(event.target.value))}><option value="example">Exact timing example</option><option value="invalid">Reserved HALT bits → FAULT</option><option value="fallthrough">SET then out-of-range fetch</option></select></label><label className="stacked">WAIT count<input aria-label="WAIT count" type="number" min="0" max="65535" disabled={scenario !== 'example'} value={count} onChange={(event) => configure(() => setCount(Math.max(0, Math.min(65535, Math.floor(Number(event.target.value) || 0)))))} /></label>
      <h3>Decoded program</h3><ol className="program-list" start={0}>{program.map((word, index) => <li key={index}><code>{wordHex(word)}</code><span>{describe(word)}</span></li>)}</ol><p className="muted">Committed program; loader and synchronizer are not modeled here. Other valid M1 extensions are outside this reference subset.</p><a href={`${atlas.repository}/blob/${atlas.source.mainSnapshot}/docs/specs/m1-execution-contract.md`} target="_blank" rel="noreferrer">Execution contract ↗</a>
    </aside>
    <div className="canvas-region"><div className="region-heading"><div><h1>Reference cycles</h1><p>DERIVED · independent model, not RTL or hardware capture</p></div><span className="metric">{current.machine.state}<small>live model state</small></span></div>
      <div className="toolbar cycle-toolbar"><button className="action" onClick={step} disabled={rows.length >= 65541}>Step clock edge</button><button disabled={terminal || rows.length >= 65541} onClick={() => setPlaying(!playing)}>{playing ? 'Pause' : 'Play model'}</button><button onClick={restart}>Restart model</button><label><input type="checkbox" checked={ena} onChange={(event) => setEna(event.target.checked)} /> ena</label><label><input type="checkbox" checked={!rstN} onChange={(event) => setRstN(!event.target.checked)} /> Assert reset</label></div>
      <p className="subtle-note">State is shown after each rising edge. Reset wins over enable; disabled edges do not consume a WAIT count. 20 ns per edge assumes the 50 MHz TARGET, not measured Fmax.</p>
      <div className="table-scroll cycle-table-wrap"><table className="cycle-table"><caption className="sr-only">Reference post-edge state. Select an edge to inspect.</caption><thead><tr><th scope="col">Clock edge</th><th scope="col">Accepted</th><th scope="col">Condition</th><th scope="col">PC [4:0]</th><th scope="col">State</th><th scope="col">WAIT [15:0]</th><th scope="col">GPIO [7:0]</th><th scope="col">OE [7:0]</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.edge} className={selected === index ? 'row-selected' : ''}><th scope="row"><button onClick={() => setSelected(index)} aria-pressed={selected === index}>Edge {row.edge}</button></th><td>{row.accepted}</td><td>{row.mode}</td><td>{row.machine.pc}</td><td>{row.machine.state}</td><td>{row.machine.waitLeft}</td><td><code>{byte(row.machine.gpio)}</code></td><td><code>{byte(row.machine.oe)}</code></td></tr>)}</tbody></table></div>
      <div className="trace-summary" role="status"><span className="eyebrow">Playback boundary</span><p>Only explicit Step or Play advances this model. Relationship tracing cannot start it. HALT and FAULT hold until a sampled reset.</p></div>
    </div>
    <aside className="inspector" aria-label="Selected edge inspector"><span className="eyebrow">Selected reference row</span><h2>Edge {viewed.edge}</h2><dl className="field-list"><div><dt>Condition</dt><dd>{viewed.mode}</dd></div><div><dt>PC</dt><dd>{viewed.machine.pc}</dd></div><div><dt>State</dt><dd>{viewed.machine.state}</dd></div><div><dt>wait_left</dt><dd>{viewed.machine.waitLeft}</dd></div><div><dt>Stored value</dt><dd><code>0x{byte(viewed.machine.gpio)}</code></dd></div><div><dt>Output enable</dt><dd><code>0x{byte(viewed.machine.oe)}</code></dd></div></dl><h3>Observable pin controls</h3><ul className="register-list">{Array.from({ length: 8 }, (_, pin) => <li key={pin}><code>uio[{pin}]</code><span>{viewed.machine.oe & (1 << pin) ? `drive ${(viewed.machine.gpio >> pin) & 1}` : 'released · Z'}</span></li>)}</ul><p>Released pins do not drive their stored value. No analog glitch, contention or open-drain safety claim follows from this model.</p><div className="inspector-note"><h3>Measured traces</h3><p>Recorded RTL traces belong to the evidence view; they are not substituted for reference playback.</p><a href={`${atlas.repository}/blob/${atlas.source.mainSnapshot}/evidence/E0018-uart-rx-public/README.md`} target="_blank" rel="noreferrer">Open retained RTL evidence ↗</a></div></aside>
  </section>;
}
