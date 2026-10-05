// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from 'react';
import { atlas } from './data';

export type View = 'architecture' | 'cycles' | 'evidence' | 'progress';
export type Location = { view: View; module: string; relation: string; signals: boolean; zoom: number; evidence: string; edge: number };
export function readLocation(): Location {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const number = (key: string, fallback: number, min: number, max: number) => {
    const value = Number(params.get(key) ?? fallback);
    return Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;
  };
  const view = params.get('view') ?? 'architecture';
  const module = params.get('module') ?? 'engine';
  const relation = params.get('relation') ?? '';
  const evidence = params.get('evidence') ?? 'E0018';
  return {
    view: (['architecture', 'cycles', 'evidence', 'progress'].includes(view) ? view : 'architecture') as View,
    module: atlas.modules.some((item) => item.id === module) ? module : 'engine',
    relation: atlas.relations.some((item) => item.id === relation) ? relation : '',
    signals: params.get('signals') !== '0', zoom: number('zoom', 1, .8, 1.4),
    evidence: atlas.evidence.some((item) => item.id === evidence) ? evidence : 'E0018',
    edge: Math.floor(number('edge', 0, 0, 65540)),
  };
}
export function useLocation() {
  const [location, setLocation] = useState(readLocation);
  useEffect(() => {
    const handler = () => setLocation(readLocation());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);
  const navigate = (patch: Partial<Location>) => {
    const next = { ...readLocation(), ...patch };
    const params = new URLSearchParams({ view: next.view, module: next.module, relation: next.relation, signals: next.signals ? '1' : '0', zoom: String(next.zoom), evidence: next.evidence, edge: String(next.edge) });
    window.location.hash = params.toString();
    setLocation(next);
  };
  return [location, navigate] as const;
}
