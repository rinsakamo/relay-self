"""DEV comparison of two original S49 Worlds with seven *equal* Paper bonus ticks.

Exact Paper-positive tick count is checked independently per source. This
does NOT synchronize Paper tick phase, Mineflayer physics callbacks or native
Action start/stop, nor attest same-Self recovery of physical P1.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from adapters.mineflayer.s49_p1_synced_motor_pair_dev import (
    review_p1_synced_world_pair_dev,
)


class MatchedBoostDevRejected(ValueError):
    """Paper source failed positive boost count, order, or owner boundary."""


def matched_boost_rows_dev(
    raw: str, *, action_id: str, session_id: str, expected_count: int = 7,
) -> dict:
    if (
        type(raw) is not str or type(action_id) is not str
        or type(session_id) is not str or not action_id or not session_id
        or type(expected_count) is not int or expected_count != 7
    ):
        raise MatchedBoostDevRejected("invalid bounded DEV motor source arguments")
    rows, completes = [], []
    for line in raw.splitlines():
        if "S49_DASH_DEV_TICK " in line:
            payload = line.split("S49_DASH_DEV_TICK ", 1)[1]
            kind = "tick"
        elif "S49_DASH_DEV_COMPLETE " in line:
            payload = line.split("S49_DASH_DEV_COMPLETE ", 1)[1]
            kind = "complete"
        else:
            continue
        try:
            fields = dict(v.split("=", 1) for v in payload.split() if v.count("=") == 1)
        except ValueError as exc:
            raise MatchedBoostDevRejected("malformed Paper tick row") from exc
        if fields.get("action_id") != action_id:
            continue
        if fields.get("session_id") != session_id:
            raise MatchedBoostDevRejected("foreign original S49 Paper motor session")
        if kind == "complete":
            completes.append(fields)
        else:
            rows.append(fields)
    if len(completes) != 1 or not 10 <= len(rows) <= 40:
        raise MatchedBoostDevRejected("incomplete original S49 Paper motor series")
    release = completes[0]
    if (
        release.get("reason") != "OWNER_RELEASE"
        or release.get("p1_matched_boost_cap") != "7"
        or release.get("p1_matched_boost_cap_reached") != "true"
        or release.get("forward_boost_ticks") != "7"
        or release.get("modifier_applied") != "false"
        or release.get("P1_APPLIED") != "false"
        or release.get("M0_POSTED") != "false"
    ):
        raise MatchedBoostDevRejected("Paper duration cap not verified")
    positive, all_ticks = [], []
    last_index, last_tick, actor_world, actor_player = 0, None, None, None
    for item in rows:
        try:
            index = int(item["index"])
            wtick = int(item["tick"])
            p1_index = int(item["p1_world_ticks"])
            boosted = item["modifier_applied"]
            speed = float(item["sampled_speed_mps"])
            power = float(item["p1_current_applied_power"])
        except (ValueError, KeyError, TypeError) as exc:
            raise MatchedBoostDevRejected("Paper typed tick row invalid") from exc
        if (
            index != last_index + 1 or p1_index != index
            or (last_tick is not None and wtick != last_tick + 1)
            or not 0 <= speed < 100 or not math.isfinite(speed)
            or not math.isfinite(power) or not 0 <= power <= 1
            or boosted not in ("true", "false")
            or (boosted == "true") != (power > 0)
            or item.get("p1_motor_dev") != "true"
        ):
            raise MatchedBoostDevRejected("Paper tick gap, replay or boost mismatch")
        if actor_world is None:
            actor_world = item.get("world")
            actor_player = item.get("player_uuid")
        if (
            not actor_world or not actor_player
            or item.get("world") != actor_world
            or item.get("player_uuid") != actor_player
        ):
            raise MatchedBoostDevRejected("Paper actor/world changed mid motor")
        all_ticks.append((wtick, index, speed))
        if boosted == "true":
            positive.append((wtick, index, speed, power))
        last_tick, last_index = wtick, index
    if (
        len(positive) != expected_count
        or release.get("world") != actor_world
        or release.get("player_uuid") != actor_player
        or int(release.get("p1_world_ticks", -1)) != len(rows)
        or any(b[0] != a[0] + 1 for a, b in zip(positive, positive[1:]))
        or any(b[1] != a[1] + 1 for a, b in zip(positive, positive[1:]))
    ):
        raise MatchedBoostDevRejected("not exactly seven contiguous source bonus ticks")
    if (
        positive[-1][1] >= len(rows)
        or any(x[1] > positive[-1][1] and x[1] <= len(rows) and
               x[0] <= positive[-1][0] for x in all_ticks)
    ):
        raise MatchedBoostDevRejected("no observed cap-release tick after bonus")
    speeds = [v[2] for v in positive]
    powers = [v[3] for v in positive]
    return {
        "classification": "P1_ORIGINAL_S49_PAPER_SEVEN_BONUS_TICKS_SOURCE_VERIFIED_DEV",
        "action_id": action_id,
        "session_id": session_id,
        "world": actor_world,
        "player_uuid": actor_player,
        "paper_source_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "exact_paper_positive_bonus_ticks": len(positive),
        "positive_first_tick": positive[0][0],
        "positive_last_tick": positive[-1][0],
        "positive_first_index": positive[0][1],
        "positive_last_index": positive[-1][1],
        "paper_total_gait_ticks": len(rows),
        "matched_positive_speed_by_ordinal_mps": speeds,
        "matched_positive_power_by_ordinal": powers,
        "matched_positive_speed_mean_mps": sum(speeds) / len(speeds),
        "paper_action_owner_issued": False,
        "same_world_tick_clock_as_other_world": False,
        "qualification_go": False,
        "science_go": False,
    }


def compare_matched_boost_pairs_dev(synced: dict, source: dict[str, dict]) -> dict:
    if (
        type(synced) is not dict or type(source) is not dict
        or set(source) != {"CARRY", "WAIT_ASSUMED"}
        or synced.get("classification")
           != "P1_SYNCED_TWO_MODEL_WORLD_PHYSICAL_DASH_SENSITIVITY_DEV_ONLY"
        or synced.get("model_f_preloaded_not_lived") is not True
        or synced.get("same_self_longitudinal_wait_recovery_observed") is not False
        or synced.get("paper_node_clocks_synchronized") is not False
        or synced.get("fatigue_recovery_causally_identified") is not False
        or synced.get("l0_physical_dash_power_admission") is not None
        or synced.get("new_native_action_issuers") != 0
        or synced.get("new_native_packet_readers") != 0
        or synced.get("r_qualified_wait_ticks") != 0
        or synced.get("qualification_go") is not False
        or synced.get("science_go") is not False
    ):
        raise MatchedBoostDevRejected("prior native source pair was promoted")
    for case in ("CARRY", "WAIT_ASSUMED"):
        x, y = synced.get("arms", {}).get(case), source[case]
        if (
            type(x) is not dict or type(y) is not dict
            or y.get("classification")
               != "P1_ORIGINAL_S49_PAPER_SEVEN_BONUS_TICKS_SOURCE_VERIFIED_DEV"
            or y.get("action_id") != x.get("first_action_id")
            or y.get("session_id") != x.get("session_id")
            or y.get("world") != x.get("paper_world_uuid")
            or y.get("exact_paper_positive_bonus_ticks") != 7
            or y.get("paper_action_owner_issued") is not False
            or y.get("same_world_tick_clock_as_other_world") is not False
            or y.get("qualification_go") is not False
            or y.get("science_go") is not False
            or not isinstance(y.get("matched_positive_speed_by_ordinal_mps"), list)
            or not isinstance(y.get("matched_positive_power_by_ordinal"), list)
            or len(y["matched_positive_speed_by_ordinal_mps"]) != 7
            or len(y["matched_positive_power_by_ordinal"]) != 7
            or abs(y["matched_positive_power_by_ordinal"][0]
                   - x.get("paper_first_applied_power", 0)) > 1e-10
        ):
            raise MatchedBoostDevRejected(f"{case} Paper positive cap source not bound")
    a, b = source["CARRY"], source["WAIT_ASSUMED"]
    paired_speeds = [
        post - base for base, post in zip(
            a["matched_positive_speed_by_ordinal_mps"],
            b["matched_positive_speed_by_ordinal_mps"],
        )
    ]
    paired_powers = [
        post - base for base, post in zip(
            a["matched_positive_power_by_ordinal"],
            b["matched_positive_power_by_ordinal"],
        )
    ]
    if (
        any(not math.isfinite(x) for x in paired_speeds + paired_powers)
        or min(paired_powers) < 0.1
    ):
        raise MatchedBoostDevRejected("matched F model power never separated")
    return {
        "classification": "P1_TWO_INDEPENDENT_WORLDS_MATCHED_SEVEN_BONUS_TICKS_DEV_ONLY",
        "arms": source,
        "native_original_s16_displacement_gain_m":
            synced["actual_first_s16_displacement_gain_m"],
        "positive_matched_paper_speed_delta_by_ordinal_mps": paired_speeds,
        "positive_matched_paper_power_delta_by_ordinal": paired_powers,
        "mean_matched_positive_paper_speed_delta_mps":
            sum(paired_speeds) / len(paired_speeds),
        "mean_matched_positive_paper_power_delta":
            sum(paired_powers) / len(paired_powers),
        "original_s49_first_action_duration_matched_by_world_tick": False,
        "same_number_of_positive_paper_boost_ticks": True,
        "client_boost_physics_tick_counts_equal_not_required": True,
        "world_clock_phase_matched": False,
        "matched_ordinal_not_same_absolute_world_tick": True,
        "model_preload_not_actual_longitudinal_p1_recovery": True,
        "native_displacement_causally_attributed_only_to_p1": False,
        "physical_l0_dash_power_admission": None,
        "m0_or_p1_extra_postings": 0,
        "new_action_issuers": 0,
        "r_qualified_wait_ticks": 0,
        "qualification_go": False,
        "science_go": False,
    }


def review_p1_matched_boost_worlds_dev(root: Path) -> dict:
    if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
        raise MatchedBoostDevRejected("not original disposable World source root")
    synced = review_p1_synced_world_pair_dev(root)
    sources = {}
    for case in ("CARRY", "WAIT_ASSUMED"):
        arm = synced["arms"][case]
        path = root / case / "paper_server.log"
        if path.is_symlink() or not path.is_file():
            raise MatchedBoostDevRejected("Paper raw log absent")
        sources[case] = matched_boost_rows_dev(
            path.read_text(encoding="utf-8"),
            action_id=arm["first_action_id"],
            session_id=arm["session_id"],
        )
    out = compare_matched_boost_pairs_dev(synced, sources)
    (root / "p1_matched_boost_world_comparison_dev.json").write_text(
        json.dumps(out, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review_p1_matched_boost_worlds_dev(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
