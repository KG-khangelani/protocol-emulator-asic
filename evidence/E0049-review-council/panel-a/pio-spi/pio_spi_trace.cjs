// SPDX-License-Identifier: Apache-2.0
// Read one JSON case on stdin and return public-pin/FIFO/IRQ observations.
const fs = require("node:fs");
const path = require("node:path");
const tools = path.resolve(process.argv[2]);
const { RP2040 } = require(path.join(tools, "cjs", "rp2040.js"));
const experiment = JSON.parse(fs.readFileSync(0, "utf8"));
const { ClockPeer } = require("./clock_peer.cjs");
const chip = new RP2040();
const pio = chip.pio[0];
const sm = pio.machines[0];
const io = chip.gpio;
const PIO = 0x50200000;
let operations = [];
function write(group, address, value) {
    operations.push([group, "w", address >>> 0, value >>> 0]);
    chip.writeUint32(address >>> 0, value >>> 0);
}
function read(group, address) {
    const value = chip.readUint32(address >>> 0) >>> 0;
    operations.push([group, "r", address >>> 0, value]);
    return value;
}
function portState() {
    let outputs = 0;
    let enables = 0;
    for (let pin = 0; pin < 8; pin++) {
        outputs |= Number(io[pin].outputValue) << pin;
        enables |= Number(io[pin].outputEnable) << pin;
    }
    return [outputs, enables];
}

