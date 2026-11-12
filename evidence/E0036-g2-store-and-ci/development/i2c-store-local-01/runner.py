# SPDX-License-Identifier: Apache-2.0
"""Prove every real word's transition and every public read/control relation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"experiments/spi_phase"))
from run_program_sensitivity import execute, vcd_frames


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def properties(capacity):
    banks = 4 if capacity == 128 else 5
    reads, transitions = [], []
    for index in range(capacity):
        reads.append(f"""
        if (pc == 8'd{index}) assert(instruction == word{index});
        if (!load_length && f_address == 8'd{index})
            assert(data_out == ((word{index} >> f_shift) & 32'hff));""")
        transitions.append(f"""
            if (!$past(rst_n)) assert(word{index} == 0);
            else if ($past(f_data_write && f_address == 8'd{index}))
                assert(word{index} == (($past(word{index}) & ~$past(f_mask)) | $past(f_value)));
            else assert(word{index} == $past(word{index}));""")
    return f"""
// Independent specification: addressed byte replacement, all other bits held.
reg f_past_valid = 1'b0;
wire [7:0] f_address = {{program_bank, byte_address[4:2]}};
wire [4:0] f_shift = {{byte_address[1:0], 3'b000}};
wire [31:0] f_mask = 32'hff << f_shift;
wire [31:0] f_value = {{24'd0, data_in}} << f_shift;
wire f_write = ena && load_mode && load_write;
wire f_data_write = f_write && !load_bank && !load_length;
wire f_length_valid = data_in != 0 && {{1'b0, data_in}} <= 9'd{capacity};
always @(*) begin
    assert(instruction_valid == (program_ready && pc < program_length && pc < 8'd{capacity}));
    if (load_length) assert(data_out == program_length);
    if (pc >= 8'd{capacity}) assert(instruction == 0 && !instruction_valid);
    if (!load_length && f_address >= 8'd{capacity}) assert(data_out == 0);
    {''.join(reads)}
end
always @(posedge clk) begin
    f_past_valid <= 1'b1;
`ifdef REACHABLE
    if (!f_past_valid) assume(!rst_n);
`endif
    if (f_past_valid) begin
        {''.join(transitions)}
        if (!$past(rst_n)) begin
            assert(program_length == 0 && !program_ready && program_bank == 0);
        end else if ($past(f_write && load_bank)) begin
            assert(program_length == 0 && !program_ready);
            assert(program_bank == ($past(data_in) < {1 << banks} ? $past(data_in[{banks-1}:0]) : 0));
        end else if ($past(f_write && load_length)) begin
            assert(program_bank == 0);
            assert(program_ready == $past(f_length_valid));
            assert(program_length == ($past(f_length_valid) ? $past(data_in) : 0));
        end else begin
            assert(program_length == $past(program_length) && program_bank == $past(program_bank));
            assert(program_ready == ($past(f_write) ? 0 : $past(program_ready)));
        end
        cover(program_ready && program_length == {capacity} && pc == {capacity-1} && instruction != 0);
        cover(rst_n && f_write && load_bank && data_in == 255);
        cover(rst_n && f_data_write && f_address == {capacity-1} && byte_address[1:0] == 3 && data_in == 165);
    end
end
"""


def inspect_control(task, capacity):
    violations = []
    for witness in (task/"proof/engine_0").glob("trace*.vcd"):
        source = witness.read_text()
        normalized = source.replace("$scope module m1_program_store $end", "$scope module public_spi $end")
        assert normalized != source
        parsed = task/("parsed-"+witness.name)
        parsed.write_text(normalized)
        rows = [r for r in vcd_frames(parsed) if r["time"] % 10 == 0]
        for a, b in zip(rows, rows[1:]):
            if not (a.get("rst_n") and a.get("ena") and a.get("load_mode") and a.get("load_write")
                    and not a.get("load_bank") and not a.get("load_length")):
                continue
            address = 8*a["program_bank"] + a["byte_address"]//4
            shift = 8*(a["byte_address"] % 4)
            for index in range(capacity):
                name = f"word{index}"
                if name not in a or name not in b:
                    continue
                expected = ((a[name] & ~(255 << shift)) | (a["data_in"] << shift)) if index == address else a[name]
                if b[name] != expected:
                    violations.append(dict(edge=a["time"], bank=a["program_bank"], byte_address=a["byte_address"],
                        addressed_word=address, affected_word=index, data=a["data_in"],
                        before=a[name], expected=expected, observed=b[name]))
    return dict(validated=bool(violations), violations=violations)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variants", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--variant", action="append", choices=("od128", "literal255"))
    p.add_argument("--tasks", nargs="+", choices=("prove", "cover", "alias", "lane"), default=("prove", "cover", "alias", "lane"))
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated output required")
    out.mkdir(parents=True)
    result = {"status": "RUNNING", "scope": "ALL_ALLOCATED_WORD_TRANSITIONS_AND_ALL_READ_CONTROL_RELATIONS",
              "runner_sha256": digest(Path(__file__)), "sources": {}, "tasks": [],
              "assumptions": {"prove": "no reset or environment assumptions; arbitrary initial memory/control state",
                              "cover_and_controls": "first sampled edge reset; subsequent inputs unrestricted"},
              "variant_selection": args.variant or ["od128", "literal255"], "task_selection": list(args.tasks)}

    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")

    save()
    try:
        for variant in args.variant or ("od128", "literal255"):
            capacity = 128 if variant == "od128" else 255
            source_path = args.variants.resolve()/variant/"src/m1_program_store.v"
            source = source_path.read_text()
            result["sources"][variant] = digest(source_path)
            appendix = properties(capacity)
            instrumented = source.replace("endmodule", appendix+"endmodule")
            assert instrumented.replace(appendix, "") == source
            for name in args.tasks:
                if name in ("alias", "lane") and variant != "od128":
                    continue
                task = out/(variant+"-"+name)
                task.mkdir()
                rtl = instrumented
                if name == "alias":
                    assert rtl.count("{program_bank, byte_address}") == 1
                    rtl = rtl.replace("{program_bank, byte_address}", "{1'b0, program_bank[2:0], byte_address}")
                elif name == "lane":
                    old = "[8*byte_address[1:0] +: 8] <= data_in;"
                    assert rtl.count(old) == capacity
                    rtl = rtl.replace(old, "[8*(byte_address[1:0] ^ 2'b01) +: 8] <= data_in;")
                mode = name if name in ("prove", "cover") else "bmc"
                expected = "PASS" if name in ("prove", "cover") else "FAIL"
                flags = "" if name == "prove" else "-D REACHABLE"
                depth = 4 if name == "prove" else 10 if name == "cover" else 6
                (task/"store.v").write_text(rtl)
                config = f"[options]\nmode {mode}\ndepth {depth}\nexpect {expected.lower()}\n\n[engines]\nsmtbmc z3\n\n[script]\n"
                config += f"read -formal -sv {flags} store.v\nprep -top m1_program_store\n\n[files]\n{task/'store.v'}\n"
                (task/"proof.sby").write_text(config)
                run = execute(["sby", "-f", "-d", str(task/"proof"), str(task/"proof.sby")], task/"run.log", 600)
                raw = (task/"proof/status").read_text().strip() if (task/"proof/status").exists() else "MISSING"
                match = re.fullmatch(r"(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}", raw)
                status = match[1] if match else "MISSING"
                induction = "successful proof by k-induction" in (task/"run.log").read_text()
                witnesses = {p.relative_to(task).as_posix(): digest(p) for p in (task/"proof/engine_0").glob("trace*.vcd")}
                control = inspect_control(task, capacity) if mode == "bmc" and status == "FAIL" else None
                accepted = run["returncode"] == 0 and not run["timed_out"] and status == expected
                accepted &= induction if mode == "prove" else bool(witnesses)
                if mode == "bmc":
                    accepted &= bool(control and control["validated"])
                result["tasks"].append(dict(variant=variant, name=name, mode=mode, expected=expected, status=status,
                    accepted=accepted, induction=induction, witnesses=witnesses, control=control,
                    input_sha256=digest(task/"store.v"), **run))
                save()
                print(variant, name, status, "ACCEPTED" if accepted else "NOT_QUALIFIED", flush=True)
        result["status"] = "PASS_SELECTED_STORE_TASKS" if all(t["accepted"] for t in result["tasks"]) else "NOT_QUALIFIED"
        if not args.variant and set(args.tasks) == {"prove", "cover", "alias", "lane"} and result["status"] == "PASS_SELECTED_STORE_TASKS":
            result["status"] = "PASS_ALL_WORD_STORE_PROOFS_WITH_CHECKED_CONTROLS"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
