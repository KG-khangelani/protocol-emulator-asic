import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { buildAtlas, repoRoot } from '../tools/export_atlas.mjs';
const sha = (raw) => createHash('sha256').update(raw).digest('hex');
const candidate = JSON.parse(readFileSync(resolve(repoRoot, 'evidence/E0042-sram-prefetch-screen/candidate.json')));
const overrides = {};
for (const [name, expected] of Object.entries(candidate.source_sha256)) {
  const raw = readFileSync(resolve(repoRoot, 'build/g2-sram-candidate-01/src', name));
  assert.equal(sha(raw), expected);
  overrides['src/' + name] = raw.toString();
}
const data = buildAtlas(repoRoot, overrides);
assert.deepEqual(data.modules.map((m) => m.stateBits), [0, 184, 128, 25, 16]);
assert.equal(data.totalStateBits, 353);
assert.deepEqual(data.storage, { logicalWords: 128, memoryBits: 8192, interfaceId: '0x22' });
assert.equal(data.source.allSourceMatches, false);
assert.equal(data.physical.status, 'NOT_EVALUATED');
assert.equal(data.relations.find((r) => r.id === 'engine-program').wire, 'prefetch_pc');
assert.throws(() => buildAtlas(repoRoot, { ...overrides,
  'src/project.v': overrides['src/project.v'].replace('.prefetch_pc(prefetch_pc)', '.prefetch_pc(wrong_signal)') }), /wiring mismatch/);
const invalid = buildAtlas(repoRoot, { ...overrides, 'tools/production-profile.json': '{}' });
assert.equal(invalid.physical.status, 'NOT_VERIFIED');
assert.equal(invalid.source.allSourceMatches, false);
const out = resolve(repoRoot, 'build/g2-sram-atlas-preparation-01');
mkdirSync(out, { recursive: true });
writeFileSync(resolve(out, 'candidate-data.json'), JSON.stringify(data, null, 2) + '\n');
writeFileSync(resolve(out, 'source-check.json'), JSON.stringify({ status: 'PASS_SRAM_STATE_ACCOUNTING_WITHOUT_QUALIFICATION',
  source_sha256: candidate.source_sha256, register_bits: 353, memory_bits: 8192, logical_words: 128,
  controls: ['wrong-prefetch-wire-rejected', 'invalid-profile-cannot-borrow-old-qualification'],
  scope: 'Actual retained candidate sources, data export only; not production adoption.' }, null, 2) + '\n');
console.log('PASS_SRAM_STATE_ACCOUNTING_WITHOUT_QUALIFICATION');
