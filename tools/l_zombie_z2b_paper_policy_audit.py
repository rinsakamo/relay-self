"""Independent L-Z2b Paper policy freeze + CHEAP score readback.

Only a *separately* validated original real Gemma packet may qualify this
as a prepared-model-selected policy. A shaped Paper log or SHA alone does
not prove model identity, process custody or L2 online reasoning.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from adapters.mineflayer.l_zombie_z2b_policy_contract import (
    PreparedZombiePolicy,
    prediction_from_prior,
)
from tools.l_zombie_paper_original_audit import PaperZombieSourceRejected
from tools.l_zombie_z2a_prospective_audit import (
    FLOAT_EPS,
    TICK,
    _finite_number,
    _row,
    _strict_int,
    audit_z2a_prospective,
)
from tools.l_zombie_z2b_prepare_gemma import verify_prepared_archive

PREPARED = "L_ZOMBIE_PREPARED_L2_FREEZE_V3 "
KEYS = {
    "marker", "session", "world", "entity_uuid", "entity_id",
    "issued_tick", "target_tick", "policy_sha256", "strategy", "speed",
    "player_x", "player_z", "predicted_x", "predicted_z",
}



def _prepared_line(line: str) -> dict[str, str]:
    """V3 fields use numeric names such as policy_sha256."""
    bits = line.split(PREPARED, 1)[1].split(" ")
    if any(re.fullmatch(r"[a-z0-9_]+=[^\s=]+", p) is None for p in bits):
        raise PaperZombieSourceRejected("malformed prepared policy Paper source")
    obj = dict(p.split("=", 1) for p in bits)
    if len(obj) != len(bits):
        raise PaperZombieSourceRejected("duplicate prepared policy source field")
    return obj

def audit_prepared_l2_world(
    original: bytes, *, sha256: str, marker: str, session: str,
    prepared: PreparedZombiePolicy,
) -> dict:
    """Read original 31 Paper ticks, exactly one CHEAP and one L2 policy freeze."""
    if not isinstance(prepared, PreparedZombiePolicy):
        raise PaperZombieSourceRejected("typed original prepared policy needed")
    cheap = audit_z2a_prospective(
        original, sha256=sha256, marker=marker, session=session,
    )
    lines = original.decode("utf-8", errors="strict").splitlines()
    candidates = []
    offsets = {}
    for line_number, line in enumerate(lines):
        if PREPARED in line:
            candidates.append((line_number, _prepared_line(line)))
        if TICK in line:
            point = _row(line, TICK)
            if point.get("marker") == marker and point.get("session") == session:
                idx = _strict_int(point, "offset")
                if idx in offsets:
                    raise PaperZombieSourceRejected("duplicate tick/offset")
                offsets[idx] = (line_number, point)
    if len(candidates) != 1 or set(offsets) != set(range(31)):
        raise PaperZombieSourceRejected("one prepared-L2 original before target required")
    index, packet = candidates[0]
    if (
        set(packet) != KEYS
        or packet.get("marker") != marker
        or packet.get("session") != session
        or packet.get("world") != cheap["world_uuid"]
        or packet.get("entity_uuid") != cheap["entity_uuid"]
        or _strict_int(packet, "entity_id") != cheap["entity_id"]
        or _strict_int(packet, "issued_tick") != cheap["issued_tick"]
        or _strict_int(packet, "target_tick") != cheap["target_tick"]
        or packet.get("policy_sha256") != prepared.policy_sha256
        or packet.get("strategy") != prepared.strategy
        or not offsets[10][0] < index < offsets[11][0]
    ):
        raise PaperZombieSourceRejected("prepared policy wrong owner, time or future-leaking freeze")
    if prepared.strategy == "TARGET_APPROACH":
        speed = _finite_number(packet, "speed")
        if abs(speed - prepared.speed_m_per_tick) > FLOAT_EPS:
            raise PaperZombieSourceRejected("prepared-model speed changed")
    elif packet["speed"] != "none":
        raise PaperZombieSourceRejected("nonapproach strategy must not carry velocity")
    _, first = offsets[0]
    _, at_freeze = offsets[10]
    player_xz = (_finite_number(packet, "player_x"), _finite_number(packet, "player_z"))
    earlier = (_finite_number(first, "x"), _finite_number(first, "z"))
    current = (_finite_number(at_freeze, "x"), _finite_number(at_freeze, "z"))
    expected = prediction_from_prior(
        prepared, first_xz=earlier, issued_xz=current,
        player_xz=player_xz,
    )
    if expected is None:
        if packet["predicted_x"] != "null" or packet["predicted_z"] != "null":
            raise PaperZombieSourceRejected("unscorable Gemma policy must abstain without numbers")
        predicted = None
        model_error = None
    else:
        predicted = (
            _finite_number(packet, "predicted_x"),
            _finite_number(packet, "predicted_z"),
        )
        if math.dist(predicted, expected) > FLOAT_EPS:
            raise PaperZombieSourceRejected("frozen L2 policy computation mismatches pre-outcome inputs")
        model_error = math.dist(predicted, cheap["original_target_xz_m"])
    return {
        "schema": "L_ZOMBIE_Z2B_PREPARED_POLICY_WORLD_V3",
        "classification": (
            "Z2B_PAPER_PREPARED_L2_POLICY_SCORED_SOURCE_ONLY"
            if predicted is not None else
            "Z2B_PAPER_PREPARED_L2_POLICY_ABSTAIN_SOURCE_ONLY"
        ),
        "original_paper_sha256": sha256,
        "policy_sha256": prepared.policy_sha256,
        "model_request_sha256": prepared.model_request_sha256,
        "model_response_sha256": prepared.model_response_sha256,
        "world_uuid": cheap["world_uuid"],
        "zombie_uuid": cheap["entity_uuid"],
        "source_first_tick": cheap["issued_tick"] - 10,
        "issued_tick": cheap["issued_tick"],
        "target_tick": cheap["target_tick"],
        "frozen_before_next_tick": True,
        "forecast_kind": "ZOMBIE_HORIZONTAL_XZ_METERS",
        "strategy": prepared.strategy,
        "player_xz_m": player_xz,
        "model_prepared_xz_m": predicted,
        "future_actual_xz_m": cheap["original_target_xz_m"],
        "prepared_policy_error_m": model_error,
        "cheap_stationary_error_m": cheap["stationary_error_m"],
        "cheap_velocity_error_m": cheap["constant_velocity_error_m"],
        "prepared_policy_owner": "EARLIER_EPOCH_MODEL_PREPARED_SHADOW",
        "model_live_in_world_calls": 0,
        "model_original_wire_cryptographically_joined_by_this_parser": False,
        "actual_real_gguf_mapping_verified_by_this_parser": False,
        "native_mineflayer_exact_paper_tick_join": False,
        "self_action_count": 0,
        "learning_admission": False,
        "l0_promotion": False,
        "qualification_go": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-original", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--marker", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--prepared-root", type=Path, required=True)
    parser.add_argument("--z1b-paper-original", type=Path, required=True)
    parser.add_argument("--z2a-paper-original", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        for path in (args.paper_original, args.report):
            if not path.is_absolute() or path.is_symlink():
                raise PaperZombieSourceRejected("absolute non-symlink source required")
        if args.report.exists() or args.report == args.paper_original:
            raise PaperZombieSourceRejected("exclusive independent source report required")
        packet = verify_prepared_archive(
            prepared_root=args.prepared_root,
            z1b_original=args.z1b_paper_original,
            z2a_original=args.z2a_paper_original,
        )
        report = audit_prepared_l2_world(
            args.paper_original.read_bytes(), sha256=args.sha256,
            marker=args.marker, session=args.session, prepared=packet,
        )
        # Strict raw original + model wire readback completed before report.
        report["model_original_wire_cryptographically_joined_by_this_parser"] = True
        with args.report.open("x", encoding="utf-8") as dest:
            json.dump(report, dest, indent=2, sort_keys=True)
            dest.write("\n")
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"Z2B_PREPARED_L2_WORLD_AUDIT_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "classification": report["classification"],
        "prepared_policy_error_m": report["prepared_policy_error_m"],
        "cheap_stationary_error_m": report["cheap_stationary_error_m"],
        "cheap_velocity_error_m": report["cheap_velocity_error_m"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
