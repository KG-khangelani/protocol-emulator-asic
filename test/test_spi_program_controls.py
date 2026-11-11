# SPDX-License-Identifier: Apache-2.0
"""Focused actual-program controls; observations use only public pins."""
import cocotb
from test_spi_mode0_pins import transact

@cocotb.test()
async def actual_program_controls(dut):
    for order, wrong in ((0, 0xD3), (1, 0xB4)):
        baseline = await transact(dut, f"baseline-{order}", 0x96, 0x69, order,
                                  [499999]*8, retain=True)
        assert baseline["accepted"] and baseline["raw_rx"] == 0x69
        early = await transact(dut, f"early-{order}", 0x96, 0x69, order,
                               [499999]*8, early=True, require=False)
        assert early["pin_schedule_ok"] and not early["aperture_violations"]
        assert not early["response_profile_violations"]
        assert early["wire_rx"] == 0x69 and early["raw_rx"] == wrong
        assert early["status"] == 0xA7 and early["valid_probes"]["379"] == 1
        assert not early["accepted"]
        late = await transact(dut, f"late-input-{order}", 0x96, 0x69, order,
                              [500001]*8, require=False)
        assert late["pin_schedule_ok"] and late["response_profile_violations"]
        assert late["aperture_violations"] and not late["accepted"]
        assert late["wire_rx"] == late["raw_rx"] == wrong
