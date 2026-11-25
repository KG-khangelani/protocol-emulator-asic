# SPDX-License-Identifier: Apache-2.0
"""Replay probe-loading scenarios for the council's passive branch-current fixture."""
from pathlib import Path
import sys

COUNCIL = Path(__file__).resolve().parents[1] / "E0049-review-council/panel-b/fixture"
sys.path.insert(0, str(COUNCIL))
from fixture_sensitivity import Rig, cross, rk_check


def main():
    sense_ohm = 470.0
    resistance_error_ohm = 0.01 * sense_ohm
    resistance_min_ohm = sense_ohm - resistance_error_ohm
    voltage_error_mv = 40.0
    released_ma = 0.25
    # Solve I + U_I <= released_ma using the council's worst-case error budget.
    pass_limit_ma = (released_ma - voltage_error_mv / resistance_min_ohm) / (
        1.0 + resistance_error_ohm / resistance_min_ohm
    )
    print(f"Maximum current reading for this uncertainty budget: {pass_limit_ma:.6f} mA")
    print("pF/node  to 0.25 mA (ns)  to pass limit (ns)  |I| at 8 ns (mA)  |I| at 56 ns (mA)")
    for capacitance_pf in (13, 16, 17, 20, 27):
        rig = Rig(capacitance_pf, capacitance_pf, sense_ohm=sense_ohm)

        def current_ma(t):
            return abs(rig.current_ma(rig.released(t, rig.supply_v, 0)))

        nominal_ns = cross(lambda t: current_ma(t) <= released_ma)
        conservative_ns = cross(lambda t: current_ma(t) <= pass_limit_ma)
        for t in (8, 56, nominal_ns, conservative_ns):
            opposite_ma = rig.current_ma(rig.released(t, 0, rig.supply_v))
            if abs(current_ma(t) + opposite_ma) > 1e-10:
                raise ValueError("The two opposing bias polarities disagree")
        if max(rk_check(rig, drive, bias, True)
               for drive, bias in ((rig.supply_v, 0), (0, rig.supply_v))) > 1e-8:
            raise ValueError("The branch voltages disagree with the independent integrator")
        print(f"{capacitance_pf:7d}  {nominal_ns:15.3f}  {conservative_ns:18.3f}"
              f"  {current_ma(8):16.3f}  {current_ma(56):17.3f}")


if __name__ == "__main__":
    main()
