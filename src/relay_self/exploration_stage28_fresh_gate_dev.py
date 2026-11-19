"""D6: reuse the REAL Stage28 fresh L1 evidence gate before D reconsideration.

No independent owner, new model call, GPU grant, or physical issue. The existing
B Stage28 Native/Paper/GPU witness is required as an input, and current actual
B original resident owners must agree before a NEW L1 choice can be considered.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.exploration_continuity_dev import open_question_refs
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.resident_llama_inference_lane_dev import LlamaSlotIdleReceipt
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28ForkPaperEpoch,
    Stage28FreshL1Eligibility,
    Stage28NativePaperBodyLink,
    stage28_require_fresh_l1_eligibility,
)
from relay_self.stage28c2_recovered_resident_owner_dev import Stage28c2aOfflineOwners
from relay_self.world_resident_lifecycle_dev import NativeLoginEvidence, WorldLifetime


class D6FreshReconsiderationHold(RuntimeError):
    """Fresh original World/Owner/L1 evidence missing; do not reuse L2."""


@dataclass(frozen=True, slots=True)
class D6CurrentQuestionView:
    self_id: str
    native_session_id: str
    current_source_world_session_id: str
    active_question_refs: tuple[str, ...]
    prior_l2_attempt_refs: tuple[str, ...]
    l1_new_reevaluation_eligible: bool = True
    prior_l2_reissue_authorized: bool = False
    physical_action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class D6NewL1Admission:
    eligibility: Stage28FreshL1Eligibility
    questions: tuple[D6CurrentQuestionView, ...]
    old_l1_decision_reusable: bool = False
    l2_model_call_authorized: bool = False
    action_issue_authorized: bool = False


def inspect_d6_new_exploration_reevaluation(
    recovered: Stage28c2aOfflineOwners,
    *,
    world: WorldLifetime,
    logins: tuple[NativeLoginEvidence, ...],
    idle: LlamaSlotIdleReceipt,
    boot: Stage28ForkPaperEpoch,
    links: tuple[Stage28NativePaperBodyLink, ...],
) -> D6NewL1Admission:
    """Read-only admission: the original B gate plus current A/B native probes.

    Restored OPEN Questions are inert references. A *new* CPU projection/L1
    request must still be constructed by existing Cognition Owners; this
    receipt does not choose a Goal, schedule GPU work, or reopen any old L2.
    """
    if not isinstance(recovered, Stage28c2aOfflineOwners):
        raise D6FreshReconsiderationHold("real Stage28 original owner required")
    try:
        eligible = stage28_require_fresh_l1_eligibility(
            recovered.plan, world=world, logins=logins,
            idle=idle, boot=boot, links=links,
        )
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        raise D6FreshReconsiderationHold(
            "original Stage28 fresh Native/Paper/GPU evidence HOLD"
        ) from exc
    # Check against the *actual* restored owner, not a supplied standalone
    # login dataclass or the old archived L2 reservation receipt.
    try:
        if (
            not eligible.l1_reevaluation_eligible
            or eligible.old_l1_decision_reusable
            or eligible.physical_action_issue_authorized
            or eligible.generation_id != recovered.receipt.generation_id
            or eligible.fork_branch_id != recovered.receipt.fork_branch_id
            or eligible.world_id != recovered.receipt.source_world_id
            or eligible.paper_session_id != world.paper_session_id
            or recovered.physical.active_action_ids
            or not recovered.physical.all_residents_offline
            or tuple(sorted(recovered.owners)) != tuple(recovered.plan.roster)
        ):
            raise D6FreshReconsiderationHold(
                "recovered cohort or original physical permission mismatch"
            )
        with recovered.cognitive_work.lock:
            proof_by_self = {proof.self_id: proof for proof in logins}
            current = []
            for self_id, new_session in eligible.native_sessions:
                owner = recovered.owners[self_id]
                e, actual_session, world_epoch = (
                    recovered.cognitive_work.current_scope(self_id)
                )
                observation = owner.current_worldbody_observation
                proof = proof_by_self[self_id]
                if (
                    type(e) is not int or e < 1
                    or world_epoch != eligible.world_epoch
                    or actual_session != new_session
                    or owner.cohort is not recovered.cognitive_work
                    or owner.native_session_id != new_session
                    or owner.fresh_native_observation_required
                    or not isinstance(observation, MineflayerObservation)
                    or observation.kind != "probe"
                    or observation.session_id != new_session
                    or observation.request_id != proof.observation_ref
                    or observation.snapshot.time is None
                    or owner.last_observed_tick != (
                        observation.snapshot.time.day * 24000
                        + observation.snapshot.time.time_of_day
                    )
                    or owner.retained.identity.self_id != self_id
                    or owner.files.cognition_file.is_symlink()
                    or owner.files.cognition_file != owner.files.self_root / "cognition.json"
                    or load_persistent_cognition(owner.files.cognition_file) != owner.retained
                    or (owner.retained.pattern_registry is not None
                        and owner.retained.pattern_registry != owner.pattern_registry)
                ):
                    raise D6FreshReconsiderationHold(
                        "original resident native probe not current/qualified"
                    )
                open_refs = open_question_refs(
                    owner.retained, expected_self_id=self_id,
                )
                if not set(open_refs).issubset(owner.pending_questions):
                    raise D6FreshReconsiderationHold(
                        "restored Question not adopted by original resident"
                    )
                prior = owner.retained.exploration_continuity
                current.append(D6CurrentQuestionView(
                    self_id=self_id, native_session_id=new_session,
                    current_source_world_session_id=world.paper_session_id,
                    active_question_refs=open_refs,
                    prior_l2_attempt_refs=() if prior is None else tuple(
                        a.attempt_ref for a in prior.attempts
                    ),
                ))
    except D6FreshReconsiderationHold:
        raise
    except (KeyError, ValueError, RuntimeError, TypeError, AttributeError) as exc:
        raise D6FreshReconsiderationHold(
            "original restored A/B resident not admitted"
        ) from exc
    return D6NewL1Admission(eligible, tuple(current))
