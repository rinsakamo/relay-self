"""Stage27d: one new isolated real Paper World, dual real Gemma and A PLACE MOVE.

Separate command from Stage26. Reuses its canonical checkpoint/rejoin/model
source runner through a PRIVATE opt-in hook. Default Stage26 remains nonissuing.
Never starts Paper without existing operator EULA/real-world DEV approvals.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    PhysicalGrantStage,
)
from experiments.p0d_real_preset_checkpoint_dev import (
    run_real_two_self_preset_checkpoint,
)
from experiments.p0d_real_resident_presence_dev import _bounded_b_probe
from relay_self.p0d_stage27_owned_move_intent_dev import (
    begin_stage27_owned_move_intent,
)
from relay_self.p0d_stage27b_place_motion_dev import resolve_stage27_place_motion
from relay_self.p0d_stage27c_l0_place_proposal_dev import (
    propose_stage27c_original_place_move,
)
from relay_self.p0d_stage27f_l1_evaluation_dev import (
    prepare_stage27f_outcome_evaluation,
)
from relay_self.p0d_stage27g_real_l1_evaluation_dev import (
    finish_stage27g_original_evaluation,
    submit_stage27g_original_evaluation,
)
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hBoundedMoveLoop
from relay_self.p0d_stage27i_model_http_census_dev import (
    census_stage27i_model_http,
    freeze_stage27i_model_http,
    require_stage27i_two_initial_calls,
)
from relay_self.p0d_stage27i_precision_gait_dev import choose_stage27i_gait
from relay_self.persistent_cognition import Memory, PersistentCognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.stage27e_independent_evidence_dev import (
    capture_original_prepared_wal,
    correlate_owned_paper_position,
)


class Stage27RealWorldRefusal(RuntimeError):
    """A source-qualified one-shot real A physical action did not qualify."""


def _freeze_stage27h_l0_diagnostic(
    evidence: Path, loop: Stage27hBoundedMoveLoop, step, *,
    world_uuid: str, error: BaseException | None,
    filename: str = "c-stage27h-l0-diagnostic.json",
) -> None:
    """Preserve observed state, including incomplete reservations, without inference."""
    now_ns = time.monotonic_ns()
    budget = loop.invocation.budget
    wal = loop.owner.files.physical_wal_file
    try:
        wal_sha = hashlib.sha256(wal.read_bytes()).hexdigest()
        wal_error = None
    except OSError as exc:
        wal_sha = None
        wal_error = f"{type(exc).__name__}: {exc}"
    payload = {
        "classification": "C_STAGE27H_L0_DIAGNOSTIC_DEV",
        "world_uuid": world_uuid,
        "self_id": loop.owner.self_id,
        "native_session_id": loop.prepared.native_session,
        "last_step": asdict(step) if step is not None else None,
        "terminal_status": loop.terminal_status,
        "action_count": loop.action_count,
        "last_action_id": loop.last_action_id,
        "last_native_seq": loop.last_native_seq,
        "last_assessed_native_seq": loop._source_seq,
        "last_validated_wal_sha256": loop.last_wal_digest or None,
        "raw_wal_sha256": wal_sha,
        "raw_wal_read_error": wal_error,
        "elapsed_ms": (now_ns - loop.start_ns) / 1_000_000,
        "remaining_duration_ms": max(
            0, budget.max_duration_ms - (now_ns - loop.start_ns) / 1_000_000,
        ),
        "remaining_actions": budget.max_actions - loop.action_count,
        "observation_count": loop.observation_count,
        "remaining_observations": budget.max_observations - loop.observation_count,
        "settling_observations_reserved": loop._settlement_reserved,
        "reserved_source_seq": loop._reserved_source_seq,
        "cumulative_distance_m": loop.cumulative_distance_m,
        "remaining_distance_m": budget.max_distance_m - loop.cumulative_distance_m,
        "error_type": type(error).__name__ if error is not None else None,
        "error": str(error) if error is not None else None,
        "physical_state_certified": False,
    }
    raw = (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    path = evidence / filename
    with path.open("xb") as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())
    fd = os.open(evidence, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.is_symlink() or path.read_bytes() != raw:
        raise Stage27RealWorldRefusal("L0 diagnostic readback failed")


def _native_place_wire_readback(
    raw_file: Path, *, session_id: str, parent: str, new_probe_seq: int,
    ack_seqs: tuple[int, int, int], stop_probe_seqs: tuple[int, int, int],
    sneak_ack_seq: int | None = None,
) -> dict[str, object]:
    """Reread exact owned native stdout bytes: no fabricated child ACK evidence."""
    if raw_file.is_symlink() or not raw_file.is_file():
        raise Stage27RealWorldRefusal("original A native stdout file absent")
    data = raw_file.read_bytes()
    probes: list[tuple[int, str]] = []
    effects: list[tuple[int, str, str, str]] = []
    for line in data.splitlines():
        row = json.loads(line)
        if type(row) is not dict or row.get("session_id") != session_id:
            raise Stage27RealWorldRefusal("foreign native stdout source in A window")
        if row.get("type") == "observation" and row.get("kind") == "probe":
            probes.append((row.get("seq"), row.get("request_id")))
        elif row.get("type") == "effect_result":
            effects.append((
                row.get("seq"), row.get("action_id"),
                row.get("effect"), row.get("result"),
            ))
    expected = (
        (ack_seqs[0], parent + "-look", "look", "applied"),
        (ack_seqs[1], parent + "-start", "set_control", "applied"),
        (ack_seqs[2], parent + "-stop", "clear_controls", "applied"),
    )
    sneak_ack = (
        (sneak_ack_seq, parent + "-sneak", "set_control", "applied")
        if sneak_ack_seq is not None else None
    )
    if (
        len(ack_seqs) != 3
        or not new_probe_seq < ack_seqs[0] < ack_seqs[1] < ack_seqs[2]
        or (sneak_ack is not None
            and not ack_seqs[0] < sneak_ack_seq < ack_seqs[1])
        or not ack_seqs[2] < stop_probe_seqs[0] < stop_probe_seqs[1] < stop_probe_seqs[2]
        or any(effects.count(x) != 1 for x in expected)
        or (sneak_ack is not None and effects.count(sneak_ack) != 1)
        or sum(1 for x in effects if x[1].startswith(parent)) != (
            4 if sneak_ack is not None else 3
        )
        or not any(x[0] == new_probe_seq for x in probes)
        or any(sum(1 for x in probes if x[0] == seq) != 1
               for seq in stop_probe_seqs)
    ):
        raise Stage27RealWorldRefusal("original LOOK/ON/STOP native stdout readback mismatch")
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "length": len(data),
        "source": str(raw_file),
        "exact_native_action_child_effect_results": [
            *[list(x) for x in expected],
            *([list(sneak_ack)] if sneak_ack is not None else []),
        ],
        "precision_sneak_effect_attested": sneak_ack is not None,
        "original_native_look_start_stop_sequence_verified": True,
        "no_independent_paper_position_claim": True,
    }



def _stage27h_all_settling_stdout_readback(
    raw_file: Path, *, session_id: str,
    stop_seq: int, probes: tuple,
) -> dict[str, object]:
    """Read every STOP observation from original native stdout, exact-once.

    This verifies the *whole* requested settling window, not just the first,
    first-stable and terminal sample. No OCR, Paper inference, or generated
    synthetic probe can replace an exact stdout (seq, request_id) row.
    """
    if (
        raw_file.is_symlink() or not raw_file.is_file()
        or not session_id or type(stop_seq) is not int
        or type(probes) is not tuple or len(probes) < 3
    ):
        raise Stage27RealWorldRefusal("Stage27h native STOP sample source absent")
    data = raw_file.read_bytes()
    expected = [(p.seq, p.request_id) for p in probes]
    entries: list[tuple[int, str]] = []
    for line in data.splitlines():
        try:
            row = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise Stage27RealWorldRefusal(
                "Stage27h original native stdout corrupted"
            ) from exc
        if type(row) is not dict or row.get("session_id") != session_id:
            raise Stage27RealWorldRefusal("Stage27h native STOP source foreign")
        if row.get("type") == "observation" and row.get("kind") == "probe":
            entries.append((row.get("seq"), row.get("request_id")))
    actual_window = [
        row for row in entries
        if type(row[0]) is int and stop_seq < row[0] <= probes[-1].seq
    ]
    if (
        actual_window != expected
        or len({x[0] for x in expected}) != len(expected)
        or len({x[1] for x in expected}) != len(expected)
        or any(not isinstance(x[1], str) or not x[1] for x in expected)
    ):
        raise Stage27RealWorldRefusal(
            "Stage27h STOP probe count/source differs from original native stdout"
        )
    return {
        "original_native_stdout_sha256": hashlib.sha256(data).hexdigest(),
        "source": str(raw_file),
        "original_stop_seq": stop_seq,
        "stop_probe_count": len(expected),
        "original_stop_probes": [list(x) for x in expected],
        "all_stop_probes_exact_once": True,
    }


def _native_post_model_probe_readback(
    raw_file: Path, *, session_id: str, probe_id: str, probe_seq: int,
    prior_settled_seq: int,
) -> dict[str, object]:
    """Independently reread original A native stdout after the model recheck.

    This binds exact source bytes to the returned fresh probe. In-process
    sequencing proves it was *requested* after the model result; stdout alone
    is not a timestamped cross-process causality proof.
    """
    if (
        raw_file.is_symlink() or not raw_file.is_file()
        or not session_id or not probe_id
        or type(probe_seq) is not int or type(prior_settled_seq) is not int
        or probe_seq <= prior_settled_seq
    ):
        raise Stage27RealWorldRefusal("invalid original post-model native source")
    data = raw_file.read_bytes()
    rows: list[tuple[int, str]] = []
    for line in data.splitlines():
        try:
            event = json.loads(line)
        except (UnicodeError, ValueError) as exc:
            raise Stage27RealWorldRefusal("native stdout JSONL corrupted") from exc
        if (
            type(event) is not dict
            or event.get("session_id") != session_id
        ):
            raise Stage27RealWorldRefusal("foreign original native source")
        if event.get("type") == "observation" and event.get("kind") == "probe":
            rows.append((event.get("seq"), event.get("request_id")))
    if (
        rows.count((probe_seq, probe_id)) != 1
        or sum(1 for seq, _ in rows if seq == probe_seq) != 1
        or sum(1 for _, ident in rows if ident == probe_id) != 1
    ):
        raise Stage27RealWorldRefusal(
            "original native post-model probe stdout missing or duplicate"
        )
    return {
        "original_a_native_stdout_sha256_after_l1": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "original_a_native_stdout": str(raw_file),
        "post_model_probe_request_id": probe_id,
        "post_model_probe_seq": probe_seq,
        "source_readback": "EXACT_ONCE_NATIVE_STDOUT_DEV",
        "independent_model_vs_native_wallclock_causality": False,
    }


def _grant(stage: PhysicalGrantStage, binding):
    """Explicit DEV operator grant label; not external principal attestation."""
    return PhysicalDevGrant(
        stage=stage,
        authority_id="stage27-one-shot-" + stage.value.lower(),
        provenance=Provenance(
            "operator-standing-stage27-dev-" + stage.value.lower(),
            binding.native_source.reference,
        ),
        intent_id=binding.intent_id,
        action_id=binding.action_id,
        session_id=binding.scope.world_session_id,
        probe_seq=binding.native_seq,
        probe_request_id=binding.native_request_id,
        selected_target_ref=binding.target_ref,
        granted=True,
    )


def _peer_snapshot(owner, *, allow_changed: bool = False) -> dict[str, object]:
    """Content-address all original B Intent/Skill/Memory and canonical WAL.

    Counts alone do not detect replacement of a Memory's content/provenance.
    A new hash is computed from the LIVE retained cognition, not a stale
    checkpoint or the on-disk cognition file. Freeze only digests and IDs,
    not sensitive raw Memory contents, in the DEV motor report.
    """
    if type(allow_changed) is not bool or (
        not allow_changed and (
            owner.intent.current_intent is not None or owner.skills
        )
    ):
        raise Stage27RealWorldRefusal("peer B original Intent/Skill already mutated")
    retained = owner.retained
    if (
        not isinstance(retained, PersistentCognition)
        or retained.identity.self_id != owner.self_id
        or any(not isinstance(m, Memory) for m in retained.memories)
    ):
        raise Stage27RealWorldRefusal("peer B live retained Memory missing or foreign")
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=owner.self_id,
    )
    if not allow_changed:
        journal.require_clear()

    def digest(value: object) -> str:
        content = json.dumps(
            value, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    memories = [asdict(item) for item in retained.memories]
    memory_record_digests = [
        {"memory_id": memory["memory_id"], "sha256": digest(memory)}
        for memory in memories
    ]
    intent_events = [asdict(event) for event in owner.intent.events]
    skill_histories = [
        {
            "execution_id": skill.execution_id,
            "skill_id": skill.skill_id,
            "intent_id": skill.intent_id,
            "events": [asdict(event) for event in skill.events],
        }
        for _, skill in sorted(owner.skills.items())
    ]
    return {
        "intent_event_count": len(intent_events),
        "intent_events_sha256": digest(intent_events),
        "intent_current": (
            None if owner.intent.current_intent is None
            else asdict(owner.intent.current_intent)
        ),
        "skill_execution_count": len(skill_histories),
        "skill_histories_sha256": digest(skill_histories),
        "memory_count": len(memories),
        "memory_records_sha256": digest(memories),
        "memory_record_digests": memory_record_digests,
        "physical_wal_sha256": journal.digest,
        "physical_wal_action_rows": len(journal.records),
        "physical_wal_unresolved": bool(journal.unresolved),
        "open_action_count": len(owner.supervisor.open_actions),
    }


def _freeze_peer_b_snapshot(
    evidence: Path, *, label: str, snapshot: dict[str, object],
) -> dict[str, object]:
    """Write-once + fsync one B snapshot before comparing or issuing effects."""
    if label not in ("before", "after") or type(snapshot) is not dict:
        raise Stage27RealWorldRefusal("unknown original peer-B evidence snapshot")
    raw = (
        json.dumps(snapshot, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    path = evidence / f"stage27i-peer-b-{label}.json"
    if evidence.is_symlink() or not evidence.is_dir() or path.is_symlink():
        raise Stage27RealWorldRefusal("unsafe original B evidence destination")
    with path.open("xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    directory = os.open(evidence, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    digest = hashlib.sha256(raw).hexdigest()
    if path.read_bytes() != raw:
        raise Stage27RealWorldRefusal("peer B original Memory evidence readback failed")
    return {
        "path": str(path),
        "sha256": digest,
        "frozen_original": True,
        "memory_content_compared_by_sha256": True,
    }


def _freeze_owned_paper_source(evidence: Path, name: str, source: bytes) -> str:
    """Retain owned Paper Popen stdout bytes without modifying the source."""
    if evidence.is_symlink() or not evidence.is_dir() or type(source) is not bytes:
        raise Stage27RealWorldRefusal("owned Paper evidence directory/source invalid")
    path = evidence / name
    with path.open("xb") as output:
        output.write(source)
        output.flush()
        os.fsync(output.fileno())
    if path.read_bytes() != source:
        raise Stage27RealWorldRefusal("owned Paper evidence raw-byte mismatch")
    return hashlib.sha256(source).hexdigest()


async def stage27_real_a_motor_hook(
    *, paper, bridge, physical, lane, owners, world_epoch, prepared,
    tickets, witnesses, refreshed, evidence, world_uuid, native_audit,
    capture_independent_evidence: bool = False,
    capture_stage27f_evaluation: bool = False,
    capture_stage27g_real_evaluation: bool = False,
) -> dict[str, object]:
    """Original A Self only; one accepted real bounded L1 and one native MOVE."""
    if capture_stage27g_real_evaluation and not capture_stage27f_evaluation:
        raise Stage27RealWorldRefusal(
            "Stage27g requires original Stage27f evaluation source"
        )
    if capture_stage27f_evaluation and not capture_independent_evidence:
        raise Stage27RealWorldRefusal(
            "Stage27f requires Stage27e independent evidence before physical issue"
        )
    if (
        set(prepared) != {"A", "B"}
        or set(tickets) != {"A", "B"}
        or set(witnesses) != {"A", "B"}
        or set(refreshed) != {"A", "B"}
        or set(bridge.sessions) != {"A", "B"}
        or set(owners) != {"A", "B"}
        or paper.owned_session_id is None
        or physical.closed or physical.active_action_ids
        or lane is None
    ):
        raise Stage27RealWorldRefusal("two original Self/Paper/GPU owners missing")
    lane.require_world_idle()
    peer_before = _peer_snapshot(owners["B"])
    original_a = witnesses["A"]
    b = witnesses["B"]
    if (
        original_a.selected_number != "1"
        or original_a.l1_status != "READY"
    ):
        after_b = _peer_snapshot(owners["B"], allow_changed=True)
        if after_b != peer_before:
            raise Stage27RealWorldRefusal("nonready A altered original peer B")
        return {
            "classification": "REAL_STAGE27_A_MOVE_NOT_SELECTED_NO_PHYSICAL_DEV",
            "physical_effect_observed": False,
            "self_a_selected_number": original_a.selected_number,
            "self_a_status": original_a.l1_status,
            "self_b_selected_number": b.selected_number,
            "self_b_status": b.l1_status,
            "original_peer_b_before": peer_before,
            "original_peer_b_after": after_b,
            "stage27_a_intent_started": False,
            "stage27_native_action_count": 0,
        }
    actor = owners["A"]
    session = bridge.sessions["A"]
    original_a_native = session.started.session_id
    if (
        original_a_native != prepared["A"].native_session
        or session.process_returncode is not None
        or physical.current_native_sessions["A"] != original_a_native
        or physical.resident_states["A"] != "ONLINE"
    ):
        raise Stage27RealWorldRefusal("original A resident source not live")
    # Only model number-1 source, not the operator, may select the MOVE.
    t0 = time.monotonic_ns()
    handoff = begin_stage27_owned_move_intent(
        prepared["A"], ticket=tickets["A"], witness=original_a,
        refreshed=refreshed["A"], lane=lane, physical=physical,
        actor_self_id="A", at_ns=t0,
        provenance=Provenance("stage27-real-original-A", world_uuid),
    )
    # Need two distinct *native* probes for physical source-window admission;
    # both after model inference. Stage26's post-model probe is the first.
    current = await _bounded_b_probe(session)
    if (
        current.session_id != original_a_native
        or current.seq <= refreshed["A"].seq
        or current.seq > refreshed["A"].seq + 32
        or current.request_id == refreshed["A"].request_id
    ):
        raise Stage27RealWorldRefusal("fresh A physical-proposal probe unavailable")
    plan = resolve_stage27_place_motion(
        prepared["A"], handoff, current, owner=actor,
        physical=physical, world_epoch=world_epoch,
    )
    at = time.monotonic_ns()
    proposal = propose_stage27c_original_place_move(
        prepared["A"], handoff, plan, current,
        owner=actor, physical=physical, world_epoch=world_epoch,
        capability=PhysicalCapability(
            "MOVE", 1, "locomotion", "DESTINATION", True,
        ),
        at_ns=at, provenance=Provenance("stage27-real-l0", current.provenance.reference),
    )
    binding = proposal.proposal.binding
    journal = PhysicalActionJournal.restore(
        actor.files.physical_wal_file, self_id="A",
    )
    journal.require_clear()
    # The optional Stage27e tap takes the original Paper source BEFORE
    # physical issuance. PREPARED is independently copied AFTER reservation,
    # before native LOOK, through the issuer-owned pre-native callback.
    paper_pre = None
    prepared_original: dict[str, object] = {}
    if capture_independent_evidence:
        paper_pre = paper.read_owned_log(paper.owned_session_id)
        _freeze_owned_paper_source(evidence, "stage27e-paper-pre-native.log", paper_pre)

    def capture_reserved(journal_to_capture, reserved_action_id):
        prepared_original.update(capture_original_prepared_wal(
            journal_to_capture, evidence, action_id=reserved_action_id,
        ))

    # Original physical issuer owns PREPARED, three native effect IDs,
    # STOP and settlement. ONE invocation only, no automatic retry.
    receipt = await physical.issue_place_move(
        session, proposal=proposal.proposal,
        l0=proposal, prepared=prepared["A"],
        handoff=handoff, motion=plan,
        previous_probe=refreshed["A"],
        current_probe=current,
        owner=actor, physical=physical,
        propose_grant=_grant(PhysicalGrantStage.PROPOSE, binding),
        issue_grant=_grant(PhysicalGrantStage.ISSUE, binding),
        journal=journal,
        at_ns=at + 3,
        provenance=Provenance("stage27-real-physical", current.provenance.reference),
        grant_real_world=True,
        acknowledge_dev_unverified_principal=True,
        pulse_seconds=0.15,
        evidence_timeout_s=15.0,
        pre_native_evidence=capture_reserved if capture_independent_evidence else None,
    )
    if (
        receipt.action_id != binding.action_id
        or receipt.original_invocation_ref != handoff.invocation_ref
        or receipt.original_preset_ref != handoff.preset_ref
        or receipt.target_contract_ref != plan.target_contract_ref
        or receipt.l0_step_status != "YIELD_EVALUATION"
        or not receipt.native_effect_issued
        or receipt.skill_success_attested
        or receipt.paper_causal_attribution
    ):
        raise Stage27RealWorldRefusal("original L0 Action/WAL outcome source mismatch")
    # Validate original disk after result, never just in-memory Action.
    reread = PhysicalActionJournal.restore(
        actor.files.physical_wal_file, self_id="A",
    )
    reread.require_clear()
    row = reread.records[-1]
    if (
        len(reread.records) != 1
        or row["capability"] != "MOVE_PLACE"
        or row["status"] != receipt.journal_status
        or row["invocation_ref"] != handoff.invocation_ref
        or row["preset_ref"] != handoff.preset_ref
        or row["target_contract_ref"] != plan.target_contract_ref
        or row["action_id"] != binding.action_id
        or row["after_seq"] != receipt.settled_probe.seq
    ):
        raise Stage27RealWorldRefusal("original terminal WAL readback mismatch")
    native_source = _native_place_wire_readback(
        native_audit, session_id=original_a_native,
        parent=binding.action_id, new_probe_seq=current.seq,
        ack_seqs=(
            receipt.look_ack.seq, receipt.start_ack.seq, receipt.stop_ack.seq,
        ),
        stop_probe_seqs=(
            receipt.initial_stop_probe.seq,
            receipt.first_stable_probe.seq, receipt.settled_probe.seq,
        ),
    )
    paper_correlated = None
    if capture_independent_evidence:
        if paper_pre is None or not prepared_original:
            raise Stage27RealWorldRefusal("original PREPARED evidence absent after issue")
        paper_post = paper.read_owned_log(paper.owned_session_id)
        _freeze_owned_paper_source(evidence, "stage27e-paper-post-native.log", paper_post)
        a0, a1 = current.snapshot.position, receipt.settled_probe.snapshot.position
        paper_correlated = correlate_owned_paper_position(
            before=paper_pre, after=paper_post,
            paper_session_id=paper.owned_session_id, world_uuid=world_uuid,
            native_start_xyz=(a0.x, a0.y, a0.z),
            native_settled_xyz=(a1.x, a1.y, a1.z),
        )
    stage27f_frame = None
    if capture_stage27f_evaluation:
        stage27f_frame = prepare_stage27f_outcome_evaluation(
            prepared["A"], handoff, proposal, receipt,
            owner=actor, physical=physical, world_epoch=world_epoch,
        )
    stage27g_result = None
    if capture_stage27g_real_evaluation:
        if stage27f_frame is None:
            raise Stage27RealWorldRefusal("Stage27g original evaluation frame absent")
        evaluation_ticket = submit_stage27g_original_evaluation(
            stage27f_frame, prepared["A"], owner=actor,
            physical=physical, lane=lane,
        )
        evaluation_choice, evaluation_witness = await finish_stage27g_original_evaluation(
            stage27f_frame, prepared["A"], owner=actor, physical=physical,
            lane=lane, ticket=evaluation_ticket,
            fresh_probe=lambda: _bounded_b_probe(session),
        )
        post_model_raw = _native_post_model_probe_readback(
            native_audit, session_id=original_a_native,
            probe_id=evaluation_witness.fresh_native_probe_request_id,
            probe_seq=evaluation_witness.fresh_native_probe_seq,
            prior_settled_seq=receipt.settled_probe.seq,
        )
        stage27g_result = {
            "choice": asdict(evaluation_choice),
            "witness": asdict(evaluation_witness),
            "native_post_model_source": post_model_raw,
            "model_evaluation_decision_only": True,
            "next_physical_action_authorized": False,
            "original_goal_or_skill_completed": False,
        }
    peer_after = _peer_snapshot(owners["B"], allow_changed=True)
    if peer_before != peer_after:
        raise Stage27RealWorldRefusal("original B cognitive/WAL state changed")
    lane.require_world_idle()
    status_label = {
        "NATIVE_PLACE_MOVE_SETTLED": "REAL_STAGE27_A_PLACE_MOVE_NATIVE_OBSERVED_DEV",
        "NATIVE_PLACE_MOVE_NO_PROGRESS":
            "REAL_STAGE27_A_PLACE_NO_PROGRESS_NATIVE_OBSERVED_DEV",
        "NATIVE_PLACE_MOVE_OVERSHOOT":
            "REAL_STAGE27_A_PLACE_MOVE_OVERSHOOT_DEV",
    }.get(receipt.journal_status)
    if status_label is None:
        raise Stage27RealWorldRefusal("unknown original PLACE MOVE outcome")
    return {
        "classification": status_label,
        "physical_effect_observed": True,
        "original_world_uuid": world_uuid,
        "paper_ownership_session": paper.owned_session_id,
        "original_world_epoch": world_epoch,
        "self_a_selected_number": original_a.selected_number,
        "self_a_status": original_a.l1_status,
        "self_b_selected_number": b.selected_number,
        "self_b_status": b.l1_status,
        "self_a_native_session": original_a_native,
        "self_a_preissue_native_probe": current.request_id,
        "self_a_preissue_native_seq": current.seq,
        "original_peer_b_before": peer_before,
        "original_peer_b_after": peer_after,
        "original_intent": handoff.intent_id,
        "original_skill": handoff.skill_execution_id,
        "original_action": binding.action_id,
        "original_invocation_ref": handoff.invocation_ref,
        "original_preset_ref": handoff.preset_ref,
        "original_target_contract_ref": plan.target_contract_ref,
        "native_expected_yaw": plan.desired_mineflayer_yaw_rad,
        "native_look_ack_seq": receipt.look_ack.seq,
        "native_forward_ack_seq": receipt.start_ack.seq,
        "native_stop_ack_seq": receipt.stop_ack.seq,
        "native_settled_probe_seq": receipt.settled_probe.seq,
        "native_settled_probe": asdict(receipt.settled_probe),
        "native_displacement_m": receipt.displacement_m,
        "original_wal_status": receipt.journal_status,
        "original_wal_sha256": reread.digest,
        "original_wal_rows": len(reread.records),
        "l0_terminal_status": receipt.l0_step_status,
        "stage27_native_action_count": 1,
        "native_source": native_source,
        "independent_paper_displacement_attested": bool(
            paper_correlated is not None
            and paper_correlated["paper_position_independently_correlated"]
        ),
        **({
            "stage27e_preissue_original_wal": prepared_original,
            "stage27e_independent_paper_position": paper_correlated,
        } if capture_independent_evidence else {}),
        **({
            "stage27f_read_only_l1_evaluation_frame": asdict(stage27f_frame),
            "stage27f_real_l1_evaluation_model_called":
                capture_stage27g_real_evaluation,
        } if stage27f_frame is not None else {}),
        **({"stage27g_real_l1_post_action_evaluation": stage27g_result}
           if stage27g_result is not None else {}),
        "goal_success_attested": False,
        "skill_success_attested": False,
        "qual_and_science_attested": False,
    }


async def stage27e_real_a_motor_hook(**kwargs) -> dict[str, object]:
    """Explicit Stage27e hook; never changes Stage26/27d default issuance."""
    return await stage27_real_a_motor_hook(
        **kwargs, capture_independent_evidence=True,
    )


async def stage27f_real_a_motor_hook(**kwargs) -> dict[str, object]:
    """Explicit opt-in: original A physical Outcome -> read-only L1 frame."""
    return await stage27_real_a_motor_hook(
        **kwargs, capture_independent_evidence=True,
        capture_stage27f_evaluation=True,
    )


async def stage27g_real_a_motor_hook(**kwargs) -> dict[str, object]:
    """Only explicit real post-Action L1 call on original GPU lane."""
    return await stage27_real_a_motor_hook(
        **kwargs, capture_independent_evidence=True,
        capture_stage27f_evaluation=True,
        capture_stage27g_real_evaluation=True,
    )


def _stage27h_capture_prepared(
    journal: PhysicalActionJournal, evidence: Path, *,
    action_id: str, action_index: int,
) -> dict[str, object]:
    """Freeze a complete canonical WAL with the LAST row still PREPARED.

    Stage27e's original one-row evidence collector remains intentionally
    unchanged. Stage27h snapshots distinct WAL versions for each child.
    """
    if (
        not isinstance(journal, PhysicalActionJournal)
        or not journal.unresolved or evidence.is_symlink()
        or type(action_index) is not int or not 0 <= action_index < 4
        or len(journal.records) != action_index + 1
        or any(row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
               for row in journal.records[:-1])
        or journal.records[-1]["status"] != "PREPARED_UNRESOLVED"
        or journal.records[-1]["capability"] != "MOVE_PLACE"
        or journal.records[-1]["action_id"] != action_id
        or journal.path.is_symlink()
    ):
        raise Stage27RealWorldRefusal("Stage27h original per-Action PREPARED invalid")
    raw = journal.path.read_bytes()
    if PhysicalActionJournal.restore(
        journal.path, self_id="A",
    ).digest != journal.digest:
        raise Stage27RealWorldRefusal("Stage27h original PREPARED WAL changed")
    dest = evidence / f"stage27h-A-PREPARED-{action_index + 1}.json"
    with dest.open("xb") as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    folder_fd = os.open(evidence, os.O_RDONLY)
    try:
        os.fsync(folder_fd)
    finally:
        os.close(folder_fd)
    if dest.read_bytes() != raw:
        raise Stage27RealWorldRefusal("Stage27h immutable PREPARED source mismatch")
    frozen = PhysicalActionJournal.restore(dest, self_id="A")
    if frozen.digest != journal.digest or not frozen.unresolved:
        raise Stage27RealWorldRefusal("Stage27h PREPARED independent readback failed")
    return {
        "original_action_id": action_id,
        "action_number": action_index + 1,
        "snapshot": str(dest),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "journal_digest": journal.digest,
        "before_any_native_effect": True,
    }


async def stage27h_real_a_motor_hook(
    *, paper, bridge, physical, lane, owners, world_epoch, prepared,
    tickets, witnesses, refreshed, evidence, world_uuid, native_audit,
    precision_stage27i: bool = False,
    c_lane_stage27h_post_review: bool = False,
) -> dict[str, object]:
    """Strict Stage27h opt-in: CPU L0 repeats ORIGINAL bounded MOVE Actions.

    Uses the existing Stage27c child interpreter and original resident
    physical issuer for EACH short Action. There is only one initial real L1
    choice and no model evaluation inside the L0 MOVE loop.
    """
    if (
        type(c_lane_stage27h_post_review) is not bool
        or (c_lane_stage27h_post_review and precision_stage27i)
    ):
        raise Stage27RealWorldRefusal(
            "C Stage27h post-L0 L1 is incompatible with Stage27i two-POST census"
        )
    if (
        set(prepared) != {"A", "B"} or set(tickets) != {"A", "B"}
        or set(witnesses) != {"A", "B"} or set(refreshed) != {"A", "B"}
        or set(owners) != {"A", "B"} or set(bridge.sessions) != {"A", "B"}
        or paper.owned_session_id is None
        or lane is None or physical.closed or physical.active_action_ids
    ):
        raise Stage27RealWorldRefusal("Stage27h original 2-Self ownership absent")
    lane.require_world_idle()
    model_before = (
        census_stage27i_model_http(evidence, lane=lane, tickets=tickets)
        if precision_stage27i else None
    )
    model_before_evidence = (
        freeze_stage27i_model_http(
            evidence, label="before", snapshot=model_before,
        ) if model_before is not None else None
    )
    if model_before is not None:
        require_stage27i_two_initial_calls(model_before)
    peer_before = _peer_snapshot(owners["B"])
    peer_before_evidence = (
        _freeze_peer_b_snapshot(
            evidence, label="before", snapshot=peer_before,
        ) if precision_stage27i else None
    )
    if witnesses["A"].selected_number != "1" or witnesses["A"].l1_status != "READY":
        if precision_stage27i:
            # Zero-effect path still saves the complete B Memory comparison.
            lane.require_world_idle()
            model_after = census_stage27i_model_http(
                evidence, lane=lane, tickets=tickets,
            )
            model_after_evidence = freeze_stage27i_model_http(
                evidence, label="after", snapshot=model_after,
            )
            require_stage27i_two_initial_calls(model_after)
            if model_after != model_before:
                raise Stage27RealWorldRefusal(
                    "Stage27i additional model POST on no-MOVE path"
                )
            peer_after = _peer_snapshot(owners["B"], allow_changed=True)
            peer_after_evidence = _freeze_peer_b_snapshot(
                evidence, label="after", snapshot=peer_after,
            )
            if peer_before != peer_after:
                raise Stage27RealWorldRefusal(
                    "Stage27i nonselected A changed original peer B"
                )
            return {
                "classification": "REAL_STAGE27_A_MOVE_NOT_SELECTED_NO_PHYSICAL_DEV",
                "stage27i_precision_enabled": True,
                "physical_effect_observed": False,
                "stage27_native_action_count": 0,
                "self_a_selected_number": witnesses["A"].selected_number,
                "self_a_status": witnesses["A"].l1_status,
                "self_b_selected_number": witnesses["B"].selected_number,
                "self_b_status": witnesses["B"].l1_status,
                "stage27_a_intent_started": False,
                "original_peer_b_before": peer_before,
                "original_peer_b_after": peer_after,
                "stage27h_peer_b_before": peer_before,
                "stage27h_peer_b_after": peer_after,
                "stage27i_peer_b_before_evidence": peer_before_evidence,
                "stage27i_peer_b_after_evidence": peer_after_evidence,
                "stage27i_model_http_before": model_before,
                "stage27i_model_http_after": model_after,
                "stage27i_model_http_before_evidence": model_before_evidence,
                "stage27i_model_http_after_evidence": model_after_evidence,
                "stage27h_additional_model_requests": (
                    model_after["request_count"] - model_before["request_count"]
                ),
                "stage27h_goal_success": False,
                "stage27h_skill_success": False,
            }
        return await stage27_real_a_motor_hook(
            paper=paper, bridge=bridge, physical=physical, lane=lane,
            owners=owners, world_epoch=world_epoch, prepared=prepared,
            tickets=tickets, witnesses=witnesses, refreshed=refreshed,
            evidence=evidence, world_uuid=world_uuid, native_audit=native_audit,
        )
    owner = owners["A"]
    session = bridge.sessions["A"]
    native_id = session.started.session_id
    if (
        native_id != prepared["A"].native_session
        or owner.native_session_id != native_id
        or session.process_returncode is not None
        or physical.current_native_sessions.get("A") != native_id
        or physical.resident_states.get("A") != "ONLINE"
    ):
        raise Stage27RealWorldRefusal("Stage27h original A live session unavailable")
    original_model_count = 2  # A and B initial choices; no later L1 in the loop
    handoff = begin_stage27_owned_move_intent(
        prepared["A"], ticket=tickets["A"], witness=witnesses["A"],
        refreshed=refreshed["A"], lane=lane, physical=physical,
        actor_self_id="A", at_ns=time.monotonic_ns(),
        provenance=Provenance("stage27h-original-A", world_uuid),
    )
    loop = Stage27hBoundedMoveLoop(
        prepared["A"], handoff, owner=owner, physical=physical,
        world_epoch=world_epoch, start_ns=time.monotonic_ns(),
    )
    last_step = None
    try:
        previous = refreshed["A"]
        current = await _bounded_b_probe(session)
        if current.seq <= previous.seq or current.session_id != native_id:
            raise Stage27RealWorldRefusal("Stage27h first post-L1 native source stale")
        result = loop.pre_action(current, now_ns=time.monotonic_ns())
        last_step = result
        first_action_probe = current
        last_settled_probe = None
        action_receipts: list[dict[str, object]] = []
        while result.status == "L0_CONTINUE_MOVE":
            if len(action_receipts) != loop.action_count:
                raise Stage27RealWorldRefusal("Stage27h multi-Action record count diverged")
            idx = loop.action_count
            # L0 can pick a gait only within the immutable operator-accepted
            # precision Preset; L1 never runs between its physical child Actions.
            gait_choice = (
                choose_stage27i_gait(loop, result, current)
                if precision_stage27i else None
            )
            # Charge a complete 60-sample STOP settlement quota against the
            # immutable parent Invocation BEFORE even proposing the next Action.
            # The issuer cannot request more native probes than this reservation.
            stop_probe_quota = loop.reserve_settling_observations(
                source_probe=current,
            )
            # Native target geometry is recalculated from the SAME frozen Target.
            # No new L1 choice, no new invocation, no parameter/preset tuning.
            plan = resolve_stage27_place_motion(
                prepared["A"], handoff, current, owner=owner,
                physical=physical, world_epoch=world_epoch,
            )
            proposal = propose_stage27c_original_place_move(
                prepared["A"], handoff, plan, current, owner=owner,
                physical=physical, world_epoch=world_epoch,
                capability=PhysicalCapability(
                    "MOVE", 1, "locomotion", "DESTINATION", True,
                ), at_ns=time.monotonic_ns(),
                provenance=Provenance("stage27h-original-l0", current.provenance.reference),
            )
            binding = proposal.proposal.binding
            journal = PhysicalActionJournal.restore(
                owner.files.physical_wal_file, self_id="A",
            )
            journal.require_clear()
            if len(journal.records) != idx:
                raise Stage27RealWorldRefusal("Stage27h pre-Action journal row count wrong")
            paper_before = paper.read_owned_log(paper.owned_session_id)
            _freeze_owned_paper_source(
                evidence, f"stage27h-Paper-pre-{idx + 1}.log", paper_before,
            )
            original_prepared: dict[str, object] = {}

            def capture_reserved(source, action):
                original_prepared.update(_stage27h_capture_prepared(
                    source, evidence, action_id=action, action_index=idx,
                ))

            t0 = time.monotonic_ns()
            receipt = await physical.issue_place_move(
                session, proposal=proposal.proposal,
                l0=proposal, prepared=prepared["A"],
                handoff=handoff, motion=plan,
                previous_probe=previous, current_probe=current,
                owner=owner, physical=physical,
                propose_grant=_grant(PhysicalGrantStage.PROPOSE, binding),
                issue_grant=_grant(PhysicalGrantStage.ISSUE, binding),
                journal=journal, at_ns=t0 + 3,
                provenance=Provenance(
                    "stage27h-original-physical", current.provenance.reference,
                ),
                grant_real_world=True,
                acknowledge_dev_unverified_principal=True,
                pulse_seconds=(
                    gait_choice.pulse_seconds if gait_choice is not None else 0.15
                ),
                precision_gait=(
                    gait_choice.gait_mode if gait_choice is not None else None
                ),
                evidence_timeout_s=15.0,
                pre_native_evidence=capture_reserved,
                allow_prior_terminal_place_actions=idx > 0,
                settlement_probe_limit=stop_probe_quota,
            )
            if not original_prepared or original_prepared["original_action_id"] != binding.action_id:
                raise Stage27RealWorldRefusal("Stage27h original PREPARED missing")
            # Original WAL closes before a second Action can ever be proposed.
            post = loop.observe_terminal_action(
                receipt, source_probe=current, now_ns=time.monotonic_ns(),
            )
            last_step = post
            readback = _native_place_wire_readback(
                native_audit, session_id=native_id, parent=binding.action_id,
                new_probe_seq=current.seq,
                ack_seqs=(receipt.look_ack.seq, receipt.start_ack.seq,
                          receipt.stop_ack.seq),
                stop_probe_seqs=(receipt.initial_stop_probe.seq,
                                 receipt.first_stable_probe.seq,
                                 receipt.settled_probe.seq),
                sneak_ack_seq=(
                    receipt.gait_control_ack.seq
                    if receipt.gait_control_ack is not None else None
                ),
            )
            all_settling_readback = _stage27h_all_settling_stdout_readback(
                native_audit, session_id=native_id,
                stop_seq=receipt.stop_ack.seq,
                probes=receipt.all_stop_probes,
            )
            paper_after = paper.read_owned_log(paper.owned_session_id)
            _freeze_owned_paper_source(
                evidence, f"stage27h-Paper-post-{idx + 1}.log", paper_after,
            )
            p0, p1 = current.snapshot.position, receipt.settled_probe.snapshot.position
            correlated = correlate_owned_paper_position(
                before=paper_before, after=paper_after,
                paper_session_id=paper.owned_session_id, world_uuid=world_uuid,
                native_start_xyz=(p0.x, p0.y, p0.z),
                native_settled_xyz=(p1.x, p1.y, p1.z),
            )
            action_receipts.append({
                "action": receipt.action_id,
                "invocation_ref": receipt.original_invocation_ref,
                "preset_ref": receipt.original_preset_ref,
                "target_contract_ref": receipt.target_contract_ref,
                "native_source": readback,
                "all_stop_probes_native_stdout": all_settling_readback,
                "stop_probe_reserved": stop_probe_quota,
                "stop_probe_actual": len(receipt.all_stop_probes),
                "observation_count_after_settlement": loop.observation_count,
                "prepared_source": original_prepared,
                "terminal_wal_status": receipt.journal_status,
                "terminal_wal_digest": receipt.journal_sha256,
                "original_native_probe_seq": current.seq,
                "settled_native_probe_seq": receipt.settled_probe.seq,
                "displacement_m": receipt.displacement_m,
                "gait_mode": receipt.gait_mode,
                "gait_ack_seq": (
                    receipt.gait_control_ack.seq
                    if receipt.gait_control_ack is not None else None
                ),
                "prebound_gait_choice": (
                    asdict(gait_choice) if gait_choice is not None else None
                ),
                "paper_correlational_position": correlated,
                "l0_feedback": asdict(post),
                "goal_success": False,
                "skill_success": False,
            })
            last_settled_probe = receipt.settled_probe
            result = post
            if result.status != "L0_CONTINUE_MOVE":
                break
            previous = receipt.settled_probe
            current = await _bounded_b_probe(session)
            if current.session_id != native_id or current.seq <= previous.seq:
                raise Stage27RealWorldRefusal(
                    "Stage27h fresh next-motor WorldBody observation unavailable"
                )
            result = loop.pre_action(current, now_ns=time.monotonic_ns())
            last_step = result
        if c_lane_stage27h_post_review:
            _freeze_stage27h_l0_diagnostic(
                evidence, loop, last_step, world_uuid=world_uuid, error=None,
                filename="c-stage27h-l0-terminal.json",
            )
        if result.status == "L0_CONTINUE_MOVE":
            raise Stage27RealWorldRefusal("Stage27h L0 loop ended without evaluation")
        peer_after = _peer_snapshot(owners["B"], allow_changed=True)
        peer_after_evidence = (
            _freeze_peer_b_snapshot(
                evidence, label="after", snapshot=peer_after,
            ) if precision_stage27i else None
        )
        if peer_after != peer_before:
            raise Stage27RealWorldRefusal("Stage27h mutated original peer B")
        lane.require_world_idle()
        model_after = (
            census_stage27i_model_http(evidence, lane=lane, tickets=tickets)
            if precision_stage27i else None
        )
        model_after_evidence = (
            freeze_stage27i_model_http(
                evidence, label="after", snapshot=model_after,
            ) if model_after is not None else None
        )
        if model_after is not None:
            require_stage27i_two_initial_calls(model_after)
            if model_after != model_before:
                raise Stage27RealWorldRefusal(
                    "Stage27i extra model POST within original L0 loop"
                )
        if c_lane_stage27h_post_review and (
            loop.action_count < 1 or last_settled_probe is None
        ):
            raise Stage27RealWorldRefusal(
                "C Stage27h has no settled Action for bounded review"
            )
        stage = "27I" if precision_stage27i else "27H"
        status = {
            "L0_TARGET_REACHED_YIELD_EVALUATION":
                f"REAL_STAGE{stage}_L0_TARGET_REACHED_NATIVE_OBSERVED_DEV",
            "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION":
                f"REAL_STAGE{stage}_L0_BUDGET_EXHAUSTED_DEV",
            "L0_NO_PROGRESS_YIELD_EVALUATION":
                f"REAL_STAGE{stage}_L0_NO_PROGRESS_DEV",
        }.get(result.status, f"REAL_STAGE{stage}_L0_UNREACHED_DEV")
        original_skill = owner.skills.get(handoff.skill_execution_id)
        if (
            original_skill is None
            or owner.intent.current_intent is None
            or owner.intent.current_intent.intent_id != handoff.intent_id
            or original_skill.intent_id != handoff.intent_id
        ):
            raise Stage27RealWorldRefusal(
                "Stage27h original Intent/Skill not retained for final hook result"
            )
        original_result = {
            "classification": status,
            "stage27i_precision_enabled": precision_stage27i,
            # Explicit Stage25 parent-runner contract. A terminal Action has
            # already been observed; this flag does NOT attest Skill/Goal success.
            "physical_effect_observed": loop.action_count > 0,
            "stage27_native_action_count": loop.action_count,
            "self_a_selected_number": witnesses["A"].selected_number,
            "self_a_status": witnesses["A"].l1_status,
            "self_b_selected_number": witnesses["B"].selected_number,
            "self_b_status": witnesses["B"].l1_status,
            "original_peer_b_before": peer_before,
            "original_peer_b_after": peer_after,
            "stage27h_self_a_intent_current": owner.intent.current_intent.intent_id,
            "stage27h_self_a_skill_state": original_skill.state.value,
            "stage27h_elapsed_ms": (time.monotonic_ns() - loop.start_ns) / 1_000_000,
            "original_world_uuid": world_uuid,
            "original_world_epoch": world_epoch,
            "original_paper_session": paper.owned_session_id,
            "stage27h_original_intent": handoff.intent_id,
            "stage27h_original_skill": handoff.skill_execution_id,
            "stage27h_invocation_ref": handoff.invocation_ref,
            "stage27h_preset_ref": handoff.preset_ref,
            "stage27h_bound_model_initial_requests_expected": original_model_count,
            "stage27h_additional_model_requests": (
                0 if model_after is None or model_before is None
                else model_after["request_count"] - model_before["request_count"]
            ),
            "stage27i_model_http_before": model_before,
            "stage27i_model_http_after": model_after,
            "stage27i_model_http_before_evidence": model_before_evidence,
            "stage27i_model_http_after_evidence": model_after_evidence,
            "stage27h_l0_action_count": loop.action_count,
            "stage27h_l0_feedback": asdict(result),
            "stage27h_original_action_witnesses": action_receipts,
            "stage27h_peer_b_before": peer_before,
            "stage27h_peer_b_after": peer_after,
            "stage27i_peer_b_before_evidence": peer_before_evidence,
            "stage27i_peer_b_after_evidence": peer_after_evidence,
            "stage27h_goal_success": False,
            "stage27h_skill_success": False,
            "stage27h_operator_dev_template_not_autonomous": True,
            "qual_and_science_attested": False,
        }
        if not c_lane_stage27h_post_review:
            return original_result
        # OPT-IN: original bounded L0 ended; unlike Stage27i, a separate
        # read-only L1 review is permitted ONLY AFTER the original full WAL is
        # terminal. A durable pre-review source is frozen before model POST.
        from experiments.c_lane_stage27h_real_post_l0_review_dev import (
            capture_stage27h_real_post_l0_readonly_review,
        )

        assert last_settled_probe is not None
        review = await capture_stage27h_real_post_l0_readonly_review(
            loop=loop, step=result,
            first_action_probe=first_action_probe,
            last_settled_probe=last_settled_probe,
            physical=physical, lane=lane, bridge=bridge,
            evidence=evidence, world_uuid=world_uuid,
            original_native_stdout=native_audit,
            fresh_probe=lambda: _bounded_b_probe(session),
        )
        if (
            review["original_wal_sha256"] != loop.last_wal_digest
            or review["original_skill_state"] != "started"
            or review["original_action_ids"] != [
                r["action"] for r in action_receipts
            ]
            or owners["A"].skills[handoff.skill_execution_id].state.value != "started"
            or review["c1_memory_written"] is not False
            or review["action_issue_authorized"] is not False
        ):
            raise Stage27RealWorldRefusal(
                "post-L0 bounded review cannot change original Skill/WAL/authority"
            )
        peer_final = _peer_snapshot(owners["B"], allow_changed=True)
        if peer_final != peer_before:
            raise Stage27RealWorldRefusal(
                "post-L0 model review changed original peer B"
            )
        return {
            **original_result,
            "stage27h_additional_model_requests": 1,
            "c_lane_stage27h_post_l0_review": review,
        }

    finally:
        if c_lane_stage27h_post_review:
            _freeze_stage27h_l0_diagnostic(
                evidence, loop, last_step, world_uuid=world_uuid,
                error=sys.exc_info()[1],
            )


async def stage27i_real_a_motor_hook(**kwargs) -> dict[str, object]:
    """Stage27i opt-in only: source-bound precise gait within Stage27h parent."""
    return await stage27h_real_a_motor_hook(
        **kwargs, precision_stage27i=True,
    )


async def run_stage27_real_world(
    *, paper_jar: Path, paper_sha256: str,
    plugin_jar: Path, plugin_sha256: str,
    scratch_parent: Path, accepted_eula: bool,
    real_world_dev_grant: bool,
    gemma_l1_endpoint: str, gemma_l1_model: str,
    java: str = "java", node: str = "node",
    timeout_s: float = 120.0, heap_mb: int = 1536,
    stage27e_independent_evidence: bool = False,
    stage27f_cpu_evaluation: bool = False,
    stage27g_real_l1_evaluation: bool = False,
    stage27h_l0_move_loop: bool = False,
    stage27i_precision_gait: bool = False,
    c_lane_stage27h_post_review: bool = False,
) -> Path:
    """Run the Stage26 original World only via the Stage27 opt-in motor hook."""
    if (
        accepted_eula is not True or real_world_dev_grant is not True
        or not gemma_l1_endpoint or not gemma_l1_model
    ):
        raise Stage27RealWorldRefusal("original real Gemma/EULA/World DEV prerequisites missing")
    if (
        type(stage27h_l0_move_loop) is not bool
        or type(stage27i_precision_gait) is not bool
        or type(c_lane_stage27h_post_review) is not bool
        or (c_lane_stage27h_post_review and not stage27h_l0_move_loop)
        or (stage27h_l0_move_loop and stage27i_precision_gait)
        or (stage27i_precision_gait and (
            stage27e_independent_evidence or stage27f_cpu_evaluation
            or stage27g_real_l1_evaluation
        ))
        or (stage27h_l0_move_loop and (
            stage27e_independent_evidence or stage27f_cpu_evaluation
            or stage27g_real_l1_evaluation
        ))
    ):
        raise Stage27RealWorldRefusal(
            "Stage27h multi-Action mode must be the sole explicit DEV stage"
        )
    # Separate opt-in, always using the SAME original Stage27h physical
    # issuer and original complete Stage25 preset/rejoin parent runner.
    # No second physical owner or automatic C1 approval is created.
    async def _stage27h_c_lane_hook(**kwargs):
        return await stage27h_real_a_motor_hook(
            **kwargs, c_lane_stage27h_post_review=True,
        )

    return await run_real_two_self_preset_checkpoint(
        paper_jar=paper_jar, paper_sha256=paper_sha256,
        plugin_jar=plugin_jar, plugin_sha256=plugin_sha256,
        scratch_parent=scratch_parent,
        accepted_eula=accepted_eula,
        real_world_dev_grant=real_world_dev_grant,
        java=java, node=node,
        timeout_s=timeout_s, heap_mb=heap_mb,
        real_gemma_l1=True, gemma_l1_endpoint=gemma_l1_endpoint,
        gemma_l1_model=gemma_l1_model,
        gemma_l1_jev=False,
        _stage27h_multi_preset=(
            stage27h_l0_move_loop or stage27i_precision_gait
        ),
        _stage27i_precision_target=stage27i_precision_gait,
        _stage27_motor_hook=(
            stage27i_real_a_motor_hook if stage27i_precision_gait
            else _stage27h_c_lane_hook if c_lane_stage27h_post_review
            else stage27h_real_a_motor_hook if stage27h_l0_move_loop
            else stage27g_real_a_motor_hook if stage27g_real_l1_evaluation
            else stage27f_real_a_motor_hook if stage27f_cpu_evaluation
            else stage27e_real_a_motor_hook if stage27e_independent_evidence
            else stage27_real_a_motor_hook
        ),
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paper-jar", type=Path, required=True)
    p.add_argument("--paper-sha256", required=True)
    p.add_argument("--plugin-jar", type=Path, required=True)
    p.add_argument("--plugin-sha256", required=True)
    p.add_argument("--scratch-parent", type=Path, required=True)
    p.add_argument("--eula-accepted", action="store_true")
    p.add_argument("--real-world-dev-grant", action="store_true")
    p.add_argument("--gemma-l1-endpoint", required=True)
    p.add_argument("--gemma-l1-model", required=True)
    p.add_argument("--java", default="java")
    p.add_argument("--node", default="node")
    p.add_argument("--timeout-s", type=float, default=120.0)
    p.add_argument("--heap-mb", type=int, default=1536)
    p.add_argument("--stage27e-independent-evidence", action="store_true")
    p.add_argument("--stage27f-cpu-evaluation", action="store_true")
    p.add_argument("--stage27g-real-l1-evaluation", action="store_true")
    p.add_argument("--stage27h-l0-move-loop", action="store_true")
    p.add_argument("--stage27i-precision-gait", action="store_true")
    p.add_argument("--c-lane-stage27h-post-review", action="store_true")
    args = p.parse_args()
    try:
        report = asyncio.run(run_stage27_real_world(
            paper_jar=args.paper_jar, paper_sha256=args.paper_sha256,
            plugin_jar=args.plugin_jar, plugin_sha256=args.plugin_sha256,
            scratch_parent=args.scratch_parent,
            accepted_eula=args.eula_accepted,
            real_world_dev_grant=args.real_world_dev_grant,
            gemma_l1_endpoint=args.gemma_l1_endpoint,
            gemma_l1_model=args.gemma_l1_model,
            java=args.java, node=args.node,
            timeout_s=args.timeout_s, heap_mb=args.heap_mb,
            stage27e_independent_evidence=args.stage27e_independent_evidence,
            stage27f_cpu_evaluation=args.stage27f_cpu_evaluation,
            stage27g_real_l1_evaluation=args.stage27g_real_l1_evaluation,
            stage27h_l0_move_loop=args.stage27h_l0_move_loop,
            stage27i_precision_gait=args.stage27i_precision_gait,
            c_lane_stage27h_post_review=args.c_lane_stage27h_post_review,
        ))
    except Exception as exc:
        print(f"STAGE27_REAL_WORLD_HOLD={type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"STAGE27_REAL_WORLD_REPORT={report}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
