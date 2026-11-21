"""Stage24b DEV: real SystemOne choice -> ORIGINAL resident physical MOVE owner.

One real Bounded SystemOne call from the existing per-Self inference lane
chooses a PREBOUND numbered relative Skill option. This is not a new Action
issuer, a navigation controller or a proof of Goal completion. No retries.
"""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.cognitive_physical_executor_dev import PhysicalDevGrant, PhysicalGrantStage
from experiments.p0d_real_paper_smoke_dev import _write_bytes_new, file_sha256
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderDecision, RelayEngine
from relay_self.resident_exploration_gate_audit_dev import audit_exploration_gate
from relay_self.resident_l1_move_options_dev import (
    MOVE_PULSE_SECONDS,
    build_resident_l1_move_turn,
    propose_resident_l1_move,
    resolve_resident_l1_move,
)
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from relay_self.resident_move_raw_audit_dev import readback_owned_move_native_source


class Stage24bMoveRefusal(RuntimeError):
    """One original-world/model/option/issuer source could not be qualified."""


class Stage24bNoAction(Stage24bMoveRefusal):
    """The actual model declined, was unresolved, or its choice went stale."""


B_CAPABILITY = PhysicalCapability("MOVE", 1, "locomotion", "RELATIVE", True)


def _frozen_model_choice(
    *, turn, provider: ProviderDecision, selected, ticket,
    model_elapsed_ns: int, probe_before: MineflayerObservation,
    probe_after: MineflayerObservation, ticket_intent_owner,
) -> dict[str, object]:
    """Model output is source-qualified, but not independently raw HTTP replayed."""
    request = turn.round.request
    return {
        "schema": 1,
        "classification": "STAGE24B_ACTUAL_L1_CHOICE_SOURCE_DEV",
        "self_id": ticket.self_id,
        "work_ref": ticket.work_ref,
        "self_epoch": ticket.self_epoch,
        "world_epoch": ticket.world_epoch,
        "backend_ref": ticket.backend_ref,
        "mode": ticket.mode.value,
        "request_id": request.request_id,
        "request_instruction": request.instruction,
        "request_choices": [
            {"id": x.choice_id, "description": x.description}
            for x in request.choices
        ],
        "request_context": [
            {"key": x.key, "value_json": x.value_json,
             "source": x.provenance.source, "reference": x.provenance.reference}
            for x in request.context
        ],
        "candidates_sha256": turn.candidate_set_sha256,
        "cpu_epoch": turn.round.frame.epoch,
        "cpu_schema_elapsed_ns": turn.round.frame.elapsed_ns,
        "cpu_exploration_need_active": turn.exploration_need_active,
        "stage24c_gate_historical_indicators_only": True,
        "stage24c_original_gate": asdict(audit_exploration_gate(
            probe_before, intent_owner=ticket_intent_owner,
        )),
        "stage24c_latest_gate": asdict(audit_exploration_gate(
            probe_after, intent_owner=ticket_intent_owner,
        )),
        "before_native_session": probe_before.session_id,
        "before_native_seq": probe_before.seq,
        "before_request_id": probe_before.request_id,
        "before_provenance_ref": probe_before.provenance.reference,
        "after_native_session": probe_after.session_id,
        "after_native_seq": probe_after.seq,
        "after_request_id": probe_after.request_id,
        "after_provenance_ref": probe_after.provenance.reference,
        "actual_model_status": provider.status.value,
        "actual_model_choice_id": provider.choice_id,
        "actual_model_reason": provider.reason,
        "actual_model_facts": asdict(provider.call_facts),
        "actual_model_elapsed_ns": model_elapsed_ns,
        "selected_status": selected.status,
        "selected_reason": selected.selection.reason,
        "selected_goal_id": (
            selected.candidate.option.goal_id if selected.candidate else None
        ),
        "selected_skill_id": (
            selected.candidate.option.skill_id if selected.candidate else None
        ),
        "selected_target_ref": (
            selected.candidate.option.target_ref if selected.candidate else None
        ),
        "selected_preset_ref": (
            selected.candidate.preset_ref if selected.candidate else None
        ),
        "selected_pulse_seconds": (
            selected.candidate.pulse_seconds if selected.candidate else None
        ),
        "actual_original_action_issued": False,
        "model_raw_http_bytes_archived": False,
        "physical_action_authorized_by_model": False,
    }


