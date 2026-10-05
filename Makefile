PYTHON ?= python3
LEARN_SECTION ?= all
ifneq ($(wildcard .venv/bin/python),)
PYTHON := $(CURDIR)/.venv/bin/python
export PATH := $(CURDIR)/.venv/bin:$(PATH)
endif
.PHONY: help setup doctor check lint test test-rtl-icarus test-gl-harness test-waveform-provenance test-verilator formal synth evidence learn-status learn-m0 learn-m0-verify learn-waveform clean
help:
	@echo "setup doctor check lint test test-rtl-icarus test-gl-harness test-waveform-provenance test-verilator formal synth evidence learn-status learn-m0 learn-m0-verify learn-waveform clean"
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
	$(PYTHON) -m unittest discover -s test -p 'test_uart_rx_oracle.py'
	$(PYTHON) -m unittest discover -s test -p 'test_uart_rx_host_service.py'
	$(PYTHON) -m unittest discover -s test -p 'test_waveform_provenance.py'
lint:
	verible-verilog-lint --rules_config_search src/project.v src/m1_engine.v src/m1_program_store.v src/m1_data_store.v src/m1_input_sync.v
test:
	$(MAKE) test-rtl-icarus
	$(MAKE) test-gl-harness
	$(MAKE) test-waveform-provenance
test-rtl-icarus:
	rm -f test/tb.fst test/results.xml build/rtl-icarus-waveform-checkpoint.json build/waveform-provenance.json
	$(MAKE) -C test
	$(PYTHON) tools/check_junit.py test/results.xml
	$(PYTHON) tools/check_waveform_provenance.py checkpoint
test-gl-harness:
	rm -f test/tb-gl-harness.fst test/results-gl-harness.xml
	$(MAKE) -C test COMPILE_ARGS="-DGL_TEST -DGL_HARNESS_SMOKE" COCOTB_TEST_MODULES=test_gate_harness_smoke SIM_BUILD=sim_build/icarus-gl-harness COCOTB_RESULTS_FILE=results-gl-harness.xml
	$(PYTHON) tools/check_junit.py test/results-gl-harness.xml
test-waveform-provenance:
	$(PYTHON) tools/check_waveform_provenance.py verify
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
	sby -f -d build/formal/data-store-prove formal/m1_data_store.sby prove
	sby -f -d build/formal/data-store-cover formal/m1_data_store.sby cover
	sby -f -d build/formal/input-sync-prove formal/m1_input_sync.sby prove
	sby -f -d build/formal/input-sync-cover formal/m1_input_sync.sby cover
	sby -f -d build/formal/public-readout-prove formal/m1_public_readout.sby
	$(PYTHON) tools/check_host_deadline.py
synth:
	mkdir -p build
	yosys -Q -l build/synthesis.log -p 'read_verilog src/project.v src/m1_engine.v src/m1_program_store.v src/m1_data_store.v src/m1_input_sync.v; hierarchy -check -top tt_um_khangelani_protocol_emulator; synth -top tt_um_khangelani_protocol_emulator; check -assert; stat; write_json build/synth.json'
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
	rm -rf build test/sim_build test/results.xml test/results-verilator.xml test/results-gl-harness.xml test/results-learning.xml test/tb.fst test/tb-gl-harness.fst
