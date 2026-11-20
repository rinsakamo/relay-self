from experiments.stage27l3a_capture_validation import validate_capture

ID = "12345678-1234-4234-8234-123456789abc"


def sample():
    return {"request_id": ID, "boot_id": ID, "world_uuid": ID, "player_uuid": ID,
            "start_tick": 42, "end_tick": 42, "body_aabb": [-1, 0, -1, 0, 2, 0],
            "terrain_complete": True, "entities": [], "entity_coverage_complete": True}


def test_missing_and_forged_coverage_fail_closed():
    assert validate_capture(None)["reason"] == "SNAPSHOT_MISSING"
    assert validate_capture(sample()) == {"status": "INCOMPLETE", "reason": "COVERAGE_UNATTESTED"}


def test_identity_tick_and_boxes():
    for key, value, reason in [("request_id", "bad", "INVALID_REQUEST_ID"),
                               ("end_tick", 43, "TICK_MISMATCH"),
                               ("body_aabb", [0, 0, 0, 0, 1, 1], "BODY_AABB_INVALID")]:
        item = sample()
        item[key] = value
        assert validate_capture(item)["reason"] == reason
    assert validate_capture(sample(), "different")["reason"] == "WORLD_MISMATCH"


def test_terrain_and_nonfinite():
    item = sample()
    item["terrain_complete"] = False
    assert validate_capture(item)["reason"] == "TERRAIN_UNAVAILABLE"
    item["body_aabb"][0] = float("nan")
    assert validate_capture(item)["reason"] == "BODY_AABB_INVALID"
