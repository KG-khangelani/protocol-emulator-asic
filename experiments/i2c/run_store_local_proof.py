# SPDX-License-Identifier: Apache-2.0
"""Prove every real word's transition and every public read/control relation."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def properties(capacity, scope="all", indices=None, reachable_checks=False):
    banks = 4 if capacity == 128 else 5
    reads, transitions = [], []
    for index in range(capacity) if indices is None else indices:
        reads.append(f"""
        if (pc == 8'd{index}) assert(instruction == word{index});
        if (!load_length && f_address == 8'd{index})
            assert(data_out == ((word{index} >> f_shift) & 32'hff));""")
        transitions.append(f"""
            if (!$past(rst_n)) assert(word{index} == 0);
            else if ($past(f_data_write && f_address == 8'd{index}))
                assert(word{index} == (($past(word{index}) & ~$past(f_mask)) | $past(f_value)));
            else assert(word{index} == $past(word{index}));""")
    header = f"""
// Independent specification: addressed byte replacement, all other bits held.
reg f_past_valid = 1'b0;
wire [7:0] f_address = {{program_bank, byte_address[4:2]}};
wire [4:0] f_shift = {{byte_address[1:0], 3'b000}};
wire [31:0] f_mask = 32'hff << f_shift;
wire [31:0] f_value = {{24'd0, data_in}} << f_shift;
wire f_write = ena && load_mode && load_write;
wire f_data_write = f_write && !load_bank && !load_length;
wire f_length_valid = data_in != 0 && {{1'b0, data_in}} <= 9'd{capacity};
"""
    read_properties = f"""
always @(*) begin
    assert(instruction_valid == (program_ready && pc < program_length && pc < 8'd{capacity}));
    if (load_length) assert(data_out == program_length);
    if (pc >= 8'd{capacity}) assert(instruction == 0 && !instruction_valid);
    if (!load_length && f_address >= 8'd{capacity}) assert(data_out == 0);
    {''.join(reads)}
end
"""
    if reachable_checks:
        read_properties = read_properties.replace("always @(*) begin\n", "always @(*) begin\n    if (f_past_valid) begin\n", 1)
        before, after = read_properties.rsplit("end", 1)
        read_properties = before + "    end\nend" + after
    state_properties = f"""
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
    assert scope in ("all", "state", "read")
    return header + (read_properties if scope != "state" else "") + (state_properties if scope != "read" else "")


def inspect_control(task, capacity):
    violations, aliased_reads = [], []
    for witness in (task/"proof/engine_0").glob("trace*.vcd"):
        source = witness.read_text()
        normalized = source.replace("$scope module m1_program_store $end", "$scope module public_spi $end")
        assert normalized != source
        parsed = task/("parsed-"+witness.name)
        parsed.write_text(normalized)
        rows = [r for r in vcd_frames(parsed) if r["time"] % 10 == 0]
        for row in rows:
            if not row.get("f_past_valid") or row.get("load_length") or row.get("program_bank", 0) < 8:
                continue
            address = 8*row["program_bank"] + row["byte_address"]//4
            shift = 8*(row["byte_address"] % 4)
            intended, aliased = row.get(f"word{address}"), row.get(f"word{address & 63}")
            if intended is None or aliased is None:
                continue
            expected, other = (intended >> shift) & 255, (aliased >> shift) & 255
            if row.get("data_out") == other and other != expected:
                aliased_reads.append(dict(edge=row["time"], bank=row["program_bank"], byte_address=row["byte_address"],
                    addressed_word=address, aliased_word=address & 63, expected=expected, observed=other))
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
    return dict(validated=bool(violations), violations=violations, aliased_reads=aliased_reads)


def prepare_model(directory, source, capacity):
    """Lower the unchanged real store once; partition only its appended assertions."""
    directory.mkdir()
    appendix = properties(capacity)
    rtl = source.replace("endmodule", appendix + "endmodule")
    assert rtl.replace(appendix, "") == source and "assert(" not in source
    path = directory / "store.v"
    path.write_text(rtl)
    script = (f"read -formal -sv {path}\nprep -top m1_program_store\n"
              f"write_rtlil {directory/'prepared.il'}\nwrite_json {directory/'prepared.json'}\n")
    (directory / "prepare.ys").write_text(script)
    run = execute(["yosys", "-Q", "-T", "-s", str(directory / "prepare.ys")], directory / "run.log", 600)
    assert run["returncode"] == 0 and not run["timed_out"], "formal model preparation failed"
    lines = rtl.splitlines()
    boundary = next(i + 1 for i, line in enumerate(lines) if line == "    f_past_valid <= 1'b1;")
    start = next(i + 1 for i, line in enumerate(lines) if line.startswith("// Independent specification:"))
    assertions = {}
    module = json.loads((directory / "prepared.json").read_text())["modules"]["m1_program_store"]
    cells = module["cells"]
    assert not any(c["type"] == "$assume" or c["type"] == "$check" and
                   c["parameters"]["FLAVOR"] == "assume" for c in cells.values()), "positive model contains an assumption"
    assert not any("init" in module["netnames"][f"word{i}"]["attributes"] for i in range(capacity)), "actual memory was initialized"
    for name, cell in cells.items():
        if not (cell["type"] == "$assert" or cell["type"] == "$check" and cell["parameters"]["FLAVOR"] == "assert"):
            continue
        location = cell["attributes"]["src"]
        match = re.search(r":(\d+)\.\d+-(\d+)\.\d+$", location)
        assert match, location
        first, last = map(int, match.groups())
        assert first > start, "unexpected assertion outside the appended specification"
        indices = sorted({int(n) for n in re.findall(r"\bword(\d+)\b", "\n".join(lines[first-1:last]))})
        assert len(indices) <= 1
        assertions[name] = {"scope": "read" if first < boundary else "state", "words": indices, "src": location}
    for scope in ("state", "read"):
        assert {i for a in assertions.values() if a["scope"] == scope for i in a["words"]} == set(range(capacity))
    record = dict(run=run, instrumented_sha256=digest(path), lowered_sha256=digest(directory / "prepared.il"),
                  assertions=assertions, transformation="Only irrelevant assertions are deleted per task; no assumptions added")
    (directory / "model.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variants", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--variant", action="append", choices=("od128", "literal255"))
    p.add_argument("--lane-style", choices=("indexed", "explicit"), default="indexed")
    p.add_argument("--proof-engine", choices=("abc", "smtbmc"), default="smtbmc")
    p.add_argument("--words-per-task", type=int, default=8)
    p.add_argument("--jobs", type=int, choices=(1, 2, 3, 4), default=2)
    p.add_argument("--tasks", nargs="+", choices=("state", "read", "cover", "alias", "lane"),
                   default=("state", "read", "cover", "alias", "lane"))
    args = p.parse_args()
    if not 1 <= args.words_per_task <= 255:
        p.error("words per task must be 1..255")
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated output required")
    out.mkdir(parents=True)
    result = {"status": "RUNNING", "scope": "ALL_ALLOCATED_WORD_TRANSITIONS_AND_ALL_READ_CONTROL_RELATIONS",
              "runner_sha256": digest(Path(__file__)), "sources": {}, "tasks": [], "models": {},
              "assumptions": {"prove": "no reset or environment assumptions; arbitrary initial memory/control state",
                              "cover_and_controls": "first sampled edge reset; subsequent inputs unrestricted"},
              "variant_selection": args.variant or ["od128", "literal255"], "task_selection": list(args.tasks),
              "proof_engine": args.proof_engine, "words_per_task": args.words_per_task, "jobs": args.jobs}

    def save():
        temporary = out/"result.json.tmp"
        temporary.write_text(json.dumps(result, indent=2)+"\n")
        temporary.replace(out/"result.json")

    save()
    try:
        for variant in args.variant or ("od128", "literal255"):
            capacity = 128 if variant == "od128" else 255
            source_path = args.variants.resolve()/variant/"src/m1_program_store.v"
            source = source_path.read_text()
            result["sources"][variant] = digest(source_path)
            model_dir = out / (variant + "-model")
            model = prepare_model(model_dir, source, capacity) if set(args.tasks) & {"state", "read"} else None
            if model:
                result["models"][variant] = model
                save()
            work = [(name, list(range(start, min(start + args.words_per_task, capacity))))
                    for name in args.tasks for start in (range(0, capacity, args.words_per_task)
                        if name in ("state", "read") else [0])]
            def one_task(item):
                name, indices = item
                if name in ("alias", "lane") and variant != "od128":
                    return None
                task = out/(variant+"-"+name+(f"-{indices[0]:03}" if name in ("state", "read") else ""))
                task.mkdir()
                scope = name if name in ("state", "read") else "all"
                appendix = properties(capacity, reachable_checks=name in ("alias", "lane"))
                rtl = source.replace("endmodule", appendix+"endmodule")
                assert rtl.replace(appendix, "") == source
                if name == "alias":
                    assert rtl.count("{program_bank, byte_address}") == 1
                    rtl = rtl.replace("{program_bank, byte_address}", "{1'b0, program_bank[2:0], byte_address}")
                elif name == "lane":
                    if args.lane_style == "explicit":
                        old = "case (byte_address[1:0])"
                        assert rtl.count(old) == capacity
                        rtl = rtl.replace(old, "case (byte_address[1:0] ^ 2'b01)")
                    else:
                        old = "[8*byte_address[1:0] +: 8] <= data_in;"
                        assert rtl.count(old) == capacity
                        rtl = rtl.replace(old, "[8*(byte_address[1:0] ^ 2'b01) +: 8] <= data_in;")
                mode = "prove" if name in ("state", "read") else "cover" if name == "cover" else "bmc"
                expected = "PASS" if mode != "bmc" else "FAIL"
                flags = "" if mode == "prove" else "-D REACHABLE"
                depth = 1 if name == "read" else 2 if name == "state" else 10 if mode == "cover" else 6
                (task/"store.v").write_text(rtl)
                engine = "abc pdr" if mode == "prove" and args.proof_engine == "abc" else "smtbmc z3"
                config = f"[options]\nmode {mode}\ndepth {depth}\nexpect {expected.lower()}\n\n[engines]\n{engine}\n\n[script]\n"
                selected = []
                if mode == "prove":
                    selected = [cell for cell, a in model["assertions"].items() if a["scope"] == scope and
                                (not a["words"] or a["words"][0] in indices)]
                    assert selected
                    config += "read_rtlil prepared.il\n"
                    for cell in model["assertions"]:
                        if cell not in selected:
                            config += f"delete m1_program_store/c:{cell}\n"
                    config += f"prep -top m1_program_store\n\n[files]\n{model_dir/'prepared.il'}\n"
                else:
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
                unbounded = status == "PASS" and (induction or engine == "abc pdr")
                accepted &= unbounded if mode == "prove" else bool(witnesses)
                if mode == "bmc":
                    accepted &= bool(control and control["validated"])
                return dict(variant=variant, name=name, directory=task.name, mode=mode, proof_scope=scope,
                    word_indices=indices if scope != "all" else list(range(capacity)),
                    selected_assertions=selected,
                    expected=expected, status=status,
                    accepted=accepted, induction=induction, unbounded_proof=unbounded if mode == "prove" else None,
                    engine=engine, witnesses=witnesses, control=control,
                    input_sha256=digest(task/"store.v"), **run)

            with ThreadPoolExecutor(max_workers=args.jobs) as pool:
                for future in as_completed([pool.submit(one_task, item) for item in work]):
                    record = future.result()
                    if record is None:
                        continue
                    result["tasks"].append(record)
                    save()
                    print(record["directory"], record["status"],
                          "ACCEPTED" if record["accepted"] else "NOT_QUALIFIED", flush=True)
            for name in set(args.tasks) & {"state", "read"}:
                covered = [i for task in result["tasks"] if task["variant"] == variant and task["name"] == name
                           for i in task["word_indices"]]
                assert sorted(covered) == list(range(capacity)), "incomplete or overlapping word coverage"
            if {"state", "read"} <= set(args.tasks):
                checked = {cell for task in result["tasks"] if task["variant"] == variant
                           for cell in task["selected_assertions"]}
                assert checked == set(model["assertions"]), "an assertion was omitted from the partitioned proof"
        result["tasks"].sort(key=lambda item: (item["variant"], item["name"], item["word_indices"][0]))
        result["status"] = "PASS_SELECTED_STORE_TASKS" if all(t["accepted"] for t in result["tasks"]) else "NOT_QUALIFIED"
        if not args.variant and set(args.tasks) == {"state", "read", "cover", "alias", "lane"} and result["status"] == "PASS_SELECTED_STORE_TASKS":
            result["status"] = "PASS_ALL_WORD_STORE_PROOFS_WITH_CHECKED_CONTROLS"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
