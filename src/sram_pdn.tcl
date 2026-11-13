# SPDX-License-Identifier: Apache-2.0
# Generated from the pinned macro Metal4 supply rectangles.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/set_global_connections.tcl
set_global_connections
set_voltage_domain -name CORE -power $::env(VDD_NET) -ground $::env(GND_NET)
set block [ord::get_db_block]
set core_x [expr {double([[$block getCoreArea] xMin])/[$block getDbUnitsPerMicron]}]
if {abs($core_x - 2.88) > 0.0001} {error "Unexpected core origin"}
define_pdn_grid -name stdcell_grid -starts_with POWER -voltage_domains CORE -pins Metal4
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {12.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {16.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {25.825 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {31.445 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {37.065 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {42.685 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {48.305 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {53.925 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {59.545 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {65.165 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {70.785 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {76.405 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {82.025 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {87.645 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {93.265 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {98.885 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {104.505 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {110.125 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {115.745 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {121.365 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {126.985 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {132.605 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {138.225 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {143.845 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {149.465 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {155.085 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {160.705 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {166.325 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {171.945 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {177.565 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {183.185 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {188.805 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {194.425 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {200.045 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {210.455 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {215.605 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {220.755 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {225.905 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {231.055 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {236.205 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {241.355 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {246.505 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {256.915 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {262.535 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {268.155 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {273.775 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {279.395 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {285.015 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {290.635 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {296.255 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {301.875 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {307.495 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {313.115 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {318.735 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {324.355 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {329.975 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {335.595 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {341.215 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {346.835 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {352.455 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {358.075 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {363.695 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {369.315 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {374.935 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {380.555 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {386.175 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {391.795 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {397.415 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {403.035 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {408.655 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {414.275 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {419.895 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {425.515 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {431.135 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {462.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {466.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {512.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {516.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {562.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {566.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {612.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {616.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {662.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {666.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {712.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {716.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {762.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {766.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {812.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {816.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {862.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {866.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {912.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {916.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {962.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {966.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1012.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1016.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1062.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1066.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1112.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1116.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1162.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1166.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1212.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1216.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1262.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1266.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1312.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1316.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1362.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1366.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1412.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1416.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1462.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1466.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1512.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1516.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1562.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1566.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1612.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1616.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1662.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1666.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1712.88 - $core_x}] -number_of_straps 1 -nets VPWR
add_pdn_stripe -grid stdcell_grid -layer Metal4 -width 2.1 -pitch 2000 -offset [expr {1716.98 - $core_x}] -number_of_straps 1 -nets VGND
add_pdn_stripe -grid stdcell_grid -layer $::env(PDN_RAIL_LAYER) -width $::env(PDN_RAIL_WIDTH) -followpins
add_pdn_connect -grid stdcell_grid -layers "$::env(PDN_RAIL_LAYER) Metal4"
define_pdn_grid -macro -name sram_grid -instances {store.program_memory} -grid_over_boundary -halo {0 0} -starts_with POWER
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 5.665 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 16.905 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 28.145 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 39.385 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 50.625 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 61.865 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 73.105 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 84.345 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 95.585 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 106.825 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 118.065 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 129.305 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 140.545 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 151.785 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 163.025 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 174.265 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 195.445 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 205.745 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 210.895 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 221.195 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 242.375 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 253.615 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 264.855 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 276.095 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 287.335 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 298.575 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 309.815 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 321.055 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 332.295 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 343.535 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 354.775 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 366.015 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 377.255 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 388.495 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 399.735 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 410.975 -number_of_straps 1 -nets VPWR -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 11.285 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 22.525 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 33.765 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 45.005 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 56.245 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 67.485 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 78.725 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 89.965 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 101.205 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 112.445 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 123.685 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 134.925 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 146.165 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 157.405 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 168.645 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 179.885 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 190.295 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 200.595 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 216.045 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 226.345 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 236.755 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 247.995 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 259.235 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 270.475 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 281.715 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 292.955 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 304.195 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 315.435 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 326.675 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 337.915 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 349.155 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 360.395 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 371.635 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 382.875 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 394.115 -number_of_straps 1 -nets VGND -extend_to_boundary
add_pdn_stripe -grid sram_grid -layer Metal4 -width 2.1 -pitch 2000 -offset 405.355 -number_of_straps 1 -nets VGND -extend_to_boundary
