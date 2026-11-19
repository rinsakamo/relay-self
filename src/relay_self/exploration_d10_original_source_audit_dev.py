"""D10 independent SECOND-PROCESS readback of original D9 source bytes.

No filesystem writes, model calls, Paper spawn, native JOIN, GPU lease, or
Action issuance. This checks immutable historical file inventory, the original
typed 3D Paper World + A/B cognition/Owner/WAL, B's recorded A0/A1/B0 lineage,
three owned native JSONL streams, original Paper events, and the ONE captured
Jev/SystemOne HTTP request/response bytes with its genuinely chosen number.
A signed execution provenance cannot be inferred from self-reported booleans:
the result is SOURCE_BYTES_CORRELATED_DEV only until actual local process
ownership has been separately witnessed.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from adapters.llama_cpp.relay_engine import parse_llama_cpp_jev_decision
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
    parse_mineflayer_line,
)
from relay_self.common_io import ScopeRef
from relay_self.exploration_continuity_dev import AttemptPhase, open_question_refs
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.relay_engine import BoundedChoice, BoundedChoiceRequest
from relay_self.resident_paper_presence_join_dev import (
    parse_owned_paper_resident_trace,
    require_pre_inference_resident_presence,
)
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28c1_inert_restore_dev import inspect_stage28c_source
from relay_self.stage28c2b_historical_native_sessions_dev import (
    inspect_original_stage28b_native_sessions,
)


class D10OriginalAuditHold(RuntimeError):
    """Original D9 World/Body/Model/Owner evidence is incomplete or changed."""


@dataclass(frozen=True, slots=True)
class D10OriginalAuditReceipt:
    original_evidence_manifest_sha256: str
    original_evidence_files: int
    original_report_sha256: str
    generation_id: str
    world_id: str
    source_branch_id: str
    committed_sha256: str
    original_a_native_first: str
    original_a_native_rejoined: str
    original_b_native: str
    native_raw_sha256: tuple[tuple[str, str], ...]
    original_paper_stdout_sha256: str
    original_paper_preinference_sha256: str
    original_paper_boot_id: str
    original_model_request_sha256: str
    original_model_response_sha256: str
    original_model_preflight_sha256: str
    original_model_choice_id: str
    original_model_request_id: str
    original_question_refs: tuple[tuple[str, tuple[str, ...]], ...]
    original_attempt_refs: tuple[tuple[str, tuple[str, ...]], ...]
    independent_source_classification: str = "D10_ORIGINAL_BYTES_CORRELATED_DEV"
    original_l2_replay_authorized: bool = False
    original_action_replay_authorized: bool = False
    original_real_world_execution_attested: bool = False


def _sha(file: Path) -> str:
    if file.is_symlink() or not file.is_file():
        raise D10OriginalAuditHold("source evidence file absent or symlinked")
    h = hashlib.sha256()
    with file.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _json(path: Path) -> dict:
    if path.is_symlink():
        raise D10OriginalAuditHold("original JSON evidence symlink")
    data = json.loads(path.read_bytes())
    if type(data) is not dict:
        raise D10OriginalAuditHold("original evidence JSON object required")
    return data


def _native_raw(
    root: Path, report: dict, *,
    native_ids: dict[str, str], request_ids: dict[str, str],
) -> tuple[tuple[str, str], ...]:
    declared = report.get("d10_original_native_sources")
    if type(declared) is not dict or set(declared) != {"A0", "A1", "B0"}:
        raise D10OriginalAuditHold("three distinct original native raw sources missing")
    digests: list[tuple[str, str]] = []
    pids: set[int] = set()
    for name in ("A0", "A1", "B0"):
        entry = declared[name]
        path = root / ("D10-original-native-" + name + ".jsonl")
        if (
            type(entry) is not dict
            or entry.get("source_name") != path.name
            or entry.get("session_id") != native_ids[name]
            or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256")))
            or type(entry.get("bytes")) is not int
            or entry["bytes"] <= 0
            or type(entry.get("pid")) is not int or entry["pid"] <= 1
            or entry["pid"] in pids
            or path.is_symlink()
            or _sha(path) != entry["sha256"]
            or path.stat().st_size != entry["bytes"]
        ):
            raise D10OriginalAuditHold("raw original native ID/PID/SHA mismatch")
        pids.add(entry["pid"])
        messages = [
            parse_mineflayer_line(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        if (
            not messages
            or any(x.session_id != native_ids[name] for x in messages)
            or any(isinstance(x, MineflayerEffectResult) for x in messages)
            or any(
                b.seq <= a.seq for a, b in zip(messages, messages[1:])
            )
        ):
            raise D10OriginalAuditHold("foreign native response or effect in source")
        probes = [
            x for x in messages
            if isinstance(x, MineflayerObservation) and x.kind == "probe"
        ]
        if (
            not probes
            or name in request_ids and not any(
                x.request_id == request_ids[name] for x in probes
            )
        ):
            raise D10OriginalAuditHold("original current native probe not in JSONL")
        digests.append((name, entry["sha256"]))
    return tuple(digests)


def audit_d10_original_d9_source(
    evidence_root: Path, generation: Path, *,
    expected_manifest_sha256: str,
    expected_files: int,
    expected_world_id: str,
    expected_source_branch_id: str,
    expected_committed_sha256: str,
) -> D10OriginalAuditReceipt:
    """Verify untrusted immutable evidence; never rely on report success alone."""
    root, generation = Path(evidence_root), Path(generation)
    if (
        root.is_symlink() or not root.is_dir()
        or type(expected_files) is not int or expected_files < 1
        or any(not isinstance(x, str) or not x for x in (
            expected_manifest_sha256, expected_world_id,
            expected_source_branch_id, expected_committed_sha256,
        ))
        or generation.parent.parent.resolve() != root.resolve()
        or generation.is_symlink()
    ):
        raise D10OriginalAuditHold("source-root, generation and pins required")
    try:
        historical = inspect_original_stage28b_native_sessions(
            root, generation,
            expected_manifest_sha256=expected_manifest_sha256,
            expected_files=expected_files,
            expected_report_classification=(
                "REAL_D9_SOURCE_A_B_TYPED_CUT_CAPTURED_INDEPENDENT_AUDIT_PENDING"
            ),
        )
        world = inspect_stage28c_source(
            generation, expected_world_id=expected_world_id,
            expected_source_branch_id=expected_source_branch_id,
            expected_generation_id=generation.name,
        )
        if world.committed_sha256 != expected_committed_sha256:
            raise D10OriginalAuditHold("old/foreign typed COMMITTED pin")
        report_file = root / "resident-presence-result.json"
        report = _json(report_file)
        trial = report["steps"][0]
        a = _json(root / "D9-A-question-only.json")
        b = _json(root / "D9-B-original-bounded-L1.json")
        outcomes = report.get("d9_original_a_b")
        if (
            type(outcomes) is not list or len(outcomes) != 2
            or outcomes != [a, b]
            or trial.get("d9_original_a_b") != outcomes
            or report.get("world_uuid") != world.world_id
            or trial.get("world_uuid") != world.world_id
            or report.get("real_world_permission") is not True
            or report.get("cleanup_uncertain")
            or report.get("d9_actual_model_post_count") != 1
            or report.get("d9_previous_l2_model_post_count") != 0
            or report.get("real_b_physical_action") is not False
            or report.get("real_b_physical_wal_outcome") is not False
            or trial.get("b_actual_physical_action") is not False
            or trial.get("b_physical_wal_outcome") is not False
            or trial.get("real_peer_transport_executed") is not False
            or trial.get("typed_world_self_generation") != str(generation)
            or trial.get("typed_world_self_roster") != ["A", "B"]
            or trial.get("typed_world_self_cut_validated") is not True
            or a.get("self_id") != "A"
            or b.get("self_id") != "B"
            or a.get("l1_model_invoked") is not False
            or b.get("l1_model_invoked") is not True
            or a.get("l2_model_invoked") is not False
            or b.get("l2_model_invoked") is not False
            or a.get("physical_action_issue_authorized") is not False
            or b.get("physical_action_issue_authorized") is not False
            or b.get("selected_status") != "ESCALATE_L2"
            or b.get("model_status") != "resolved"
            or b.get("model_choice_id") != "1"
            or not b.get("attempted_l2_ref")
        ):
            raise D10OriginalAuditHold("original D9 source report/model selection inconsistent")
        if (
            a.get("old_native_session_id") != historical.original_a_rejoined
            or b.get("old_native_session_id") != historical.original_b_initial
            or trial.get("a_original_native_session")
            != historical.original_a_initial
            or trial.get("b_original_native_session")
            != historical.original_b_initial
            or trial.get("a_relogin_evidence", {}).get("native_session_id")
            != historical.original_a_rejoined
        ):
            raise D10OriginalAuditHold("D9 real Native lifetime/owner differs")
        cut_by_self = {
            cut.self_id: cut for cut in verify_typed_generation(generation)
        }
        questions: list[tuple[str, tuple[str, ...]]] = []
        attempts: list[tuple[str, tuple[str, ...]]] = []
        for sid, outcome in (("A", a), ("B", b)):
            cut = cut_by_self[sid]
            cognition = load_persistent_cognition(
                generation / "selves" / sid / "cognition.json"
            )
            PhysicalActionJournal.restore(
                generation / "selves" / sid / "physical-wal.json",
                self_id=sid,
            ).require_clear()
            if (
                cut.former_native_session_id != outcome["old_native_session_id"]
                or cognition.identity.self_id != sid
                or cognition.exploration_continuity is None
                or outcome["question_ref"] not in open_question_refs(
                    cognition, expected_self_id=sid,
                )
                or not set(open_question_refs(
                    cognition, expected_self_id=sid,
                )).issubset(cut.pending_question_refs)
            ):
                raise D10OriginalAuditHold("original Self typed Question/Owner/WAL mismatch")
            state = cognition.exploration_continuity
            a_refs = tuple(x.attempt_ref for x in state.attempts)
            if sid == "B":
                if (
                    a_refs != (b["attempted_l2_ref"],)
                    or len(state.attempts) != 1
                    or state.attempts[0].phase is not AttemptPhase.RESERVED
                    or state.attempts[0].question_ref != b["question_ref"]
                ):
                    raise D10OriginalAuditHold("original B selection did not cause RESERVED")
            elif a_refs:
                raise D10OriginalAuditHold("A question-only may not have model history")
            questions.append((sid, open_question_refs(cognition, expected_self_id=sid)))
            attempts.append((sid, a_refs))
        native = _native_raw(
            root, report,
            native_ids={
                "A0": historical.original_a_initial,
                "A1": historical.original_a_rejoined,
                "B0": historical.original_b_initial,
            },
            request_ids={
                "A1": a["native_probe_request_id"],
                "B0": b["native_probe_request_id"],
            },
        )
        # Independently parse the actual owned Paper stdout bytes, not a
        # synthetic outcome boolean or the pre-inference summary text.
        session = trial.get("paper_session_id")
        if type(session) is not str or not session.startswith("paper-owned-"):
            raise D10OriginalAuditHold("owned Paper session not retained")
        original_log = root / (session + ".log")
        pre_log = root / "d9-pre-inference-paper-resident-owned.log"
        raw_paper = original_log.read_bytes()
        before = pre_log.read_bytes()
        if (
            original_log.is_symlink() or pre_log.is_symlink()
            or not raw_paper.startswith(before)
            or b"Stopping server" not in raw_paper[len(before):]
            or b"Saved the game" not in raw_paper[len(before):]
        ):
            raise D10OriginalAuditHold("original Paper stop/save/raw source missing")
        pre = parse_owned_paper_resident_trace(
            owned_paper_session_id=session, expected_world_uuid=world.world_id,
            owned_paper_log=before,
            log_ref="d10-pre:" + session + ":sha256:" + _sha(pre_log),
        )
        require_pre_inference_resident_presence(
            pre, a_name="RelayA", b_name="RelayB",
        )
        full = parse_owned_paper_resident_trace(
            owned_paper_session_id=session, expected_world_uuid=world.world_id,
            owned_paper_log=raw_paper,
            log_ref="d10-original:" + session + ":sha256:" + _sha(original_log),
        )
        if full.boot_id != trial.get("paper_boot"):
            raise D10OriginalAuditHold("actual Paper boot identity changed")
        paper_actors: set[str] = set()
        for sid in ("A", "B"):
            rows = [event for event in full.events if event.name == "Relay" + sid]
            expected_events = 2 if sid == "A" else 1
            if (
                len([e for e in rows if e.event == "JOIN"]) != expected_events
                or len([e for e in rows if e.event == "QUIT"]) != expected_events
                or len({e.actor_uuid for e in rows}) != 1
                or not any(e.event == "PRESENT" for e in rows)
                or rows[0].event != "JOIN" or rows[-1].event != "QUIT"
            ):
                raise D10OriginalAuditHold("Paper A/B distinct JOIN/QUIT/PRESENT missing")
            paper_actors.add(rows[0].actor_uuid)
        if len(paper_actors) != 2:
            raise D10OriginalAuditHold("Paper A/B actor UUID collision")
        # The old native session's lifecycle is not numerically comparable
        # to Paper ticks; use only each stream's ordered own source.
        if (
            trial.get("a_actor_uuid") not in paper_actors
            or trial.get("b_actor_uuid") not in paper_actors
        ):
            raise D10OriginalAuditHold("Paper owner actors differ")
        model_dir = root / "stage24g-systemone-http"
        model_request = model_dir / "systemone-request-body.bin"
        model_response = model_dir / "systemone-response-body.bin"
        manifest = _json(model_dir / "systemone-http-evidence.json")
        if (
            manifest.get("capture_type")
            != "urllib_http_entity_bodies_not_wire_headers"
            or manifest.get("http_status") != 200
            or manifest.get("request_body_sha256") != _sha(model_request)
            or manifest.get("response_body_sha256") != _sha(model_response)
            or manifest.get("request_body_bytes") != model_request.stat().st_size
            or manifest.get("response_body_bytes") != model_response.stat().st_size
            or report.get("model_http_request_sha256") != _sha(model_request)
            or report.get("model_http_response_sha256") != _sha(model_response)
        ):
            raise D10OriginalAuditHold("original Jev HTTP entity-body capture changed")
        request = json.loads(model_request.read_bytes())
        response = json.loads(model_response.read_bytes())
        model_preflight = root / "stage24g-model-preworld.json"
        preflight = _json(model_preflight)
        criteria = request["questions"]["decision"]["criteria"]
        if (
            request.get("model") != preflight.get("model_alias")
            or preflight.get("slot_count") != 1
            or preflight.get("slot_id") != 0
            or not preflight.get("gguf_sha256")
            or request["state"]["request_id"] != b["l1_request_id"]
            or set(criteria) != {
                "1", "2", "__relay_self_unresolved__",
            }
            or criteria["1"] != "ESCALATE_L2"
            or criteria["2"] != "DEFER"
            or b.get("model_choice_id") != "1"
        ):
            raise D10OriginalAuditHold("Jev model request not original bounded choice")
        parsed = parse_llama_cpp_jev_decision(
            response,
            request=BoundedChoiceRequest(
                b["l1_request_id"], "original D9 finite options",
                None, "GOAL_SKILL_TARGET",
                (BoundedChoice("1", "ESCALATE_L2"),
                 BoundedChoice("2", "DEFER")),
                (), think_allowed=False,
            ),
        )
        if (
            parsed.choice_id != "1"
            or parsed.status.value != b["model_status"]
            or parsed.call_facts.prompt_tokens != b["requested_prompt_tokens"]
            or parsed.call_facts.completion_tokens != b["completion_tokens"]
            or parsed.call_facts.finish_reason != b["finish_reason"]
        ):
            raise D10OriginalAuditHold("model raw choice differs from Owner record")
    except D10OriginalAuditHold:
        raise
    except (OSError, ValueError, TypeError, KeyError, RuntimeError,
            UnicodeError, IndexError) as exc:
        raise D10OriginalAuditHold("original D9 raw Paper/Native/Model evidence HOLD") from exc

    return D10OriginalAuditReceipt(
        expected_manifest_sha256, expected_files, _sha(report_file),
        world.generation_id, world.world_id, world.source_branch_id,
        expected_committed_sha256, historical.original_a_initial,
        historical.original_a_rejoined, historical.original_b_initial,
        native, _sha(original_log), _sha(pre_log), full.boot_id,
        _sha(model_request), _sha(model_response), _sha(model_preflight),
        "1", b["l1_request_id"], tuple(questions), tuple(attempts),
    )
