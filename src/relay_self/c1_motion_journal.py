"""Crash-safe DEV persistence for the SAME C1/S10 motion owner, not a new owner.

One bounded C1 experience identity and its exact existing S10 committed
snapshot are atomically written together. This prevents a *persisted* feedback
from being applied twice after process restart. It does NOT provide a physical
Action write-ahead log, revive an original World/Intent, guarantee source
independence, or replace general Persistent Cognition autosave.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import stat
import tempfile
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterator

from relay_self.learning import (
    LearningCommitRecord,
    LearningCommitResult,
    LearningPreferenceState,
    LearningProposalStatus,
)
from relay_self.provenance import Provenance

_SCHEMA = 1
_TARGET = "motion_decimeters"


class C1JournalError(ValueError):
    """Invalid, missing or unqualified C1 journal state."""


class C1JournalConflict(C1JournalError):
    """Duplicate experience, replay or stale concurrent S10 writer."""


def _require_fields(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise C1JournalError(f"{label}: exact JSON fields required")
    return value


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip() or any(c.isspace() for c in value):
        raise C1JournalError(f"{label}: nonempty structured identity required")
    return value


def _int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise C1JournalError(f"{label}: nonnegative integer required")
    return value


def _number(value: object, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise C1JournalError(f"{label}: finite nonnegative number required")
    return float(value)


def _provenance(value: object) -> Provenance:
    p = _require_fields(value, {"source", "reference"}, "provenance")
    return Provenance(_text(p["source"], "source"), _text(p["reference"], "reference"))


def _encode_state(state: LearningPreferenceState) -> dict[str, Any]:
    encoded = asdict(state)
    if state.last_update is not None:
        encoded["last_update"]["status"] = state.last_update.status.value
    return encoded


def _decode_state(value: object) -> LearningPreferenceState:
    doc = _require_fields(
        value, {
            "target_id", "value", "minimum", "maximum", "revision",
            "origin_provenance", "last_update",
        }, "retained S10 owner",
    )
    record = doc["last_update"]
    last = None
    if record is not None:
        typed = _require_fields(record, {
            "target_id", "feedback_id", "feedback_provenance", "rule_id",
            "rule_version", "authority_id", "authority_provenance",
            "update_provenance", "previous_value", "resulting_value",
            "previous_revision", "committed_revision", "status",
        }, "S10 commit record")
        last = LearningCommitRecord(
            target_id=_text(typed["target_id"], "record target"),
            feedback_id=_text(typed["feedback_id"], "feedback"),
            feedback_provenance=_provenance(typed["feedback_provenance"]),
            rule_id=_text(typed["rule_id"], "rule id"),
            rule_version=_int(typed["rule_version"], "rule version"),
            authority_id=_text(typed["authority_id"], "authority id"),
            authority_provenance=_provenance(typed["authority_provenance"]),
            update_provenance=_provenance(typed["update_provenance"]),
            previous_value=typed["previous_value"],
            resulting_value=typed["resulting_value"],
            previous_revision=_int(typed["previous_revision"], "previous revision"),
            committed_revision=_int(typed["committed_revision"], "committed revision"),
            status=LearningProposalStatus(typed["status"]),
        )
    state = LearningPreferenceState(
        target_id=_text(doc["target_id"], "S10 target"),
        value=doc["value"], minimum=doc["minimum"], maximum=doc["maximum"],
        revision=_int(doc["revision"], "S10 revision"),
        origin_provenance=_provenance(doc["origin_provenance"]),
        last_update=last,
    )
    if state.target_id != _TARGET or not 0 <= state.maximum <= 1000:
        raise C1JournalError("journal only stores bounded S10 motion owner")
    return state


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _envelope(body: dict[str, Any]) -> bytes:
    digest = hashlib.sha256(_canonical(body)).hexdigest()
    return _canonical({"body": body, "sha256": digest}) + b"\n"


def _validate_body(value: object) -> tuple[dict[str, Any], LearningPreferenceState]:
    body = _require_fields(
        value, {"schema", "self_id", "seed_revision", "seed_value", "retained", "entries"},
        "C1 motion journal",
    )
    if body["schema"] != _SCHEMA:
        raise C1JournalError("unsupported C1 journal schema")
    _text(body["self_id"], "self_id")
    revision = _int(body["seed_revision"], "seed revision")
    seed_value = _int(body["seed_value"], "seed value")
    state = _decode_state(body["retained"])
    if not isinstance(body["entries"], list):
        raise C1JournalError("C1 entries must be an array")
    seen_experiences: set[str] = set()
    seen_intents: set[tuple[str, str]] = set()
    seen_actions: set[tuple[str, str]] = set()
    value_before = seed_value
    most_recent_feedback: str | None = None
    for entry in body["entries"]:
        e = _require_fields(entry, {
            "experience_id", "session_id", "intent_id", "action_ids",
            "decision_probe_seqs", "source_sha256", "forecast_revision",
            "predicted_total_m", "measured_total_m", "comparison", "terminal_kind",
            "before_value", "after_value", "after_revision", "trained",
        }, "one terminal C1 experience")
        exp_id = _text(e["experience_id"], "experience_id")
        session_id = _text(e["session_id"], "session_id")
        intent_id = _text(e["intent_id"], "intent_id")
        if exp_id in seen_experiences or (session_id, intent_id) in seen_intents:
            raise C1JournalConflict("duplicate experience or same original Intent")
        seen_experiences.add(exp_id)
        seen_intents.add((session_id, intent_id))
        if (
            not isinstance(e["action_ids"], list) or not e["action_ids"]
            or len(e["action_ids"]) > 8
            or not isinstance(e["decision_probe_seqs"], list)
            or len(e["decision_probe_seqs"]) != len(e["action_ids"])
        ):
            raise C1JournalError("C1 Action/native-source cardinality mismatch")
        for action in e["action_ids"]:
            key = (session_id, _text(action, "original Action ID"))
            if key in seen_actions:
                raise C1JournalConflict("original Action reused in same session")
            seen_actions.add(key)
        for seq in e["decision_probe_seqs"]:
            _int(seq, "native source seq")
        if any(x >= y for x, y in zip(
            e["decision_probe_seqs"], e["decision_probe_seqs"][1:],
        )):
            raise C1JournalError("original decision sources not increasing")
        digest = e["source_sha256"]
        if (
            type(digest) is not str or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise C1JournalError("invalid source evidence digest")
        if e["comparison"] not in {
            "shorter", "longer", "within_tolerance", "unknown",
        } or e["terminal_kind"] not in {
            "completed", "failed", "invalidated", "reconsidered_release",
        }:
            raise C1JournalError("invalid C1 assessment type")
        _number(e["predicted_total_m"], "prior motion prediction")
        if e["measured_total_m"] is not None:
            _number(e["measured_total_m"], "measured motion")
        elif e["comparison"] != "unknown":
            raise C1JournalError("missing physical measurement in qualified comparison")
        if (
            _int(e["forecast_revision"], "forecast revision") != revision
            or _int(e["before_value"], "previous S10 value") != value_before
            or type(e["trained"]) is not bool
        ):
            raise C1JournalError("C1 source-S10 chain not continuous")
        after_revision = _int(e["after_revision"], "next S10 revision")
        after_value = _int(e["after_value"], "next S10 value")
        if e["trained"]:
            if e["comparison"] == "unknown" or after_revision != revision + 1:
                raise C1JournalError("trained experience must commit one S10 revision")
            most_recent_feedback = "intent-motion:" + exp_id
        elif (
            e["comparison"] != "unknown"
            or after_revision != revision
            or after_value != value_before
        ):
            raise C1JournalError("untrained experience changed the S10 owner")
        revision = after_revision
        value_before = after_value
    if (
        state.revision != revision or state.value != value_before
        or (most_recent_feedback is None and state.revision != body["seed_revision"])
        or (most_recent_feedback is not None and (
            state.last_update is None
            or state.last_update.feedback_id != most_recent_feedback
        ))
    ):
        raise C1JournalError("durable S10 owner does not match C1 history")
    return body, state


def _read(path: Path) -> tuple[dict[str, Any], LearningPreferenceState, str]:
    if path.is_symlink() or not path.is_file():
        raise C1JournalError("C1 journal must be an existing regular non-symlink file")
    try:
        raw = path.read_bytes()
        doc = json.loads(raw)
        outer = _require_fields(doc, {"body", "sha256"}, "journal envelope")
        body, state = _validate_body(outer["body"])
        sha = hashlib.sha256(_canonical(body)).hexdigest()
        if sha != outer["sha256"]:
            raise C1JournalError("C1 snapshot checksum mismatch")
        return body, state, sha
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise C1JournalError(f"cannot trust durable C1 snapshot: {exc}") from exc


@contextmanager
def _exclusive(path: Path) -> Iterator[None]:
    lock = path.with_name(path.name + ".lock")
    if lock.is_symlink() or path.is_symlink() or path.parent.is_symlink():
        raise C1JournalError("symlink journal/parent/lock path refused")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise C1JournalError("lock must be a regular file")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _write(path: Path, body: dict[str, Any]) -> str:
    rendered = _envelope(body)
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix="." + path.name + ".")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        Path(temp).unlink(missing_ok=True)
    return hashlib.sha256(_canonical(body)).hexdigest()


class C1MotionJournal:
    """Durable sidecar to one original S49/S10 owner; never an Action issuer."""

    def __init__(
        self, path: Path, body: dict[str, Any],
        state: LearningPreferenceState, sha: str,
    ) -> None:
        self.path = path
        self._body = body
        self.state = state
        self.sha256 = sha

    @property
    def self_id(self) -> str:
        return self._body["self_id"]

    @property
    def experience_ids(self) -> tuple[str, ...]:
        return tuple(e["experience_id"] for e in self._body["entries"])

    @classmethod
    def create(
        cls, path: str | os.PathLike[str], *,
        self_id: str, seed: LearningPreferenceState,
    ) -> C1MotionJournal:
        target = Path(path)
        _text(self_id, "self_id")
        if target.parent.is_symlink() or not target.parent.is_dir():
            raise C1JournalError("existing normal journal directory required")
        if not isinstance(seed, LearningPreferenceState) or seed.target_id != _TARGET:
            raise C1JournalError("original motion S10 seed required")
        if seed.revision != 0 or seed.last_update is not None:
            raise C1JournalError("fresh C1 journal must start at original S10 revision0")
        body = {
            "schema": _SCHEMA, "self_id": self_id,
            "seed_revision": seed.revision, "seed_value": seed.value,
            "retained": _encode_state(seed), "entries": [],
        }
        _validate_body(body)
        with _exclusive(target):
            if target.exists() or target.is_symlink():
                raise C1JournalConflict("existing journal must be restored, never reseeded")
            sha = _write(target, body)
        return cls(target, body, seed, sha)

    @classmethod
    def restore(
        cls, path: str | os.PathLike[str], *, self_id: str,
    ) -> C1MotionJournal:
        target = Path(path)
        with _exclusive(target):
            body, state, sha = _read(target)
        if body["self_id"] != _text(self_id, "self_id"):
            raise C1JournalError("foreign Self journal cannot become S10 owner")
        return cls(target, body, state, sha)

    def commit(self, experience: object, learning: LearningCommitResult | None) -> None:
        """One fsynced snapshot commits BOTH the C1 identity and S10 revision."""
        from adapters.mineflayer.bug0_intent_motion_learning import (
            IntentMotionExperience,
            MotionComparison,
        )

        if not isinstance(experience, IntentMotionExperience):
            raise C1JournalError("original assessed C1 experience required")
        forecast = experience.forecast
        if (
            forecast.self_id != self.self_id
            or forecast.target_id != _TARGET
            or forecast.owner_revision != self.state.revision
            or forecast.predicted_total_m != self.state.value / 10
            or experience.experience_id in self.experience_ids
        ):
            raise C1JournalConflict("stale, replayed or foreign original C1 experience")
        if experience.comparison is MotionComparison.UNKNOWN:
            if learning is not None:
                raise C1JournalError("UNKNOWN must never commit motion learning")
            next_owner = self.state
        else:
            if (
                not isinstance(learning, LearningCommitResult)
                or learning.previous_state is not self.state
                or learning.new_state.revision != self.state.revision + 1
                or learning.record is not learning.new_state.last_update
                or learning.record.feedback_id != "intent-motion:" + experience.experience_id
            ):
                raise C1JournalConflict("S10 exact committed owner object is required")
            next_owner = learning.new_state
        from adapters.mineflayer.execution import WorldConsequenceStatus
        from relay_self.action import ActionState

        action_ids = [r.terminal.action_id for r in experience.action_receipts]
        sources = [p.seq for p in experience.decision_probes]
        if (
            len(action_ids) != len(sources)
            or not action_ids or len(action_ids) > 8
        ):
            raise C1JournalError("invalid original S49 Action/source cardinality")
        prior_after = -1
        for i, (receipt, selected) in enumerate(
            zip(experience.action_receipts, experience.decision_probes)
        ):
            physical = receipt.consequence
            if (
                receipt.terminal.intent_id != forecast.intent_id
                or receipt.terminal.action_id != physical.action_id
                or receipt.terminal.state is not ActionState.OUTCOME
                or physical.status is not WorldConsequenceStatus.EXECUTED
                or physical.session_id != forecast.session_id
                or physical.before_observation is None
                or physical.after_observation is None
                or selected.session_id != forecast.session_id
                or receipt.source != selected.provenance
                or selected.seq <= prior_after
                or physical.before_observation.seq <= selected.seq
                or physical.after_observation.seq <= physical.before_observation.seq
                or (
                    i == 0 and (
                        selected.seq != forecast.source_probe_seq
                        or selected.provenance != forecast.source_provenance
                    )
                )
            ):
                raise C1JournalError(
                    "original S49 source/Action/Intent evidence is not bound"
                )
            prior_after = physical.after_observation.seq
        source_data = [{
            "action": r.terminal.action_id,
            "terminal": r.terminal.state.value,
            "selected_source": r.source.reference,
            "selected_seq": p.seq,
            "before_seq": r.consequence.before_observation.seq,
            "after_seq": r.consequence.after_observation.seq,
        } for r, p in zip(experience.action_receipts, experience.decision_probes)]
        entry = {
            "experience_id": experience.experience_id,
            "session_id": forecast.session_id,
            "intent_id": forecast.intent_id,
            "action_ids": action_ids,
            "decision_probe_seqs": sources,
            "source_sha256": hashlib.sha256(_canonical(source_data)).hexdigest(),
            "forecast_revision": forecast.owner_revision,
            "predicted_total_m": forecast.predicted_total_m,
            "measured_total_m": experience.measured_total_m,
            "comparison": experience.comparison.value,
            "terminal_kind": experience.terminal_kind.value,
            "before_value": self.state.value,
            "after_value": next_owner.value,
            "after_revision": next_owner.revision,
            "trained": learning is not None,
        }
        candidate = {
            **self._body,
            "retained": _encode_state(next_owner),
            "entries": [*self._body["entries"], entry],
        }
        _validate_body(candidate)
        with _exclusive(self.path):
            remote, _, remote_sha = _read(self.path)
            if remote_sha != self.sha256 or remote != self._body:
                raise C1JournalConflict("file owner advanced since loaded: restore first")
            updated_sha = _write(self.path, candidate)
        # In-memory owner advances ONLY after atomic replace + fsync succeeds.
        self._body = candidate
        self.state = next_owner
        self.sha256 = updated_sha
