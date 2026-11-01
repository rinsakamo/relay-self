"""MP8 offline frozen ice-prior and matched-pair shadow scoring.

No World I/O, no owner authority, no learning admission and no physical source
qualification. A later original-Paper auditor must independently verify targets.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

MP7_GIT_BLOB_SHA = "7458cbee8f830507cbded9ad9f64894afc35637c"
MP7_RUN = 41274077794
MP7_HEAD = "49ba1f5f1d2d0c255fc471542c9f7c062229641c"
MP5_SLOPE = 0.20331885786720635
DEFAULT_ARCHIVE = (
    Path(__file__).resolve().parents[2]
    / "docs/evidence/issue653-mp7-ice-floor-20261101/run1/independent-physical-readback.json"
)


class MP8Rejected(ValueError):
    """A missing, contaminated or non-matched offline experimental source."""


@dataclass(frozen=True)
class IcePrior:
    source_git_blob_sha: str
    source_world_uuid: str
    previous_normal_slope: float
    fitted_ice_slope: float
    sample_pairs: int
    surface: str = "PACKED_ICE"
    claim: str = "TRAINING_FIT_ONLY_NO_TRANSFER"


@dataclass(frozen=True)
class TargetSetup:
    world_uuid: str
    subject_uuid: str
    seed: str
    condition: str
    # A canonical, independently recorded pre-intervention state digest
    # EXCLUDING the intended underfoot material intervention.
    matched_state_sha256: str
    native_action_spec_sha256: str
    original_surface: str = "GRASS_BLOCK"


@dataclass(frozen=True)
class FrozenPair:
    training: IcePrior
    normal: TargetSetup
    ice: TargetSetup
    ticket_sha256: str
    claim: str = "OFFLINE_TICKET_ONLY"


def _git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def _sha256_json(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()


def _series(value: object) -> tuple[float, ...]:
    if type(value) is not list or len(value) != 8:
        raise MP8Rejected("exactly eight original ordered WAIT samples are required")
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
           for v in value):
        raise MP8Rejected("invalid displacement")
    return tuple(float(v) for v in value)


def _fit_slope(motions: tuple[float, ...]) -> float:
    denominator = sum(x * x for x in motions[:-1])
    if denominator <= 1e-12:
        raise MP8Rejected("training input has insufficient motion for fitting")
    slope = sum(x * y for x, y in zip(motions[:-1], motions[1:])) / denominator
    if not math.isfinite(slope) or slope < 0 or slope > 64:
        raise MP8Rejected("unsafe/nonfinite motion model")
    return slope


def train_from_mp7(path: Path = DEFAULT_ARCHIVE) -> IcePrior:
    """Fit MP7 only. Never train on either future target World."""
    if not isinstance(path, Path) or not path.is_file() or path.is_symlink():
        raise MP8Rejected("missing sealed MP7 archive")
    raw = path.read_bytes()
    if len(raw) > 1_000_000 or _git_blob_sha(raw) != MP7_GIT_BLOB_SHA:
        raise MP8Rejected("MP7 archive bytes do not match pinned source blob")
    data = json.loads(raw)
    floor, ice = data["paper_condition"], data["new_ice_world"]
    ticks = ice["original_wait_world_ticks"]
    if (
        data["schema"] != "RELAYSELF_MP7_ICE_FLOOR_REAL_WORLD_ORIGINAL_READBACK_V1"
        or data["physical_actions_run_id"] != MP7_RUN
        or data["executing_head"] != MP7_HEAD
        or data["actual_world_count"] != 1
        or data["actual_native_action_count"] != 1
        or data["retry_count"] != 0
        or floor["original_material"] != "GRASS_BLOCK"
        or floor["new_material"] != "PACKED_ICE"
        or floor["affected_blocks"] != 25
        or floor["original_wait_underfoot_ice_samples"] != 8
        or ice["original_log_forecast_sequence_verified"] is not True
        or ice["paper_local_future_predictions_frozen"] != 7
        or ice["paper_local_future_predictions_scored"] != 7
        or ice["real_world_dev_owner"] != "PASS"
        or len(ticks) != 8
        or any(type(t) is not int for t in ticks)
        or any(y != x + 1 for x, y in zip(ticks[:-1], ticks[1:]))
    ):
        raise MP8Rejected("MP7 is not an accepted DEV training readback")
    motions = _series(ice["original_wait_displacements_m"])
    return IcePrior(
        source_git_blob_sha=MP7_GIT_BLOB_SHA,
        source_world_uuid=floor["world_uuid"],
        previous_normal_slope=MP5_SLOPE,
        fitted_ice_slope=_fit_slope(motions),
        sample_pairs=7,
    )


def freeze_matched_pair(prior: IcePrior, normal: TargetSetup,
                        ice: TargetSetup) -> FrozenPair:
    """Freeze target metadata before Action; digest is a proposal, not Paper proof."""
    if not isinstance(prior, IcePrior) or prior.source_git_blob_sha != MP7_GIT_BLOB_SHA:
        raise MP8Rejected("model is not bound to pinned MP7 training source")
    if not isinstance(normal, TargetSetup) or not isinstance(ice, TargetSetup):
        raise MP8Rejected("typed target conditions are required")
    if normal.condition != "NORMAL" or ice.condition != "PACKED_ICE":
        raise MP8Rejected("missing normal/ice target pair")
    identifiers = (
        normal.world_uuid, ice.world_uuid, prior.source_world_uuid,
        normal.subject_uuid, ice.subject_uuid,
    )
    if any(type(s) is not str or not s for s in identifiers):
        raise MP8Rejected("missing World/Body identity")
    if len(set(identifiers[:3])) != 3:
        raise MP8Rejected("training World reused or paired Worlds are identical")
    for target in (normal, ice):
        if (target.original_surface != "GRASS_BLOCK"
                or type(target.seed) is not str or not target.seed
                or any(type(v) is not str or len(v) != 64
                       or any(c not in "0123456789abcdef" for c in v)
                       for v in (
                           target.matched_state_sha256,
                           target.native_action_spec_sha256,
                       ))):
            raise MP8Rejected("incomplete pre-action matched-state record")
    if (normal.seed != ice.seed
            or normal.matched_state_sha256 != ice.matched_state_sha256
            or normal.native_action_spec_sha256 != ice.native_action_spec_sha256):
        raise MP8Rejected("paired initial conditions or native Action differ")
    payload = {"training": asdict(prior), "normal": asdict(normal),
               "ice": asdict(ice)}
    return FrozenPair(prior, normal, ice, _sha256_json(payload))


def score_pair(ticket: FrozenPair, *, normal_motions: object,
               ice_motions: object) -> dict:
    """Diagnostic of later provided samples; no authenticity or causal authority."""
    if not isinstance(ticket, FrozenPair):
        raise MP8Rejected("missing typed frozen ticket")
    expected = freeze_matched_pair(ticket.training, ticket.normal, ticket.ice)
    if expected.ticket_sha256 != ticket.ticket_sha256:
        raise MP8Rejected("post-freeze ticket mutation")
    normal, ice = _series(normal_motions), _series(ice_motions)

    def mae(x: tuple[float, ...], slope: float) -> float:
        return sum(abs(slope * a - b) for a, b in zip(x[:-1], x[1:])) / 7

    model = ticket.training
    scores = {
        "normal_old_model_mae_m": mae(normal, model.previous_normal_slope),
        "normal_wrong_ice_model_mae_m": mae(normal, model.fitted_ice_slope),
        "ice_old_model_mae_m": mae(ice, model.previous_normal_slope),
        "ice_updated_model_mae_m": mae(ice, model.fitted_ice_slope),
        "ice_zero_baseline_mae_m": sum(ice[1:]) / 7,
        "ice_last_baseline_mae_m": sum(abs(a-b) for a,b in zip(ice[:-1], ice[1:])) / 7,
    }
    return {
        "ticket_sha256": ticket.ticket_sha256,
        "training_source": model.source_git_blob_sha,
        "training_pairs": model.sample_pairs,
        "score": scores,
        "ice_updated_minus_old_mae_m": (
            scores["ice_updated_model_mae_m"] - scores["ice_old_model_mae_m"]
        ),
        "same_information_cheap_linear": "MATHEMATICALLY_EQUIVALENT",
        "source_authenticity": "NOT_AUDITED_FROM_ORIGINAL_PAPER",
        "paired_physical_control": "NOT_ATTESTED",
        "transfer_claim": "UNDETERMINED",
        "goal": "UNDETERMINED",
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }
