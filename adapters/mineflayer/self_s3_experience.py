"""S3 glue only: original S49/S16 receipt -> existing L1 Memory -> read-only next hint.

No issuer, learning authority, habit promotion, model or new persistent owner.
All S3 hints are historical observed Action *references*, NEVER safe actions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from relay_self.action import ActionState
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.experience_bridge import (
    CognitiveHint,
    ExperienceRejected,
    ReuseQuery,
    qualify_episode,
    retain_observation,
    retrieve_experience,
)
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.provenance import Provenance

CUES = ("near_zombie",)
DEFAULT_SOURCE_SEQ_LOOKBACK = 32


@dataclass(frozen=True, slots=True)
class RetainedReceipt:
    memory_id: str
    evidence_sha256: str
    source_seq: int
    session_id: str


class S3ReadOnlyExperience:
    """One S-owned session-local retained snapshot, using only existing Memory APIs.

    'world_revision' in L1 is populated with an actual source protocol seq,
    NOT a verified persistent World-state revision. Lookback only admits
    *historical context*, not current goal/safety/skill authority.
    """

    def __init__(self, session_id: str, *, lookback: int = DEFAULT_SOURCE_SEQ_LOOKBACK):
        if not isinstance(session_id, str) or not session_id.strip():
            raise ExperienceRejected("original source session required")
        if type(lookback) is not int or not 0 <= lookback <= 64:
            raise ExperienceRejected("bounded source-sequence lookback required")
        self.session_id = session_id
        self.lookback = lookback
        self._snapshot = PersistentCognition(IdentitySpecification(
            f"s3-session:{session_id}", ("Retain observations without goal or learning claims.",),
            Provenance("self-s3-operator", f"session:{session_id}"),
        ))
        self._admitted: set[str] = set()
        self._seen: set[str] = set()

    @property
    def snapshot(self) -> PersistentCognition:
        return self._snapshot

    def observe_original(
        self, receipt: NormalActionReceipt, *,
        correlated_probe: MineflayerObservation, expected_action_id: str,
    ) -> RetainedReceipt:
        """Read and verify the already-executed owner receipt; never dispatch."""
        if not isinstance(receipt, NormalActionReceipt):
            raise ExperienceRejected("existing S49 receipt required")
        if not isinstance(correlated_probe, MineflayerObservation):
            raise ExperienceRejected("original correlated native probe required")
        # A source-verified near-zombie cue is required; do not invent it
        # just because an Action later reported movement.
        if (
            correlated_probe.snapshot.nearby_entities_coverage.truncated
            or not any(
                entity.name == "zombie" and entity.distance < 4.0
                for entity in correlated_probe.snapshot.nearby_entities
            )
        ):
            raise ExperienceRejected("source did not establish near-zombie cue")
        outcome = receipt.outcome_interpretation
        terminal = receipt.terminal
        consequence = receipt.consequence
        if (
            outcome is None
            or not terminal.is_current_snapshot
            or terminal.state is not ActionState.OUTCOME
            or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
            or consequence.session_id != self.session_id
            or correlated_probe.session_id != self.session_id
            or receipt.source != correlated_probe.provenance
            or receipt.source.source != "mineflayer"
            or not correlated_probe.request_id
            or outcome.session_id != self.session_id
            or outcome.world_provenance != consequence.provenance
            or outcome.binding_id != consequence.binding_id
            or outcome.action_ref != consequence.action_ref
            or outcome.action_id != consequence.action_id
            or not isinstance(expected_action_id, str)
            or not expected_action_id
            or terminal.action_id != expected_action_id
            or outcome.action_id != expected_action_id
            or consequence.action_id != expected_action_id
            or terminal.action_id in self._seen
            or consequence.after_observation is None
            or consequence.after_observation.seq <= correlated_probe.seq
        ):
            raise ExperienceRejected("non-original or foreign S16/S49 receipt")
        # Existing native evidence checker validates ordered original frames,
        # exact Action ID, dispatch/clear ownership and independent movement.
        frames = capture_native_action_evidence(consequence)
        digest = hashlib.sha256(json.dumps(
            frames, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")).hexdigest()
        qualified = qualify_episode(
            terminal, outcome,
            world_revision=consequence.after_observation.seq,
            evidence_sha256=digest, cue_tags=CUES,
        )
        updated = retain_observation(
            self._snapshot, qualified,
            integration_provenance=Provenance(
                "self-s3-original-s16-observation",
                f"{self.session_id}:{terminal.action_id}:{digest}",
            ),
        )
        self._snapshot = updated
        self._admitted.add(digest)
        self._seen.add(terminal.action_id)
        return RetainedReceipt(
            qualified.episode.memory_id, digest,
            consequence.after_observation.seq, self.session_id,
        )

    def hint_for_next(self, reading: MineflayerObservation) -> CognitiveHint:
        """Read-only historical context for a *new* correlated native source."""
        if (
            not isinstance(reading, MineflayerObservation)
            or reading.session_id != self.session_id
            or reading.provenance.source != "mineflayer"
            or reading.provenance.reference != f"{self.session_id}:{reading.seq}"
            or reading.kind not in {"entities", "probe"}
            or not reading.request_id
            or reading.snapshot.nearby_entities_coverage.truncated
        ):
            raise ExperienceRejected("current source-qualified native probe required")
        cue_tags = (
            CUES
            if any(
                e.name == "zombie" and e.distance < 4.0
                for e in reading.snapshot.nearby_entities
            )
            else ("no_zombie",)
        )
        return retrieve_experience(
            self._snapshot,
            ReuseQuery(
                self.session_id, reading.seq, cue_tags,
                frozenset(self._admitted), max_revision_lag=self.lookback,
            ),
        )
