"""Check that the council audit rejects plausible false passes, using in-memory copies."""
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import audit


def rejected(record, change, check, expected):
    original = audit.read

    def read_copy(path):
        result = original(path)
        if path == audit.HERE / record:
            change(result)
        return result

    with patch.object(audit, "read", read_copy):
        try:
            check()
        except ValueError as error:
            if str(error) != expected:
                raise
            print("Rejected:", expected)
            return
    raise AssertionError("Changed observation escaped: " + record)


def lose_remote_slot(result):
    result["in_envelope"][0]["sensed_slots"] = 16


def extend_uart_service(result):
    result["bounds"]["102"]["max_all_phase_H_plus_L"] = 4340


def hide_high_stall(result):
    row = next(r for r in result["observations"] if r["kind"] == "candidate" and r["profile"] == "high_abort")
    start = row["frames"][0]["release_reference_ns"]
    edge = next(edge for edge in row["public_oe_value_edges"] if edge[0] >= start and edge[1] == 0)
    edge[0] = start + 160


if __name__ == "__main__":
    audit.observations()
    audit.interface_boundaries()
    rejected("onewire/rise/recovery-results.json.gz", lose_remote_slot, audit.interface_boundaries,
             "wider slots at the remote receiver")
    rejected("panel-a/uart/results.json.gz", extend_uart_service, audit.interface_boundaries,
             "UART host-service boundary")
    rejected("panel-a/pio-target/records/attempt-02.json.gz", hide_high_stall, audit.observations,
             "stopped-high public MISO releases after CS")
