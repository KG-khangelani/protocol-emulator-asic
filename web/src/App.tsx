// SPDX-License-Identifier: Apache-2.0
import { useState } from 'react';
import { Architecture } from './Architecture';
import { Cycles } from './Cycles';
import { EvidenceView, Progress } from './Evidence';
import { atlas, short } from './data';
import { useLocation } from './navigation';
import type { View } from './navigation';
import { useTheme } from './theme';
import type { Theme } from './theme';

export function App() {
  const [location, navigate] = useLocation();
  const [theme, chooseTheme] = useTheme();
  const [copyStatus, setCopyStatus] = useState('');
  const copy = async () => { try { await navigator.clipboard.writeText(window.location.href); setCopyStatus('View link copied'); } catch { setCopyStatus('Copy unavailable — use the address bar'); } };
  return <><a className="skip-link" href="#main-content" onClick={(event) => { event.preventDefault(); document.getElementById('main-content')?.focus(); }}>Skip to main content</a><header className="app-header"><a className="brand" href="#view=architecture">Protocol atlas <span>protocol-emulator-asic</span></a><nav aria-label="Views">{(['architecture', 'cycles', 'evidence', 'progress'] as View[]).map((view) => <button key={view} aria-current={location.view === view ? 'page' : undefined} onClick={() => navigate({ view })}>{view[0].toUpperCase() + view.slice(1)}</button>)}</nav><div className="header-tools"><label className="theme-choice"><span>Theme</span><select aria-label="Theme" value={theme} onChange={(event) => chooseTheme(event.target.value as Theme)}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label><button onClick={copy}>Copy view link</button><span className="sr-only" role="status">{copyStatus}</span></div></header>
    <div className="source-context"><span><span className={atlas.source.allSourceMatches ? 'pass-glyph' : ''} aria-hidden="true">{atlas.source.allSourceMatches ? '✓' : '○'}</span> {atlas.source.allSourceMatches ? '5/5 source hashes match E0018' : 'Source qualification unavailable'}</span><span>Main snapshot <code>{short(atlas.source.mainSnapshot)}</code> · qualified RTL <code>{short(atlas.source.revision)}</code></span><span className="context-limit">Schematic / reference / evidence — no live device</span></div>
    <main id="main-content" tabIndex={-1}>{location.view === 'architecture' ? <Architecture location={location} navigate={navigate} /> : location.view === 'cycles' ? <Cycles location={location} navigate={navigate} /> : location.view === 'evidence' ? <EvidenceView location={location} navigate={navigate} /> : <Progress />}</main>
    <footer><span>M1 physical: NOT EVALUATED</span><span>M0 owner fluency: {atlas.learning.m0Fluency}</span><span>PR8: draft / not merged at snapshot</span><a href={atlas.repository} target="_blank" rel="noreferrer">Repository ↗</a></footer>
  </>;
}
