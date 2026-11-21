"""#860 Stage22: operator-gated REAL Paper + two resident Self body presence.

Default is native login/logout, B observation and World continuity.
Stage23 adds explicit operator-selected B MOVE via original ActionPort,
WAL, capability-bound native START/STOP and Paper motion witness. No GPU,
autonomous Skill selection or Action-specific Paper causation is claimed.
Never attaches to an existing server.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import uuid
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerLaunchConfig,
    MineflayerObservation,
)
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    PhysicalGrantStage,
)
from experiments.cognitive_physical_move_issue_dev import ResidentMoveDevReceipt
from experiments.p0d_real_paper_smoke_dev import (
    _bootstrap_paper,
    _free_local_port,
    _world_uuid,
    _write_bytes_new,
    file_sha256,
)
from experiments.p0d_real_two_native_smoke_dev import (
    preflight_two_native,
    two_native_server_properties,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
)
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.owned_resident_physical_bridge_dev import (
    OwnedResidentPhysicalBridge,
)
from relay_self.paper_tick_witness_dev import PaperMainThreadTickReader
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalCapability,
    PhysicalReadback,
    propose_bound_physical_action,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.resident_move_raw_audit_dev import readback_owned_move_native_source
from relay_self.resident_paper_presence_join_dev import (
    ResidentPaperVerdict,
    join_resident_paper_presence,
    parse_owned_paper_resident_trace,
)
from relay_self.world_only_owned_checkpoint_dev import (
    WorldOnlyOwnedPaperCheckpoint,
    verify_world_only_generation,
)
from relay_self.world_resident_lifecycle_dev import (
    WorldLifetime,
    WorldResidentLifecycle,
)


class RealResidentPresenceRefusal(RuntimeError):
    """Real Paper observation or explicit operator/owner evidence not qualified."""


def _immutable_receipt(evidence_dir: Path, name: str, receipt: object) -> dict[str, str]:
    """Preserve each ORIGINAL actor receipt as exclusive fsynced source evidence."""
    path = evidence_dir / (name + ".json")
    body = (json.dumps(asdict(receipt), sort_keys=True, indent=2) + "\n").encode()
    _write_bytes_new(path, body)
    if path.read_bytes() != body:
        raise RealResidentPresenceRefusal("immutable logout receipt readback mismatch")
    return {"path": str(path), "sha256": file_sha256(path)}


def _immutable_cognition(
    evidence_dir: Path, name: str, source: Path,
) -> dict[str, str]:
    """Freeze the *first* logout cognition bytes before any Self relogin."""
    original = source.read_bytes()
    if not original:
        raise RealResidentPresenceRefusal("original cognition not persisted")
    path = evidence_dir / (name + ".json")
    _write_bytes_new(path, original)
    if path.read_bytes() != original or file_sha256(path) != file_sha256(source):
        raise RealResidentPresenceRefusal("first cognition snapshot readback mismatch")
    return {"path": str(path), "sha256": file_sha256(path)}


async def _bounded_b_probe(
    native: MineflayerProcessSession, *, timeout_s: float = 12.0,
) -> MineflayerObservation:
    """Native B sensor source after A logout; not a physical Action issuer."""
    native_id = native.started.session_id
    request_id = "p0d-b-online-" + uuid.uuid4().hex
    await native.send_observe(request_id)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    for _ in range(256):
        left = deadline - loop.time()
        if left <= 0:
            break
        try:
            item = await asyncio.wait_for(native.receive(), left)
        except TimeoutError as exc:
            raise RealResidentPresenceRefusal("B native probe timeout") from exc
        if item.session_id != native_id or isinstance(
            item, (
                MineflayerConnectionEnd, MineflayerAdapterErrorMessage,
                MineflayerCommandError,
            ),
        ):
            raise RealResidentPresenceRefusal("B native stream ended/foreign during A logout")
        if isinstance(item, MineflayerObservation) and item.kind == "probe":
            if (
                item.request_id != request_id
                or item.snapshot.health <= 0
                or item.snapshot.time is None
            ):
                raise RealResidentPresenceRefusal("B live native source mismatched")
            return item
    raise RealResidentPresenceRefusal("B requested probe not received")


async def _issue_original_selected_b_move_core(
    *,
    session: MineflayerProcessSession,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    pulse_seconds: float,
) -> tuple[dict[str, object], ResidentMoveDevReceipt, MineflayerObservation]:
    """Core original-owner MOVE; result still needs source-independent audit.

    Opt-in B physical DEV pulse after A quit; NOT an autonomous L1 choice.

    Uses the exact original Self's Intent/Skill/ActionPort and original WAL.
    The *operator* supplies this preselected relative MOVE DEV objective;
    do not conflate it with spontaneous Self Goal/Skill selection.
    """
    if (
        owner.self_id != "B"
        or owner.native_session_id != session.started.session_id
        or physical.current_native_sessions.get("B") != session.started.session_id
        or physical.resident_states["B"] != "ONLINE"
        or owner.supervisor.recorded_actions
        or not 0.15 <= pulse_seconds <= 0.75
    ):
        raise RealResidentPresenceRefusal("B original selected MOVE owner unavailable")
    old_probe = await _bounded_b_probe(session)
    current_probe = await _bounded_b_probe(session)
    if (
        current_probe.seq <= old_probe.seq
        or current_probe.seq > old_probe.seq + 32
        or current_probe.session_id != old_probe.session_id
    ):
        raise RealResidentPresenceRefusal("fresh B two-probe WorldBody window missing")

    intent_id = "p0d-b-move-intent-" + uuid.uuid4().hex
    skill_id = "p0d-b-move-skill-" + uuid.uuid4().hex
    action_id = "p0d-b-move-action-" + uuid.uuid4().hex
    source = Provenance(
        "p0d-operator-selected-move-dev",
        current_probe.provenance.reference,
    )
    owner.commit_intent(
        intent_id, "WALK_RELATIVE", at_ns=1, provenance=source,
    )
    owner.start_skill(
        skill_id, "MOVE", at_ns=2, provenance=source,
    )
    selected = owner.skills[skill_id]
    binding = PhysicalActionBinding(
        scope=ScopeRef("B", current_probe.session_id),
        intent_id=intent_id, goal_id="WALK_RELATIVE",
        skill_id="MOVE", skill_version=1,
        skill_execution_id=selected.execution_id, action_id=action_id,
        capability_ref="MOVE", capability_version=1,
        body_channel="locomotion", target_kind="RELATIVE",
        target_ref="relative:forward",
        native_seq=current_probe.seq,
        native_request_id=current_probe.request_id,
        native_source=current_probe.provenance,
    )
    proposal = propose_bound_physical_action(
        binding,
        capability=PhysicalCapability(
            "MOVE", 1, "locomotion", "RELATIVE", True,
        ),
        readback=PhysicalReadback(
            binding.scope, current_probe.provenance,
            current_probe.seq, current_probe.request_id,
            (binding.target_ref,), current_probe.snapshot.health > 0,
        ),
        intent_owner=owner.intent, skill_execution=selected,
        supervisor=owner.supervisor, at_ns=3, provenance=source,
    )

    def grant(stage: PhysicalGrantStage) -> PhysicalDevGrant:
        return PhysicalDevGrant(
            stage=stage,
            authority_id="operator-stage23-" + stage.value.lower(),
            provenance=Provenance(
                "operator-approved-dev-" + stage.value.lower(),
                current_probe.provenance.reference,
            ),
            intent_id=binding.intent_id, action_id=binding.action_id,
            session_id=current_probe.session_id,
            probe_seq=current_probe.seq,
            probe_request_id=current_probe.request_id,
            selected_target_ref=binding.target_ref,
            granted=True,
        )

    original_wal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="B",
    )
    receipt = await physical.issue_move(
        session, proposal=proposal,
        previous_probe=old_probe, current_probe=current_probe,
        propose_grant=grant(PhysicalGrantStage.PROPOSE),
        issue_grant=grant(PhysicalGrantStage.ISSUE),
        intent_owner=owner.intent, skill_execution=selected,
        supervisor=owner.supervisor, journal=original_wal,
        at_ns=4, provenance=source,
        grant_real_world=True,
        acknowledge_dev_unverified_principal=True,
        evidence_timeout_s=15,
        pulse_seconds=pulse_seconds,
    )
    checked = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="B",
    )
    if (
        checked.unresolved
        or not checked.records
        or checked.records[-1]["status"] != "NATIVE_MOVE_SETTLED"
        or checked.records[-1]["action_id"] != action_id
        or checked.digest != receipt.journal_sha256
        or owner.supervisor.open_actions
    ):
        raise RealResidentPresenceRefusal("B original native MOVE/WAL terminal not verified")
    result = {
        "classification": "DEV_ORIGINAL_B_NATIVE_MOVE_SETTLED",
        "original_action_id": action_id,
        "original_intent_id": intent_id,
        "original_skill_execution_id": selected.execution_id,
        "b_native_session": current_probe.session_id,
        "native_start_ack_seq": receipt.start_ack.seq,
        "native_stop_ack_seq": receipt.stop_ack.seq,
        "initial_stop_seq": receipt.initial_stop_probe.seq,
        "first_stable_seq": receipt.first_stable_probe.seq,
        "settled_seq": receipt.settled_probe.seq,
        "native_net_displacement_m": receipt.displacement_m,
        "original_canonical_wal_sha256": receipt.journal_sha256,
        "operator_selected_dev_move": True,
        "autonomous_l1_skill_selection": False,
        "skill_success_attested": False,
        "paper_action_causation": False,
        "gpu_inference_ran": False,
    }
    return result, receipt, current_probe


async def _issue_original_selected_b_move(
    *,
    session: MineflayerProcessSession,
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    pulse_seconds: float,
    evidence_dir: Path | None = None,
) -> dict[str, object]:
    """Use original issuer and, if real, freeze all original source bytes.

    Offline fixtures can omit evidence_dir; an actual real-Paper runner
    MUST provide the owned evidence directory to enable raw-source audit.
    """
    if evidence_dir is None:
        result, _, _ = await _issue_original_selected_b_move_core(
            session=session, owner=owner, physical=physical,
            pulse_seconds=pulse_seconds,
        )
        return result
    if type(evidence_dir) is not Path or not evidence_dir.is_dir():
        raise RealResidentPresenceRefusal("owned raw native audit directory missing")
    raw = evidence_dir / "B-original-move-native-source.jsonl"
    # Fail before native MOVE if the exact owned stream cannot be recorded.
    session.start_raw_source_audit(raw)
    try:
        result, receipt, current = await _issue_original_selected_b_move_core(
            session=session, owner=owner, physical=physical,
            pulse_seconds=pulse_seconds,
        )
    finally:
        # Readback of this immutable source is available on a HOLD too:
        # every received line was fsynced at the original process boundary.
        session.finish_raw_source_audit()

    independently_checked = readback_owned_move_native_source(
        raw_path=raw,
        journal_path=owner.files.physical_wal_file,
        self_id="B",
        action_id=str(result["original_action_id"]),
        current_probe=current,
        receipt=receipt,
    )
    audit_path = evidence_dir / "B-original-move-native-readback.json"
    _write_bytes_new(
        audit_path,
        (json.dumps(independently_checked, sort_keys=True, indent=2) + "\n").encode(),
    )
    if json.loads(audit_path.read_text()) != independently_checked:
        raise RealResidentPresenceRefusal("independent MOVE raw audit write/readback mismatch")
    result["independent_native_source"] = {
        "raw_file": str(raw), "raw_sha256": file_sha256(raw),
        "readback_file": str(audit_path),
        "readback_sha256": file_sha256(audit_path),
        "readback_classification": independently_checked["classification"],
        "all_settle_probes": len(independently_checked["all_stop_probes"]),
        "native_start_ack": independently_checked["native_start_ack"],
        "native_stop_ack": independently_checked["native_stop_ack"],
    }
    return result


async def _owned_resident_trial(
    *,
    paper: OwnedPaperWorld,
    bridge: OwnedResidentPhysicalBridge,
    physical: PhysicalIssueAdmission,
    lifecycle: WorldResidentLifecycle,
    world_uuid: str,
    evidence_dir: Path,
    b_heartbeat_s: float,
    world_only: bool,
    b_selected_move_dev: bool = False,
    b_pulse_seconds: float = 0.35,
) -> dict[str, object]:
    """One strictly bounded native body scenario. No model/Skill/Action issue."""
    if (
        paper.owned_session_id is None
        or not 2 <= b_heartbeat_s <= 12
        or bridge.lifecycle is not lifecycle
        or bridge.physical is not physical
        or tuple(sorted(bridge.owners)) != ("A", "B")
        or not physical.resident_mode
        or not physical.all_residents_offline
    ):
        raise RealResidentPresenceRefusal("two initial offline residents and owned Paper required")

    paper_session = paper.owned_session_id
    assert paper_session is not None
    original_a = await bridge.login("A")
    original_b = await bridge.login("B")
    old_a = bridge.sessions["A"].started.session_id
    a_initial_pid = bridge.sessions["A"].owned_child_pid
    original_b_native = bridge.sessions["B"].started.session_id
    b_initial_pid = bridge.sessions["B"].owned_child_pid
    # The passive Paper sampler emits a PRESENT heartbeat per player each
    # 40 Bukkit ticks. No native effect is sent to produce that heartbeat.
    await asyncio.sleep(float(b_heartbeat_s))
    a_logout = await bridge.logout("A")
    if a_logout.native_session_id != old_a:
        raise RealResidentPresenceRefusal("A native terminal source mismatch")
    a_first_logout_receipt = _immutable_receipt(
        evidence_dir, "A-first-logout-original", a_logout,
    )
    a_first_cognition_snapshot = _immutable_cognition(
        evidence_dir, "A-first-logout-cognition",
        bridge.owners["A"].files.cognition_file,
    )
    await asyncio.sleep(float(b_heartbeat_s))
    b_probe = await _bounded_b_probe(bridge.sessions["B"])
    if (
        physical.current_native_sessions["B"] != original_b_native
        or bridge.sessions["B"].started.session_id != original_b_native
    ):
        raise RealResidentPresenceRefusal("B changed original native owner after A quit")
    b_move = None
    if b_selected_move_dev:
        b_move = await _issue_original_selected_b_move(
            session=bridge.sessions["B"],
            owner=bridge.owners["B"], physical=physical,
            pulse_seconds=b_pulse_seconds,
            evidence_dir=evidence_dir,
        )
    a_relogin_ticket = await bridge.login("A")
    a_relogin = bridge.last_login_evidence["A"]
    a_relogin_pid = bridge.sessions["A"].owned_child_pid
    if a_relogin.native_session_id == old_a:
        raise RealResidentPresenceRefusal("A reused native process")
    await asyncio.sleep(1.0)
    # This reads ONLY the explicitly owned Paper Popen stdout log.
    source = paper.read_owned_log(paper_session)
    import hashlib

    source_ref = (
        f"paper-owned-log:{paper_session}:sha256:"
        f"{hashlib.sha256(source).hexdigest()}"
    )
    trace = parse_owned_paper_resident_trace(
        owned_paper_session_id=paper_session,
        expected_world_uuid=world_uuid,
        owned_paper_log=source, log_ref=source_ref,
    )
    result = join_resident_paper_presence(
        trace=trace, world=lifecycle.world,
        a_name="RelayA", b_name="RelayB",
        a_logout=a_logout, a_relogin=a_relogin,
        original_b_native=original_b_native,
        surviving_b_native=physical.current_native_sessions["B"],
    )
    # A settled original B native MOVE and Paper movement can corroborate
    # motion, but no Action-ID Paper ticket means NO causal attribution.
    if b_move is not None and result.status is not ResidentPaperVerdict.MOVEMENT_CORRELATED:
        raise RealResidentPresenceRefusal(
            "B original native MOVE terminal but independent Paper movement absent"
        )
    result_data: dict[str, object] = {
        "classification": "REAL_PAPER_RESIDENT_PRESENCE_DEV",
        "paper_player_continuity": result.status.value,
        "independent_paper_source": result.paper_source_ref,
        "paper_boot": trace.boot_id,
        "world_uuid": world_uuid,
        "paper_session_id": paper_session,
        "a_original_ticket": asdict(original_a),
        "b_original_ticket": asdict(original_b),
        "a_original_native_session": old_a,
        "a_original_owned_pid": a_initial_pid,
        "b_original_owned_pid": b_initial_pid,
        "a_relogin_owned_pid": a_relogin_pid,
        "a_logout": asdict(a_logout),
        "a_first_logout_receipt_file": a_first_logout_receipt,
        "a_first_logout_cognition_snapshot": a_first_cognition_snapshot,
        "a_relogin_ticket": asdict(a_relogin_ticket),
        "a_relogin_evidence": asdict(a_relogin),
        "b_original_native_session": original_b_native,
        "b_probe": {
            "session": b_probe.session_id,
            "seq": b_probe.seq,
            "request_id": b_probe.request_id,
            "provenance": b_probe.provenance.reference,
            "world_day": b_probe.snapshot.time.day if b_probe.snapshot.time else None,
            "time_of_day": (
                b_probe.snapshot.time.time_of_day if b_probe.snapshot.time else None
            ),
            "health": b_probe.snapshot.health,
            "x": b_probe.snapshot.position.x,
            "y": b_probe.snapshot.position.y,
            "z": b_probe.snapshot.position.z,
        },
        "b_actor_uuid": result.b_actor_uuid,
        "a_actor_uuid": result.a_actor_uuid,
        "a_paper_quit_tick": result.a_quit_tick,
        "b_paper_continuation_tick": result.b_later_tick,
        "a_paper_rejoin_tick": result.a_rejoin_tick,
        "b_paper_displacement_m": result.b_movement_m,
        "b_actual_physical_action": b_move is not None,
        "b_physical_wal_outcome": b_move is not None,
        "b_original_selected_move": b_move,
        "b_move_action_causality": False,
        "real_l1_l2_gpu_executed": False,
        "real_peer_transport_executed": False,
    }
    final_a = await bridge.logout("A")
    final_b = await bridge.logout("B")
    result_data["final_a_logout_receipt_file"] = _immutable_receipt(
        evidence_dir, "A-final-logout-original", final_a,
    )
    result_data["final_b_logout_receipt_file"] = _immutable_receipt(
        evidence_dir, "B-final-logout-original", final_b,
    )
    if not bridge.world_only_quiescence().no_unresolved_physical_actions:
        raise RealResidentPresenceRefusal("not all original issuer receipts retired")
    if world_only:
        store = evidence_dir / "world-only-generations"
        store.mkdir(mode=0o700)
        result_world = WorldOnlyOwnedPaperCheckpoint(
            lifecycle=lifecycle, owned_paper=paper, store=store,
            issuer_quiescence=bridge.world_only_quiescence,
        ).cycle()
        verify_world_only_generation(result_world.checkpoint_dir)
        result_data["world_only_generation"] = str(result_world.checkpoint_dir)
        result_data["world_only_new_session"] = (
            result_world.new_world.paper_session_id
        )
        result_data["world_only_new_epoch"] = result_world.new_world.epoch
    return result_data


def _adopt_verified_trial_report(
    report: dict[str, object],
    trial: dict[str, object],
    *, b_selected_move_dev: bool, world_only: bool,
) -> None:
    """One source of truth for top-level flags, step and classification.

    Never mark a real B MOVE from an operator option alone; the original
    issuer/WAL, Paper MOVE and frozen raw-native readback must all agree.
    """
    if (
        type(trial) is not dict
        or type(b_selected_move_dev) is not bool
        or type(world_only) is not bool
    ):
        raise RealResidentPresenceRefusal("unqualified real World trial result")
    moved = trial.get("b_actual_physical_action") is True
    terminal = trial.get("b_physical_wal_outcome") is True
    detail = trial.get("b_original_selected_move")
    if moved != terminal or moved != b_selected_move_dev:
        raise RealResidentPresenceRefusal("real B action flag contradicts original WAL")
    if world_only and (
        not trial.get("world_only_generation")
        or not trial.get("world_only_new_session")
    ):
        raise RealResidentPresenceRefusal("requested World-only generation not verified")
    if moved:
        if (
            type(detail) is not dict
            or detail.get("classification") != "DEV_ORIGINAL_B_NATIVE_MOVE_SETTLED"
            or not detail.get("original_action_id")
            or not detail.get("original_canonical_wal_sha256")
            or detail.get("autonomous_l1_skill_selection") is not False
            or detail.get("paper_action_causation") is not False
            or trial.get("b_move_action_causality") is not False
            or trial.get("paper_player_continuity")
            != ResidentPaperVerdict.MOVEMENT_CORRELATED.value
        ):
            raise RealResidentPresenceRefusal("original B MOVE and Paper source not correlated")
        raw = detail.get("independent_native_source")
        if (
            type(raw) is not dict
            or raw.get("readback_classification")
            != "OWNED_NATIVE_MOVE_RAW_SOURCE_READBACK_DEV"
            or type(raw.get("all_settle_probes")) is not int
            or raw["all_settle_probes"] < 3
            or not all(
                type(raw.get(k)) is str
                for k in ("raw_file", "readback_file", "raw_sha256", "readback_sha256")
            )
            or file_sha256(Path(raw["raw_file"])) != raw["raw_sha256"]
            or file_sha256(Path(raw["readback_file"])) != raw["readback_sha256"]
        ):
            raise RealResidentPresenceRefusal("immutable B raw native source not independently verified")
        # Read the frozen verification sidecar again, not just its filename
        # and caller-supplied SHA fields.
        try:
            sidecar = json.loads(Path(raw["readback_file"]).read_text())
        except (OSError, ValueError) as exc:
            raise RealResidentPresenceRefusal("B raw sidecar unreadable") from exc
        if (
            type(sidecar) is not dict
            or sidecar.get("classification") != raw["readback_classification"]
            or sidecar.get("original_action_id") != detail["original_action_id"]
            or sidecar.get("canonical_wal_digest")
            != detail["original_canonical_wal_sha256"]
            or sidecar.get("source_sha256") != raw["raw_sha256"]
            or sidecar.get("original_self_id") != "B"
            or sidecar.get("original_native_session") != detail.get("b_native_session")
            or type(sidecar.get("all_stop_probes")) is not list
            or len(sidecar["all_stop_probes"]) != raw["all_settle_probes"]
            or not sidecar.get("native_start_ack")
            or not sidecar.get("native_stop_ack")
            or sidecar.get("paper_action_id_causal_ticket") is not False
            or sidecar.get("autonomous_l1_skill_selection") is not False
        ):
            raise RealResidentPresenceRefusal("frozen B raw source/WAL identity sidecar inconsistent")
    elif detail is not None:
        raise RealResidentPresenceRefusal("unrequested B MOVE detail in presence-only trial")

    # Only reach success classifications after all nested source evidence
    # is checked. On any exception the outer report remains HOLD/UNKNOWN.
    classification = (
        "REAL_PAPER_B_MOVE_CORRELATED_WORLD_ONLY_DEV"
        if moved and world_only
        else "REAL_PAPER_B_MOVE_CORRELATED_DEV" if moved
        else "REAL_PAPER_RESIDENT_PRESENCE_AND_WORLD_ONLY_DEV"
        if world_only else "REAL_PAPER_RESIDENT_PRESENCE_DEV"
    )
    report["steps"] = [trial]
    report["real_b_physical_action"] = moved
    report["real_b_physical_wal_outcome"] = terminal
    report["native_move_raw_source_attested"] = moved
    report["classification"] = classification


def _require_stage24g_systemone_capture(evidence: Path) -> dict[str, object]:
    """Verify original one-POST evidence before promoting any integrated result."""
    folder = evidence / "stage24g-systemone-http"
    try:
        request = (folder / "systemone-request-body.bin").read_bytes()
        response = (folder / "systemone-response-body.bin").read_bytes()
        manifest = json.loads((folder / "systemone-http-evidence.json").read_bytes())
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise RealResidentPresenceRefusal(
            "Stage24g SystemOne original HTTP evidence unavailable"
        ) from exc
    if (
        type(manifest) is not dict
        or manifest.get("capture_type") != "urllib_http_entity_bodies_not_wire_headers"
        or manifest.get("http_status") != 200
        or manifest.get("request_body_sha256") != hashlib.sha256(request).hexdigest()
        or manifest.get("response_body_sha256") != hashlib.sha256(response).hexdigest()
        or manifest.get("request_body_bytes") != len(request)
        or manifest.get("response_body_bytes") != len(response)
    ):
        raise RealResidentPresenceRefusal(
            "Stage24g actual SystemOne HTTP body/status digest mismatch"
        )
    return {
        "model_http_entity_bodies_archived": True,
        "model_http_wire_headers_archived": False,
        "model_http_status_attested": 200,
        "model_http_request_sha256": manifest["request_body_sha256"],
        "model_http_response_sha256": manifest["response_body_sha256"],
    }


async def run_real_resident_presence(
    *, paper_jar: Path, paper_sha256: str,
    plugin_jar: Path, plugin_sha256: str,
    scratch_parent: Path, accepted_eula: bool,
    real_world_dev_grant: bool,
    java: str = "java", node: str = "node",
    timeout_s: float = 120.0, heap_mb: int = 1536,
    b_heartbeat_s: float = 4.0, world_only: bool = False,
    b_selected_move_dev: bool = False, b_pulse_seconds: float = 0.35,
) -> Path:
    """One genuine Paper/Mineflayer scenario, no implicit EULA/DEV grants."""
    if real_world_dev_grant is not True:
        raise RealResidentPresenceRefusal(
            "HOLD_REAL_WORLD_GRANT: explicit real Paper/native DEV approval required"
        )
    if type(b_heartbeat_s) not in (int, float) or not 2 <= b_heartbeat_s <= 12:
        raise RealResidentPresenceRefusal("bounded Paper heartbeat delay required")
    if (
        type(b_selected_move_dev) is not bool
        or type(b_pulse_seconds) not in (int, float)
        or not math.isfinite(b_pulse_seconds)
        or not 0.15 <= b_pulse_seconds <= 0.75
    ):
        raise RealResidentPresenceRefusal(
            "bounded explicit operator-selected B MOVE DEV required before Paper launch"
        )
    paper_src, plugin_src, scratch = preflight_two_native(
        paper_jar=paper_jar, paper_sha256=paper_sha256,
        plugin_jar=plugin_jar, plugin_sha256=plugin_sha256,
        scratch_parent=scratch_parent, accepted_eula=accepted_eula,
        java=java, node=node, timeout_s=timeout_s, heap_mb=heap_mb,
    )
    root = Path(tempfile.mkdtemp(prefix="p0d-resident-presence-", dir=scratch))
    os.chmod(root, 0o700)
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700)
    plugins = root / "plugins"
    plugins.mkdir(mode=0o700)
    shutil.copyfile(paper_src, root / "paper.jar")
    shutil.copyfile(plugin_src, plugins / "P0BRecorder.jar")
    _write_bytes_new(root / "eula.txt", b"eula=true\n")
    port = _free_local_port()
    _write_bytes_new(
        root / "server.properties",
        two_native_server_properties(port).encode(),
    )
    launch_command = (
        java, "-Xms512M", f"-Xmx{heap_mb}M",
        "-jar", str(root / "paper.jar"), "--nogui",
    )
    report_path = evidence / "resident-presence-result.json"
    report: dict[str, object] = {
        "schema": 1,
        "classification": "HOLD",
        "real_world_permission": True,
        "paper_sha256": paper_sha256,
        "plugin_sha256": plugin_sha256,
        "scratch": str(root),
        "localhost_port": port,
        # A selected MOVE is UNKNOWN until original WAL, Paper and exact
        # native stdout bytes are independently checked, not automatically false.
        "real_b_physical_action": None if b_selected_move_dev else False,
        "real_b_physical_wal_outcome": None if b_selected_move_dev else False,
        "native_move_raw_source_attested": False,
        "real_gpu": False,
        "steps": [],
    }
    owner = None
    bridge = None
    physical = None
    try:
        bootstrap = _bootstrap_paper(
            world_root=root, launch=launch_command, timeout_s=timeout_s,
        )
        world_uuid = _world_uuid(root / "world")
        report["bootstrap_sha256"] = file_sha256(bootstrap)
        report["world_uuid"] = world_uuid
        holder: dict[str, OwnedPaperWorld] = {}
        tick = PaperMainThreadTickReader(
            spool_dir=plugins / "P0BRecorder" / "p0d-ticks",
            expected_world_uuid=world_uuid,
            read_owned_log=lambda sess: holder["paper"].read_owned_log(sess),
            timeout_seconds=min(15.0, timeout_s / 3),
        )
        owner = OwnedPaperWorld(
            server_dir=root, world_dir=root / "world",
            evidence_dir=evidence, command=launch_command,
            world_id=world_uuid, branch_id="p0d-real-resident-presence",
            tick_readback=tick, timeout_seconds=timeout_s,
        )
        holder["paper"] = owner
        paper_session = owner.start_owned()
        names = ("A", "B")
        initial_native = {sid: "offline-born-" + sid for sid in names}
        physical = PhysicalIssueAdmission(
            initial_native, resident_mode=True, initially_offline=True,
            allow_resident_move=b_selected_move_dev,
        )
        configs = {
            sid: MineflayerLaunchConfig(
                host="127.0.0.1", port=port,
                username="Relay" + sid, version="1.21.8",
            ) for sid in names
        }
        originals: dict[str, CheckpointedCognitiveOwner] = {}
        for sid in names:
            folder = root / ("self-" + sid)
            folder.mkdir(mode=0o700)
            wal = folder / "physical-wal.json"
            PhysicalActionJournal.create(wal, self_id=sid)
            originals[sid] = CheckpointedCognitiveOwner(
                retained=PersistentCognition(
                    IdentitySpecification(
                        sid, ("World-independent retained identity",),
                        Provenance("p0d-real-resident", sid),
                    )
                ),
                intent=IntentCommitment(),
                pattern_registry=initial_patterns(),
                native_session_id=initial_native[sid],
                last_observed_tick=0,
                files=CognitiveOwnerFiles(
                    folder, folder / "cognition.json", wal,
                ),
                physical_supervisor=ActionSupervisor(),
            )
        cognition = ResidentCognitiveWorkOwner(originals)
        lifecycle = WorldResidentLifecycle(
            world=WorldLifetime(
                world_uuid, "p0d-real-resident-presence", paper_session, 0, 0,
            ),
            persisted_self_refs={
                sid: f"boot-original-cognition:{sid}" for sid in names
            },
        )

        async def native_factory(config: MineflayerLaunchConfig):
            return await MineflayerProcessSession.launch(
                config, node_executable=node,
                startup_timeout_s=min(30.0, timeout_s / 3),
            )

        bridge = OwnedResidentPhysicalBridge(
            lifecycle=lifecycle, physical=physical, paper=owner,
            configs=configs, owners=originals,
            launch=native_factory, cognitive_work=cognition,
            probe_timeout_s=min(30.0, timeout_s / 3),
        )
        trial = await _owned_resident_trial(
            paper=owner, bridge=bridge, physical=physical,
            lifecycle=lifecycle, world_uuid=world_uuid,
            evidence_dir=evidence,
            b_heartbeat_s=b_heartbeat_s, world_only=world_only,
            b_selected_move_dev=b_selected_move_dev,
            b_pulse_seconds=b_pulse_seconds,
        )
        _adopt_verified_trial_report(
            report, trial, b_selected_move_dev=b_selected_move_dev,
            world_only=world_only,
        )
    except BaseException as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
        if physical is not None:
            physical.hold_for_operator()
        raise
    finally:
        if bridge is not None:
            for session in {id(s): s for s in bridge.sessions.values()}.values():
                try:
                    if session.process_returncode is None:
                        await asyncio.wait_for(session.terminate(), timeout=8.0)
                except BaseException:
                    report["cleanup_uncertain"] = True
                    report["classification"] = "HOLD"
        if owner is not None and owner.owned_session_id is not None and not owner.held_uncertain:
            try:
                owner.stop_and_save()
            except BaseException:
                report["cleanup_uncertain"] = True
                report["classification"] = "HOLD"
        _write_bytes_new(
            report_path, (json.dumps(report, indent=2, sort_keys=True) + "\n").encode(),
        )
        print(f"P0D_RESIDENT_REAL_AUDIT={report_path}", file=sys.stderr, flush=True)
        if owner is not None and owner.owned_session_id is not None:
            print(
                "P0D_HOLD: owned disposable Paper may still run; inspect"
                " this exact PID/source, no blind kill/retry.",
                file=sys.stderr, flush=True,
            )
    if report["classification"] not in (
        "REAL_PAPER_RESIDENT_PRESENCE_DEV",
        "REAL_PAPER_RESIDENT_PRESENCE_AND_WORLD_ONLY_DEV",
        "REAL_PAPER_B_MOVE_CORRELATED_DEV",
        "REAL_PAPER_B_MOVE_CORRELATED_WORLD_ONLY_DEV",
    ):
        raise RealResidentPresenceRefusal("resident Paper evidence unqualified")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--plugin-sha256", required=True)
    parser.add_argument("--scratch-parent", type=Path, required=True)
    parser.add_argument("--eula-accepted", action="store_true")
    parser.add_argument("--real-world-dev-grant", action="store_true")
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--heap-mb", type=int, default=1536)
    parser.add_argument("--b-heartbeat-s", type=float, default=4.0)
    parser.add_argument("--world-only", action="store_true")
    parser.add_argument("--b-selected-move-dev", action="store_true")
    parser.add_argument("--b-pulse-seconds", type=float, default=0.35)
    args = parser.parse_args()
    try:
        result = asyncio.run(run_real_resident_presence(
            paper_jar=args.paper_jar, paper_sha256=args.paper_sha256,
            plugin_jar=args.plugin_jar, plugin_sha256=args.plugin_sha256,
            scratch_parent=args.scratch_parent, accepted_eula=args.eula_accepted,
            real_world_dev_grant=args.real_world_dev_grant,
            java=args.java, node=args.node,
            timeout_s=args.timeout_s, heap_mb=args.heap_mb,
            b_heartbeat_s=args.b_heartbeat_s, world_only=args.world_only,
            b_selected_move_dev=args.b_selected_move_dev,
            b_pulse_seconds=args.b_pulse_seconds,
        ))
    except Exception as exc:
        print(f"P0D_RESIDENT_HOLD={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2
    print(f"P0D_RESIDENT_REAL_RESULT={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
