"""Conservative offline validation of the current Paper capture protocol.

No current provider establishes entity coverage or non-loading shape reads.
This validator therefore cannot grant COMPLETE on this protocol version.
"""
import math
import uuid


def _uuid(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def _box(value):
    return (isinstance(value, list) and len(value) == 6
            and all(type(v) in (int, float) and math.isfinite(v) for v in value)
            and all(value[i] < value[i + 3] for i in range(3)))


def validate_capture(snapshot, expected_world_uuid=None):
    """Return a status and reason; missing information never becomes COMPLETE."""
    if snapshot is None:
        return {"status": "INCOMPLETE", "reason": "SNAPSHOT_MISSING"}
    if not isinstance(snapshot, dict):
        return {"status": "INVALID", "reason": "SNAPSHOT_TYPE"}
    for key in ("request_id", "boot_id", "world_uuid", "player_uuid"):
        if key not in snapshot:
            return {"status": "INCOMPLETE", "reason": "MISSING_" + key.upper()}
        if not _uuid(snapshot[key]):
            return {"status": "INVALID", "reason": "INVALID_" + key.upper()}
    if expected_world_uuid is not None and snapshot["world_uuid"] != expected_world_uuid:
        return {"status": "INVALID", "reason": "WORLD_MISMATCH"}
    for key in ("start_tick", "end_tick"):
        if key not in snapshot:
            return {"status": "INCOMPLETE", "reason": "MISSING_" + key.upper()}
        if type(snapshot[key]) is not int:
            return {"status": "INVALID", "reason": "INVALID_" + key.upper()}
    if snapshot["start_tick"] != snapshot["end_tick"]:
        return {"status": "INVALID", "reason": "TICK_MISMATCH"}
    if "body_aabb" not in snapshot:
        return {"status": "INCOMPLETE", "reason": "BODY_AABB_MISSING"}
    if not _box(snapshot["body_aabb"]):
        return {"status": "INVALID", "reason": "BODY_AABB_INVALID"}
    if snapshot.get("terrain_complete") is not True:
        return {"status": "INCOMPLETE", "reason": "TERRAIN_UNAVAILABLE"}
    return {"status": "INCOMPLETE", "reason": "COVERAGE_UNATTESTED"}
