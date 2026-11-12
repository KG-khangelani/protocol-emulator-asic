# SPDX-License-Identifier: Apache-2.0
"""Compare the real banked FF store with an independent behavioral memory."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"experiments/spi_phase"))
from run_program_sensitivity import execute


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(capacity):
    banks = 4 if capacity == 128 else 5
    # The independent model uses one indexed word memory. Exposed aliases are
    # state matching points only; each state transition must still be proved.
    aliases = "\n".join(f"    (* keep *) wire [31:0] word{i} = memory[{i}];" for i in range(capacity))
    return f"""// SPDX-License-Identifier: Apache-2.0
`default_nettype none
module reference_store (
    input wire clk, rst_n, ena, load_mode, load_write, load_length, load_bank,
    input wire [4:0] byte_address, input wire [7:0] data_in, pc,
    output reg [7:0] data_out, program_length, output reg program_ready,
    output reg [{banks-1}:0] program_bank, output reg [31:0] instruction,
    output wire instruction_valid
);
    reg [31:0] memory [0:{capacity-1}];
    integer index;
    wire [7:0] address = {{program_bank, byte_address[4:2]}};
    wire accepted_length = data_in != 0 && {{1'b0, data_in}} <= 9'd{capacity};
{aliases}
    always @(posedge clk) begin
        if (!rst_n) begin
            for (index=0; index<{capacity}; index=index+1)
                memory[index] <= 0;
            program_bank <= 0;
            program_length <= 0;
            program_ready <= 0;
        end else if (ena && load_mode && load_write) begin
            if (load_bank) begin
                program_bank <= data_in < {1 << banks} ? data_in[{banks-1}:0] : 0;
                program_length <= 0;
                program_ready <= 0;
            end else if (load_length) begin
                program_bank <= 0;
                program_length <= accepted_length ? data_in : 0;
                program_ready <= accepted_length;
            end else begin
                program_ready <= 0;
                if (address < {capacity})
                    case (byte_address[1:0])
                        0: memory[address][7:0] <= data_in;
                        1: memory[address][15:8] <= data_in;
                        2: memory[address][23:16] <= data_in;
                        3: memory[address][31:24] <= data_in;
                    endcase
            end
        end
    end
    always @(*) begin
        instruction = pc < {capacity} ? memory[pc] : 32'd0;
        data_out = 0;
        if (address < {capacity})
            case (byte_address[1:0])
                0: data_out = memory[address][7:0];
                1: data_out = memory[address][15:8];
                2: data_out = memory[address][23:16];
                3: data_out = memory[address][31:24];
            endcase
        if (load_length) data_out = program_length;
    end
    assign instruction_valid = program_ready && pc < program_length && pc < {capacity};
endmodule
`default_nettype wire
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variants", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated output required")
    out.mkdir(parents=True)
    result = {"status": "RUNNING", "scope": "ALL_WORD_STATE_AND_PUBLIC_STORE_REFINEMENT",
              "runner_sha256": digest(Path(__file__)), "tasks": [],
              "assumptions": "same inputs and corresponding state; synchronous reset establishes matching all-zero store/control state"}

    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")

    save()
    try:
        for variant, capacity in (("od128", 128), ("literal255", 255)):
            path = out/variant
            path.mkdir()
            actual = args.variants.resolve()/variant/"src/m1_program_store.v"
            (path/"reference.v").write_text(reference(capacity))
            script = f"read_verilog {actual} {path/'reference.v'}; proc; memory_map; opt; "
            script += "equiv_make reference_store m1_program_store equivalence; hierarchy -top equivalence; "
            script += "equiv_simple; equiv_induct -seq 3; equiv_status -assert"
            (path/"proof.ys").write_text(script+"\n")
            run = execute(["yosys", "-Q", "-s", str(path/"proof.ys")], path/"run.log", 360)
            accepted = run["returncode"] == 0 and "Equivalence successfully proven!" in (path/"run.log").read_text()
            result["tasks"].append(dict(variant=variant, accepted=accepted, source_sha256=digest(actual),
                reference_sha256=digest(path/"reference.v"), **run))
            save()
            print(variant, "PASS" if accepted else "NOT_QUALIFIED", flush=True)
        result["status"] = "PASS_BEHAVIORAL_STORE_EQUIVALENCE" if all(t["accepted"] for t in result["tasks"]) else "NOT_QUALIFIED"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
