"""S10: source-matched read-only Memory withheld/present A/B shadow.

This is a prospective *engineering negative control*. It does not replay a
physical World or demonstrate that Memory changed an Action. Both arms see the
same original typed native event/probe and retained L0 configuration. Existing
S3/L1 full-scan retrieval is already the cheap baseline; no faster/better
Memory mechanism is inferred by observing a recall.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_s3_experience import S3ReadOnlyExperience
from relay_self.experience_bridge import ReuseStatus


class S10AblationRejected(ValueError):
    """A source, Memory arm, or genuinely paired pre-decision check was absent."""


@dataclass(frozen=True, slots=True)
class S10ShadowAB:
    session_id: str
    event_seq: int
    probe_seq: int
    present_hint: str
    withheld_hint: str
    retained_memory_count: int
    present_selection: str
    withheld_selection: str
    cheap_baseline: str = "L1_EXISTING_FULL_SCAN"
    disposition: str = "RECALL_DIFFERENCE_NO_L0_DECISION_EFFECT"
    physical_runs: int = 0
    issued_actions: int = 0
    goal_attested: bool = False
    memory_caused_physical_action: bool = False
    learning_updates: int = 0
    habit_grants: int = 0
    scientific_go: bool = False


def compare_shadow_ab(
    *,
    event: MineflayerObservation,
    probe: MineflayerObservation,
    memory_present: S3ReadOnlyExperience,
    memory_withheld: S3ReadOnlyExperience,
    l0_present: NormalWorldL0,
    l0_withheld: NormalWorldL0,
) -> S10ShadowAB:
    """Compare S3 historical hint against withholding with identical L0 input.

    The two L0 checks are strictly read-only; no decide(), grant(), Action
    execution, World dispatch, or model call occurs. A real S9 source must
    first be separately admitted by R/V; synthetic tests remain synthetic.
    """
    if (
        not isinstance(event, MineflayerObservation)
        or not isinstance(probe, MineflayerObservation)
        or event.kind != "entities" or probe.kind != "probe"
        or not probe.request_id or event.request_id is not None
        or event.seq >= probe.seq
        or event.provenance.source != "mineflayer"
        or probe.provenance.source != "mineflayer"
        or event.snapshot.nearby_entities_coverage.truncated
        or probe.snapshot.nearby_entities_coverage.truncated
        or not isinstance(memory_present, S3ReadOnlyExperience)
        or not isinstance(memory_withheld, S3ReadOnlyExperience)
        or memory_present is memory_withheld
        or not isinstance(l0_present, NormalWorldL0)
        or not isinstance(l0_withheld, NormalWorldL0)
        or l0_present is l0_withheld
    ):
        raise S10AblationRejected("two independently owned source-matched arms required")
    sid = event.session_id
    if (
        probe.session_id != sid
        or memory_present.session_id != sid
        or memory_withheld.session_id != sid
        or l0_present.session_id != sid
        or l0_withheld.session_id != sid
        or l0_present.intent_id != l0_withheld.intent_id
        or l0_present.retained != l0_withheld.retained
        or l0_present.events or l0_withheld.events
        or l0_present.action_requests or l0_withheld.action_requests
        or l0_present._last_seq != l0_withheld._last_seq
        or l0_present._seen_entities != l0_withheld._seen_entities
        or l0_present._used_action_ids != l0_withheld._used_action_ids
        or l0_present.max_events != l0_withheld.max_events
        or l0_present.max_action_requests != l0_withheld.max_action_requests
        or not memory_present.snapshot.memories
        or memory_withheld.snapshot.memories
        or memory_present.snapshot.identity != memory_withheld.snapshot.identity
        or memory_present.lookback != memory_withheld.lookback
    ):
        raise S10AblationRejected("A/B source, L0 or Memory states are not matched")
    # Existing S3's S-owned admitted digest list is only set after original
    # typed S16/Action source checks; NEVER construct a fake admitted Memory.
    on_hint = memory_present.hint_for_next(probe)
    off_hint = memory_withheld.hint_for_next(probe)
    if (
        on_hint.status is not ReuseStatus.RECALL
        or off_hint.status is ReuseStatus.RECALL
        or not on_hint.memory_ids
        or off_hint.memory_ids
        or len(set(on_hint.memory_ids)) != len(on_hint.memory_ids)
    ):
        raise S10AblationRejected("independently source-retained recall contrast missing")
    before_a = (l0_present.events, l0_present.action_requests)
    before_b = (l0_withheld.events, l0_withheld.action_requests)
    # ._check only evaluates original S49 policy and does NOT issue anything.
    choice_on = l0_present._check(event, probe)
    choice_off = l0_withheld._check(event, probe)
    if (
        (l0_present.events, l0_present.action_requests) != before_a
        or (l0_withheld.events, l0_withheld.action_requests) != before_b
        or choice_on.selection != choice_off.selection
        or choice_on.entity_id != choice_off.entity_id
        or choice_on.provenance != choice_off.provenance
        or choice_on.probe_seq != choice_off.probe_seq
        or choice_on.action_authorized or choice_off.action_authorized
    ):
        raise S10AblationRejected("source-matched no-authority L0 invariant broken")
    return S10ShadowAB(
        session_id=sid, event_seq=event.seq, probe_seq=probe.seq,
        present_hint=on_hint.status.value,
        withheld_hint=off_hint.status.value,
        retained_memory_count=len(memory_present.snapshot.memories),
        present_selection=choice_on.selection.value,
        withheld_selection=choice_off.selection.value,
    )
