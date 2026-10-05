// SPDX-License-Identifier: Apache-2.0
// Independent inspection model of SET/WAIT/HALT only, never a device driver.
export type Machine = { pc: number; state: 'RUN' | 'WAIT' | 'HALT' | 'FAULT'; waitLeft: number; gpio: number; oe: number };
export type Instruction = { kind: 'SET'; mask: number; value: number; oe: number } | { kind: 'WAIT'; count: number } | { kind: 'HALT' } | { kind: 'INVALID'; reason: string };
export const resetState = (): Machine => ({ pc: 0, state: 'RUN', waitLeft: 0, gpio: 0, oe: 0 });
export const wordHex = (word: number) => `0x${word.toString(16).padStart(8, '0').toUpperCase()}`;
export function decodeWord(word: number): Instruction {
  if (!Number.isSafeInteger(word) || word < 0 || word > 0xffffffff) return { kind: 'INVALID', reason: 'Not an unsigned 32-bit word' };
  const opcode = word >>> 30;
  if (opcode === 0 && (word & 0x3f000000) === 0) return { kind: 'SET', mask: (word >>> 16) & 255, value: (word >>> 8) & 255, oe: word & 255 };
  if (opcode === 1 && (word & 0x3fff0000) === 0) return { kind: 'WAIT', count: word & 0xffff };
  if (word === 0x80000000) return { kind: 'HALT' };
  return { kind: 'INVALID', reason: opcode === 3 ? 'Opcode outside this reference subset' : 'Reserved bits or unsupported extension' };
}
export function nextState(previous: Machine, program: readonly number[], rstN = true, ena = true): Machine {
  if (!rstN) return resetState();
  const next = { ...previous };
  if (!ena || next.state === 'HALT' || next.state === 'FAULT') return next;
  if (next.state === 'WAIT') {
    if (next.waitLeft > 1) next.waitLeft--;
    else { next.waitLeft = 0; next.pc++; next.state = 'RUN'; }
    return next;
  }
  const decoded: Instruction = next.pc < program.length ? decodeWord(program[next.pc]) : { kind: 'INVALID', reason: 'Fetch outside declared program' };
  if (decoded.kind === 'INVALID') { next.state = 'FAULT'; next.waitLeft = 0; }
  if (decoded.kind === 'HALT') { next.state = 'HALT'; next.waitLeft = 0; }
  if (decoded.kind === 'SET') {
    next.gpio = ((next.gpio & ~decoded.mask) | (decoded.value & decoded.mask)) & 255;
    next.oe = ((next.oe & ~decoded.mask) | (decoded.oe & decoded.mask)) & 255;
    next.pc++; next.waitLeft = 0;
  }
  if (decoded.kind === 'WAIT') {
    next.waitLeft = decoded.count;
    if (decoded.count === 0) next.pc++;
    else next.state = 'WAIT';
  }
  return next;
}
export const exampleProgram = (count = 1) => [0x00010101, 0x40000000 + count, 0x80000000];
export function describe(word: number) {
  const decoded = decodeWord(word);
  if (decoded.kind === 'SET') return `SET mask=${decoded.mask.toString(16).padStart(2, '0')} value=${decoded.value.toString(16).padStart(2, '0')} oe=${decoded.oe.toString(16).padStart(2, '0')}`;
  if (decoded.kind === 'WAIT') return `WAIT(${decoded.count})`;
  if (decoded.kind === 'INVALID') return `INVALID · ${decoded.reason}`;
  return 'HALT';
}
