"""L14: audit S7-style original bridge bytes and per-Action spatial Goal.

No World/Action I/O, no source signing and no new native receipt owner.
The caller supplies actual captured original raw bridge streams and the S7
source index. Type/SHA-verified streams are not proof of Minecraft TCP or
absence of unobserved external/physical interventions.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
    MineflayerStreamDecoder,
)
from relay_self.l10_world_body_cue_learning import WorldBodyCueWitness
from relay_self.l13_independent_goal_receipt import (
    L13IndependentSourceAdmission,
    L13ReadOnlyReview,
    L13ReceiptStatus,
    L13ReceiptTriplet,
    _no_duplicate_json_keys,
    join_independent_action_goal_source,
)

SCHEMA = "L14_NATIVE_BRIDGE_PER_ACTION_GOAL_WINDOW_V1"
CRITERION_SCHEMA = "L14_PREDECLARED_SPATIAL_GOAL_V1"
MAX_RECEIVED = 16 * 1024 * 1024
MAX_SENT = 4 * 1024 * 1024
MAX_RECEIVED_LINES = 4096
MAX_SENT_LINES = 512
MAX_ONE_LINE = 1024 * 1024
CRITERION_KEYS = frozenset({
    "schema", "session_id", "action_id", "criterion_id", "owner_ref",
    "created_before_seq", "target_x", "target_z", "tolerance_m",
    "stable_probe_delta_max_m",
})


class L14SourceRejected(ValueError):
    """Original bytes or prospective external criterion do not close a window."""


@dataclass(frozen=True, slots=True)
class L14GoalWindow:
    schema: str
    source_session_id: str
    action_id: str
    before_native_seq: int
    action_end_native_seq: int
    goal_probe_seq: int
    second_stable_probe_seq: int
    original_received_sha256: str
    original_sent_sha256: str
    original_criterion_sha256: str
    original_s16_action_sha256: str
    original_external_goal_sha256: str
    original_positive_present_sha256: str
    goal_error_probe_1_m: float
    goal_error_probe_2_m: float
    observed_goal_status: str
    criterion_matches_external_goal_result: bool
    no_other_outbound_action_in_captured_bytes: bool
    captured_native_effect_ack_for_action: bool
    l13_source_shaped_candidate: L13ReadOnlyReview
    independent_physical_goal_authenticated: bool = False
    native_tcp_authenticated: bool = False
    actual_intervention_absence_proven: bool = False
    physical_learning_attested: bool = False
    qualified_real_learning_pairs: int = 0
    s10_updates: int = 0
    habit_grants: int = 0
    action_issues: int = 0
    new_worlds: int = 0


def _lines(raw: bytes, cap: int, max_lines: int, label: str) -> tuple[bytes, ...]:
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= cap
            or not raw.endswith(b"\n")):
        raise L14SourceRejected(f"{label}: bounded original JSONL required")
    rows = tuple(line + b"\n" for line in raw.split(b"\n")[:-1])
    if (
        not 1 <= len(rows) <= max_lines
        or any(len(v) > MAX_ONE_LINE or len(v) == 1 for v in rows)
    ):
        raise L14SourceRejected(f"{label}: original complete line/count invalid")
    return rows


def _json(line: bytes) -> dict:
    try:
        d = json.loads(line.decode("utf-8"), object_pairs_hook=_no_duplicate_json_keys)
    except (ValueError, UnicodeError) as exc:
        raise L14SourceRejected("invalid/duplicate original JSON") from exc
    if not isinstance(d, dict):
        raise L14SourceRejected("original JSON must be object")
    return d


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _strict_receipt(receipt: dict, received: bytes, sent: bytes,
                    rlines: tuple[bytes, ...], slines: tuple[bytes, ...]) -> None:
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != "SELF_S7_RAW_MINEFLAYER_JSONL_RECEIPT_V1"
        or receipt.get("received_sha256") != _sha(received)
        or receipt.get("sent_sha256") != _sha(sent)
        or type(receipt.get("received_bytes")) is not int
        or receipt["received_bytes"] != len(received)
        or type(receipt.get("sent_bytes")) is not int
        or receipt["sent_bytes"] != len(sent)
        or type(receipt.get("received_lines")) is not int
        or receipt["received_lines"] != len(rlines)
        or type(receipt.get("sent_lines")) is not int
        or receipt["sent_lines"] != len(slines)
        or receipt.get("received_measured_before_decode") is not True
        or receipt.get("sent_measured_before_write") is not True
        or receipt.get("minecraft_tcp_packet_bytes") is not False
        or receipt.get("native_execution_ack_attested") is not False
        or receipt.get("v_science_qualified") is not False
    ):
        raise L14SourceRejected("S7 original byte index is missing or untrusted")


def _finite(x: object) -> float:
    if type(x) not in (int, float) or not math.isfinite(x):
        raise L14SourceRejected("goal geometry must be finite")
    return float(x)


def audit_l14_native_goal_window(
    *,
    received_original: bytes,
    sent_original: bytes,
    s7_source_receipt: dict,
    external_criterion_original: bytes,
    independently_admitted_criterion_sha256: frozenset[str],
    item: L13ReceiptTriplet,
    admission: L13IndependentSourceAdmission,
    current: WorldBodyCueWitness,
) -> L14GoalWindow:
    """Audit only one already-captured original single-Action bridge stream.

    Outbound original stream has no timeline: even an exact full trace of a
    single Action does not prove absence of other environmental intervention.
    The independent external Goal owner must certify that separately.
    """
    if not isinstance(independently_admitted_criterion_sha256, frozenset):
        raise L14SourceRejected("external independent criterion admission required")
    rlines = _lines(received_original, MAX_RECEIVED, MAX_RECEIVED_LINES, "received")
    slines = _lines(sent_original, MAX_SENT, MAX_SENT_LINES, "sent")
    _strict_receipt(s7_source_receipt, received_original, sent_original, rlines, slines)
    l13 = join_independent_action_goal_source(item, admission, current=current)
    criterion_rows = _lines(external_criterion_original, MAX_ONE_LINE, 1, "criterion")
    criterion = _json(criterion_rows[0])
    criterion_sha = _sha(external_criterion_original)
    if (
        criterion_sha not in independently_admitted_criterion_sha256
        or len(set(criterion)) != len(CRITERION_KEYS)
        or set(criterion) != CRITERION_KEYS
        or criterion.get("schema") != CRITERION_SCHEMA
        or criterion.get("session_id") != item.native.observation.session_id
        or criterion.get("action_id") != item.action.action_id
        or criterion.get("owner_ref") != admission.goal_owner
        or type(criterion.get("created_before_seq")) is not int
        or not 0 <= criterion["created_before_seq"] < item.native.observation.seq
    ):
        raise L14SourceRejected("goal criterion not independently preregistered")
    goal_data = _json(item.raw_external_goal)
    action_data = _json(item.raw_s16_action)
    if (
        criterion.get("criterion_id") != goal_data.get("criterion_id")
        or criterion.get("owner_ref") != goal_data.get("external_goal_owner_ref")
    ):
        raise L14SourceRejected("external Goal original uses another criterion")
    tx = _finite(criterion.get("target_x"))
    tz = _finite(criterion.get("target_z"))
    tol = _finite(criterion.get("tolerance_m"))
    stable = _finite(criterion.get("stable_probe_delta_max_m"))
    if not (0 < tol <= 16 and 0 < stable <= 0.1):
        raise L14SourceRejected("goal spatial/two-probe threshold invalid")

    # Whole original native received stream, with original seq continuity.
    decoder = MineflayerStreamDecoder()
    msgs = []
    for raw in rlines:
        _json(raw)  # Reject duplicate keys before adapter JSON decode.
        try:
            msg = decoder.decode(raw.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise L14SourceRejected("invalid native stream original seq/session") from exc
        msgs.append(msg)
    aid = item.action.action_id
    before = action_data["before_seq"]
    after = action_data["after_seq"]
    goal_seq = goal_data["goal_observed_seq"]
    if not (0 < before < after < goal_seq and goal_seq+1 < len(msgs)):
        raise L14SourceRejected("Action/Goal readback outside continuous original stream")
    if rlines[before] != item.raw_native_probe or msgs[before] != item.native.observation:
        raise L14SourceRejected("L13 pre-Action original missing or changed in stream")
    if any(
        isinstance(m, MineflayerEffectResult) and m.action_id != aid
        for m in msgs
    ):
        raise L14SourceRejected("other Action has native received effect during window")
    effects = [
        m for m in msgs
        if isinstance(m, MineflayerEffectResult)
        and before < m.seq <= after and m.action_id == aid and m.result == "applied"
    ]
    if not effects:
        raise L14SourceRejected("original S16 action interval lacks native effect ACK")
    # Every outbound effect in *the entire bounded original stream* must be
    # for this Action. Sent stream lacks time/seq, so no causality claim.
    outbound_effect_count = 0
    for raw in slines:
        command = _json(raw)
        if command.get("type") == "effect":
            if (
                command.get("action_id") != aid
                or not isinstance(command.get("effect"), str)
            ):
                raise L14SourceRejected("another/unidentified outbound Action")
            outbound_effect_count += 1
        elif command.get("type") != "observe":
            raise L14SourceRejected("original outbound stream has unknown request")
    if outbound_effect_count == 0:
        raise L14SourceRejected("no original outbound S49 Action intent in sent stream")
    first, second = msgs[goal_seq], msgs[goal_seq+1]
    if (
        not isinstance(first, MineflayerObservation)
        or not isinstance(second, MineflayerObservation)
        or first.kind != "probe" or second.kind != "probe"
        or first.seq != goal_seq or second.seq != goal_seq+1
        or any(not isinstance(m, MineflayerObservation)
               for m in msgs[after+1:goal_seq+2])
        or any(m.kind in ("death", "respawn", "forcedMove")
               for m in msgs[after+1:])
    ):
        raise L14SourceRejected("two original terminal probes not after S16 closure")
    a = first.snapshot.position
    b = second.snapshot.position
    error1 = math.hypot(a.x-tx, a.z-tz)
    error2 = math.hypot(b.x-tx, b.z-tz)
    unchanged = math.hypot(a.x-b.x, a.z-b.z) <= stable
    if not unchanged or (error1 <= tol) != (error2 <= tol):
        observed = "UNDETERMINED"
    else:
        observed = "REACHED" if error2 <= tol else "NOT_REACHED"
    external = goal_data["goal_status"]
    if external != "UNDETERMINED" and external != observed:
        raise L14SourceRejected("externally claimed Goal disagrees with native probes")
    if observed == "UNDETERMINED" and external != "UNDETERMINED":
        raise L14SourceRejected("unstable/ambiguous Goal cannot be assigned a label")
    if l13.status is L13ReceiptStatus.UNKNOWN_NO_GOAL_LABEL and external != "UNDETERMINED":
        raise L14SourceRejected("L13 Goal label conflict")
    if l13.status is L13ReceiptStatus.SOURCE_SHAPED_GOAL_CANDIDATE and external == "UNDETERMINED":
        raise L14SourceRejected("L13 candidate cannot be an unknown Goal")
    return L14GoalWindow(
        schema=SCHEMA, source_session_id=first.session_id, action_id=aid,
        before_native_seq=before, action_end_native_seq=after,
        goal_probe_seq=goal_seq, second_stable_probe_seq=goal_seq+1,
        original_received_sha256=_sha(received_original),
        original_sent_sha256=_sha(sent_original),
        original_criterion_sha256=criterion_sha,
        original_s16_action_sha256=l13.source_action_sha256,
        original_external_goal_sha256=l13.source_goal_sha256,
        original_positive_present_sha256=l13.source_present_sha256,
        goal_error_probe_1_m=error1, goal_error_probe_2_m=error2,
        observed_goal_status=observed,
        criterion_matches_external_goal_result=external == observed,
        no_other_outbound_action_in_captured_bytes=True,
        captured_native_effect_ack_for_action=True,
        l13_source_shaped_candidate=l13,
    )
