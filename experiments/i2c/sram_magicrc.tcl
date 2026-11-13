# SPDX-License-Identifier: Apache-2.0
# Keep every native Magic step; align only the complete GDS DRC invocation.
if {![info exists ::env(_TCL_ENV_IN)]} {
    error "SRAM Magic setup requires the native flow environment"
}
source $::env(_TCL_ENV_IN)
set sram_native_magic_dir [file dirname $::env(MAGIC_TECH)]
if {$::env(STEP_ID) eq "Magic.DRC"} {
    set sram_aligned_dir [file join $::env(STEP_DIR) sram-magic-aligned]
    set sram_helper [file join [file dirname [file normalize [info script]]] align_sram_magic.py]
    puts stdout [exec python3 $sram_helper --source-tech $::env(MAGIC_TECH) --output $sram_aligned_dir --drc-script $::env(_MAGIC_SCRIPT)]
    source [file join $sram_aligned_dir ihp-sg13cmos5l.magicrc]

    # The original drc.tcl still executes its complete synchronous rule check.
    # Avoid background DRC on partially imported hierarchy; restore it even
    # when the native import raises an error.
    proc ::sram_import_enter {command operation} {
        if {[lindex $command 1] eq "read"} {
            drc off
            puts stdout "SRAM GDS import: background DRC suspended"
            flush stdout
        }
    }
    proc ::sram_import_leave {command code result operation} {
        if {[lindex $command 1] eq "read"} {
            drc on
            puts stdout "SRAM GDS import: background DRC restored"
            flush stdout
        }
    }
    trace add execution ::gds enter ::sram_import_enter
    trace add execution ::gds leave ::sram_import_leave
} else {
    source [file join $sram_native_magic_dir ihp-sg13cmos5l.magicrc]
}