def require_frozen_stage24b_choice(
    path: Path, sha256: str, *,
    original_action_id: str, intent_id: str, skill_execution_id: str,
    target_ref: str, model_choice_id: str,
) -> dict[str, object]:
    """Recheck actual frozen L1 choice lineage, not a mutable report flag."""
    if file_sha256(path) != sha256:
        raise Stage24bMoveRefusal("frozen actual L1 choice digest changed")
    try:
        result = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise Stage24bMoveRefusal("model choice source not readable") from exc
    if (
        type(result) is not dict
        or result.get("classification") != "STAGE24B_ACTUAL_L1_CHOICE_SOURCE_DEV"
        or result.get("self_id") != "B"
        or result.get("mode") != CognitionMode.BOUNDED.value
        or result.get("actual_model_status") != "resolved"
        or result.get("actual_model_choice_id") != model_choice_id
        or result.get("selected_status") != "READY"
        or result.get("selected_target_ref") != target_ref
        or result.get("selected_skill_id") != "MOVE"
        or result.get("selected_goal_id") != "EXPLORE_WORLD"
        or result.get("selected_pulse_seconds") != MOVE_PULSE_SECONDS
        or result.get("actual_original_action_issued") is not False
        or result.get("physical_action_authorized_by_model") is not False
        or result.get("model_raw_http_bytes_archived") is not False
        or not isinstance(result.get("candidates_sha256"), str)
        or len(result["candidates_sha256"]) != 64
        or not any(
            x.get("id") == model_choice_id and target_ref in x.get("description", "")
            for x in result.get("request_choices", ())
            if type(x) is dict
        )
    ):
        raise Stage24bMoveRefusal("frozen SystemOne number/Skill/Target not admissible")
    # The only path that assigns these original ID strings is the caller's
    # existing Intent/Skill/Action owner, not the model.
    for identity in (original_action_id, intent_id, skill_execution_id):
        if type(identity) is not str or not identity:
            raise Stage24bMoveRefusal("original owner identity missing")
    return result


def require_frozen_stage24b_binding(
    path: Path, sha256: str, *,
    model_choice_sha256: str, action_id: str, intent_id: str,
    skill_execution_id: str, target_ref: str, chosen_number: str,
    native_probe_seq: int, native_request_id: str,
) -> dict[str, object]:
    """Independent disk readback of the typed original pre-ISSUE binding."""
    if file_sha256(path) != sha256:
        raise Stage24bMoveRefusal("frozen Stage24b Intent/Skill/Action binding digest changed")
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise Stage24bMoveRefusal("frozen Stage24b original binding unreadable") from exc
    binding = record.get("physical_binding") if type(record) is dict else None
    if (
        type(record) is not dict
        or record.get("classification") != "STAGE24B_PREISSUE_L1_OPTION_BINDING_DEV"
        or record.get("actual_model_choice_sha256") != model_choice_sha256
        or record.get("selected_number") != chosen_number
        or record.get("physical_authorized") is not False
        or record.get("physical_issued") is not False
        or type(binding) is not dict
        or binding.get("action_id") != action_id
        or binding.get("intent_id") != intent_id
        or binding.get("skill_execution_id") != skill_execution_id
        or binding.get("target_ref") != target_ref
        or binding.get("native_seq") != native_probe_seq
        or binding.get("native_request_id") != native_request_id
        or binding.get("goal_id") != "EXPLORE_WORLD"
        or binding.get("skill_id") != "MOVE"
        or binding.get("skill_version") != 1
        or binding.get("target_kind") != "RELATIVE"
        or binding.get("capability_ref") != "MOVE"
    ):
        raise Stage24bMoveRefusal("frozen L1 option and original Action binding diverged")
    return record


