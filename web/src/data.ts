// SPDX-License-Identifier: Apache-2.0
import data from './data/atlas.json';
export const atlas = data;
export type Module = typeof data.modules[number];
export type Relation = typeof data.relations[number];
export type Evidence = typeof data.evidence[number];
export const moduleById = (id: string) => atlas.modules.find((item) => item.id === id)!;
export const relationById = (id: string) => atlas.relations.find((item) => item.id === id);
export const short = (hash: string) => hash.slice(0, 8);
