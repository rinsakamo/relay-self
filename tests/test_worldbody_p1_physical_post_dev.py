"""Original pinned P1 World log algebra and S49 same-World source negatives."""
from __future__ import annotations

from copy import deepcopy

import pytest

from tools.worldbody_p1_physical_post_dev import (
    P1PhysicalPostRejected,
    inspect_original_p1_physical_dev,
)

SESSION = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
WORLD = "11111111-2222-3333-4444-555555555555"
PLAYER = "99999999-aaaa-bbbb-cccc-111111111111"
NONCE = SESSION.replace("-", "")[:20]
HEAD = "0ab76b4e46efd914877e543a65de58b6cfc71326"
SHA = "d23f1f595095adb1da0b3ce74a72803b85b68359dc94d2ee8b03fcd2078f68b0"


def report() -> dict:
    return {
        "session_id": SESSION,
        "worldbody_p1_source_nonce": NONCE,
        "status": "PASS",
        "classification": "DEV_ONLY_PINNED_P1_WORLD_PHYSICAL_CAP_NATIVE_S49",
        "worldbody_profile": "PINNED_ORIGINAL_P1_PER_WORLD_TICK_CAP_DEV",
        "worldbody_p1_physics_dev": True,
        "worldbody_p1_same_world_source_dev": True,
        "worldbody_true_fatigue_received_by_self": False,
        "worldbody_physics_write_from_self": False,
        "worldbody_postmove_l0_choice": {
            "selected": "WAIT", "rest_action_issued": False,
        },
        "worldbody_rest_action_count": 0,
        "actual_native_actions": [
            {"action": "s49-native-move-19", "event_seq": 19,
             "source": SESSION, "terminal": "outcome", "movement_m": 0.32},
            {"action": "s49-native-move-50", "event_seq": 50,
             "source": SESSION, "terminal": "outcome", "movement_m": 0.28},
        ],
    }


def log() -> str:
    out = [
        f"P1WORLD_READY original_p1={HEAD} profile={SHA} "
        "legacy_worldbody_active=false world_rates_self_mutable=false "
        "source_qualification=DEV_UNATTESTED",
        f"S49P1_START nonce={NONCE} world={WORLD} tick=100 "
        f"player={PLAYER} coverage=SERVER_TICK_CALLBACK_NOT_FULL_TICK",
        f"P1WORLD_ATTACH nonce={NONCE} world={WORLD} player={PLAYER} "
        f"tick=100 original_p1={HEAD} enabled_profile_sha={SHA} "
        "independent_s_r_attestation=false",
    ]
    markers = [
        (102, "begin", "s49-native-move-19"),
        (106, "closed", "s49-native-move-19"),
        (108, "begin", "s49-native-move-50"),
        (111, "closed", "s49-native-move-50"),
    ]
    for tick, phase, action in markers:
        out.append(
            f"P1WORLD_S49_ACTION nonce={NONCE} world={WORLD} tick={tick} "
            f"phase={phase} action={action}"
        )
        out.append(
            f"S49P1_ACTION nonce={NONCE} world={WORLD} tick={tick} "
            f"index={tick-100} phase={phase} action={action}"
        )
    out.append(
        f"S49P1_CHOICE nonce={NONCE} world={WORLD} tick=113 "
        "index=13 selected=WAIT"
    )
    fatigue = 0.0
    activities = {"MOVE": 0, "WAIT": 0, "FIGHT": 0}
    for tick in range(101, 119):
        dist = 0.5 if tick == 103 else 0.2 if tick == 109 else 0.0
        blocked = tick == 104
        kind = "MOVE" if dist or blocked else "WAIT"
        recovery = 0.0
        if kind == "MOVE":
            fatigue = min(1.0, fatigue + dist * 0.04)
        else:
            recovery = min(fatigue, 0.1)
            fatigue -= recovery
        cap = max(0.2, 1.0 - 0.7 * fatigue)
        activities[kind] += 1
        out.append(
            f"P1WORLD_TICK nonce={NONCE} world={WORLD} tick={tick} "
            f"activity={kind} accepted_blocks={dist} "
            f"blocked={str(blocked).lower()} truth_fatigue={fatigue} "
            f"p1_cap_blocks={cap} recovered={recovery} r_qualified=false"
        )
        out.append(
            f"S49P1_TICK nonce={NONCE} world={WORLD} tick={tick} "
            f"index={tick-100} x=2.5 y=-60 z=0.5 "
            f"move_events={int(dist>0)} move_distance={dist} "
            "fight_events=0 swing_events=0 interact_events=0 "
            "velocity_events=0 teleport_events=0 player_damage_events=0 "
            "sprint=false sneak=false swimming=false"
        )
    out.append(
        f"P1WORLD_STOP nonce={NONCE} world={WORLD} tick=119 "
        f"committed=18 move={activities['MOVE']} fight=0 "
        f"wait_candidate={activities['WAIT']} cap_applied=0 "
        "independent_s_r_attestation=false"
    )
    out.append(
        f"S49P1_STOP nonce={NONCE} world={WORLD} tick=119 index=18 "
        "faults=0 coverage=SERVER_TICK_CALLBACK_NOT_FULL_TICK"
    )
    return "\n".join(out)


