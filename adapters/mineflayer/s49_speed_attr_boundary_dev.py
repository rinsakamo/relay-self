"""DEV-only Node-local trace audit across Paper attribute -> Mineflayer physics.

Data is from the already-existing S49 Mineflayer bot. No new packet
receiver, native Action, source-bound World tick, or physiological P1 sensor.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


class SpeedAttrBoundaryRejected(ValueError):
    pass


def _attr_boost(value: object) -> float | None:
    if value is None:
        return None
    if (type(value) is not dict or type(value.get("value")) not in (int, float)
            or not math.isfinite(value["value"])
            or not 0.099 < value["value"] < 0.101
            or type(value.get("modifiers")) is not list
            or len(value["modifiers"]) > 5):
        raise SpeedAttrBoundaryRejected("malformed native speed attribute")
    boosts = []
    for mod in value["modifiers"]:
        if (type(mod) is not dict
                or type(mod.get("uuid")) is not str
                or type(mod.get("amount")) not in (int, float)
                or not math.isfinite(mod["amount"])
                or type(mod.get("operation")) is not int):
            raise SpeedAttrBoundaryRejected("untrusted attribute modifier")
        if mod["uuid"] == "relays49dashdev:forward_dash_only":
            if mod["operation"] != 2 or not 0 < mod["amount"] <= .5:
                raise SpeedAttrBoundaryRejected("invalid Paper DASH source")
            boosts.append(mod["amount"])
    if len(boosts) > 1:
        raise SpeedAttrBoundaryRejected("duplicated speed bonus")
    return boosts[0] if boosts else 0.


def review_speed_attr_boundary_dev(
    path: Path, *, session_id: str, action_id: str, sync_expected: bool,
) -> dict:
    if (not isinstance(path, Path) or path.is_symlink() or not path.is_file()
            or path.stat().st_size > 170_000 or path.stat().st_size < 200
            or type(session_id) is not str or not session_id
            or type(action_id) is not str or not action_id
            or type(sync_expected) is not bool):
        raise SpeedAttrBoundaryRejected("no authentic-shape local trace")
    try:
        trace = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SpeedAttrBoundaryRejected("unreadable bounded Node trace") from exc
    if (
        type(trace) is not dict
        or trace.get("version") != "S49_SPEED_ATTR_NATIVE_BOUNDARY_DEV_V1"
        or trace.get("session_id") != session_id
        or trace.get("action_id") != action_id
        or trace.get("sync_enabled") is not sync_expected
        or trace.get("source_attested") is not False
        or trace.get("paper_clock_synchronized") is not False
        or trace.get("added_issuers") != 0
        or trace.get("added_readers") != 0
        or trace.get("complete") is not True
        or type(trace.get("physics_ticks")) is not int
        or trace["physics_ticks"] < 3
        or type(trace.get("rows")) is not list
        or not 5 <= len(trace["rows"]) <= 120
    ):
        raise SpeedAttrBoundaryRejected("trace owner or completion mismatch")
    packet_boosts, generic_boosts, target_boosts, physics_boosts = [], [], [], []
    physics = []
    last_time = None
    for n, row in enumerate(trace["rows"], 1):
        if (type(row) is not dict or row.get("ordinal") != n
                or row.get("kind") not in (
                    "FIRST_ORIGINAL_SET", "RAW_PACKET", "DECODED_ATTR",
                    "ACTIVE_PHYSICS", "FIRST_ORIGINAL_CLEAR",
                )
                or type(row.get("monotonic_ms")) is not int
                or (last_time is not None and row["monotonic_ms"] < last_time)):
            raise SpeedAttrBoundaryRejected("Node event order or source shape changed")
        last_time = row["monotonic_ms"]
        raw = row.get("raw_generic_scale")
        target = row.get("physics_movement_speed")
        generic_boosts.append(_attr_boost(raw))
        target_boosts.append(_attr_boost(target))
        if row["kind"] == "RAW_PACKET":
            items = row.get("packet_properties")
            if type(items) is not list or not 1 <= len(items) <= 4:
                raise SpeedAttrBoundaryRejected("source packet omitted")
            for item in items:
                if type(item) is not dict or item.get("key") not in (
                    "generic.scale", "minecraft:movement_speed",
                ):
                    raise SpeedAttrBoundaryRejected("unexpected source attribute")
                packet_boosts.append(_attr_boost({
                    "value": item.get("value"), "modifiers": item.get("modifiers"),
                }))
        if row["kind"] == "ACTIVE_PHYSICS":
            if (row.get("forward") is not True or row.get("sprint") is not True
                    or type(row.get("physics_ordinal")) is not int
                    or row["physics_ordinal"] != len(physics) + 1):
                raise SpeedAttrBoundaryRejected("foreign physical motor phase")
            for key in ("x", "z", "vx", "vz"):
                if (type(row.get(key)) not in (float, int)
                        or not math.isfinite(row[key])):
                    raise SpeedAttrBoundaryRejected("invalid Mineflayer motion")
            physics.append(row)
            physics_boosts.append(_attr_boost(target))
    if (trace["rows"][0]["kind"] != "FIRST_ORIGINAL_SET"
            or trace["rows"][-1]["kind"] != "FIRST_ORIGINAL_CLEAR"
            or len(physics) != trace["physics_ticks"]):
        raise SpeedAttrBoundaryRejected("first original native control not bracketed")
    def positive(xs):
        return sum(v is not None and v > 0 for v in xs)
    displacement = math.hypot(
        physics[-1]["x"] - physics[0]["x"],
        physics[-1]["z"] - physics[0]["z"],
    )
    return {
        "classification": "S49_NODE_PAPER_ATTRIBUTE_TO_PHYSICS_KEY_DIAGNOSTIC_DEV_ONLY",
        "session_id": session_id, "action_id": action_id,
        "native_sync_enabled": sync_expected,
        "node_packet_paper_dash_seen_count": positive(packet_boosts),
        "node_decoded_generic_dash_seen_count": positive(generic_boosts),
        "node_projected_physics_dash_seen_count": positive(target_boosts),
        "node_active_physics_key_dash_seen_count": positive(physics_boosts),
        "node_physics_ticks_sampled": len(physics),
        "node_local_active_displacement_m": displacement,
        "paper_native_clock_same_epoch": False,
        "physics_speed_attribute_consumed_proven": False,
        "no_additional_packet_reader": True,
        "physical_fatigue_attested": False,
        "native_action_changed": False,
        "actual_p1_state_updated": False,
        "qualification_go": False, "science_go": False,
    }