// Substitute a fixture clock for the library's batch scheduler. Neither its
// decoder nor its instruction-delay counter is modified.
pio.run = () => {};
function runCase(testcase, cold) {
    operations = [];
    const peer = testcase.peer ? new ClockPeer(testcase.peer.mode, testcase.order, testcase.peer.rx, testcase.peer.delays) : null;
    write("disable_restart", PIO, 0x10);
    if (!cold) {
        const previousFstat = read("previous_fstat", PIO + 4);
        const previousIrq = read("previous_irq", PIO + 0x30);
        if (!(previousFstat & 0x100) || !(previousIrq & 1)) throw new Error("prior result was pending or lacked completion");
        write("release_previous_dirs", PIO + 0xd8, 0xf080);
        if (portState()[1] !== 0) throw new Error("pins still active on mode change");
    }
    for (let pin = 0; pin < 4; pin++) {
        const invert = pin === 2 ? (testcase.cpol ^ Number(testcase.wrongPolarity)) << 8 : 0;
        if (cold || pin === 2) write("gpio_mux", 0x40014004 + 8 * pin, 6 | invert);
        if (cold) write("gpio_pad", 0x4001c004 + 4 * pin, 0x52);
    }
    if (cold) {
        write("clock_divisor", PIO + 0xc8, 1 << 16);
        write("sm_exec", PIO + 0xcc, 31 << 12);
        write("input_synchronization", PIO + 0x38, testcase.bypass ? 2 : 0);
    }
    const shiftDirections = testcase.order === 0 ? ((1 << 18) | (1 << 19)) : 0;
    const autopush = testcase.manualPush ? 0 : 1 << 16;
    write("sm_shift", PIO + 0xd0, (8 << 20) | autopush | shiftDirections);
    const groups = (2 << 29) | (4 << 26) | (1 << 20) | (1 << 15) | (2 << 10);
    if (cold) {
        write("pin_groups", PIO + 0xdc, groups);
        write("clear_all_dirs", PIO + 0xd8, 0xf080);  // SET PINDIRS,0 SIDE 2
    }
    write("idle_output_latches", PIO + 0xd8, 0xf008); // SET PINS,8 SIDE 2
    if (portState()[1] !== 0) throw new Error("chip drives during load");
    for (let address = 0; cold && address < testcase.words.length; address++) {
        write("program", PIO + 0x48 + 4 * address, testcase.words[address]);
    }
    for (let address = 0; cold && address < testcase.words.length; address++) {
        write("readback_jump", PIO + 0xd8, 0x1000 | address); // forced JMP SIDE 2, idle
        if (read("readback_word", PIO + 0xd8) !== testcase.words[address]) throw new Error("readback");
        if (portState()[1] !== 0) throw new Error("drive during verification");
    }
    write("restore_pc", PIO + 0xd8, 0x1000 | (testcase.entry || 0));
    write("counter_seed", PIO + 0xd8, 0xf047); // SET Y,7 SIDE 2
    write("tx_fifo", PIO + 0x10, testcase.order === 0 ? testcase.tx : testcase.tx << 24);
    write("force_pull", PIO + 0xd8, 0x90a0); // PULL BLOCK SIDE 2
    write("clear_irq", PIO + 0x30, 1);
    if (testcase.primed) write("prelaunch_idle_directions", PIO + 0xd8, 0xf08c); // SET PINDIRS,12 SIDE 2
    if (!(pio.readUint32(4) & 0x100) || (pio.readUint32(0x30) & 1)) throw new Error("stale FIFO or IRQ at launch");
    const setupCount = operations.length;
    write("launch", PIO, 1);
    if (!sm.enabled) throw new Error("reported SM not enabled");
    const postLaunchOperationCount = operations.length;
    const pinPipeline = portState(); // Post-readback configuration is settled before launch.
    let registeredOutputs = pinPipeline;
    const inputPipeline = Array(testcase.inputStages).fill(true);
    const rows = [];
    let nextIssue = 1;
    function observe(port) {
        // These are non-mutating fixture monitors. A consuming host does not have
        // to poll these registers each tick to operate the transfer.
        const valid = (pio.readUint32(0x004) & 0x100) === 0;
        const irq = (pio.readUint32(0x030) & 1) !== 0;
        rows.push(port[0], port[1], Number(valid) | (Number(irq) << 1));
    }
    observe(pinPipeline);
    if (peer) peer.observe(0, ...pinPipeline);
    const targetRaw = [1];
    let stable = true;
    let terminalSnapshot = null;
    for (let edge = 1; edge <= testcase.finish + 400; edge++) {
        const raw = peer ? Boolean(peer.atCoreEdge(edge)) : testcase.raw[Math.min(edge, testcase.raw.length - 1)] === "1";
        if (peer && edge <= testcase.finish) targetRaw.push(Number(raw));
        if (edge === nextIssue) {
            io[1].setInputValue(inputPipeline[inputPipeline.length - 1]);
            const before = sm.cycles;
            sm.step();
            const duration = sm.cycles - before;
            if (sm.waiting || duration < 1 || duration > 8) throw new Error("SM stalled or delay outside range at edge " + edge);
            nextIssue = edge + duration;
        }
        inputPipeline.pop();
        inputPipeline.unshift(raw);
        const newOutputs = portState();
        const physical = testcase.outputStages ? registeredOutputs : newOutputs;
        registeredOutputs = newOutputs;
        if (peer) peer.observe(edge, ...physical);
        observe(physical);
        const row = rows.slice(-3);
        if (edge === testcase.finish) terminalSnapshot = row;
        if (edge > testcase.finish && row.some((x, n) => x !== terminalSnapshot[n])) stable = false;
    }
    if (operations.length !== postLaunchOperationCount) throw new Error("host service before terminal observation");
    const endStatus = read("terminal_irq", PIO + 0x30);
    const finalWord = read("terminal_rx_fifo", PIO + 0x20);
    const afterPopEmpty = (pio.readUint32(0x004) & 0x100) !== 0;
    const receiveByte = testcase.order === 0 ? finalWord >>> 24 : finalWord & 255;
    const counts = {};
    for (const [group] of operations) counts[group] = (counts[group] || 0) + 1;
    const result = { setupCount, counts, receiveByte, fifoWord: finalWord, afterPopEmpty, endStatus, stable,
        publicRows: Buffer.from(rows.slice(0, 3 * (testcase.finish + 1))).toString("base64") };
    if (testcase.retainHost) result.operations = operations;
    if (peer) {
        result.peerResult = peer.result();
        result.targetRaw = targetRaw.join("");
    }
    return result;
}
if (experiment.batch) {
    const results = experiment.batch.map((entry, index) => runCase(entry, index === 0));
    process.stdout.write(JSON.stringify(results));
} else {
    process.stdout.write(JSON.stringify(runCase(experiment, true)));
}