def test_original_p1_world_math_and_s49_source_join_remain_dev_only():
    result = inspect_original_p1_physical_dev(report(), log())
    assert result["p1_world_physics_installed"] is True
    assert result["paper_p1_tick_count"] == 18
    assert result["paper_original_callback_tick_count"] == 18
    assert result["activity_counts"] == {"MOVE": 3, "WAIT": 15, "FIGHT": 0}
    assert result["p1_b_source_bound_tick_formally_admitted"] == 0
    assert result["full_tick_wait_independently_r_attested"] is False
    assert result["native_speed_loss_caused_by_p1_cap_proven"] is False
    assert result["qualification_go"] is False


@pytest.mark.parametrize("variant", [
    "other-world", "different-native-session", "wrong-profile",
    "fabricated-fatigue", "false-wait-credit", "missing-paper-tick",
    "missing-p1-stop", "missing-s49-stop", "other-action",
    "wrong-rest-choice", "unqualified-flag", "nonzero-actions",
])
def test_bad_p1_physical_receipts_fail_closed(variant):
    raw = log()
    original = deepcopy(report())
    if variant == "other-world":
        raw = raw.replace(
            f"P1WORLD_ATTACH nonce={NONCE} world={WORLD}",
            f"P1WORLD_ATTACH nonce={NONCE} world={PLAYER}",
        )
    elif variant == "different-native-session":
        original["session_id"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeef"
    elif variant == "wrong-profile":
        raw = raw.replace(f"enabled_profile_sha={SHA}", "enabled_profile_sha=bad")
    elif variant == "fabricated-fatigue":
        raw = raw.replace("truth_fatigue=0.02", "truth_fatigue=0.70")
    elif variant == "false-wait-credit":
        raw = raw.replace("recovered=0.0", "recovered=0.1", 1)
    elif variant == "missing-paper-tick":
        raw = "\n".join(
            line for line in raw.splitlines()
            if "S49P1_TICK " not in line or "tick=107 " not in line
        )
    elif variant == "missing-p1-stop":
        raw = "\n".join(line for line in raw.splitlines()
                        if "P1WORLD_STOP " not in line)
    elif variant == "missing-s49-stop":
        raw = "\n".join(line for line in raw.splitlines()
                        if "S49P1_STOP " not in line)
    elif variant == "other-action":
        raw = raw.replace("action=s49-native-move-50", "action=forged")
    elif variant == "wrong-rest-choice":
        raw = raw.replace("selected=WAIT", "selected=REST")
    elif variant == "unqualified-flag":
        raw = raw.replace("r_qualified=false", "r_qualified=true", 1)
    else:
        original["worldbody_rest_action_count"] = 1
    with pytest.raises(P1PhysicalPostRejected):
        inspect_original_p1_physical_dev(original, raw)
