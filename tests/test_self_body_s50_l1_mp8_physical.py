"""MP8 physical preparation tests. All synthetic; none qualify a World."""
import asyncio

import pytest

from adapters.mineflayer.l23_paper_live_assets import (
    L23PaperBlocked,
    wait_paper_line,
)

from adapters.mineflayer.self_body_s50_l1_mp8_physical import (
    SEED,
    attest_surface_lock,
    set_fixed_seed,
    surface_command,
)
from adapters.mineflayer.self_body_s50_l1_paper_dispatch import ForecastDispatchRejected
from tools.l1_mp8_two_world_dev import compare_original_states


def original(mode="ICE", surface="PACKED_ICE", *, seed="1234", world="new-world"):
    m = "PACKED_ICE_5X5" if mode == "ICE" else "GRASS_BLOCK_5X5_READONLY"
    return (
        f"[INFO] S50_DEV_SURFACE_LOCK marker_id=action-1 world={world} "
        f"subject_uuid=subject-1 seed={seed} mode={m} "
        f"original_material=GRASS_BLOCK target_material={surface} "
        "blocks_verified=25 full_time=201 x=0.5 y=-60.0 z=0.5 "
        "yaw=0.0 pitch=0.0 vx=0.0 vy=0.0 vz=0.0 "
        "on_ground=true food=20 health=20.0 game_mode=CREATIVE "
        "floor_x=0 floor_y=-61 floor_z=0 "
        "status=REAL_PAPER_PRE_ACTION_SURFACE_LOCK\n"
    ).encode()


def confirm(data, mode="ICE"):
    return attest_surface_lock(
        data, marker="action-1", world="new-world",
        subject_uuid="subject-1", mode=mode,
    )


def test_modes_only_original_paper_console_commands():
    assert surface_command("action-1", "NORMAL") == (
        "relaydevicefloor action-1 GRASS_BLOCK_5X5_READONLY")
    assert surface_command("action-1", "ICE") == (
        "relaydevicefloor action-1 PACKED_ICE_5X5")
    for mode in ("BLUE_ICE", "SLOWNESS", ""):
        with pytest.raises(ForecastDispatchRejected):
            surface_command("action-1", mode)
    with pytest.raises(ForecastDispatchRejected):
        surface_command("bad\ncommand", "NORMAL")


def test_one_verified_real_paper_source():
    assert confirm(original())["mode"] == "PACKED_ICE_5X5"
    assert confirm(original("NORMAL", "GRASS_BLOCK"), "NORMAL")[
        "target_material"] == "GRASS_BLOCK"


@pytest.mark.parametrize("raw", [
    b"", b"relaydevicefloor action-1 PACKED_ICE_5X5\n",
    original() + original(),
    original(world="foreign"),
    original(seed="NaN"),
    original(surface="STONE"),
    original().replace(b"on_ground=true", b"on_ground=false"),
    original().replace(b"vx=0.0", b"vx=nan"),
    original().replace(b"blocks_verified=25", b"blocks_verified=24"),
])
def test_reject_missing_forged_or_partial_source(raw):
    with pytest.raises(ForecastDispatchRejected):
        confirm(raw)


def test_same_seed_pre_server_config_only(tmp_path):
    properties = tmp_path / "server.properties"
    properties.write_text("server-ip=127.0.0.1\nlevel-type=minecraft:flat\n")
    record = set_fixed_seed(tmp_path)
    assert record["declared_seed"] == SEED
    assert properties.read_text().endswith(f"level-seed={SEED}\n")
    with pytest.raises(ForecastDispatchRejected):
        set_fixed_seed(tmp_path)


def test_reject_unmatched_server_config(tmp_path):
    (tmp_path / "server.properties").write_text(
        "server-ip=127.0.0.1\nlevel-type=minecraft:default\n")
    with pytest.raises(ForecastDispatchRejected):
        set_fixed_seed(tmp_path)


def surface(mode):
    return {"lock": confirm(original(mode,
                 "PACKED_ICE" if mode == "ICE" else "GRASS_BLOCK"), mode),
            "world_uuid": "world-" + mode}


def test_preaction_sampled_match_and_negative_controls():
    a, b = surface("NORMAL"), surface("ICE")
    assert compare_original_states(a, b)["matched"]
    changed = {"lock": {**b["lock"], "x": "0.6"}, "world_uuid": "world-ICE"}
    assert "x" in compare_original_states(a, changed)["mismatches"]
    same = {"lock": b["lock"], "world_uuid": a["world_uuid"]}
    assert "world_uuid_NOT_DISTINCT" in compare_original_states(a, same)[
        "mismatches"]
    changed_seed = {"lock": {**b["lock"], "seed": "42"},
                    "world_uuid": "world-ICE"}
    assert "seed" in compare_original_states(a, changed_seed)["mismatches"]

def test_mp8_new_paper_source_markers_allowed_but_arbitrary_rejected(tmp_path):
    log = tmp_path / "original-paper-console.log"
    log.write_text(
        "[INFO] S50_DEV_NORMAL_FLOOR_VERIFIED marker_id=action-1 "
        "world=live-source status=REAL_PAPER_READONLY_PRE_S49_ACTION\\n"
        "[INFO] S50_DEV_SURFACE_LOCK marker_id=action-1 "
        "world=live-source status=REAL_PAPER_PRE_ACTION_SURFACE_LOCK\\n"
    )
    for kind in ("S50_DEV_NORMAL_FLOOR_VERIFIED", "S50_DEV_SURFACE_LOCK"):
        asyncio.run(wait_paper_line(log, marker="action-1",
                                    kind=kind, timeout_s=0.02))
    with pytest.raises(L23PaperBlocked, match="unapproved"):
        asyncio.run(wait_paper_line(log, marker="action-1",
                                    kind="UNTRUSTED_APP_MARKER", timeout_s=0.02))
