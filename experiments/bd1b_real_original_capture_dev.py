"""Original B+D live-model one POST capture within an already owned Paper/Native bridge.

This is an opt-in callback, NOT a second Paper/World launcher. An independently
qualified original exploration Schema/source is a precondition. Captured
real-model HTTP entity bytes still require separate independent source audit.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from experiments.p0d_real_paper_smoke_dev import _write_bytes_new
from experiments.stage28c2c_real_original_l1_dev import OriginalRawBoundedLlamaProvider
from relay_self.bd1b_original_issuer_once_dev import issue_original_adoption_once
from relay_self.bd1b_real_issuer_preflight_dev import (
    BD1bRealIssuerHold,
    inspect_bd1b_real_issuer,
)
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentLlamaInferenceLane,
)


class BD1bSinglePostRawProvider(OriginalRawBoundedLlamaProvider):
    """Exactly one BOUNDED POST, never JEV/THINK or transparent retry."""

    def _call(self, request_body, *, endpoint=None):
        if self.attempted or endpoint is not None:
            raise BD1bRealIssuerHold("additional or alternate model POST forbidden")
        return super()._call(request_body, endpoint=endpoint)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _snapshot_owner_bytes(owner):
    path, wal = owner.files.cognition_file, owner.files.physical_wal_file
    root = owner.files.self_root
    if (path != root / "cognition.json" or root.is_symlink()
            or any(p.is_symlink() or not p.is_file() for p in (path, wal))
            or any(p.stat().st_nlink != 1 for p in (path, wal))
            or load_persistent_cognition(path) != owner.retained):
        raise BD1bRealIssuerHold("original disk and resident cognition differ")
    PhysicalActionJournal.restore(wal, self_id=owner.self_id).require_clear()
    return path.read_bytes(), wal.read_bytes()


async def capture_bd1b_real_original_once(
    *, bridge, boot, world, links, self_id: str,
    gguf_path: Path, llama_pid: int, model_alias: str, llama_endpoint: str,
    evidence_dir: Path, model_wait_s: float = 60.0,
) -> Path:
    """Use the original lane and Owner; retain raw copies, never claim QUAL.

    Requires an already-owned Paper/Native original bridge with registered
    source-qualified exploration Schema. Caller owns eventual bridge.logout()
    and independently audits original Paper/Native/HTTP evidence.
    """
    if (type(model_wait_s) not in (int, float) or not 0 < model_wait_s <= 75
            or not isinstance(evidence_dir, Path)):
        raise BD1bRealIssuerHold("typed bounded real-model trial required")
    root = evidence_dir.absolute()
    parent = root.parent
    if (root.exists() or root.is_symlink() or not parent.is_dir()
            or parent.is_symlink()
            or any(root == owner.files.self_root.absolute()
                   or owner.files.self_root.absolute() in root.parents
                   for owner in getattr(bridge, "owners", {}).values())):
        raise BD1bRealIssuerHold("new separate immutable evidence directory required")
    # All original source and actual PID/GGUF/GPU/slot checks happen before
    # creating evidence or attaching the GPU lane.
    pre = inspect_bd1b_real_issuer(
        bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
        gguf_path=gguf_path, llama_pid=llama_pid,
        model_alias=model_alias, llama_endpoint=llama_endpoint,
    )
    owner, turn = pre.turn.owner, pre.turn
    with bridge.cognitive_work.lock:
        before_cognition, before_wal = _snapshot_owner_bytes(owner)
    root.mkdir(mode=0o700)
    _write_bytes_new(root / "cognition.before.json", before_cognition)
    _write_bytes_new(root / "physical.before.wal", before_wal)
    _write_bytes_new(root / "original-source-preflight.json", (
        json.dumps({
            "kind": "REAL_MODEL_INGRESS_UNAUDITED", "self_id": self_id,
            "gate": asdict(pre.gate), "turn": {
                "self_id": turn.self_id, "work_ref": turn.work_ref,
                "owner_scope": list(turn.owner_scope),
                "candidate_set_sha256": turn.candidate_set_sha256,
                "source": asdict(turn.source), "request": asdict(turn.request),
            }, "original_probe": asdict(turn.original_probe),
            "cognition_before_sha256": _digest(before_cognition),
            "wal_before_sha256": _digest(before_wal),
            "physical_action_authorized": False,
        }, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8"))
    raw = root / "http"
    raw.mkdir(mode=0o700)
    provider = BD1bSinglePostRawProvider(
        endpoint=llama_endpoint, model=model_alias, raw_dir=raw,
        timeout=min(45.0, model_wait_s),
    )
    witness = LlamaCppSingleSlotWitness(
        provider=provider, backend_ref="bd1b-original-llama-pid-" + str(llama_pid),
    )
    lane = ResidentLlamaInferenceLane(
        provider=provider, cognitive_work=bridge.cognitive_work, witness=witness,
    )
    attached = False
    try:
        bridge.attach_observation_only_bounded_l1(lane)
        attached = True
        outcome = await issue_original_adoption_once(
            bridge=bridge, lane=lane, boot=boot, world=world, links=links,
            turn=turn, timeout_s=model_wait_s,
        )
        if provider.attempted != 1 or provider.completed != 1:
            raise BD1bRealIssuerHold("one original model HTTP POST not attested")
        original = provider.source_receipts
        request = raw / "bounded-1-request-body.bin"
        response = raw / "bounded-1-response-body.bin"
        receipt = raw / "bounded-1-http-evidence.json"
        if (len(original) != 1 or any(p.is_symlink() or not p.is_file()
                                       for p in (request, response, receipt))
                or _digest(request.read_bytes()) != original[0]["request_body_sha256"]
                or _digest(response.read_bytes()) != original[0]["response_body_sha256"]
                or json.loads(receipt.read_bytes()) != original[0]):
            raise BD1bRealIssuerHold("original raw HTTP entity bodies incomplete")
        with bridge.cognitive_work.lock:
            after_cognition, after_wal = _snapshot_owner_bytes(owner)
            job = lane._jobs[(turn.self_id, turn.work_ref)]
            state = job.question_adoption_state
            if (after_wal != before_wal or
                    (outcome.selection != "ADOPT" and after_cognition != before_cognition)
                    or (outcome.selection == "ADOPT" and (
                        state != "committed" or after_cognition == before_cognition))):
                raise BD1bRealIssuerHold("original cognition or WAL result disagrees")
            copied = {
                "classification": "BD1B_REAL_CAPTURED_INDEPENDENT_AUDIT_PENDING",
                "ticket": asdict(outcome.ticket), "readback": asdict(outcome.readback),
                "selection": outcome.selection, "job_state": state,
                "candidate_set_sha256": turn.candidate_set_sha256,
                "request_sha256": outcome.readback.verified_submitted_request_sha256,
                "raw_http": original[0],
                "cognition_before_sha256": _digest(before_cognition),
                "cognition_after_sha256": _digest(after_cognition),
                "physical_wal_sha256": _digest(after_wal),
                "physical_action_issued": False,
                "real_model_independently_audited": False,
                "real_paper_independently_audited": False,
            }
        _write_bytes_new(root / "cognition.after.json", after_cognition)
        _write_bytes_new(root / "physical.after.wal", after_wal)
        _write_bytes_new(root / "issuer-capture.json", (
            json.dumps(copied, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8"))
        return root / "issuer-capture.json"
    except BaseException as exc:
        # Capture remains on disk; a failed attempt is never silently retried.
        _write_bytes_new(root / "issuer-HOLD.json", (
            json.dumps({"classification": "BD1B_REAL_HOLD", "failure_type":
                        type(exc).__name__, "model_post_attempted": provider.attempted,
                        "model_post_completed": provider.completed},
                       sort_keys=True) + "\n"
        ).encode("utf-8"))
        if attached:
            bridge.quarantine(self_id)
        raise
