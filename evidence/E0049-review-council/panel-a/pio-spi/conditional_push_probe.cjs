// SPDX-License-Identifier: Apache-2.0
// Force documented RP2040 instructions, then inspect public FIFO status and level.
const fs = require("node:fs");
const path = require("node:path");
const tools = path.resolve(process.argv[2]);
const { RP2040 } = require(path.join(tools, "cjs", "rp2040.js"));
const PIO = 0x50200000;
const tests = [
    {name: "one_manual_conditional", count: 1, automatic: false, conditional: true, expected: 0},
    {name: "eight_manual_conditional", count: 8, automatic: false, conditional: true, expected: 1},
    {name: "one_automatic_conditional", count: 1, automatic: true, conditional: true, expected: 0},
    {name: "one_manual_unconditional", count: 1, automatic: false, conditional: false, expected: 1},
];
const results = [];
for (const test of tests) {
    const chip = new RP2040();
    chip.writeUint32(PIO, 0x10);
    chip.writeUint32(PIO + 0xd0, (8 << 20) | (test.automatic ? 1 << 16 : 0));
    chip.writeUint32(PIO + 0xd8, 0x4060 | test.count); // IN NULL, n
    const before = (chip.readUint32(PIO + 0x0c) >>> 4) & 0xf;
    chip.writeUint32(PIO + 0xd8, test.conditional ? 0x8060 : 0x8020); // PUSH IFFULL BLOCK or PUSH BLOCK
    const after = (chip.readUint32(PIO + 0x0c) >>> 4) & 0xf;
    const empty = Boolean(chip.readUint32(PIO + 0x04) & 0x100);
    if (before !== 0 || empty !== (after === 0)) throw new Error("inconsistent public FIFO level");
    results.push({...test, before, observed: after, expected_matches: after === test.expected});
}
if (results.map(r => r.observed).join(",") !== "1,1,0,1") throw new Error("decoder behavior changed");
const output = JSON.stringify({node: process.version, observations: results}, null, 2) + "\n";
if (process.argv[3]) fs.writeFileSync(process.argv[3], output, {flag: "wx"});
else process.stdout.write(output);
