"""S #537 S2-B: genuine S49 live L0/Intent owner epoch read-only witness.

The original S49 runner alone invokes note_original_epoch() on the same
native probe used by its predecision live_probe callback. S2-A source
identity is checked before any S60 context can be formed. The owner Intent
does not have a revision property: its exact immutable event-history
length is used as the causal intent generation, not a fabricated "1".
No native read, model call, Action grant, retained mutation or learner.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.normal_action import (
    NormalActionClosedReadback,
    NormalWorldL0,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s537_s2a_l2_read_port import S2AReadOnlyInput
from adapters.mineflayer.s537_s2b_gated_l2_shadow import (
    S2BOwnerContextRead,
    S2BSourceRejected,
)
from relay_self.intent import IntentCommitment, IntentEventKind
from relay_self.interruption_fence import CognitionContext
from relay_self.learning import LearningPreferenceState


@dataclass(frozen=True, slots=True)
class _OriginalEpochSource:
    probe: MineflayerObservation
    host: NormalWorldL0
    intent: IntentCommitment
    intent_generation: int
    retained_revision: int
    intent_id: str
    intent_events: tuple[object, ...]
    retained_source: LearningPreferenceState


class S2BOriginalOwnerEpochBinder:
    """A single-session, fail-closed original-source observer (max 8)."""

    def __init__(self) -> None:
        self._session: str | None = None
        self._host: NormalWorldL0 | None = None
        self._intent: IntentCommitment | None = None
        self._entries: list[_OriginalEpochSource] = []
        self.errors: list[str] = []

    def note_original_epoch(
        self, probe: MineflayerObservation,
        host: NormalWorldL0,
        intent: IntentCommitment,
    ) -> None:
        """Invoked before original live_probe, never allowed to veto S49."""
        try:
            if (
                not isinstance(probe, MineflayerObservation)
                or probe.kind != "probe"
                or not isinstance(host, NormalWorldL0)
                or not isinstance(intent, IntentCommitment)
                or not isinstance(probe.request_id, str)
                or not probe.request_id.startswith(
                    f"s49-actual:{probe.session_id}:event-"
                )
                or host.session_id != probe.session_id
                or self._session not in (None, probe.session_id)
                or (self._host is not None and self._host is not host)
                or (self._intent is not None and self._intent is not intent)
                or not isinstance(host.retained, LearningPreferenceState)
                or type(host.retained.revision) is not int
                or host.retained.revision < 0
                or not isinstance(intent.events, tuple)
                or not intent.events
                or intent.current_intent is None
                or intent.pending_reconsideration is not None
                or intent.current_intent.intent_id != host.intent_id
                or not 1 <= len(intent.events) <= 32
                or intent.events[-1].kind not in (
                    IntentEventKind.COMMITTED,
                    IntentEventKind.RECONSIDERED_CONTINUE,
                )
                or len(self._entries) >= 8
                or (
                    self._entries
                    and (
                        probe.seq <= self._entries[-1].probe.seq
                        or len(intent.events) < self._entries[-1].intent_generation
                        or host.retained.revision <
                        self._entries[-1].retained_revision
                        or intent.events[:len(self._entries[-1].intent_events)]
                        != self._entries[-1].intent_events
                    )
                )
            ):
                raise S2BSourceRejected("original L0/Intent owner source unavailable")
            self._session = probe.session_id
            self._host = host
            self._intent = intent
            self._entries.append(_OriginalEpochSource(
                probe=probe, host=host, intent=intent,
                intent_generation=len(intent.events),
                retained_revision=host.retained.revision,
                intent_id=host.intent_id,
                intent_events=intent.events,
                retained_source=host.retained,
            ))
        except (ValueError, TypeError, AttributeError) as exc:
            self.errors.append(type(exc).__name__)

    def bind(
        self, source: S2AReadOnlyInput, original_probe: MineflayerObservation,
    ) -> S2BOwnerContextRead:
        """Same exact native object and owner identity; no future revision."""
        if (
            self.errors
            or not isinstance(source, S2AReadOnlyInput)
            or not isinstance(original_probe, MineflayerObservation)
            or not self._entries
            or not isinstance(self._host, NormalWorldL0)
            or not isinstance(self._intent, IntentCommitment)
        ):
            raise S2BSourceRejected("no original owner epoch witness")
        entry = self._entries[-1]
        if (
            entry.probe is not original_probe
            or entry.host is not self._host
            or entry.intent is not self._intent
            or original_probe.session_id != source.session_id
            or original_probe.seq != source.probe_seq
            or original_probe.request_id != source.request_id
            or entry.intent_id != entry.host.intent_id
            or entry.intent.current_intent is None
            or entry.intent.pending_reconsideration is not None
            or entry.intent.current_intent.intent_id != entry.intent_id
            or entry.host.retained is not entry.retained_source
            or entry.host.retained.revision != entry.retained_revision
            or entry.intent.events != entry.intent_events
            or len(entry.intent.events) != entry.intent_generation
        ):
            raise S2BSourceRejected("original owner has advanced or changed identity")
        return S2BOwnerContextRead(
            source_input=source,
            context=CognitionContext(
                session_id=source.session_id,
                world_seq=source.probe_seq,
                intent_revision=entry.intent_generation,
                retained_revision=entry.retained_revision,
            ),
            intent_id=entry.intent_id,
            owner_scope="ORIGINAL_S49_L0_AND_INTENT_READ_ONLY",
        )

    def context_at_original_s16(
        self, closed: NormalActionClosedReadback,
    ) -> CognitionContext:
        """Read actual original owner state at S16, without a new World probe."""
        if (
            self.errors or not isinstance(closed, NormalActionClosedReadback)
            or not self._entries or self._host is None or self._intent is None
            or self._entries[-1].probe is not closed.original_probe
            or self._entries[-1].host is not self._host
            or self._entries[-1].intent is not self._intent
            or self._intent.current_intent is None
            or self._intent.pending_reconsideration is not None
            or self._intent.current_intent.intent_id != self._host.intent_id
            or self._intent.events[:len(self._entries[-1].intent_events)]
            != self._entries[-1].intent_events
            or len(self._intent.events) < self._entries[-1].intent_generation
            or self._host.retained.revision < self._entries[-1].retained_revision
        ):
            raise S2BSourceRejected("S16 cannot read original current owners")
        after = closed.consequence.after_observation
        if (
            after is None or after.session_id != self._session
            or type(after.seq) is not int
            or after.seq <= closed.original_probe.seq
            or closed.terminal.action_id != closed.consequence.action_id
        ):
            raise S2BSourceRejected("S16 native after source is not current")
        return CognitionContext(
            session_id=after.session_id,
            world_seq=after.seq,
            intent_revision=len(self._intent.events),
            retained_revision=self._host.retained.revision,
        )

    def bounded_row(self) -> dict[str, object]:
        return {
            "schema": "S537_S2B_ORIGINAL_EPOCH_OWNER_WITNESS_DEV_V1",
            "status": "RECORDED" if self._entries and not self.errors else "DEFERRED",
            "session_id": self._session,
            "epochs": [
                {
                    "native_probe_seq": item.probe.seq,
                    "intent_generation": item.intent_generation,
                    "retained_revision": item.retained_revision,
                    "intent_id": item.intent_id,
                }
                for item in self._entries
            ],
            "errors": list(self.errors),
            "model_calls": 0,
            "action_authority": False,
            "source_attested": False,
        }
