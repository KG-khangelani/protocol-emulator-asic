// SPDX-License-Identifier: Apache-2.0
// Drives Wokwi's pinned PIO decoder through public RP2040 registers.
const fs = require("node:fs");
const path = require("node:path");
const [toolsDir, hexPath, delayArg, widthArg, stuckArg, parasiteArg, commandArg, corruptArg] = process.argv.slice(2);
const { RP2040 } = require(path.join(path.resolve(toolsDir), "cjs", "rp2040.js"));
const program = fs.readFileSync(hexPath, "ascii").trim().split(/\s+/).map(word => parseInt(word, 16));
if (program.length !== 32 || program.some(word => !Number.isInteger(word) || word < 0 || word > 0xffff)) {
    throw new Error("unexpected assembled program");
}
const chip = new RP2040();
const pio = chip.pio[0];
const sm = pio.machines[0];
const io = chip.gpio;
const PIO = 0x50200000;
const IO = 0x40014000;
const PADS = 0x4001c000;
const ops = [];
function write(group, address, value) {
    ops.push([group, "write", address >>> 0, value >>> 0]);
    chip.writeUint32(address >>> 0, value >>> 0);
}
function read(group, address) {
    const value = chip.readUint32(address >>> 0) >>> 0;
    ops.push([group, "read", address >>> 0, value]);
    return value;
}

// The published library's default scheduler batches 1000 instructions per
// JavaScript turn. Supply system edges in order so the external peer can act
// between instructions. Its instruction decoder and delay counter stay intact.
pio.run = () => {};
write("disable_restart_sm", PIO, 0x10);
for (let pin = 0; pin < 4; pin++) {
    write("gpio_mux", IO + 4 + 8 * pin, 6);
    write("gpio_pad", PADS + 4 + 4 * pin, 0x52); // input/Schmitt enabled, no internal pulls
}
write("clock_divider", PIO + 0xc8, 50 << 16);  // 50 MHz / 50 yields 1 us
write("sm_exec", PIO + 0xcc, (1 << 29) | (31 << 12));
write("sm_shift", PIO + 0xd0, (16 << 25) | (1 << 19));
write("pin_groups_init", PIO + 0xdc, (1 << 29) | (4 << 26));
write("clear_gpio_dirs", PIO + 0xd8, 0xe080); // SET PINDIRS, 0  SIDE 0
write("clear_gpio_outs", PIO + 0xd8, 0xe000); // SET PINS, 0     SIDE 0
write("pin_groups_run", PIO + 0xdc, (1 << 29) | (3 << 26) | (1 << 5));
for (let address = 0; address < program.length; address++) {
    const value = program[address] ^ (Number(corruptArg) && address === 0 ? 1 : 0);
    write("program_words", PIO + 0x48 + 4 * address, value);
}
for (let address = 0; address < program.length; address++) {
    write("readback_jumps", PIO + 0xd8, address);
    if (read("readback_words", PIO + 0xd8) !== program[address]) {
        console.log("READBACK_MISMATCH " + address);
        process.exit(12);
    }
}
write("restore_pc", PIO + 0xd8, 0);
write("command_fifo", PIO + 0x10, parseInt(commandArg, 16));
write("force_pull", PIO + 0xd8, 0x80a0); // PULL BLOCK SIDE 0
const prelaunchOperations = ops.length;
write("enable_sm", PIO, 1);
if (!sm.enabled) throw new Error("public launch failed");
console.log("HOST " + JSON.stringify(ops));
console.log("LOAD " + prelaunchOperations);

const delay = Number(delayArg) * 50;
const width = Number(widthArg) * 50;
const stuck = Number(stuckArg) !== 0;
const parasite = Number(parasiteArg) !== 0;
let issueAt = 1;
let pulse = -1;
let fall = -1;
let resetRelease = -1;
let targetLow = false;
let driven = false;
let stage1 = true;
let stage2 = true;
let commandSeen = 0;
let finish = null;
for (let edge = 1; edge <= 125000; edge++) {
    const sampledRaw = !driven && !targetLow;
    if (edge === issueAt) {
        // The emulator reads GPIO directly. Model the declared 2-system-clock
        // synchronizer externally. The 1 MHz PIO instruction issue is slower.
        io[0].setInputValue(stage2);
        const before = sm.cycles;
        sm.step();
        const cost = sm.cycles - before;
        if (sm.waiting || cost < 1 || cost > 16) throw new Error("stalled or invalid instruction time");
        issueAt = edge + 50 * cost;
    }
    stage2 = stage1;
    stage1 = sampledRaw;
    const current = io[0].outputEnable;
    if (current && io[0].outputValue) throw new Error("actively drove DQ high");
    if (current !== driven) {
        console.log("DRIVE " + edge + " " + Number(current));
        if (current) {
            pulse++;
            fall = edge;
        } else if (pulse === 0) {
            resetRelease = edge;
        }
        driven = current;
    }
    if (pulse >= 1 && pulse <= 16 && edge - fall === 1500) {
        const bit = Number(!driven && !targetLow);
        commandSeen |= bit << (pulse - 1);
        console.log("WIREBIT " + (pulse - 1) + " " + bit);
    }
    if (pulse === 0 && resetRelease >= 0) {
        const age = edge - resetRelease;
        targetLow = stuck || (age >= delay && age < delay + width);
    } else if (pulse === 17 && commandSeen === 0xb4cc) {
        const age = edge - fall;
        targetLow = parasite && age >= 500 && age < 2250;
    } else {
        targetLow = false;
    }
    if (io[3].outputEnable && io[3].outputValue) {
        if (driven || !io[1].outputEnable || !io[2].outputEnable) throw new Error("incomplete terminal marker");
        const marker = Number(io[1].outputValue) | (Number(io[2].outputValue) << 1);
        if (!finish) {
            finish = { edge, marker };
            console.log("HALT " + edge + " " + marker);
        } else if (marker !== finish.marker) {
            throw new Error("unstable terminal marker");
        }
    } else if (finish) {
        throw new Error("terminal marker was lost");
    }
    if (finish && edge - finish.edge >= 500) {
        console.log("HOLD 500");
        process.exit(0);
    }
}
throw new Error("runtime cap exceeded");
