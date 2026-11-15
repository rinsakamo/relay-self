"""DEV adapter: existing L1-selected native shadow -> new physical PROPOSED.

This is a temporary compatibility path for #844's already-tested read-only
two-probe evidence, *not* the original S49 runtime, a new Action issuer, or
a policy that maps EAT/ATTACK to primitive effects. That mapping belongs to
the verified Skill interpreter and WorldBody capability catalogue.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.cognitive_s49_readonly_handoff import (
    S49ReadOnlyHandoff,
    assess_s49_readonly_handoff,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import SchemaFrame, Selection
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalActionProposalReceipt,
    PhysicalCapability,
    PhysicalReadback,
    propose_bound_physical_action,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


@dataclass(frozen=True, slots=True)
class CognitivePhysicalProposal:
    """Two-probe native witness and nonissuing existing Action PROPOSED."""

    read_only_witness: S49ReadOnlyHandoff
    port_proposal: PhysicalActionProposalReceipt


def propose_from_cognitive_readonly_evidence(
    selection: Selection,
    *,
    original_frame: SchemaFrame,
    current_frame: SchemaFrame,
    previous_probe: MineflayerObservation,
    current_probe: MineflayerObservation,
    selected_intent_id: str,
    capability: PhysicalCapability,
    action_id: str,
    intent_owner: IntentCommitment,
    skill_execution: SkillExecution,
    supervisor: ActionSupervisor,
    at_ns: int,
    provenance: Provenance,
) -> CognitivePhysicalProposal:
    """Require exact L1 Target, original native source, existing Skill/Intent.

    Callers must supply a *trusted, pre-mapped primitive capability*, not an
    LLM-invented Action ID/capability. EAT is a multi-primitive Skill; this
    prepares only one already-bound primitive, never executes the meal.
    """
    witness = assess_s49_readonly_handoff(
        selection,
        original_frame=original_frame,
        current_frame=current_frame,
        previous_probe=previous_probe,
        current_probe=current_probe,
        proposed_intent_id=selected_intent_id,
    )
    option = selection.option
    assert option is not None

    binding = PhysicalActionBinding(
        scope=current_frame.scope,
        intent_id=witness.proposed_intent_id,
        goal_id=witness.goal_id,
        skill_id=witness.skill_id,
        skill_version=witness.skill_version,
        skill_execution_id=skill_execution.execution_id,
        action_id=action_id,
        capability_ref=capability.capability_ref,
        capability_version=capability.version,
        body_channel=capability.body_channel,
        target_kind=option.target_kind,
        target_ref=witness.target_ref,
        native_seq=witness.current_probe_seq,
        native_request_id=witness.current_probe_request_id,
        native_source=current_probe.provenance,
    )
    readback = PhysicalReadback(
        scope=current_frame.scope,
        source=current_probe.provenance,
        seq=current_probe.seq,
        request_id=current_probe.request_id or "",
        observed_target_refs=(witness.target_ref,),
        body_viable=(
            current_probe.snapshot.health > 0
            and current_probe.snapshot.oxygen_level != 0
        ),
    )
    result = propose_bound_physical_action(
        binding,
        capability=capability,
        readback=readback,
        intent_owner=intent_owner,
        skill_execution=skill_execution,
        supervisor=supervisor,
        at_ns=at_ns,
        provenance=provenance,
    )
    return CognitivePhysicalProposal(witness, result)
