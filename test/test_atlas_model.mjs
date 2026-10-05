// SPDX-License-Identifier: Apache-2.0
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { exampleProgram, nextState, resetState, decodeWord } from '../web/src/model.ts';

test('exact approved specimen aligns every post-edge field', () => {
  let machine = resetState();
  const expected = [[1, 'RUN', 0], [1, 'WAIT', 1], [2, 'RUN', 0], [2, 'HALT', 0]];
  for (const [pc, state, waitLeft] of expected) {
    machine = nextState(machine, exampleProgram());
    assert.deepEqual(machine, { pc, state, waitLeft, gpio: 1, oe: 1 });
  }
});
test('WAIT 0, 1, 2 and 65535 take exactly count subsequent accepted edges', () => {
  for (const count of [0, 1, 2, 65535]) {
    const program = [0x40000000 + count, 0x80000000];
    let machine = nextState(resetState(), program);
    for (let edge = 0; edge < count; edge++) {
      assert.equal(machine.state, 'WAIT');
      assert.equal(machine.waitLeft, count - edge);
      assert.deepEqual(nextState(machine, program, true, false), machine);
      machine = nextState(machine, program);
    }
    assert.equal(machine.pc, 1); assert.equal(machine.state, 'RUN');
    assert.equal(nextState(machine, program).state, 'HALT');
  }
});
test('reset wins from RUN/WAIT/HALT/FAULT even while disabled', () => {
  for (const state of ['RUN', 'WAIT', 'HALT', 'FAULT']) {
    const machine = { pc: 2, state, waitLeft: 12, gpio: 255, oe: 255 };
    assert.deepEqual(nextState(machine, [], false, false), resetState());
    assert.deepEqual(nextState(machine, [], true, false), machine);
  }
});
test('masked SET preserves every unselected value and direction bit', () => {
  for (let mask = 0; mask < 256; mask++) {
    const value = mask ^ 0xa5, oe = mask ^ 0x5a;
    const before = { ...resetState(), gpio: 0x3c, oe: 0xc3 };
    const after = nextState(before, [mask * 65536 + value * 256 + oe]);
    for (let bit = 0; bit < 8; bit++) {
      assert.equal((after.gpio >> bit) & 1, ((mask & (1 << bit) ? value : before.gpio) >> bit) & 1);
      assert.equal((after.oe >> bit) & 1, ((mask & (1 << bit) ? oe : before.oe) >> bit) & 1);
    }
  }
});
test('empty, corrupt, reserved and truncated programs fault without wrap', () => {
  for (const program of [[], [0x80000001], [0x01000000], [0x40010000], [0xc0000000]]) {
    const fault = nextState(resetState(), program);
    assert.deepEqual(fault, { ...resetState(), state: 'FAULT' });
    assert.deepEqual(nextState(fault, exampleProgram()), fault);
  }
  const end = nextState(resetState(), [0x00010101]);
  const fault = nextState(end, [0x00010101]);
  assert.deepEqual(fault, { pc: 1, state: 'FAULT', waitLeft: 0, gpio: 1, oe: 1 });
  assert.equal(decodeWord(-1).kind, 'INVALID');
});
test('HALT holds outputs and PC on every later accepted edge', () => {
  const before = { ...resetState(), gpio: 0xa5, oe: 0x5a };
  const halted = nextState(before, [0x80000000, 0]);
  assert.equal(halted.pc, 0); assert.equal(halted.state, 'HALT');
  for (let i = 0; i < 100; i++) assert.deepEqual(nextState(halted, [0x80000000, 0]), halted);
});

test('128 retained-seed programs agree with the separately decoded Python oracle on 8192 edges', () => {
  // Fixed seed is retained here; the oracle never receives JS decoder output.
  let seed = 0xa71a5206;
  const random = () => { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; return seed >>> 0; };
  const fixtures = [];
  for (let fixture = 0; fixture < 128; fixture++) {
    const words = [], decoded = [];
    for (let index = 0; index < 6; index++) {
      if (random() & 1) {
        const mask = random() & 255, value = random() & 255, oe = random() & 255;
        words.push(mask * 65536 + value * 256 + oe); decoded.push({ opcode: 'SET', mask, value, oe });
      } else {
        const count = random() & 3;
        words.push(0x40000000 + count); decoded.push({ opcode: 'WAIT', count });
      }
    }
    if (fixture % 3 === 0) { words.push(0x80000000); decoded.push({ opcode: 'HALT' }); }
    if (fixture % 3 === 1) { words.push(0x80000001); decoded.push({ opcode: 'INVALID' }); }
    const inputs = Array.from({ length: 64 }, (_, edge) => ({ rstN: edge !== 0 && (random() & 15) !== 0, ena: (random() & 3) !== 0 }));
    let state = resetState();
    const expected = inputs.map(({ rstN, ena }) => (state = nextState(state, words, rstN, ena)));
    fixtures.push({ decoded, inputs, expected });
  }
  const python = process.env.ATLAS_PYTHON ?? (process.platform === 'win32' ? 'python' : 'python3');
  const result = spawnSync(python, ['-B', fileURLToPath(new URL('../tools/atlas_model_oracle.py', import.meta.url))], {
    input: JSON.stringify(fixtures.map(({ decoded, inputs }) => ({ decoded, inputs }))), encoding: 'utf8', maxBuffer: 4 * 1024 * 1024,
  });
  assert.equal(result.status, 0, `Independent Python oracle unavailable/failed: ${result.error?.message ?? result.stderr}`);
  const actual = JSON.parse(result.stdout);
  fixtures.forEach((fixture, index) => assert.deepEqual(actual[index], fixture.expected, `Retained seed 0xa71a5206, program ${index}`));
});
