# Modified 2026-09-22: resolve paths reliably with make -C.
# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= icarus
FST ?= -fst # Use more efficient FST format
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(CURDIR)/../src
PROJECT_SOURCES = project.v m1_engine.v m1_program_store.v m1_data_store.v m1_input_sync.v
COCOTB_TEST_MODULES = test,test_uart_rx_public,test_spi_mode0_public

# The prospective production profile includes the complete current matrix and
# the directly driven core. It is opt-in until physical qualification/adoption.
ifeq ($(G2_CURRENT),yes)
COMPILE_ARGS += -DG2_CURRENT
COCOTB_TEST_MODULES = test,test_uart_rx_public,test_spi_mode0_public,test_spi_timed_gpio,test_i2c_general_public,test_general_boundaries,test_i2c_abort_public
endif

# Extended experimental candidates use only the public top-level interface.
ifeq ($(GENERAL_IO),yes)
COMPILE_ARGS += -DGL_TEST
endif

# G1 reuses public expectations without instantiating the directly driven engine.
ifeq ($(G1_PHYSICAL),yes)
COMPILE_ARGS += -DGL_TEST
COCOTB_TEST_MODULES = test,test_uart_rx_public,test_spi_timed_gpio
COCOTB_TEST_FILTER = '^(test\.(public_pin_reload_changes_observable_program|k_input_wait_public_program_event_timeout_and_reload|k_bounded_loop_public_program_counts|k_shift_8_public_payload_both_orders|uart_tx_8n1_public_pin_oracle)|test_uart_rx_public\.[a-z0-9_]+|test_spi_timed_gpio\.timed_public_programs)$$'
endif

# G2 adds complete I2C, real-store boundaries and abort/reload to G1's public matrix.
ifeq ($(G2_PHYSICAL),yes)
COMPILE_ARGS += -DGL_TEST
COCOTB_TEST_MODULES = test,test_uart_rx_public,test_spi_timed_gpio,test_i2c_general_public,test_general_boundaries,test_i2c_abort_public
COCOTB_TEST_FILTER = '^(test\.(public_pin_reload_changes_observable_program|k_input_wait_public_program_event_timeout_and_reload|k_bounded_loop_public_program_counts|k_shift_8_public_payload_both_orders|uart_tx_8n1_public_pin_oracle)|test_uart_rx_public\.[a-z0-9_]+|test_spi_timed_gpio\.timed_public_programs|test_i2c_general_public\.complete_i2c_transactions|test_general_boundaries\.[a-z0-9_]+|test_i2c_abort_public\.public_i2c_abort_and_reload)$$'
endif

# Verilator requires an explicit decision about testbench delays.
ifeq ($(SIM),verilator)
COMPILE_ARGS += --timing
endif

# The learning target writes text VCD instead of compact FST so the repository's
# Python walkthrough can inspect the same simulated edges without a GUI viewer.
ifeq ($(LEARNING_VCD),yes)
COMPILE_ARGS += -DLEARNING_VCD
endif

ifeq ($(M0_LEARNING),yes)
COMPILE_ARGS += -DM0_LEARNING
PROJECT_SOURCES = source-project.v
SRC_DIR = $(CURDIR)/../evidence/E0010-pinned-cmos5l-run
COCOTB_TEST_MODULES = test_m0_archived
endif

ifneq ($(GATES),yes)

# RTL simulation:
SIM_BUILD				= sim_build/$(SIM)-rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

# Gate level simulation:
SIM_BUILD				= sim_build/$(SIM)-gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DSIM
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/verilog/sg13cmos5l_io.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_udp.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_stdcell.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(CURDIR)/gate_level_netlist.v

endif

# Allow sharing configuration between design and testbench via `include`:
COMPILE_ARGS 		+= -I$(SRC_DIR)

# Include the testbench sources:
VERILOG_SOURCES += $(CURDIR)/tb.v
TOPLEVEL = tb

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
