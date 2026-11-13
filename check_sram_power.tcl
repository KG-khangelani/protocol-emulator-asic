# SPDX-License-Identifier: Apache-2.0
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
if {$::env(VDD_NETS) ne "VPWR" || $::env(GND_NETS) ne "VGND"} {
    error "Unexpected supply nets"
}
foreach net {VPWR VGND} {
    set report_file $::env(STEP_DIR)/$net-grid-errors.rpt
    set f [open $report_file "w"]
    puts $f ""
    close $f
    # A failure is fatal here. GeneratePDN's existing report parser records
    # fresh per-net and aggregate metrics for the unchanged later checker.
    check_power_grid -net $net -error_file $report_file
    puts "PASS_SRAM_GRID $net"
}
write_views
report_design_area_metrics
