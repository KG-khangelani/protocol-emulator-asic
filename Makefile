PYTHON ?= python3
LEARN_SECTION ?= all
ifneq ($(wildcard .venv/bin/python),)
PYTHON := $(CURDIR)/.venv/bin/python
export PATH := $(CURDIR)/.venv/bin:$(PATH)
endif
.PHONY: help setup doctor check lint test test-verilator formal synth evidence learn-status learn-m0 learn-m0-verify learn-waveform clean
help:
	@echo "setup doctor check lint test test-verilator formal synth evidence learn-status learn-m0 learn-m0-verify learn-waveform clean"
setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-dev.txt
doctor:
	$(PYTHON) tools/doctor.py
check:
	$(PYTHON) tools/check_project.py
	$(PYTHON) tools/learning_status.py --verify
	$(PYTHON) tools/m0_walkthrough.py --verify
	$(PYTHON) -m unittest discover -s test -p 'test_m1_contract_model.py'
lint:
	verible-verilog-lint --rules_config_search src/project.v src/m1_engine.v src/m1_program_store.v src/m1_input_sync.v
test:
	$(MAKE) -C test
	$(PYTHON) tools/check_junit.py test/results.xml
	$(MAKE) -C test COMPILE_ARGS=-DGL_TEST COCOTB_TEST_MODULES=test_gate_harness_smoke SIM_BUILD=sim_build/icarus-gl-harness COCOTB_RESULTS_FILE=results-gl-harness.xml
	$(PYTHON) tools/check_junit.py test/results-gl-harness.xml
test-verilator:
	$(MAKE) -C test SIM=verilator COCOTB_RESULTS_FILE=results-verilator.xml
	$(PYTHON) tools/check_junit.py test/results-verilator.xml
formal:
	rm -rf build/formal
	mkdir -p build/formal
	sby -f -d build/formal/prove formal/m1_engine.sby prove
	sby -f -d build/formal/cover formal/m1_engine.sby cover
	sby -f -d build/formal/mutant formal/m1_engine_mutation.sby
	sby -f -d build/formal/store-prove formal/m1_program_store.sby prove
	sby -f -d build/formal/store-cover formal/m1_program_store.sby cover
	sby -f -d build/formal/input-sync-prove formal/m1_input_sync.sby prove
	sby -f -d build/formal/input-sync-cover formal/m1_input_sync.sby cover
synth:
	mkdir -p build
	yosys -Q -l build/synthesis.log -p 'read_verilog src/project.v src/m1_engine.v src/m1_program_store.v src/m1_input_sync.v; hierarchy -check -top tt_um_khangelani_protocol_emulator; synth -top tt_um_khangelani_protocol_emulator; check -assert; stat; write_json build/synth.json'
evidence:
	$(PYTHON) tools/collect_evidence.py
learn-status:
	$(PYTHON) tools/learning_status.py
learn-m0:
	$(PYTHON) tools/m0_walkthrough.py --section $(LEARN_SECTION)
learn-m0-verify:
	$(PYTHON) tools/m0_walkthrough.py --verify
learn-waveform:
	rm -f build/m0-learning.vcd test/results-learning.xml
	mkdir -p build
	$(MAKE) -C test FST= LEARNING_VCD=yes M0_LEARNING=yes SIM_BUILD=sim_build/icarus-learning COCOTB_RESULTS_FILE=results-learning.xml
	$(PYTHON) tools/check_junit.py test/results-learning.xml
	$(PYTHON) tools/m0_waveform_walkthrough.py build/m0-learning.vcd
clean:
	rm -rf build test/sim_build test/results.xml test/results-verilator.xml test/results-learning.xml test/tb.fst
