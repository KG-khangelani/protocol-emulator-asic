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
lint:
	verible-verilog-lint --rules_config_search src/project.v formal/m0_gpio_formal.sv formal/mutants/m0_increment_by_two.v
test:
	$(MAKE) -C test
	$(PYTHON) tools/check_junit.py test/results.xml
test-verilator:
	$(MAKE) -C test SIM=verilator COCOTB_RESULTS_FILE=results-verilator.xml
	$(PYTHON) tools/check_junit.py test/results-verilator.xml
formal:
	rm -rf build/formal
	mkdir -p build/formal
	sby -f -d build/formal/prove formal/m0_gpio.sby prove
	sby -f -d build/formal/cover formal/m0_gpio.sby cover
	sby -f -d build/formal/mutant formal/m0_gpio_mutation.sby
synth:
	mkdir -p build
	yosys -Q -l build/synthesis.log -p 'read_verilog src/project.v; hierarchy -check -top tt_um_khangelani_protocol_emulator; synth -top tt_um_khangelani_protocol_emulator; check -assert; stat; write_json build/synth.json'
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
	$(MAKE) -C test FST= LEARNING_VCD=yes SIM_BUILD=sim_build/icarus-learning COCOTB_RESULTS_FILE=results-learning.xml
	$(PYTHON) tools/check_junit.py test/results-learning.xml
	$(PYTHON) tools/m0_waveform_walkthrough.py build/m0-learning.vcd
clean:
	rm -rf build test/sim_build test/results.xml test/results-verilator.xml test/results-learning.xml test/tb.fst
