"""L-CF: opt-in, receipt-metered L2 fatigue physics (no Action authority).

No World tick/wall-time conversion. Only attested non-L2 host monotonic
intervals recover fatigue. An interrupted call stays active until a terminal
usage-and-backend-stop receipt; unknown compute is NEVER silently waived.
This is a deterministic evaluator-side candidate, not a live S integration.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256

_TOKEN = re.compile(r"[A-Za-z0-9_.:/-]{1,160}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class CognitiveFatigueRejected(ValueError):
    """Invalid meter, chronology, identity, or evidence boundary."""


def _id(value: object) -> bool:
    return isinstance(value, str) and _TOKEN.fullmatch(value) is not None


def _int(value: object, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _finite(value: object, low: float = 0, high: float | None = None) -> bool:
    return (type(value) in (int, float) and math.isfinite(value)
            and low <= value and (high is None or value <= high))


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class FatigueProfile:
    mode: str = "OFF"  # OFF / FIXED / LINEAR / NONLINEAR
    initial_fatigue: float = 0.0
    charge_per_total_token: float = 0.002
    recovery_per_idle_s: float = 0.02
    minimum_budget_fraction: float = 0.1
    knee: float = 0.55
    slope: float = 15.0
    block_at: float = 0.95
    resume_below: float = 0.75
    fixed_max_tokens: int = 96
    version: str = "L-CF-v1"

    def __post_init__(self) -> None:
        if (self.mode not in ("OFF", "FIXED", "LINEAR", "NONLINEAR")
                or self.version != "L-CF-v1"
                or not _finite(self.initial_fatigue, 0, 1)
                or not _finite(self.charge_per_total_token, 0, 1)
                or not _finite(self.recovery_per_idle_s, 0, 1)
                or not _finite(self.minimum_budget_fraction, 0.01, 1)
                or not _finite(self.knee, 0.01, 0.99)
                or not _finite(self.slope, 0.01, 1000)
                or not _finite(self.block_at, 0.01, 1)
                or not _finite(self.resume_below, 0, 1)
                or self.resume_below >= self.block_at
                or not _int(self.fixed_max_tokens, 1)
                or self.fixed_max_tokens > 1024):
            raise CognitiveFatigueRejected("bounded, versioned fatigue profile required")

    @property
    def sha256(self) -> str:
        from dataclasses import asdict
        return _hash(asdict(self))


@dataclass(frozen=True, slots=True)
class FatigueState:
    session_id: str
    profile_sha256: str
    last_ns: int
    seq: int
    fatigue: float
    total_metered_tokens: int
    active_work_id: str | None
    active_cumulative_tokens: int
    active_max_tokens: int
    used_work_ids: tuple[str, ...]
    blocked: bool
    chain_hash: str
    state_sha256: str
    version: str = "L-CF-v1"

    @classmethod
    def genesis(cls, profile: FatigueProfile, session_id: str, at_ns: int) -> "FatigueState":
        if (not isinstance(profile, FatigueProfile) or not _id(session_id)
                or not _int(at_ns)):
            raise CognitiveFatigueRejected("typed profile, session and host monotonic origin")
        initial = float(profile.initial_fatigue)
        if profile.mode == "OFF":
            initial = 0.0
        data = dict(session_id=session_id, profile_sha256=profile.sha256,
                    last_ns=at_ns, seq=0, fatigue=initial, total_metered_tokens=0,
                    active_work_id=None, active_cumulative_tokens=0,
                    active_max_tokens=0, used_work_ids=(),
                    blocked=(profile.mode not in ("OFF", "FIXED")
                             and initial >= profile.block_at),
                    chain_hash=_hash(["genesis", session_id, profile.sha256, at_ns]),
                    version="L-CF-v1")
        return cls(**data, state_sha256=_hash(data))


def _check(state: FatigueState, profile: FatigueProfile) -> None:
    if (not isinstance(state, FatigueState)
            or not isinstance(profile, FatigueProfile)
            or state.version != profile.version
            or state.profile_sha256 != profile.sha256
            or not _id(state.session_id)
            or not _int(state.last_ns) or not _int(state.seq)
            or not _finite(state.fatigue, 0, 1)
            or not _int(state.total_metered_tokens)
            or (state.active_work_id is not None and not _id(state.active_work_id))
            or not _int(state.active_cumulative_tokens)
            or not _int(state.active_max_tokens)
            or not isinstance(state.used_work_ids, tuple)
            or any(not _id(x) for x in state.used_work_ids)
            or len(set(state.used_work_ids)) != len(state.used_work_ids)
            or (state.active_work_id is not None and state.active_work_id not in state.used_work_ids)
            or type(state.blocked) is not bool
            or not isinstance(state.chain_hash, str)
            or _SHA.fullmatch(state.chain_hash) is None
            or (state.active_work_id is None and (state.active_cumulative_tokens or state.active_max_tokens))
            or not isinstance(state.state_sha256, str)):
        raise CognitiveFatigueRejected("foreign or invalid state")
    from dataclasses import asdict
    data = asdict(state)
    original = data.pop("state_sha256")
    if _hash(data) != original:
        raise CognitiveFatigueRejected("state hash mismatch")


def _next(state: FatigueState, event: list, **changes: object) -> FatigueState:
    from dataclasses import asdict
    data = asdict(state)
    data.pop("state_sha256")
    data.update(changes)
    data["seq"] = state.seq + 1
    data["chain_hash"] = _hash([state.chain_hash, event, data["seq"]])
    return FatigueState(**data, state_sha256=_hash(data))


def _gate(profile: FatigueProfile, was_blocked: bool, f: float) -> bool:
    if profile.mode in ("OFF", "FIXED"):
        return False
    return f >= profile.resume_below if was_blocked else f >= profile.block_at


@dataclass(frozen=True, slots=True)
class L2Budget:
    admitted: bool
    max_output_tokens: int | None
    action_authority: bool = False


def budget_for_l2(profile: FatigueProfile, state: FatigueState,
                  requested_max_tokens: int) -> L2Budget:
    _check(state, profile)
    if not _int(requested_max_tokens, 1) or requested_max_tokens > 1024:
        raise CognitiveFatigueRejected("bounded S-owned base token budget required")
    if state.active_work_id is not None:
        return L2Budget(False, None)
    if profile.mode == "OFF":
        return L2Budget(True, requested_max_tokens)
    if state.blocked:
        return L2Budget(False, None)
    if profile.mode == "FIXED":
        return L2Budget(True, min(requested_max_tokens, profile.fixed_max_tokens))
    if profile.mode == "LINEAR":
        fraction = 1 - (1 - profile.minimum_budget_fraction) * state.fatigue
    else:
        overshoot = max(0.0, state.fatigue - profile.knee)
        fraction = (profile.minimum_budget_fraction +
                    (1 - profile.minimum_budget_fraction) *
                    math.exp(-profile.slope * overshoot / (1 - profile.knee)))
    return L2Budget(True, max(1, min(requested_max_tokens,
                                   math.floor(requested_max_tokens * fraction))))


@dataclass(frozen=True, slots=True)
class L2Start:
    session_id: str
    work_id: str
    seq: int
    at_ns: int
    evidence_sha256: str
    max_output_tokens: int


@dataclass(frozen=True, slots=True)
class L2Usage:
    session_id: str
    work_id: str
    seq: int
    at_ns: int
    evidence_sha256: str
    cumulative_total_tokens: int
    status: str  # PROGRESS / COMPLETED / STOP_ACK


@dataclass(frozen=True, slots=True)
class NonL2Interval:
    session_id: str
    seq: int
    from_ns: int
    to_ns: int
    evidence_sha256: str
    source: str = "HOST_MONOTONIC_NON_L2"


def _receipt(state: FatigueState, session: str, seq: int,
             at_ns: int, evidence: str) -> None:
    if (session != state.session_id or not _int(seq, 1)
            or seq != state.seq + 1 or not _int(at_ns)
            or at_ns < state.last_ns or not isinstance(evidence, str)
            or _SHA.fullmatch(evidence) is None):
        raise CognitiveFatigueRejected("missing/foreign/replayed evidence or clock regression")


def begin_l2(profile: FatigueProfile, state: FatigueState, receipt: L2Start,
             base_max_tokens: int) -> FatigueState:
    _check(state, profile)
    if not isinstance(receipt, L2Start):
        raise CognitiveFatigueRejected("typed start receipt required")
    _receipt(state, receipt.session_id, receipt.seq, receipt.at_ns,
             receipt.evidence_sha256)
    if not _id(receipt.work_id) or receipt.work_id in state.used_work_ids:
        raise CognitiveFatigueRejected("fresh work identity required")
    budget = budget_for_l2(profile, state, base_max_tokens)
    if not budget.admitted or receipt.max_output_tokens != budget.max_output_tokens:
        raise CognitiveFatigueRejected("L2 blocked or upstream token cap mismatch")
    return _next(state, ["start", receipt.work_id, receipt.evidence_sha256,
                         receipt.at_ns, receipt.max_output_tokens],
                 last_ns=receipt.at_ns, active_work_id=receipt.work_id,
                 active_max_tokens=receipt.max_output_tokens,
                 used_work_ids=state.used_work_ids + (receipt.work_id,))


def account_l2(profile: FatigueProfile, state: FatigueState,
               receipt: L2Usage) -> FatigueState:
    _check(state, profile)
    if not isinstance(receipt, L2Usage):
        raise CognitiveFatigueRejected("typed usage required")
    _receipt(state, receipt.session_id, receipt.seq, receipt.at_ns,
             receipt.evidence_sha256)
    if (state.active_work_id is None or receipt.work_id != state.active_work_id
            or receipt.status not in ("PROGRESS", "COMPLETED", "STOP_ACK")
            or not _int(receipt.cumulative_total_tokens)
            or receipt.cumulative_total_tokens < state.active_cumulative_tokens):
        raise CognitiveFatigueRejected("usage must be cumulative for one active L2")
    delta = receipt.cumulative_total_tokens - state.active_cumulative_tokens
    f = min(1.0, state.fatigue + (
        0 if profile.mode == "OFF" else delta * profile.charge_per_total_token))
    terminal = receipt.status in ("COMPLETED", "STOP_ACK")
    return _next(state, ["usage", receipt.work_id, receipt.evidence_sha256,
                         receipt.at_ns, receipt.cumulative_total_tokens,
                         receipt.status], last_ns=receipt.at_ns,
                 total_metered_tokens=state.total_metered_tokens + delta,
                 fatigue=f, blocked=_gate(profile, state.blocked, f),
                 active_work_id=None if terminal else state.active_work_id,
                 active_cumulative_tokens=0 if terminal else receipt.cumulative_total_tokens,
                 active_max_tokens=0 if terminal else state.active_max_tokens)


def recover_idle(profile: FatigueProfile, state: FatigueState,
                 receipt: NonL2Interval) -> FatigueState:
    _check(state, profile)
    if not isinstance(receipt, NonL2Interval):
        raise CognitiveFatigueRejected("typed non-L2 interval required")
    _receipt(state, receipt.session_id, receipt.seq, receipt.to_ns,
             receipt.evidence_sha256)
    if (state.active_work_id is not None or receipt.from_ns != state.last_ns
            or receipt.to_ns <= receipt.from_ns
            or receipt.source != "HOST_MONOTONIC_NON_L2"):
        raise CognitiveFatigueRejected("idle evidence cannot overlap active/missing time")
    delta_s = (receipt.to_ns - receipt.from_ns) / 1_000_000_000
    f = max(0.0, state.fatigue - (
        0 if profile.mode == "OFF" else profile.recovery_per_idle_s * delta_s))
    return _next(state, ["idle", receipt.evidence_sha256,
                         receipt.from_ns, receipt.to_ns],
                 last_ns=receipt.to_ns, fatigue=f,
                 blocked=_gate(profile, state.blocked, f))


def sensory_projection(state: FatigueState, profile: FatigueProfile,
                       *, enabled: bool = False) -> dict[str, object]:
    """Only an explicit coarse sensor; do not expose evaluator-side F_c."""
    _check(state, profile)
    if not enabled:
        return {}
    return {"cognitive_budget_band": (
        "UNAVAILABLE" if state.blocked or state.active_work_id is not None
        else "LOW" if state.fatigue >= profile.knee else "AVAILABLE")}
