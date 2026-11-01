"""MP9: immutable MP8 body-experience priors and readonly surface selector.

Shadow only: no native Action, S10/S11/L10 admission, or qualified physics.
A surface cue is an original-paper pre-action source, not a new SelfBody owner.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from adapters.mineflayer.self_body_s50_l1_mp8_transfer import _fit_slope, _git_blob_sha, _series

SOURCE_BLOB_SHA1 = "24d38edd73ab1bebd61c7d9819e53fea7f1863b8"
SOURCE_RUN_ID = 41279293497
SOURCE_HEAD = "180967d162481336e9b306dcebc7dac06e312db6"
SOURCE_PATH = (Path(__file__).resolve().parents[2] /
               "docs/evidence/issue653-mp8-matched-20261101/"
               "success-run-41279293497/independent-physical-readback.json")


class MP9Rejected(ValueError):
    """Unqualified source/condition/identity or post-freeze mutation."""


@dataclass(frozen=True)
class SurfacePriors:
    source_sha1: str
    source_worlds: tuple[str, str]
    normal_slope: float
    ice_slope: float
    pairs_per_surface: int
    status: str = "DEV_ARCHIVAL_TRAINING_FIT_ONLY"


@dataclass(frozen=True)
class ShadowTicket:
    world_uuid: str
    subject_uuid: str
    surface: str
    selected_slope: float
    normal_slope: float
    ice_slope: float
    prior_source_sha1: str
    ticket_sha256: str
    decision: str = "PAPER_SOURCE_CONDITIONED_READONLY_SHADOW"
    qualification: str = "NO_GO"


def train_mp8_only(path: Path = SOURCE_PATH) -> SurfacePriors:
    if not isinstance(path, Path) or not path.is_file() or path.is_symlink():
        raise MP9Rejected("MP8 original readback is unavailable or a symlink")
    raw = path.read_bytes()
    if not 0 < len(raw) <= 1_000_000 or _git_blob_sha(raw) != SOURCE_BLOB_SHA1:
        raise MP9Rejected("MP8 source blob changed or unverified")
    try:
        data = json.loads(raw)
        original = data["source_readback"]
        normal = original["normal"]
        ice = original["ice"]
        movements = data["motion"]
    except (ValueError, KeyError, TypeError) as exc:
        raise MP9Rejected("MP8 incomplete source") from exc
    if (
        data.get("schema") != "RELAYSELF_MP8_MATCHED_SURFACE_REAL_WORLD_DEV_READBACK_V1"
        or data.get("run_id") != SOURCE_RUN_ID
        or data.get("executing_head") != SOURCE_HEAD
        or data.get("accepted_new_worlds") != 2
        or data.get("original_s49_actions") != 2
        or data.get("retry_count_within_run") != 0
        or original.get("physical_pair_lock_match") is not True
        or original.get("original_stdout_equals_reported_log") is not True
        or normal.get("mode") != "GRASS_BLOCK_5X5_READONLY"
        or ice.get("mode") != "PACKED_ICE_5X5"
        or normal.get("actual_underfoot") != "GRASS_BLOCK"
        or ice.get("actual_underfoot") != "PACKED_ICE"
        or normal.get("world_uuid") == ice.get("world_uuid")
        or any(row.get("paper_wait_ticks") != 8
               or row.get("forecasts_fixed") != 7
               or row.get("forecasts_scored") != 7
               or row.get("node_exit") != 0 or row.get("java_exit") != 0
               for row in (normal, ice))
    ):
        raise MP9Rejected("MP8 previous real paired source was not accepted")
    try:
        slope_normal = _fit_slope(_series(movements["normal_wait_m"]))
        slope_ice = _fit_slope(_series(movements["ice_wait_m"]))
    except (ValueError, KeyError, TypeError) as exc:
        raise MP9Rejected("MP8 finite motion series missing") from exc
    return SurfacePriors(
        SOURCE_BLOB_SHA1, (normal["world_uuid"], ice["world_uuid"]),
        slope_normal, slope_ice, 7,
    )


def freeze_from_paper_lock(prior: SurfacePriors, lock: dict[str, str],
                           *, mode: str) -> ShadowTicket:
    """Run AFTER Paper lock readback and BEFORE original S49 native Action."""
    if not isinstance(prior, SurfacePriors) or prior != train_mp8_only():
        raise MP9Rejected("foreign or mutated MP8 fitted prior")
    if not isinstance(lock, dict) or mode not in ("NORMAL", "ICE"):
        raise MP9Rejected("no typed condition / original lock")
    surface = "GRASS_BLOCK" if mode == "NORMAL" else "PACKED_ICE"
    expected_mode = "GRASS_BLOCK_5X5_READONLY" if mode == "NORMAL" else "PACKED_ICE_5X5"
    if (
        lock.get("status") != "REAL_PAPER_PRE_ACTION_SURFACE_LOCK"
        or lock.get("mode") != expected_mode
        or lock.get("target_material") != surface
        or lock.get("original_material") != "GRASS_BLOCK"
        or lock.get("blocks_verified") != "25"
        or lock.get("on_ground") != "true"
        or not lock.get("world") or not lock.get("subject_uuid")
        or lock["world"] in prior.source_worlds
    ):
        raise MP9Rejected("unsupported/stale/foreign material and World source")
    selected = prior.normal_slope if mode == "NORMAL" else prior.ice_slope
    fields = {
        "world_uuid": lock["world"], "subject_uuid": lock["subject_uuid"],
        "surface": surface, "selected_slope": selected,
        "normal_slope": prior.normal_slope, "ice_slope": prior.ice_slope,
        "prior_source_sha1": prior.source_sha1,
    }
    digest = hashlib.sha256(
        json.dumps(fields, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()
    return ShadowTicket(**fields, ticket_sha256=digest)


def evaluate_frozen_shadow(prior: SurfacePriors, ticket: ShadowTicket,
                           *, motions: object, verified_surface: str) -> dict:
    """Heldout offline score; authenticity must be supplied by original Paper auditor."""
    if not isinstance(ticket, ShadowTicket) or not isinstance(prior, SurfacePriors):
        raise MP9Rejected("ticket and original prior are required")
    if ticket.prior_source_sha1 != SOURCE_BLOB_SHA1 or prior != train_mp8_only():
        raise MP9Rejected("foreign prior")
    candidate = dict(asdict(ticket))
    candidate.pop("ticket_sha256")
    candidate.pop("decision")
    candidate.pop("qualification")
    digest = hashlib.sha256(
        json.dumps(candidate, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()
    if ticket.ticket_sha256 != digest or verified_surface != ticket.surface:
        raise MP9Rejected("forged ticket or foreign heldout condition")
    expected = prior.normal_slope if ticket.surface == "GRASS_BLOCK" else prior.ice_slope
    if ticket.selected_slope != expected:
        raise MP9Rejected("post-selection mutation or wrong material")
    try:
        movement = _series(motions)
    except ValueError as exc:
        raise MP9Rejected("invalid heldout motion samples") from exc

    def mae(slope: float) -> float:
        return sum(abs(slope * x - y) for x, y in zip(movement[:-1], movement[1:])) / 7

    return {
        "mode": ticket.surface,
        "ticket_sha256": ticket.ticket_sha256,
        "selected_mae_m": mae(ticket.selected_slope),
        "always_normal_mae_m": mae(prior.normal_slope),
        "always_ice_mae_m": mae(prior.ice_slope),
        "zero_mae_m": sum(movement[1:]) / 7,
        "last_mae_m": sum(abs(x-y) for x,y in zip(movement[:-1],movement[1:])) / 7,
        "same_information_cheap_material_rule": "MATHEMATICALLY_EQUIVALENT",
        "pre_action_selection": "CLAIMED_BY_TICKET_VERIFY_ORIGINAL_HOST_JOURNAL",
        "transfer": "UNDETERMINED_PENDING_INDEPENDENT_PAIR_AUDIT",
        "qualification": "NO_GO",
        "science": "NOT_RUN",
        "learning_admissions": 0,
    }


def compare_pair(normal: dict, ice: dict, *, margin_m: float = 0.001) -> dict:
    if normal.get("mode") != "GRASS_BLOCK" or ice.get("mode") != "PACKED_ICE":
        raise MP9Rejected("missing paired normal/ice scores")
    selected = (normal["selected_mae_m"] + ice["selected_mae_m"]) / 2
    global_normal = (normal["always_normal_mae_m"] + ice["always_normal_mae_m"]) / 2
    global_ice = (normal["always_ice_mae_m"] + ice["always_ice_mae_m"]) / 2
    last = (normal["last_mae_m"] + ice["last_mae_m"]) / 2
    delta = min(global_normal, global_ice) - selected
    specificity = (
        normal["selected_mae_m"] + margin_m <= normal["always_ice_mae_m"]
        and ice["selected_mae_m"] + margin_m <= ice["always_normal_mae_m"]
    )
    return {
        "selected_pair_mean_mae_m": selected,
        "always_normal_pair_mean_mae_m": global_normal,
        "always_ice_pair_mean_mae_m": global_ice,
        "last_pair_mean_mae_m": last,
        "delta_vs_best_constant_m": delta,
        "predeclared_improvement_margin_m": margin_m,
        "environment_specificity_gate_pass": specificity,
        "best_constant_gain_gate_pass": delta >= margin_m,
        "cheap_material_rule_equivalent": True,
        "l1_unique_advantage": False,
        "classification": (
            "CONDITION_ROUTED_SHADOW_BEATS_CONSTANTS_DEV"
            if specificity and delta >= margin_m
            else "CONDITION_SPECIFIC_TRANSFER_NOT_ESTABLISHED"
        ),
        "qualification": "NO_GO", "science": "NOT_RUN",
    }
