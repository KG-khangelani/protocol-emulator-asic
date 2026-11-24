"""Cocotb study using only project ports, host controls, and the resolved fixture."""
import gzip
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time

from assembler import assemble, load_plan
from fixture_transport import run_bus
from i2c_oracle import Transaction, assess
from target import Target


OUT = Path(os.environ["RESIDENT_OUTPUT"])
ORIGINAL = Path("i2c_write_read.asm").read_text()
A = Transaction(address=0x52, tx=0x96, rx=0x69)
B = Transaction(address=0x2a, tx=0xd2, rx=0x3b)
CONDITION = os.environ.get("RESIDENT_CONDITION", "strict")


def canon(rows):
    return (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode()


def require(actual, expected, description):
    if actual != expected:
        raise AssertionError(f"{description}: observed {actual}, expected {expected}")


def compare_transactions(records, left, right, names):
    """Preserve the complete-trace comparison before testing the narrower projection."""
    if CONDITION == "strict":
        require(records[left], records[right], "warm/cold changed transaction")
        return
    traces = [json.loads(gzip.decompress((OUT / f"{name}-trace.json.gz").read_bytes())) for name in names]
    count = Counter()
    first = None
    invalid_rows = 0
    for i, (warm, cold) in enumerate(zip(*traces, strict=True)):
        differences = {key: [warm[key],cold[key]] for key in warm if warm[key] != cold[key]}
        if differences:
            if first is None:
                first = {"row":i, "tick":warm["t"], "valid":warm["rx_valid"], "differences":differences}
            count.update(differences.keys())
            require(set(differences), {"rx"}, "unexpected complete-trace difference")
            require((warm["rx_valid"],cold["rx_valid"]), (0,0), "different raw value was marked valid")
            invalid_rows += 1
    projected = [[dict(row,rx=row["rx"] if row["rx_valid"] else None) for row in trace] for trace in traces]
    require(projected[0],projected[1], "valid-gated observations")
    require(invalid_rows > 0, True, "raw-trace rejection retained")
    records[left + "_comparison"] = {"full_equal":False, "different_fields":dict(count), "first":first,
                                       "different_invalid_rows":invalid_rows, "total_rows":len(traces[0]),
                                       "valid_gated_sha256":hashlib.sha256(canon(projected[0])).hexdigest()}


class GuardRejected(ValueError):
    pass


class Host:
    def __init__(self, dut):
        self.dut = dut
        self.counters = Counter()
        self.actions = []
        self.session_image = None
        self.selector = None
        self.driving = False
        self.connected = False

    def begin(self):
        self.counters.clear()
        self.actions = []
        self.start_ps = int(get_sim_time(unit="ps"))

    def cost(self):
        return {"counts": dict(self.counters), "simulated_setup_ps": int(get_sim_time(unit="ps"))-self.start_ps}

    async def select(self, value):
        self.counters["selector_commands"] += 1
        if self.selector != value:
            self.counters["selector_value_changes"] += 1
        self.selector = value
        self.dut.ui_in.value = value
        await Timer(2, unit="ns")

    async def direction(self, enabled, data=0):
        if enabled:
            require(int(self.dut.uio_oe.value), 0, "harness checked chip released before host drive")
            require(self.connected, False, "external peer isolated before host drive")
            self.dut.host_data.value = data
            await Timer(2, unit="ns")
        if enabled != self.driving:
            self.counters["host_direction_changes"] += 1
            self.driving = enabled
            self.dut.host_drives.value = int(enabled)
            await Timer(2, unit="ns")

    async def peer(self, connected):
        if connected != self.connected:
            self.counters["peer_isolator_changes"] += 1
            if connected:
                require(self.driving, False, "host release before target connection")
                require(int(self.dut.uio_oe.value), 0, "harness checked chip release before target connection")
                require(int(self.dut.peer_pulls.value), 0, "target starts idle")
            self.dut.peer_connected.value = int(connected)
            self.connected = connected
            await Timer(2, unit="ns")

    async def tick(self, label):
        require(int(self.dut.ena.value), 1, "powered project")
        self.counters["clocked_steps"] += 1
        self.actions.append(label)
        await Timer(10, unit="ns")
        self.dut.clk.value = 1
        await Timer(10, unit="ns")
        self.dut.clk.value = 0
        await Timer(1, unit="ns")

    async def step(self, action, ui, data=0, drive=False, expected=None):
        expected = {} if expected is None else expected
        if not drive:
            await self.direction(False)
        await self.select(ui)
        if drive:
            await self.direction(True, data)
        if action == "flush_idle":
            await self.peer(True)
        if (ui & 0xc0) == 0x80:
            require(self.connected or self.driving, False, "ASIC read without other active drivers")
        await self.tick(action)
        for key, value in expected.items():
            port = "pads" if key == "uio_out" else key
            require(int(getattr(self.dut, port).value), value, f"{action}/{port}")
            self.counters["macro_oe_checks" if key == "uio_oe" else "pad_or_status_checks"] += 1

    async def exit_loader(self):
        # Clear load first, then choose normal status while the clock remains low.
        await self.select(0x67)
        require(int(self.dut.uo_out.value), 0x22, "transition identity")
        require(int(self.dut.uio_oe.value), 0, "transition release")
        await self.select(0)
        require(int(self.dut.uo_out.value), 0x20, "PC0 ready before first run edge")

    async def cold(self, image, case):
        self.begin()
        await self.peer(False)
        await self.direction(False)
        plan = load_plan(image, payloads={"TX0": 2*case.address, "TX1": case.tx})
        for row in plan["steps"]:
            self.dut.rst_n.value = row["rst_n"]
            ui = 0xe7 if row["action"] == "flush_idle" else row["ui_in"]
            await self.step(row["action"], ui, row["uio_in"], row["host_drives_uio"], row["expected"])
        await self.exit_loader()
        self.session_image = image["binary_sha256"]
        require(self.counters["clocked_steps"], 802, "cold steps")
        return self.cost()

    async def endpoint(self):
        fields = {}
        for selector, field in [(0, "status"), (0x66, "full_pc"), (0x63, "valid"),
                                (0x62, "rx"), (0x67, "interface")]:
            await self.select(selector)
            fields[field] = int(self.dut.uo_out.value)
            self.counters["unclocked_dedicated_guard_reads"] += 1
            if field == "status":
                fields["sensed_bus_and_marker_low5"] = int(self.dut.pads.value) & 0x1f
                self.counters["unclocked_pad_guard_reads"] += 1
        return fields

    async def park_and_length(self):
        await self.peer(False)
        await self.direction(False)
        await self.select(0x67)
        await self.step("park", 0xe7, expected={"uio_oe": 0, "uo_out": 0x20})
        await self.step("read_length", 0xa0, expected={"uio_oe": 255})
        return int(self.dut.pads.value)

    async def warm(self, image, previous, next_case):
        self.begin()
        if self.session_image != image["binary_sha256"]:
            raise GuardRejected("untrusted image custody")
        fields = await self.endpoint()
        wanted = {"status": 0xb3, "full_pc": 83, "valid": 1, "rx": previous.rx,
                  "interface": 0x22, "sensed_bus_and_marker_low5": 7}
        if fields != wanted:
            raise GuardRejected(f"terminal mismatch {fields}")
        length = await self.park_and_length()
        fields["length"] = length
        if length != 96:
            raise GuardRejected(f"wrong length {length}")
        for label, base, payload in [("TX0", 1, 2*next_case.address), ("TX1", 4, next_case.tx)]:
            await self.step("write_" + label, 0xe0 | base, payload, True, {"uio_oe": 0})
            await self.step("read_" + label, 0xa0 | base, expected={"uio_oe": 255, "uio_out": payload})
        for _ in range(2):
            await self.step("flush_idle", 0xe7, expected={"uio_oe": 0, "uo_out": 0x20})
        await self.exit_loader()
        require(self.counters["clocked_steps"], 8, "warm steps")
        return fields, self.cost(), list(self.actions)

    async def transaction(self, label, case):
        target = Target(case, response=690)
        rows = await run_bus(self.dut, target, bound_ticks=1000000, extended_pc=True)
        self.selector = 0  # fixture_transport ends its dedicated snapshot at normal status
        initial = next(i for i, row in enumerate(rows)
                       if row["oe"] == 28 and row["out"] == 0 and row["bus"] == 3)
        require(any(row["out"] & row["oe"] & 3 for row in rows[:initial+1]), False, "initial bus open drain")
        offset = rows[initial]["t"]
        trace = [dict(row, t=row["t"] - offset) for row in rows[initial:]]
        assessment = assess(trace, case)
        require(assessment["errors"], [], label + " independent I2C oracle")
        require(assessment["outcome"], "OK", label + " outcome")
        require((trace[-1]["state"], trace[-1]["pc"], trace[-1]["rx"], trace[-1]["rx_valid"]),
                ("HALT", 83, case.rx, 1), label + " completion")
        decoded = [entry["byte"] for entry in target.decoded]
        require(decoded, [case.address*2, case.tx, case.address*2 + 1], label + " wire decode")
        raw = canon(trace)
        (OUT / f"{label}-trace.json.gz").write_bytes(gzip.compress(raw, mtime=0))
        return {"trace_sha256": hashlib.sha256(raw).hexdigest(), "event_rows":len(trace),
                "decoded_address_data_readaddress":decoded, "returned_data":trace[-1]["rx"],
                "halt_tick_from_judged_idle":next(row["t"] for row in trace if row["state"]=="HALT"),
                "outcome":assessment["outcome"], "oracle_errors":assessment["errors"]}


@cocotb.test()
async def resident_write_read(dut):
    d = {"status":"INCOMPLETE"}
    host = Host(dut)
    try:
        await Timer(1, unit="ns")
        dut.rst_n.value = 0
        dut.clk.value = 0
        dut.ui_in.value = 0
        dut.host_data.value = 0
        dut.host_drives.value = 0
        dut.peer_connected.value = 0
        dut.peer_pulls.value = 0
        await Timer(2, unit="ns")
        image = assemble(ORIGINAL)
        catalog = next(e for e in json.loads(Path("examples.json").read_bytes())["examples"] if e["name"]=="i2c_write_read")
        require((image["words"],image["binary_sha256"]), (catalog["expected_words"],catalog["binary_sha256"]),
                "independent G4 catalog")
        alternate = assemble(ORIGINAL.replace("WAIT cycles=235", "WAIT cycles=238", 1))
        require([i for i,(x,y) in enumerate(zip(image["words"], alternate["words"], strict=True)) if x!=y], [1],
                "alternate changes only initial WAIT")
        d["image_sha256"], d["alternate_sha256"] = image["binary_sha256"], alternate["binary_sha256"]
        d["cold_A_setup"] = await host.cold(image, A)
        d["first_A"] = await host.transaction("first-A", A)
        d["A_endpoint"],d["warm_B_setup"],d["warm_actions"] = await host.warm(image, A, B)
        d["warm_B"] = await host.transaction("warm-B", B)
        # Fresh, actually reset and reloaded reference for the NEW payloads.
        d["cold_B_setup"] = await host.cold(image, B)
        d["cold_B"] = await host.transaction("cold-B", B)
        compare_transactions(d, "warm_B", "cold_B", ["warm-B", "cold-B"])
        d["B_endpoint"], d["repeat_B_setup"], _ = await host.warm(image, B, B)
        d["repeat_B"] = await host.transaction("repeat-B", B)
        compare_transactions(d, "repeat_B", "cold_B", ["repeat-B", "cold-B"])
        # Bank selection invalidates the image. Deliberately leave a stale software cookie.
        await host.peer(False)
        await host.direction(False)
        await host.select(0x67)
        await host.select(0xe7)
        await host.step("invalidate_bank", 0xe5, 0, True, {"uio_oe":0})
        await host.direction(False)
        await host.select(0x67)
        await host.select(0)
        try:
            await host.warm(image, B, A)
        except GuardRejected as exc:
            d["bank_invalidated_guard"] = {"reason":str(exc),"clocked_before_reject":host.counters["clocked_steps"],
                                           "actions":list(host.actions)}
            require(host.actions, [], "stale session produces no payload write or run")
            require("terminal mismatch" in str(exc), True, "external terminal guard caught invalidation")
        else:
            raise AssertionError("invalidated image accepted")
        await host.select(0)
        d["bank_invalidated_guard"]["observed_status"] = int(dut.uo_out.value)
        await host.select(0x67)
        await host.select(0xe7)
        await host.step("inspect_invalid_length", 0xa0, expected={"uio_oe":255})
        d["bank_invalidated_guard"]["observed_length"] = int(dut.pads.value)
        require((d["bank_invalidated_guard"]["observed_status"],d["bank_invalidated_guard"]["observed_length"]),
                (0,0), "invalidation clears ready and length")
        d["alternate_setup"] = await host.cold(alternate, B)
        d["alternate_B"] = await host.transaction("alternate-B", B)
        require(d["alternate_B"]["trace_sha256"] != d["cold_B"]["trace_sha256"], True, "different wire timing")
        require(d["alternate_B"]["halt_tick_from_judged_idle"] - d["cold_B"]["halt_tick_from_judged_idle"],
                12, "three extra project clocks across different image")
        # Connection loss invalidates custody even with a passing previous transaction.
        host.session_image = None
        try:
            await host.warm(image, B, A)
        except GuardRejected as exc:
            require(str(exc), "untrusted image custody", "lost session")
            require(sum(host.counters.values()), 0, "refuse before any host command")
            d["lost_session_guard"] = {"reason":str(exc),"issued_commands":0}
        else:
            raise AssertionError("untrusted session accepted")
        # In a separate diagnostic, record the endpoint and length the guard could observe.
        d["alternate_endpoint"] = await host.endpoint()
        d["alternate_endpoint"]["length"] = await host.park_and_length()
        require(d["B_endpoint"], d["alternate_endpoint"], "same-length image guard indistinguishability")
        d["status"] = "PASS_VALID_GATED_DIAGNOSTIC" if CONDITION == "valid-gated" else "PASS_WARM_COMBINED_I2C"
    except Exception as error:
        d["failure"] = str(error)
        raise
    finally:
        (OUT / "observations.json").write_text(json.dumps(d, indent=2)+"\n")
