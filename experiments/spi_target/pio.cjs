// SPDX-License-Identifier: Apache-2.0
// The independent requester supplies every edge. Observe only emulated port
// levels, directions and the architected IRQ. All host MMIO is before traffic.
const fs = require("node:fs");
const path = require("node:path");
const [toolRoot, runDir] = process.argv.slice(2).map(p => path.resolve(p));
const {RP2040} = require(path.join(toolRoot, "cjs", "rp2040.js"));
const {GPIOPinState} = require(path.join(toolRoot, "cjs", "gpio-pin.js"));
const PIO = 0x50200000;
const packed = 0x523ca700;
const words = fs.readFileSync(path.join(runDir, "target.hex"), "utf8").trim()
    .split(/\s+/).map(s => parseInt(s, 16));
if (words.length > 32) throw new Error("PIO instruction budget");

function simulate(test) {
    const chip = new RP2040();
    const pio = chip.pio[0];
    const sm = pio.machines[0];
    pio.run = () => {};  // The fixture supplies one execution opportunity per 20 ns.
    const mmio = [];
    function write(address, value) {
        chip.writeUint32(address, value >>> 0);
        mmio.push(["w", address, value >>> 0]);
    }
    function read(address) {
        const value = chip.readUint32(address) >>> 0;
        mmio.push(["r", address, value]);
        return value;
    }
    function pins() {
        let oe = 0;
        for (let i = 0; i < 8; i++) oe |= Number(chip.gpio[i].outputEnable) << i;
        if (oe & ~0x38) throw new Error("requester or reserved pin driven");
        // The requester's external weak pulldown resolves an undriven MISO to zero.
        const miso = Number(chip.gpio[3].value === GPIOPinState.High);
        const marker = Number(chip.gpio[4].value === GPIOPinState.High)
            + 2 * Number(chip.gpio[5].value === GPIOPinState.High);
        return [oe, miso, marker, Number(Boolean(pio.irq & 1))];
    }
    write(PIO, 0x10);
    for (let pin = 0; pin < 6; pin++) {
        write(0x40014004 + 8 * pin, 6);
        write(0x4001c004 + 4 * pin, 0x52);
    }
    write(PIO + 0xc8, 1 << 16);
    write(PIO + 0xcc, (1 << 30) | (1 << 29) | (2 << 24) | (31 << 12));
    write(PIO + 0x38, 0);
    write(PIO + 0xd0, 0); // Shift both registers left. No automatic push or pull.
    write(PIO + 0xdc, (2 << 29) | (2 << 26) | (1 << 20) | (1 << 15) | (3 << 10) | (4 << 5) | 3);
    write(PIO + 0xd8, 0xe083); // SET PINDIRS,3 on the two marker pins.
    write(PIO + 0x10, packed);
    write(PIO + 0xd8, 0x80a0); // PULL BLOCK
    write(PIO + 0xd8, 0xa047); // MOV Y,OSR
    write(PIO + 0xd8, 0xa0c2); // MOV ISR,Y
    write(PIO + 0xd8, 0x8000); // PUSH NOBLOCK
    if (read(PIO + 0x20) !== packed) throw new Error("constant readback");
    for (let i = 0; i < words.length; i++) write(PIO + 0x48 + 4 * i, words[i]);
    for (let i = 0; i < words.length; i++) {
        write(PIO + 0xd8, i);
        if (read(PIO + 0xd8) !== words[i] || (pins()[0] & 8)) throw new Error("instruction readback");
    }
    write(PIO + 0xd8, 0);
    write(PIO, 1);
    const count = mmio.length;
    const pipeline = [4, 4, 4];
    let raw = 4, event = 0, previous = pins();
    const rows = [[0, ...previous]];
    for (let ns = 10; ns <= test.finish; ns += 20) {
        while (event < test.events.length && test.events[event][0] <= ns) {
            raw = test.events[event++][1];
        }
        const wasWaiting = sm.waiting;
        for (let pin = 0; pin < 3; pin++) chip.gpio[pin].setInputValue(Boolean(pipeline[2] & (1 << pin)));
        if (!wasWaiting) sm.step();
        else if (sm.waiting) sm.checkWait();
        pipeline.pop();
        pipeline.unshift(raw);
        if (previous.some((v, i) => v !== rows[rows.length - 1][i + 1])) rows.push([ns, ...previous]);
        previous = pins();
    }
    if (event !== test.events.length || count !== mmio.length) throw new Error("incomplete or serviced transfer");
    return {rows, mmio};
}

const cases = JSON.parse(fs.readFileSync(path.join(runDir, "cases.json"), "utf8"));
const traces = {};
let operations;
for (const [name, test] of Object.entries(cases)) {
    const result = simulate(test);
    operations ??= result.mmio;
    if (JSON.stringify(operations) !== JSON.stringify(result.mmio)) throw new Error("cold setup differs");
    traces[name] = result.rows;
}
fs.writeFileSync(path.join(runDir, "pio.json"), JSON.stringify(traces));
fs.writeFileSync(path.join(runDir, "pio-host.json"), JSON.stringify(operations));
console.log(Object.keys(traces).length, "PIO trials,", operations.length, "cold MMIO operations per trial");
