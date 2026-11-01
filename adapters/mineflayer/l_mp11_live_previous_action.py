"""MP11 L: source-bounded live Paper prior-window witness, read-only.

Unlike archived MP12, the caller MUST sample a complete-line prefix while
Paper and the original Mineflayer session are alive after original S49/S16.
The S49 owner alone provides the matching typed S16 identity. This is NOT
independent postrun source qualification, online Gemma, or Action authority.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass

from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionDatum, OpenCognitionRequest

MAX_BYTES = 16_000_000
KINDS = (
    "M02_DEV_S50_PHASE", "S50_DEV_SURFACE_LOCK",
    "S50_DEV_WAIT_BEGIN", "S50_DEV_WAIT_TICK", "S50_DEV_INPUT_TICK",
    "S50_DEV_LOCAL_FORECAST_FIXED", "S50_DEV_LOCAL_FORECAST_SCORE",
)


class LivePriorRejected(ValueError):
    """Source, session, chronology, owner closure or budget is insufficient."""


@dataclass(frozen=True, slots=True)
class LivePriorObservation:
    ordinal: int
    action_id: str
    marker_id: str
    world_uuid: str
    subject_uuid: str
    session_id: str
    native_s16_seq: int
    paper_wait_ticks: tuple[int, ...]
    paper_wait_motion_m: tuple[float, ...]
    paper_wait_total_m: float
    paper_prefix_sha256: str
    paper_prefix_length: int
    original_paper_last_complete_line: int
    paper_predicted_next_m: tuple[float, ...]
    paper_next_abs_error_m: tuple[float, ...]
    paper_cheap_zero_next_mae_m: float
    source_status: str = "LIVE_PAPER_PREFIX_UNSEALED_S49_TYPED_S16_CLAIM"
    real_paper_original_postrun_reauthenticated: bool = False
    physically_controlled_conditions_varied: bool = False
    original_paper_input_clear_tick_attested: bool = False
    action_or_learning_authority: bool = False


def _token(value: object) -> bool:
    return (
        type(value) is str and 0 < len(value) <= 128
        and not any(ch.isspace() for ch in value)
    )


def _parse_rows(raw: bytes) -> list[tuple[int, str, dict[str, str]]]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES or not raw.endswith(b"\n"):
        raise LivePriorRejected("bounded complete-line Paper snapshot required")
    try:
        lines = raw.decode("utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise LivePriorRejected("non UTF-8 original server log") from exc
    rows = []
    for i, line in enumerate(lines):
        matches = [k for k in KINDS if f"{k} marker_id=" in line]
        if not matches:
            continue
        if len(matches) != 1:
            raise LivePriorRejected("ambiguous original Paper event")
        pairs = [word.split("=", 1) for word in line.split() if word.count("=") == 1]
        names = [name for name, _ in pairs]
        if len(names) != len(set(names)):
            raise LivePriorRejected("duplicate Paper event key")
        rows.append((i, matches[0], dict(pairs)))
    return rows


def _int_field(row: dict[str, str], key: str) -> int:
    try:
        value = int(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise LivePriorRejected("missing integer Paper field") from exc
    if str(value) != row[key]:
        raise LivePriorRejected("noncanonical Paper integer")
    return value


def _float_field(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise LivePriorRejected("missing numeric Paper field") from exc
    if not math.isfinite(value):
        raise LivePriorRejected("nonfinite Paper coordinate")
    return value


class LivePriorLedger:
    """Finite, one-world, append-only source prefix journal (no model calls)."""

    def __init__(self, *, session_id: str, world_uuid: str, subject_uuid: str):
        if not all(_token(s) for s in (session_id, world_uuid, subject_uuid)):
            raise LivePriorRejected("one exact native session and Paper World required")
        self.session_id = session_id
        self.world_uuid = world_uuid
        self.subject_uuid = subject_uuid
        self.history: list[LivePriorObservation] = []
        self._previous_prefix: bytes = b""

    def accept_completed(
        self, raw_prefix: bytes, *,
        action_id: str, marker_id: str, native_s16_seq: int,
        native_outcome: str,
    ) -> LivePriorObservation:
        """Call from S49 only after S16 closure and complete Paper WAIT8/score7."""
        if (
            not _token(action_id) or not _token(marker_id)
            or marker_id != f"{action_id}-{self.session_id}"
            or type(native_s16_seq) is not int or native_s16_seq <= 0
            or native_outcome != "S16_OUTCOME"
            or len(self.history) >= 3
            or not isinstance(raw_prefix, bytes)
            or len(raw_prefix) <= len(self._previous_prefix)
            or (self._previous_prefix and
                not raw_prefix.startswith(self._previous_prefix))
        ):
            raise LivePriorRejected("native S16, source append or budget mismatch")
        if self.history and (
            native_s16_seq <= self.history[-1].native_s16_seq
            or action_id in {x.action_id for x in self.history}
        ):
            raise LivePriorRejected("repeated or nonchronological native S16")
        rows = _parse_rows(raw_prefix)
        expected_markers = {x.marker_id for x in self.history} | {marker_id}
        if any(row.get("marker_id") not in expected_markers for _, _, row in rows):
            raise LivePriorRejected("future/foreign Paper Action in live source prefix")
        for old in self.history:
            if not any(k == "S50_DEV_WAIT_TICK"
                       and r.get("marker_id") == old.marker_id
                       for _, k, r in rows):
                raise LivePriorRejected("prior original Action no longer visible")
        found = [(i, k, row) for i, k, row in rows
                 if row.get("marker_id") == marker_id]

        def select(kind: str) -> list[tuple[int, dict[str, str]]]:
            return [(i, r) for i, k, r in found if k == kind]

        phases, locks, begins = (
            select("M02_DEV_S50_PHASE"),
            select("S50_DEV_SURFACE_LOCK"),
            select("S50_DEV_WAIT_BEGIN"),
        )
        waits, inputs = select("S50_DEV_WAIT_TICK"), select("S50_DEV_INPUT_TICK")
        fixed, scores = (
            select("S50_DEV_LOCAL_FORECAST_FIXED"),
            select("S50_DEV_LOCAL_FORECAST_SCORE"),
        )
        if (
            len(phases) != 2 or len(locks) != 1 or len(begins) != 1
            or len(waits) != 8 or len(inputs) != 8
            or len(fixed) != 7 or len(scores) != 7
            or [x[1].get("phase") for x in phases]
            != ["PRE_FORWARD", "POST_CLEAR"]
            or not (
                phases[0][0] < locks[0][0] < phases[1][0]
                < begins[0][0] < waits[0][0]
            )
        ):
            raise LivePriorRejected("incomplete original Paper Action phase/window")
        lock = locks[0][1]
        if (
            lock.get("world") != self.world_uuid
            or lock.get("subject_uuid") != self.subject_uuid
            or lock.get("status") != "REAL_PAPER_PRE_ACTION_SURFACE_LOCK"
            or lock.get("original_material") != "GRASS_BLOCK"
            or lock.get("target_material") != "GRASS_BLOCK"
            or lock.get("mode") != "GRASS_BLOCK_5X5_READONLY"
            or lock.get("blocks_verified") != "25"
            or lock.get("on_ground") != "true"
        ):
            raise LivePriorRejected("G3 expected original grass surface not locked")
        if any(row.get("world") != self.world_uuid
               for _, _, row in found):
            raise LivePriorRejected("foreign Paper World source")
        if begins[0][1].get("world") != self.world_uuid:
            raise LivePriorRejected("foreign WAIT begin")
        ticks: list[int] = []
        motions: list[float] = []
        for i, ((wait_line, wait), (input_line, inp)) in enumerate(
            zip(waits, inputs), 1
        ):
            tick = _int_field(wait, "tick")
            if (
                _int_field(wait, "index") != i
                or _int_field(inp, "index") != i
                or _int_field(inp, "tick") != tick
                or inp.get("subject_uuid") != self.subject_uuid
                or wait_line >= input_line
                or (i < 8 and input_line >= waits[i][0])
                or (ticks and tick != ticks[-1] + 1)
                or (self.history and tick <= self.history[-1].paper_wait_ticks[-1])
            ):
                raise LivePriorRejected("nonoriginal WAIT/input tick and order")
            start = [_float_field(wait, f"from_{ax}") for ax in "xyz"]
            finish = [_float_field(wait, ax) for ax in "xyz"]
            ticks.append(tick)
            motions.append(math.dist(start, finish))
        predictions, errors = [], []
        for i in range(7):
            fixed_line, a = fixed[i]
            score_line, b = scores[i]
            if not (
                waits[i][0] < fixed_line < waits[i+1][0] < score_line
                and a.get("subject_uuid") == b.get("subject_uuid")
                == self.subject_uuid
                and _int_field(a, "prior_tick") == ticks[i]
                and _int_field(a, "target_tick") == ticks[i+1]
                and _int_field(b, "target_tick") == ticks[i+1]
                and a.get("ticket_sha256") == b.get("ticket_sha256")
            ):
                raise LivePriorRejected("Paper next-tick model not frozen before target")
            predicted = _float_field(a, "predicted_m")
            actual = _float_field(b, "actual_m")
            error = _float_field(b, "abs_error_m")
            if (
                predicted < 0 or error < 0
                or predicted != _float_field(b, "predicted_m")
                or not math.isclose(actual, motions[i+1], abs_tol=1e-9)
                or not math.isclose(error, abs(predicted-actual), abs_tol=1e-9)
            ):
                raise LivePriorRejected("original prediction/observed/error mismatch")
            predictions.append(predicted)
            errors.append(error)
        entry = LivePriorObservation(
            ordinal=len(self.history)+1,
            action_id=action_id, marker_id=marker_id,
            world_uuid=self.world_uuid, subject_uuid=self.subject_uuid,
            session_id=self.session_id, native_s16_seq=native_s16_seq,
            paper_wait_ticks=tuple(ticks), paper_wait_motion_m=tuple(motions),
            paper_wait_total_m=sum(motions),
            paper_prefix_sha256=hashlib.sha256(raw_prefix).hexdigest(),
            paper_prefix_length=len(raw_prefix),
            original_paper_last_complete_line=raw_prefix.count(b"\n"),
            paper_predicted_next_m=tuple(predictions),
            paper_next_abs_error_m=tuple(errors),
            paper_cheap_zero_next_mae_m=sum(motions[1:])/7,
        )
        self.history.append(entry)
        self._previous_prefix = raw_prefix
        return entry

    def model_request(self) -> OpenCognitionRequest:
        """Only prior completed trial data; never schedules next World Action."""
        if not self.history:
            raise LivePriorRejected("no closed original trial to expose")
        history = self.history
        return OpenCognitionRequest(
            request_id=f"l-mp11-live:{self.world_uuid}:after-{len(history)}",
            instruction=(
                "L2 read-only hypothesis input from S49-host-sampled live Paper "
                "prefix. Suggest tests but DO NOT order any Action or claim a "
                "physical mechanism, learned model, capability limit or goal. "
                "All completed prior actions are GRASS/MOVE_BACKWARD; "
                "physical clear tick/input duration are NOT attested. "
                "This input is provisional until independent postrun source audit."
            ),
            intent_id="investigate-motion-mismatch",
            focus="LIVE_PREVIOUS_S49_ACTION_SOURCE_L2_CONTEXT_ONLY",
            context=(
                CognitionDatum.from_value(
                    "evidence_limits",
                    {
                        "source_status": "LIVE_PAPER_PREFIX_UNSEALED_S49_TYPED_S16_CLAIM",
                        "paper_original_verified_after_exit": False,
                        "native_original_stdout_verified_after_exit": False,
                        "actual_l2_calls": 0,
                        "action_issuer": "S49_ONLY",
                        "controlled_surface_or_duration_comparison": False,
                        "effective_s15_clear_tick": "NOT_ATTESTED",
                        "no_future_action_in_prefix": True,
                        "learning_admissions": 0,
                    },
                    Provenance("l.mp11.live.paper.provisional",
                               history[-1].paper_prefix_sha256),
                ),
                CognitionDatum.from_value(
                    "completed_prior_s49_s16_s50_trials",
                    [asdict(x) for x in history],
                    Provenance("l.mp11.live.paper.prefix",
                               history[-1].paper_prefix_sha256),
                ),
            ),
        )
