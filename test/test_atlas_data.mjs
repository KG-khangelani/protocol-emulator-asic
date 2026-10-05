/* SPDX-License-Identifier: Apache-2.0 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { buildAtlas, repoRoot } from '../tools/export_atlas.mjs';

test('actual nonblocking state totals and grouping match the qualified source', () => {
  const data = buildAtlas();
  assert.equal(data.totalStateBits, 410);
  assert.deepEqual(data.modules.map((module) => module.stateBits), [0, 261, 108, 25, 16]);
  assert.equal(data.source.allSourceMatches, true);
  assert.equal(data.source.matchCount, 5);
  assert.equal(data.clockTargetHz, 50_000_000);
  assert.equal(data.tileAllocation, '6x4');
  assert.equal(data.evidence.find((item) => item.id === 'E0016').status, 'PASS');
});
test('synchronization, fetch, TX/RX and GPIO dependencies are actual named connections', () => {
  const data = buildAtlas();
  assert.equal(data.relations.find((item) => item.id === 'sync-engine').wire, 'sampled_inputs');
  assert.equal(data.relations.find((item) => item.id === 'raw-sync').from, 'top');
  assert.equal(data.relations.some((item) => item.from === 'data' && item.to === 'sync'), false);
  assert.equal(data.modules.find((item) => item.id === 'program').note.includes('Writable'), true);
});
test('changed RTL does not retain a current-source PASS', () => {
  const path = 'src/m1_engine.v';
  const source = readFileSync(resolve(repoRoot, path), 'utf8');
  const data = buildAtlas(repoRoot, { [path]: `${source}\n// retained source-drift seed\n` });
  assert.equal(data.source.allSourceMatches, false);
  assert.equal(data.evidence.find((item) => item.id === 'E0018').currentSourceMatches, false);
});
test('incorrect wiring is rejected rather than drawn as a fabricated relation', () => {
  const path = 'src/project.v';
  const source = readFileSync(resolve(repoRoot, path), 'utf8');
  assert.throws(() => buildAtlas(repoRoot, { [path]: source.replace('.sampled_in(sampled_inputs)', '.sampled_in(wrong_signal)') }), /wiring mismatch/);
});
test('missing or corrupted evidence cannot assert verified qualification', () => {
  for (const replacement of [null, '{}']) {
    const data = buildAtlas(repoRoot, { 'evidence/E0018-uart-rx-public/ci-manifest.json': replacement });
    assert.equal(data.source.evidenceIntegrity, false);
    assert.equal(data.evidence.find((item) => item.id === 'E0018').status, 'NOT_VERIFIED');
  }
});
test('archived physical evidence, owner learning and deferred branch remain distinct', () => {
  const data = buildAtlas();
  assert.equal(data.evidence.find((item) => item.id === 'E0010').archived, true);
  assert.equal(data.learning.m0Fluency, 'PENDING');
  assert.equal(data.deferred.status, 'DRAFT / NOT MERGED');
  assert.ok(data.hypotheses.every((item) => item.status === 'UNPROVEN'));
  assert.equal(JSON.stringify(data).includes('libfile_'), false);
});
test('hypothesis status comes from the ledger, not a hardcoded UI promotion', () => {
  const path = 'docs/research-ledger.md';
  const source = readFileSync(resolve(repoRoot, path), 'utf8');
  const replacement = source.replace(/^\| H1 \|.*$/m, '| H1 | altered fixture | unqualified | Not evaluated |');
  assert.equal(buildAtlas(repoRoot, { [path]: replacement }).hypotheses[0].status, 'NOT EVALUATED');
});
test('missing TX manifest cannot retain recorded TX PASS or invent tool identities', () => {
  const data = buildAtlas(repoRoot, { 'evidence/E0016-uart-tx-8n1/ci-manifest.json': null });
  const tx = data.evidence.find((item) => item.id === 'E0016');
  assert.equal(tx.status, 'NOT_VERIFIED');
  assert.deepEqual(tx.tools, []);
});
test('legacy TX qualification requires its actual retained run outcomes and cannot override explicit failure', () => {
  const path = 'evidence/E0016-uart-tx-8n1/qualification.json';
  const source = JSON.parse(readFileSync(resolve(repoRoot, path), 'utf8'));
  for (const replacement of [{ ...source, implementation_ci: 'FAIL' }, { ...source, runs: {} }]) {
    assert.equal(buildAtlas(repoRoot, { [path]: JSON.stringify(replacement) }).evidence.find((item) => item.id === 'E0016').status, 'NOT_VERIFIED');
  }
});
