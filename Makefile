PYTHON ?= python3
ifneq ($(wildcard .venv/bin/python),)
PYTHON := $(CURDIR)/.venv/bin/python
export PATH := $(CURDIR)/.venv/bin:$(PATH)
endif
.PHONY: help setup doctor check lint test formal synth evidence clean
help:
	@echo "setup doctor check lint test formal synth evidence clean"
setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-dev.txt
doctor:
	$(PYTHON) tools/doctor.py
check:
	$(PYTHON) tools/check_project.py
lint:
	verible-verilog-lint --rules_config_search src/project.v
test:
	$(MAKE) -C test
	$(PYTHON) tools/check_junit.py test/results.xml
formal:
	@echo "NOT_EVALUATED: the M0 formal harness is the next verified slice" >&2
	@exit 2
synth:
	mkdir -p build
	yosys -Q -l build/synthesis.log -p 'read_verilog src/project.v; hierarchy -check -top tt_um_khangelani_protocol_emulator; synth -top tt_um_khangelani_protocol_emulator; check -assert; stat; write_json build/synth.json'
evidence:
	$(PYTHON) tools/collect_evidence.py
clean:
	rm -rf build test/sim_build test/results.xml test/tb.fst
