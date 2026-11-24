// SPDX-License-Identifier: Apache-2.0
const fs = require("node:fs");
const path = require("node:path");
const toolRoot = path.resolve(process.argv[2]);
const {RP2040} = require(path.join(toolRoot, "cjs", "rp2040.js"));
const plan = JSON.parse(fs.readFileSync(0, "utf8"));
const PIO = 0x50200000;

function execute(test, words) {
    const chip = new RP2040();
    const pio = chip.pio[0];
    const sm = pio.machines[0];
    pio.run = () => {};
    const accesses = [];
    function write(name, address, value) {
        chip.writeUint32(address, value >>> 0);
        accesses.push([name, "write", address, value >>> 0]);
    }
    function read(name, address) {
        const value = chip.readUint32(address) >>> 0;
        accesses.push([name, "read", address, value]);
        return value;
    }
    function output() {
        let oe = 0;
        for (let i = 0; i < 8; i++) oe |= Number(chip.gpio[i].outputEnable) << i;
        if (oe & ~8) throw new Error("PIO drove a requester or unrelated GPIO");
        return oe ? Number(chip.gpio[3].outputValue) + 1 : 0;
    }
    write("disable_restart", PIO, 0x10);
    for (let pin = 0; pin < 4; pin++) {
        write("pio_gpio", 0x40014004 + 8 * pin, 6);
        write("input_pad", 0x4001c004 + 4 * pin, 0x52);
    }
    write("clock_divisor", PIO + 0xc8, 1 << 16);
    write("wrap_jump_cs", PIO + 0xcc, (2 << 24) | (31 << 12));
    write("input_sync", PIO + 0x38, 0);
    write("shift_in_left_out_right", PIO + 0xd0, 1 << 19);
    write("map_sck0_miso3", PIO + 0xdc, (1 << 26) | (1 << 20) | (3 << 5) | 3);
    write("release", PIO + 0xd8, 0xe080); // SET PINDIRS,0
    for (let addr = 0; addr < words.length; addr++) write("instruction", PIO + 0x48 + 4*addr, words[addr]);
    for (let addr = 0; addr < words.length; addr++) {
        write("forced_jump", PIO + 0xd8, addr);
        if (read("instruction_readback", PIO + 0xd8) !== words[addr] || output() !== 0) throw new Error("image readback/ownership");
    }
    write("entry", PIO + 0xd8, 0);
    const setup = accesses.length;
    write("enable", PIO, 1);
    let raw = 4; // CS high, SCK and MOSI low.
    let event = 0;
    let previousPort = output();
    const observed = [[0, previousPort]];
    const input = [4, 4, 4];
    for (let ns = 20; ns <= test.finish; ns += 20) {
        while (event < test.events.length && (test.events[event][0] < ns ||
                (test.events[event][0] === ns && !test.tieAfter))) {
            raw = test.events[event][1];
            event++;
        }
        const wasWaiting = sm.waiting;
        for (let pin = 0; pin < 3; pin++) chip.gpio[pin].setInputValue(Boolean((input[2] >> pin) & 1));
        if (!wasWaiting) sm.step();
        // An upstream GPIO change can complete a previously issued WAIT inside
        // setInputValue. That completion consumes this edge; the next fetch is later.
        else if (sm.waiting) sm.checkWait();
        input.pop();
        input.unshift(raw);
        const physical = previousPort;
        previousPort = output();
        if (physical !== observed[observed.length - 1][1]) observed.push([ns, physical]);
    }
    if (accesses.length !== setup + 1) throw new Error("mid-frame host access");
    return {setup, observed, operations: test.retainHost ? accesses : null};
}
const rows = plan.cases.map(test => execute(test, plan.images[test.kind]));
process.stdout.write(JSON.stringify(rows));
