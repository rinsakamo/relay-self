"""V6 B0: prospective source-only LOW/HIGH energy and six cheap L0 controls."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANIFEST = Path(__file__).with_name("v6_b0_two_regime_manifest.json")
SCHEMA = "RELAYSELF_V6_B0_TWO_REGIME_G0_1"
V5 = "b8162ea1d2824de366b15ddaea505d31db6b671c"
S_HEAD = "28cb0f588192ecfe5d03b12b818508352d1a40a8"
ARMS = ("SENSOR_ON", "SHAM_ON", "SENSOR_MASKED_HIGH",
        "ALWAYS_SEEK", "ALWAYS_WAIT", "EQUAL_INFO_CHEAP_THRESHOLD")


class V6Rejected(ValueError):
    """Changed source/criteria or fabricated World evidence."""


def verify(d: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(d, dict) or set(d) != {
        "schema", "issue", "parent_v5_head", "s_source_head", "state",
        "source", "controls", "endpoints", "admission", "frozen",
    }:
        raise V6Rejected("unexpected V6 manifest shape")
    canonical = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (d != canonical or d["schema"] != SCHEMA
            or d["parent_v5_head"] != V5 or d["s_source_head"] != S_HEAD
            or d["controls"] != list(ARMS)
            or d["frozen"] != ["V2", "V3", "V4", "V5"]
            or d["admission"]["new_real_world_trials"] != 0
            or d["admission"]["scientific_g3"] != "NO_GO"):
        raise V6Rejected("V6 source or prospective constraints changed")
    return d


def manifest() -> dict[str, Any]:
    return verify(json.loads(MANIFEST.read_text(encoding="utf-8")))


def first_source_choice() -> dict[str, Any]:
    x = manifest()["source"]
    rows: dict[str, dict[str, Any]] = {}
    for phase, start in (
        ("LOW", x["initial_energy_low"]), ("HIGH", x["initial_energy_high"]),
    ):
        e = start - x["wait_m0_ticks"] * x["basal"]
        sensed = float(round(e))
        sensor = "SEEK" if sensed <= 8 else "WAIT"
        rows[phase] = {
            "true_energy": e, "sensor_reading": sensed,
            "SENSOR_ON": sensor, "SHAM_ON": sensor,
            "SENSOR_MASKED_HIGH": "WAIT", "ALWAYS_SEEK": "SEEK",
            "ALWAYS_WAIT": "WAIT", "EQUAL_INFO_CHEAP_THRESHOLD": sensor,
        }
    if not (rows["LOW"]["true_energy"] == 6.5
            and rows["HIGH"]["true_energy"] == 14.5
            and rows["LOW"]["SENSOR_ON"] == "SEEK"
            and rows["HIGH"]["SENSOR_ON"] == "WAIT"):
        raise V6Rejected("source-shaped first-choice drift")
    return {
        "classification": "V6_B0_TWO_REGIME_SOURCE_CHOICES_QUALIFIABLE",
        "first_choices": rows,
        "source_supported_s_arms": [
            "SENSOR_ON", "SHAM_ON", "SENSOR_MASKED_HIGH", "ALWAYS_SEEK",
        ],
        "oracle_only_controls_not_s_live": [
            "ALWAYS_WAIT", "EQUAL_INFO_CHEAP_THRESHOLD",
        ],
        "b0_equal_info_cheap_tie_allowed": True,
        "ecological_value": "NOT_ATTESTED",
        "native_world_clock_matched": False,
        "new_world_runs": 0, "science_go": False,
    }


def main() -> int:
    print(json.dumps(first_source_choice(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