async def run_stage24b_selected_b_move(
    *, session: MineflayerProcessSession,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    evidence_dir: Path,
    read_probe: Callable[[MineflayerProcessSession], Awaitable[MineflayerObservation]],
    real_world_granted: bool,
    real_llm_granted: bool,
    epoch: int = 1,
    model_timeout_s: float = 60.0,
) -> dict[str, object]:
    """One inference and at most one original native MOVE, never retries.

    Returns only after an actual original WAL terminal and independent raw
    native replay. A model DEFER/ESCALATE/unknown is a recorded NO_ACTION HOLD.
    """
    if (
        not real_world_granted or not real_llm_granted
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or not isinstance(session, MineflayerProcessSession)
        or not isinstance(owner, CheckpointedCognitiveOwner)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(evidence_dir, Path) or not evidence_dir.is_dir()
        or not callable(read_probe)
        or type(epoch) is not int or epoch < 0
        or not 1 <= model_timeout_s <= 120
        or owner.self_id != "B"
        or owner.native_session_id != session.started.session_id
        or physical.current_native_sessions.get("B") != session.started.session_id
        or physical.resident_states.get("B") != "ONLINE"
        or owner.intent.current_intent is not None
        or owner.supervisor.recorded_actions
    ):
        raise Stage24bMoveRefusal("actual L1/World and original B owner not admitted")
    PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="B",
    ).require_clear()
    raw = evidence_dir / "B-original-move-native-source.jsonl"
    # Stage23b process-owned original stdout capture starts before first probe.
    session.start_raw_source_audit(raw)
    issued_result = None
    receipt = None
    issued_probe = None
    try:
        observed = await read_probe(session)
        turn = build_resident_l1_move_turn(
            observed, self_id="B", intent_owner=owner.intent,
            capability=B_CAPABILITY, epoch=epoch,
        )
        # An unresolved Goal still goes through genuine SystemOne to choose
        # DEFER/ESCALATE, never a forced physical MOVE fallback.
        started_ns = time.perf_counter_ns()
        ticket = lane.submit(
            "B", work_ref="stage24b-systemone-" + uuid.uuid4().hex,
            request=turn.round.request, mode=CognitionMode.BOUNDED,
        )
        provider = await lane.await_result(ticket, timeout_s=model_timeout_s)
        elapsed_ns = time.perf_counter_ns() - started_ns
        if not isinstance(provider, ProviderDecision):
            raise Stage24bMoveRefusal("real SystemOne returned nondecision")
        # Use the existing RelayEngine bounded result verifier, with the
        # *already returned* original provider decision, not a second call.
        selected_result = RelayEngine(
            lambda request, *, mode: provider,
        )(turn.round.request)
        # Two different probes AFTER model inference are mandatory before
        # selecting an original Action/physical admission lease.
        previous = await read_probe(session)
        current = await read_probe(session)
        if (
            previous.session_id != observed.session_id
            or current.session_id != observed.session_id
            or not observed.seq < previous.seq < current.seq <= previous.seq + 32
            or not previous.request_id or not current.request_id
            or len({observed.request_id, previous.request_id, current.request_id}) != 3
        ):
            raise Stage24bMoveRefusal("two fresh post-SystemOne source probes missing")
        selected = resolve_resident_l1_move(
            turn, selected_result, current_probe=current,
            intent_owner=owner.intent, capability=B_CAPABILITY, epoch=epoch + 1,
        )
        audit = _frozen_model_choice(
            turn=turn, provider=provider, selected=selected, ticket=ticket,
            model_elapsed_ns=elapsed_ns, probe_before=observed, probe_after=current,
            ticket_intent_owner=owner.intent,
        )
        decision_file = evidence_dir / "B-original-systemone-choice.json"
        _write_bytes_new(
            decision_file, (json.dumps(audit, sort_keys=True, indent=2) + "\n").encode(),
        )
        decision_sha = file_sha256(decision_file)
        # Never reinterpret an actual Gemma NO_ACTION as successful MOVE.
        if selected.status != "READY" or selected.candidate is None:
            raise Stage24bNoAction(
                f"original L1 returned {selected.status}, no native Action issued"
            )
        candidate = selected.candidate
        if (
            candidate.pulse_seconds != MOVE_PULSE_SECONDS
            or candidate.option.target_ref not in {
                "relative:forward", "relative:back",
                "relative:left", "relative:right",
            }
            or provider.choice_id != candidate.choice_id
        ):
            raise Stage24bMoveRefusal("model attempted mutable/nonphysical MOVE")
        intent_id = "stage24b-intent-" + uuid.uuid4().hex
        skill_run_id = "stage24b-run-" + uuid.uuid4().hex
        action_id = "stage24b-action-" + uuid.uuid4().hex
        require_frozen_stage24b_choice(
            decision_file, decision_sha,
            original_action_id=action_id, intent_id=intent_id,
            skill_execution_id=skill_run_id,
            target_ref=candidate.option.target_ref, model_choice_id=candidate.choice_id,
        )
        provenance = Provenance(
            "stage24b-systemone-chosen-dev", "sha256:" + decision_sha,
        )
        intent_commit_monotonic_ns = time.monotonic_ns()
        owner.commit_intent(
            intent_id, candidate.option.goal_id, at_ns=1, provenance=provenance,
        )
        owner.start_skill(
            skill_run_id, "MOVE", at_ns=2, provenance=provenance,
        )
        skill = owner.skills[skill_run_id]
        proposal = propose_resident_l1_move(
            selected, intent_owner=owner.intent,
            skill_execution=skill, supervisor=owner.supervisor,
            intent_id=intent_id, action_id=action_id,
            at_ns=3, provenance=provenance,
        )
        if (
            proposal.binding.target_ref != candidate.option.target_ref
            or proposal.binding.goal_id != candidate.option.goal_id
        ):
            raise Stage24bMoveRefusal("selected L1 option changed before issue")
        # Immutable link created *before* any native issuance and before the
        # original canonical WAL PREPARED, not a second Action authority.
        binding_file = evidence_dir / "B-stage24b-preissue-binding.json"
        binding_record = {
            "schema": 1,
            "classification": "STAGE24B_PREISSUE_L1_OPTION_BINDING_DEV",
            "actual_model_choice_sha256": decision_sha,
            "selected_number": candidate.choice_id,
            "physical_binding": asdict(proposal.binding),
            "physical_authorized": False,
            "physical_issued": False,
        }
        _write_bytes_new(
            binding_file,
            (json.dumps(binding_record, sort_keys=True, indent=2) + "\n").encode(),
        )
        binding_sha = file_sha256(binding_file)
        require_frozen_stage24b_binding(
            binding_file, binding_sha, model_choice_sha256=decision_sha,
            action_id=action_id, intent_id=intent_id,
            skill_execution_id=skill.execution_id,
            target_ref=candidate.option.target_ref,
            chosen_number=candidate.choice_id,
            native_probe_seq=current.seq,
            native_request_id=current.request_id,
        )

        def grant(stage: PhysicalGrantStage) -> PhysicalDevGrant:
            return PhysicalDevGrant(
                stage=stage,
                authority_id="operator-stage24b-physical-permission-" + stage.value.lower(),
                provenance=Provenance(
                    "stage24b-operator-physical-dev-" + stage.value.lower(),
                    current.provenance.reference,
                ),
                intent_id=intent_id, action_id=action_id,
                session_id=current.session_id, probe_seq=current.seq,
                probe_request_id=current.request_id,
                selected_target_ref=proposal.binding.target_ref,
                granted=real_world_granted,
            )
        original_wal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id="B",
        )
        receipt = await physical.issue_move(
            session, proposal=proposal,
            previous_probe=previous, current_probe=current,
            propose_grant=grant(PhysicalGrantStage.PROPOSE),
            issue_grant=grant(PhysicalGrantStage.ISSUE),
            intent_owner=owner.intent, skill_execution=skill,
            supervisor=owner.supervisor, journal=original_wal,
            at_ns=4, provenance=provenance,
            grant_real_world=real_world_granted,
            acknowledge_dev_unverified_principal=True,
            evidence_timeout_s=15,
            pulse_seconds=candidate.pulse_seconds,
        )
        # A missing/synthetic timestamp is not an admissible dispatch interval.
        if (
            type(receipt.native_start_dispatch_monotonic_ns) is not int
            or receipt.native_start_dispatch_monotonic_ns < intent_commit_monotonic_ns
        ):
            raise Stage24bMoveRefusal("original native start dispatch chronology absent")
        checked = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id="B",
        )
        if (
            checked.unresolved or not checked.records
            or checked.records[-1]["status"] not in (
                "NATIVE_MOVE_SETTLED", "NATIVE_MOVE_NO_NET_DISPLACEMENT",
            )
            or checked.records[-1]["action_id"] != action_id
            or checked.digest != receipt.journal_sha256
            or owner.supervisor.open_actions
        ):
            raise Stage24bMoveRefusal("original WAL/native terminal not qualified")
        issued_probe = current
        measured_status = checked.records[-1]["status"]
        issued_result = {
            "classification": (
                "DEV_ORIGINAL_B_NATIVE_MOVE_SETTLED"
                if measured_status == "NATIVE_MOVE_SETTLED"
                else "DEV_ORIGINAL_B_NATIVE_MOVE_NO_NET_DISPLACEMENT"
            ),
            "original_wal_terminal_status": measured_status,
            "original_action_id": action_id,
            "original_intent_id": intent_id,
            "original_skill_execution_id": skill.execution_id,
            "b_native_session": current.session_id,
            "native_start_ack_seq": receipt.start_ack.seq,
            "native_stop_ack_seq": receipt.stop_ack.seq,
            "initial_stop_seq": receipt.initial_stop_probe.seq,
            "first_stable_seq": receipt.first_stable_probe.seq,
            "settled_seq": receipt.settled_probe.seq,
            "native_net_displacement_m": receipt.displacement_m,
            "original_canonical_wal_sha256": receipt.journal_sha256,
            "operator_selected_dev_move": False,
            "autonomous_l1_skill_selection": True,
            "skill_success_attested": False,
            "paper_action_causation": False,
            "gpu_inference_ran": True,
            "model_choice_file": str(decision_file),
            "model_binding_file": str(binding_file),
            "model_binding_sha256": binding_sha,
            "model_choice_sha256": decision_sha,
            "model_choice_id": candidate.choice_id,
            "model_choice_target_ref": candidate.option.target_ref,
            "model_choice_preset_ref": candidate.preset_ref,
            "model_choice_candidates_sha256": turn.candidate_set_sha256,
            "model_elapsed_ns": elapsed_ns,
            "intent_commit_monotonic_ns": intent_commit_monotonic_ns,
            "native_start_dispatch_monotonic_ns": receipt.native_start_dispatch_monotonic_ns,
            "intent_to_native_start_dispatch_ns": (
                receipt.native_start_dispatch_monotonic_ns - intent_commit_monotonic_ns
            ),
        }
    finally:
        # A HOLD still keeps the exact captured original stdout bytes frozen.
        session.finish_raw_source_audit()

    if issued_result is None or receipt is None or issued_probe is None:
        raise Stage24bMoveRefusal("original L1 physical result missing")
    independent = readback_owned_move_native_source(
        raw_path=raw, journal_path=owner.files.physical_wal_file,
        self_id="B", action_id=issued_result["original_action_id"],
        current_probe=issued_probe, receipt=receipt,
    )
    sidecar_path = evidence_dir / "B-original-move-native-readback.json"
    _write_bytes_new(
        sidecar_path, (json.dumps(independent, sort_keys=True, indent=2) + "\n").encode(),
    )
    if json.loads(sidecar_path.read_text()) != independent:
        raise Stage24bMoveRefusal("original native raw readback sidecar mismatched")
    if independent["original_wal_terminal_status"] != issued_result["original_wal_terminal_status"]:
        raise Stage24bMoveRefusal("raw native and original WAL outcomes differ")
    issued_result["independent_native_source"] = {
        "raw_file": str(raw), "raw_sha256": file_sha256(raw),
        "readback_file": str(sidecar_path),
        "readback_sha256": file_sha256(sidecar_path),
        "readback_classification": independent["classification"],
        "all_settle_probes": len(independent["all_stop_probes"]),
        "native_start_ack": independent["native_start_ack"],
        "native_stop_ack": independent["native_stop_ack"],
    }
    return issued_result
