# SPDX-License-Identifier: Apache-2.0
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
read_current_odb
set_propagated_clock [all_clocks]
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl

# Coordinates are the exact FS macro pin centres in the frozen D43 placement.
# Native detailed placement below legalizes the proposed 15 um edge offsets.
set expected {
    {A_ADDR[0]} 224.810
    {A_ADDR[1]} 224.300
    {A_ADDR[2]} 232.460
    {A_ADDR[3]} 231.440
    {A_ADDR[4]} 235.010
    {A_ADDR[5]} 233.990
    {A_ADDR[6]} 212.570
    A_WEN 225.830
    {A_DIN[15]} 192.180
}
set macro [get_cells {store.program_memory}]
if {[llength $macro] != 1} {error "Expected one identified SRAM"}
set all_pins [get_pins -of_objects $macro]
set index 0
foreach {name x} $expected {
    set matches {}
    foreach pin $all_pins {
        if {[get_full_name $pin] eq "store.program_memory/$name"} {
            lappend matches $pin
        }
    }
    if {[llength $matches] != 1} {error "Missing or ambiguous SRAM pin $name"}
    insert_buffer -buffer_cell sg13cmos5l_buf_4 -load_pins $matches \
        -location [list $x 436.050] -buffer_name sram_input_buffer_$index \
        -net_name sram_buffered_input_$index
    puts "INSERTED_SRAM_INPUT_BUFFER $index $name"
    incr index
}
if {$index != 9} {error "Expected nine SRAM input buffers"}
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
estimate_parasitics -global_routing
write_views
