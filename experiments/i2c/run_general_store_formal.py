# SPDX-License-Identifier: Apache-2.0
"""Symbolically track an arbitrary real program word and public store controls."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def properties(capacity):
    bank_bits = 4 if capacity == 128 else 5
    choices = "\n".join(f"8'd{i}: f_actual_word = word{i};" for i in range(capacity))
    return f"""
(* anyconst *) reg [7:0] f_index;
reg [31:0] f_shadow;
reg [31:0] f_actual_word;
reg f_past_valid = 1'b0;
reg f_reset_seen = 1'b0;
wire [7:0] f_word_address = {{program_bank, byte_address[4:2]}};
wire f_write = ena && load_mode && load_write;
always @(*) begin
    assume(f_index < 8'd{capacity});
    case(f_index)
        {choices}
        default: f_actual_word = 32'd0;
    endcase
    assert(instruction_valid == (program_ready && pc < program_length && pc < 8'd{capacity}));
    if (load_length) assert(data_out == program_length);
    if (f_reset_seen) begin
        assert(f_actual_word == f_shadow);
        if (pc == f_index) assert(instruction == f_shadow);
        if (!load_length && f_word_address == f_index)
            assert(data_out == f_shadow[8*byte_address[1:0] +: 8]);
        if (pc >= 8'd{capacity}) assert(instruction == 0 && !instruction_valid);
        if (!load_length && f_word_address >= 8'd{capacity}) assert(data_out == 0);
    end
end
always @(posedge clk) begin
    f_past_valid <= 1'b1;
    if (!f_past_valid) assume(!rst_n);
    if (!rst_n) begin
        f_shadow <= 32'd0;
        f_reset_seen <= 1'b1;
    end else if (f_write && !load_bank && !load_length && f_word_address == f_index)
        f_shadow[8*byte_address[1:0] +: 8] <= data_in;
    if (f_past_valid) begin
        if (!$past(rst_n)) begin
            assert(program_length == 0 && !program_ready && program_bank == 0);
        end else if ($past(f_write && load_bank)) begin
            assert(program_length == 0 && !program_ready);
            assert(program_bank == ($past(data_in) < {1 << bank_bits} ? $past(data_in[{bank_bits-1}:0]) : 0));
        end else if ($past(f_write && load_length)) begin
            assert(program_bank == 0);
            assert(program_ready == ($past(data_in) >= 1 && $past(data_in) <= {capacity}));
            assert(program_length == (($past(data_in) >= 1 && $past(data_in) <= {capacity}) ? $past(data_in) : 0));
        end else begin
            assert(program_length == $past(program_length) && program_bank == $past(program_bank));
            assert(program_ready == ($past(f_write) ? 0 : $past(program_ready)));
        end
    end
    cover(f_reset_seen && program_ready && program_length == {capacity} && pc == {capacity-1} && instruction != 0);
    cover(f_reset_seen && f_write && load_bank && data_in == 255);
end
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variants", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new build output required")
    out.mkdir(parents=True)
    result = {"status": "RUNNING", "scope": "ARBITRARY_WORD_NONALIAS_AND_PUBLIC_STORE_CONTROL",
              "runner_sha256": digest(Path(__file__)), "sources": {}, "tasks": [],
              "assumptions": ["first sampled edge reset", "arbitrary constant allocated word index; all other inputs unrestricted"]}

    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")

    save()
    try:
        for variant, capacity in (("od128", 128), ("literal255", 255)):
            source_path = args.variants/variant/"src/m1_program_store.v"
            source = source_path.read_text()
            result["sources"][variant] = digest(source_path)
            appendix = properties(capacity)
            rtl = source.replace("endmodule", appendix+"endmodule")
            assert rtl.replace(appendix, "") == source
            for mode, depth in (("prove", 5), ("cover", 8)):
                task = out/(variant+"-"+mode)
                task.mkdir()
                (task/"store.v").write_text(rtl)
                config = f"[options]\nmode {mode}\ndepth {depth}\n\n[engines]\nsmtbmc z3\n\n[script]\n"
                config += f"read -formal -sv store.v\nprep -top m1_program_store\n\n[files]\n{task/'store.v'}\n"
                (task/"proof.sby").write_text(config)
                start = time.monotonic()
                timed_out = False
                with (task/"run.log").open("w") as log:
                    try:
                        proc = subprocess.run(["sby", "-f", "-d", str(task/"proof"), str(task/"proof.sby")],
                                              cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=240)
                        code = proc.returncode
                    except subprocess.TimeoutExpired:
                        code, timed_out = 124, True
                raw = (task/"proof/status").read_text().strip() if (task/"proof/status").exists() else "MISSING"
                match = re.fullmatch(r"(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}", raw)
                status = match[1] if match else "MISSING"
                induction = "successful proof by k-induction" in (task/"run.log").read_text()
                witnesses = {p.relative_to(task).as_posix(): digest(p) for p in (task/"proof/engine_0").glob("trace*.vcd")}
                accepted = code == 0 and status == "PASS" and not timed_out and (induction if mode == "prove" else bool(witnesses))
                result["tasks"].append(dict(variant=variant, mode=mode, status=status, accepted=accepted,
                    returncode=code, timed_out=timed_out, induction=induction, witnesses=witnesses,
                    seconds=round(time.monotonic()-start, 3), input_sha256=digest(task/"store.v")))
                save()
                print(variant, mode, status, "ACCEPTED" if accepted else "NOT_QUALIFIED", flush=True)
        result["status"] = "PASS_STORE_PROOFS" if all(t["accepted"] for t in result["tasks"]) else "NOT_QUALIFIED"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
