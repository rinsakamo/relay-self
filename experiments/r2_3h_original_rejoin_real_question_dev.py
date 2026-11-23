"""R2-3h opt-in real-Gemma seam for an ALREADY LIVE original reJOIN World.

This is not a World launcher and never constructs a synthetic original
Owner, Native/Paper observation or a second GPU lane. The caller must
already own the real first-A-reJOIN/B-continuing Original Bridge, including
its source-pinned historical A/B cut. A real model POST requires an explicit
local DEV grant, a newly verified PID/GGUF/GPU/single slot and a fresh
raw-evidence directory. There is no fallback to a staged or synthetic cut.

This seam must not be used to qualify Stage28c2c's *different* fresh A/B
recovered-login trial as the R2-3 first A-reJOIN.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from experiments.p0d_real_paper_smoke_dev import _write_bytes_new, file_sha256
from experiments.stage24g_model_gate_dev import (
    Stage24gModelGateReceipt,
    verify_stage24g_model_gate,
)
from experiments.stage28c2c_real_original_l1_dev import (
    OriginalRawBoundedLlamaProvider,
)
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.r2_3b_original_rejoin_l1_source_compare_dev import (
    R23BOriginalL1SourceComparison,
)
from relay_self.r2_3c_original_rejoin_frozen_l1_dev import (
    R23CFrozenOriginalRejoinL1,
)
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentLlamaInferenceLane,
)


class R23HOriginalRealModelHold(RuntimeError):
    """Real reJOIN Source or bounded Original Gemma evidence is not qualified."""


@dataclass(frozen=True, slots=True)
class R23HOriginalRealSource:
    """Original live first-reJOIN A/B source, never fresh-login substitution."""

    self_id: str
    a_native: str
    b_native: str
    a_scope: tuple[int, str, int]
    b_scope: tuple[int, str, int]
    source_pair_revision: str
    request_question_ref: str
    physical_issue_authorized: bool = False
    product_l1_input_switched: bool = False


@dataclass(frozen=True, slots=True)
class R23HOriginalRealModelReadback:
    """Captured real model job; still pending independent original evidence audit."""

    self_id: str
    ticket: object
    selection: str
    model_post_attempted: int
    model_post_completed: int
    raw_http_entity_bodies_captured: bool
    backend_terminal_idle: bool
    source: R23HOriginalRealSource
    report_path: Path
    question_adopted: bool = False
    physical_issue_authorized: bool = False
    product_l1_input_switched: bool = False


def inspect_r23h_original_live_source(
    *, bridge: OwnedResidentPhysicalBridge, self_id: str,
) -> R23HOriginalRealSource:
    """Strict read-only real Original A-first-reJOIN/B-continuing qualification."""
    if type(bridge) is not OwnedResidentPhysicalBridge or self_id not in ("A", "B"):
        raise R23HOriginalRealModelHold("typed Original Bridge and A/B Self required")
    resident = bridge.cognitive_work
    if resident is None:
        raise R23HOriginalRealModelHold("missing original cognitive Owner")
    try:
        with resident.lock:
            if (
                bridge.inference_lane is not None
                or not bridge.physical.observation_only
                or bridge.physical.active_action_ids
                or tuple(sorted(bridge.sessions)) != ("A", "B")
            ):
                raise R23HOriginalRealModelHold(
                    "original A/B observation-only Bridge required, without GPU lane"
                )
            a = resident.read_rejoined_l1_source_compatibility_cpu(
                bridge=bridge, self_id="A",
            )
            b = resident.read_rejoined_l1_source_compatibility_cpu(
                bridge=bridge, self_id="B",
            )
            if (
                type(a) is not R23BOriginalL1SourceComparison
                or type(b) is not R23BOriginalL1SourceComparison
                or a.source_pair_revision != b.source_pair_revision
                or a.current.source_revision_refs[0] == ""
                or b.current.source_revision_refs[0] == ""
                or getattr(resident, "_normal_second_rejoin_cut", None) is not None
                or resident.owners["A"] is not bridge.owners["A"]
                or resident.owners["B"] is not bridge.owners["B"]
            ):
                raise R23HOriginalRealModelHold(
                    "first A reJOIN and continuing B Source mismatch"
                )
            before = (
                resident.current_scope("A"),
                resident.current_scope("B"),
                a, b,
            )
            if (
                resident.read_rejoined_l1_source_compatibility_cpu(
                    bridge=bridge, self_id="A",
                ) != a
                or resident.read_rejoined_l1_source_compatibility_cpu(
                    bridge=bridge, self_id="B",
                ) != b
            ):
                raise R23HOriginalRealModelHold(
                    "Source changed while reading first reJOIN"
                )
            return R23HOriginalRealSource(
                self_id=self_id,
                a_native=before[0][1],
                b_native=before[1][1],
                a_scope=before[0],
                b_scope=before[1],
                source_pair_revision=a.source_pair_revision,
                request_question_ref=(a if self_id == "A" else b).original_inquiry.question_ref,
            )
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        raise R23HOriginalRealModelHold(
            "original first-reJOIN source not currently qualified"
        ) from exc


def inspect_r23h_original_real_model(
    *, bridge: OwnedResidentPhysicalBridge, self_id: str,
    gguf: Path, llama_pid: int, model_alias: str, endpoint: str,
) -> tuple[R23HOriginalRealSource, Stage24gModelGateReceipt]:
    """Read only: real Original source and PID-owned, GGUF-pinned idle slot."""
    source = inspect_r23h_original_live_source(bridge=bridge, self_id=self_id)
    gate = verify_stage24g_model_gate(
        gguf_path=gguf, llama_pid=llama_pid, model_alias=model_alias,
        llama_endpoint=endpoint, systemone_endpoint=endpoint,
    )
    if (
        type(gate) is not Stage24gModelGateReceipt
        or gate.llama_pid != llama_pid
        or gate.model_alias != model_alias
        or gate.slot_count != 1 or gate.slot_id != 0
    ):
        raise R23HOriginalRealModelHold("actual original single-slot model not proven")
    if inspect_r23h_original_live_source(bridge=bridge, self_id=self_id) != source:
        raise R23HOriginalRealModelHold("Original Source moved during model gate")
    return source, gate


async def run_r23h_original_real_question_once(
    *, bridge: OwnedResidentPhysicalBridge, self_id: str,
    gguf: Path, llama_pid: int, model_alias: str, endpoint: str,
    evidence_dir: Path, real_model_post_grant: bool = False,
    model_wait_s: float = 60.0,
) -> R23HOriginalRealModelReadback:
    """One real POST, no Question commit, no World start, no automatic retry.

    CALLER OWNS the existing real Paper/Native Bridge and remains responsible
    for its normal A/B logout, model retirement and independent evidence audit.
    Real Source changes while Gemma runs must become HOLD/fence, not a forged
    terminal CURRENT. Even ADOPT is read-only in this first qualification.
    """
    if (
        real_model_post_grant is not True
        or type(model_wait_s) not in (float, int)
        or not 0 < model_wait_s <= 75
        or not isinstance(evidence_dir, Path)
        or evidence_dir.exists() or evidence_dir.is_symlink()
        or not evidence_dir.parent.is_dir()
        or any(p.is_symlink() for p in (evidence_dir.parent, *evidence_dir.parent.parents))
    ):
        raise R23HOriginalRealModelHold(
            "explicit one-shot model grant and fresh evidence root required"
        )
    resident = bridge.cognitive_work
    # Evidence must never be nested in a live Owner's checkpoint or
    # existing original World/Paper execution root. It only captures bytes.
    target = evidence_dir.absolute()
    forbidden = [
        bridge.owners[sid].files.self_root.resolve(strict=True)
        for sid in ("A", "B")
    ]
    forbidden.append(bridge.paper.server_dir.resolve(strict=True))
    if any(
        target == root or root in target.parents or target in root.parents
        for root in forbidden
    ):
        raise R23HOriginalRealModelHold(
            "raw model evidence root overlaps original Owner or Paper World"
        )
    source, gate = inspect_r23h_original_real_model(
        bridge=bridge, self_id=self_id, gguf=gguf,
        llama_pid=llama_pid, model_alias=model_alias, endpoint=endpoint,
    )
    with resident.lock:
        # Freeze genuine Original Owner work ONLY before GPU attachment.
        turn = resident.prepare_rejoined_original_l1_request_cpu(
            bridge=bridge, self_id=self_id,
        )
        if (
            type(turn) is not R23CFrozenOriginalRejoinL1
            or turn.source.source_pair_revision != source.source_pair_revision
            or turn.source.original_inquiry.question_ref != source.request_question_ref
            or resident.current_scope(self_id)
            != (source.a_scope if self_id == "A" else source.b_scope)
        ):
            raise R23HOriginalRealModelHold(
                "original frozen Question does not match current reJOIN"
            )
        if inspect_r23h_original_live_source(bridge=bridge, self_id=self_id) != source:
            raise R23HOriginalRealModelHold("Source moved before real model lane attach")
        evidence_dir.mkdir(mode=0o700)
        raw_dir = evidence_dir / "original-question-model-http"
        raw_dir.mkdir(mode=0o700)
        _write_bytes_new(
            evidence_dir / "model-gate.json",
            (json.dumps(asdict(gate), sort_keys=True, indent=2) + "\n").encode(),
        )
        provider = OriginalRawBoundedLlamaProvider(
            endpoint=endpoint, model=model_alias,
            raw_dir=raw_dir, timeout=min(45.0, model_wait_s),
        )
        witness = LlamaCppSingleSlotWitness(
            provider=provider, backend_ref=f"r23h-original-pid-{llama_pid}",
        )
        witness.require_idle()
        lane = ResidentLlamaInferenceLane(
            provider=provider, cognitive_work=resident, witness=witness,
        )
        bridge.attach_observation_only_bounded_l1(lane)

    # The physical World continues moving independently of this await.
    # The original R2-3d result fence must reject naturally stale Paper
    # source; no silent snapshot freezing or client-retry occurs.
    report: dict[str, object] = {
        "classification": "R23H_REAL_ORIGINAL_MODEL_HOLD",
        "schema": 1,
        "self_id": self_id,
        "original_first_rejoin_source": asdict(source),
        "model_pid": llama_pid,
        "model_alias": model_alias,
        "original_request_id": turn.request.request_id,
        "original_work_ref": turn.work_ref,
        "real_world_created_by_this_call": False,
        "product_l1_input_switched": False,
        "question_adopted": False,
        "memory_written": False,
        "physical_issue_authorized": False,
    }
    try:
        outcome = await resident.issue_rejoined_original_question_once_dev(
            bridge=bridge, lane=lane, turn=turn, timeout_s=model_wait_s,
        )
        if (
            provider.attempted != 1 or provider.completed != 1
            or outcome.readback.ticket is not outcome.ticket
            or outcome.ticket.purpose != "original_rejoin_question"
        ):
            raise R23HOriginalRealModelHold(
                "actual original one-shot model work not singular and terminal"
            )
        idle = lane.require_world_idle()
        if idle.is_processing or idle.n_slots != 1:
            raise R23HOriginalRealModelHold("backend not terminal idle")
        report["original_gpu_ticket"] = {
            "self_id": outcome.ticket.self_id,
            "work_ref": outcome.ticket.work_ref,
            "request_id": outcome.ticket.request_id,
            "purpose": outcome.ticket.purpose,
            "self_epoch": outcome.ticket.self_epoch,
            "native_session_id": outcome.ticket.native_session_id,
            "world_epoch": outcome.ticket.world_epoch,
            "backend_ref": outcome.ticket.backend_ref,
        }
        report["selection"] = outcome.selection
        report["backend_terminal_idle"] = asdict(idle)
        report["classification"] = "R23H_REAL_MODEL_CAPTURED_INDEPENDENT_AUDIT_PENDING"
        return R23HOriginalRealModelReadback(
            self_id=self_id,
            ticket=outcome.ticket,
            selection=outcome.selection,
            model_post_attempted=provider.attempted,
            model_post_completed=provider.completed,
            raw_http_entity_bodies_captured=True,
            backend_terminal_idle=True,
            source=source,
            report_path=evidence_dir / "r23h-original-real-model-report.json",
        )
    except BaseException as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
        # The original issuer fences its submitted job on timeout/source
        # mismatch. If this runner fails after terminal read, keep the lane
        # blocked until operator retirement rather than reusing its ticket.
        with resident.lock:
            lane.fence_self(self_id)
            resident.fence_self(self_id)
        raise
    finally:
        report["model_post_attempted"] = provider.attempted
        report["model_post_completed"] = provider.completed
        report["raw_http_evidence_sha256"] = {
            p.name: file_sha256(p)
            for p in sorted(raw_dir.iterdir()) if p.is_file()
        }
        _write_bytes_new(
            evidence_dir / "r23h-original-real-model-report.json",
            (json.dumps(report, sort_keys=True, indent=2) + "\n").encode(),
        )
