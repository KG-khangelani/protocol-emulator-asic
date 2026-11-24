"""Calculate an illustrative single-pole rise after open-drain DQ release."""
import json
import math


def main():
    pullup_v = 3.3
    resistance_ohm = 4700
    thresholds = {"RP2040_host_3V3": 2.0, "DS18B20_local": 2.2, "DS18B20_parasite": 3.0}
    data = {"model": "ideal initial 0 V, exponential rise, zero leakage, no distributed line or pad delay",
            "pullup_v": pullup_v, "pullup_ohm": resistance_ohm, "loads": []}
    for pf in (100, 1000):
        tau_us = pf * 1e-6 * resistance_ohm
        volt_9 = pullup_v * (1 - math.exp(-9/tau_us))
        values = {"capacitance_pf": pf, "tau_us": tau_us, "volts_after_9us": round(volt_9, 6),
                  "release_to_threshold_us": {}, "latest_presence_start_us_if_crossing_at_threshold": {}}
        for label, voltage in thresholds.items():
            time_us = -tau_us * math.log1p(-voltage/pullup_v)
            values["release_to_threshold_us"][label] = round(time_us, 6)
            if label.startswith("DS18B20"):
                values["latest_presence_start_us_if_crossing_at_threshold"][label] = round(time_us + 60, 6)
        data["loads"].append(values)
    data["write_one_at_15us_max_capacitance_pf"] = {
        label: round(9e6/(-resistance_ohm*math.log1p(-v/pullup_v)), 4)
        for label, v in thresholds.items() if label.startswith("DS18B20")}
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
