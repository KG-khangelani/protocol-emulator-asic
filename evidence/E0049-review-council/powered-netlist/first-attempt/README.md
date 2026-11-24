# Test discovery failure

At 14:53:40 UTC the chair started the original driver. Icarus compiled the submitted netlist and the two SRAM and three IHP Verilog files. At simulation time zero cocotb imported a namespace package named `test` in the isolated working directory and failed to find the repository's `edge` helper. No workload ran.

The [original log](run.log.gz), [driver](original-driver.py.gz) and [result](result.json) preserve this outcome. The next attempt explicitly resolves the unedited helper at `test/test.py` and gives the other original helpers their repository search path. The registered pin sequence, stimuli, checks and time cap carry over.
