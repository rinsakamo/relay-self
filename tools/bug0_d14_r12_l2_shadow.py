"""R12 DEV: source-audited R11 natural experience -> optional L2 shadow Skill.

Post-World only. This module cannot issue S49 Actions, alter the World,
write the existing Memory/Learning/Habit owners, or install a Skill.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d14_natural_active_post import audit_active
from tools.bug0_d14_r11_day_foraging_post import inspect_r11_natural_day

MAX_L2_EVENTS = 48
L2_SKILL_STEPS = ("MOVE_AWAY", "ATTACK", "EAT", "REST", "WAIT")
L2_CHOICES = ("CONTINUE", "TRY_SOMETHING", "PROPOSE_SKILL", "OBSERVE", "DEFER")


class R12Rejected(ValueError):
    """The input evidence, model envelope or grant was not admissible."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _require_str(value: object, maximum: int) -> bool:
    return type(value) is str and 0 < len(value) <= maximum


def _event_view(row: dict[str, Any], kind: str, world: str,
                session: str) -> dict[str, Any]:
    """No Paper-global loot, hidden physics or model-invented Outcome."""
    if kind == "LIFE_DECISION":
        fields = (
            "cycle", "native_seq", "native_request_id", "intent_id",
            "selected", "preferred", "fallback", "reason", "health", "food",
            "zombies", "rotten_count", "r11_native_dropped_item_candidates",
            "r11_native_rotten_inventory_delta_since_last_decision",
            "action_id",
        )
        index = row.get("native_seq")
    else:
        fields = (
            "action_id", "kind", "terminal", "native_before_seq",
            "native_admitted_seq", "original_s51_food_before",
            "original_s51_food_after", "original_s51_inventory_before",
            "original_s51_inventory_after", "native_target_hurt_event_seen",
            "damage_attested", "zombie_kill_attested",
        )
        index = row.get("action_id")
    if (not isinstance(row, dict)
            or row.get("session_id") != session
            or index is None):
        raise R12Rejected("NATIVE_EVENT_SOURCE_UNBOUND")
    view = {name: row[name] for name in fields if name in row}
    return {
        "experience_id": f"r12:{world}:{session}:{kind}:{index}",
        "event_kind": kind,
        "epistemic_status": (
            "S49_S16_OUTCOME_NOT_PHYSICAL_GOAL_PROOF"
            if kind == "LIFE_ACTION" else "NATIVE_SELF_VIEW_NOT_PAPER_GLOBAL"
        ),
        "observation": view,
    }


def project_r11(*, report_bytes: bytes, paper_bytes: bytes,
                journal_bytes: bytes, nonmotion_path: Path,
                motion_path: Path) -> dict[str, Any]:
    """Re-run BOTH independent source audits; never trust a saved PASS flag."""
    originals = {
        "report": report_bytes, "paper": paper_bytes, "journal": journal_bytes,
        "nonmotion": nonmotion_path.read_bytes(),
        "motion": motion_path.read_bytes(),
    }
    try:
        report = json.loads(report_bytes)
        paper = paper_bytes.decode("utf-8")
        journal = journal_bytes.decode("utf-8")
        fence = OriginalS49NonMotionFence.restore(
            nonmotion_path, self_id="s49-original-self",
        )
        motion = OriginalS49PhysicalFence.restore(
            motion_path, self_id="s49-original-self",
        )
        active = audit_active(
            report, paper, journal, fence,
            original_sha=_sha(paper_bytes), derivative_sha=_sha(journal_bytes),
            motion_fence=motion,
        )
        day = inspect_r11_natural_day(paper, report, active)
    except (ValueError, TypeError, KeyError, UnicodeError, OSError,
            AssertionError) as exc:
        raise R12Rejected("R11_ORIGINAL_SOURCE_AUDIT_REJECTED") from exc
    if (active.get("status") != "PASS_DEV"
            or active.get("r11_natural_day_opt_in") is not True
            or day.get("status") != "PAPER_SOURCE_ONLY"
            or report.get("c1_intent_experiences") != 0
            or report.get("model_posts") != 0
            or report.get("learning_updates") != 0
            or report.get("skill_installs") != 0):
        raise R12Rejected("R11_NOT_SOURCE_QUALIFIED_FOR_L2_VIEW")
    world = active["world_uuid"]
    session = report["original_s49_session_id"]
    events: list[dict[str, Any]] = []
    for raw_line in journal.splitlines():
        row = json.loads(raw_line)
        kind = row.get("kind")
        if kind in ("LIFE_DECISION", "LIFE_ACTION"):
            source = row.get("native_observation")
            if not isinstance(source, dict):
                raise R12Rejected("NATIVE_EVENT_MISSING")
            events.append(_event_view(source, kind, world, session))
    if len(events) != active["life_decisions"] + active["original_s49_actions"]:
        raise R12Rejected("L2_SOURCE_EVENT_COUNT_MISMATCH")
    if len({event["experience_id"] for event in events}) != len(events):
        raise R12Rejected("L2_DUPLICATED_EXPERIENCE_ID")
    if any(_sha(path.read_bytes()) != _sha(originals[key]) for path, key in (
        (nonmotion_path, "nonmotion"), (motion_path, "motion"),
    )):
        raise R12Rejected("PHYSICAL_SOURCE_CHANGED_DURING_AUDIT")
    # Paper's omniscient drop/death/pickup evidence is excluded from the L2
    # present. Native inventory observations may be uncertain or incomplete.
    context = {
        "world_uuid": world,
        "native_session_id": session,
        "world_is_terminated": True,
        "world_end_reason": active["eventual_reason"],
        "goal": "stay alive while exploring and responding to observed needs",
        "experience_events": events[-MAX_L2_EVENTS:],
        "omitted_older_events": max(0, len(events) - MAX_L2_EVENTS),
        "action_authority": "NONE_POST_WORLD_READ_ONLY",
        "unknowns": [
            "Paper item provenance is not native item type knowledge",
            "S16 ATTACK outcome does not prove a zombie kill",
            "post-MOVE physical STOP is not attested",
        ],
    }
    return {
        "classification": "DEV_R12_AUDITED_NATURAL_EXPERIENCE_VIEW",
        "source_sha256": {key: _sha(raw) for key, raw in originals.items()},
        "source_audit": active["classification"],
        "paper_source_only_summary": {
            "full_day_survived": day["full_day_horizon_survived"],
            "pickup_events_not_inventory_proof":
                day["paper_pickup_event_count_not_inventory_proof"],
        },
        "total_source_events": len(events),
        "l2_context": context,
        "model_posts": 0,
        "s49_actions": 0,
        "memory_writes": 0,
        "learning_updates": 0,
        "skill_installs": 0,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def l2_schema() -> dict[str, Any]:
    step = {"type": "string", "enum": list(L2_SKILL_STEPS)}
    skill = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "name": {"type": "string"},
            "cue": {"type": "string"},
            "steps": {"type": "array", "items": step},
            "max_actions": {"type": "integer", "enum": list(range(1, 11))},
            "stop_condition": {"type": "string", "enum": ["GOAL_OR_SOURCE_CHANGE"]},
            "on_failure": {"type": "string", "enum": ["ESCALATE"]},
        },
        "required": ["name", "cue", "steps", "max_actions",
                     "stop_condition", "on_failure"],
    }
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "decision": {"type": "string", "enum": list(L2_CHOICES)},
            "reason": {"type": "string"},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
            "skill": {"anyOf": [skill, {"type": "null"}]},
        },
        "required": ["decision", "reason", "evidence_ids", "skill"],
    }


def validate_l2_choice(choice: object, context: dict[str, Any]) -> dict[str, Any]:
    """Independent semantic validation; JSON grammar acceptance is insufficient."""
    if type(choice) is not dict or set(choice) != {
        "decision", "reason", "evidence_ids", "skill",
    }:
        raise R12Rejected("L2_CHOICE_SHAPE_INVALID")
    if (choice["decision"] not in L2_CHOICES
            or not _require_str(choice["reason"], 900)
            or type(choice["evidence_ids"]) is not list
            or len(choice["evidence_ids"]) > MAX_L2_EVENTS
            or any(type(i) is not str for i in choice["evidence_ids"])):
        raise R12Rejected("L2_CHOICE_SEMANTICS_INVALID")
    allowed = {x["experience_id"] for x in context["experience_events"]}
    ids = choice["evidence_ids"]
    if len(ids) != len(set(ids)) or not set(ids) <= allowed:
        raise R12Rejected("L2_FABRICATED_OR_DUPLICATE_EVIDENCE")
    skill = choice["skill"]
    if choice["decision"] != "PROPOSE_SKILL":
        if skill is not None:
            raise R12Rejected("L2_NON_SKILL_DECISION_HAS_SKILL")
        return choice
    if (not ids or type(skill) is not dict or set(skill) != {
            "name", "cue", "steps", "max_actions", "stop_condition", "on_failure",
    } or not _require_str(skill["name"], 80)
            or not _require_str(skill["cue"], 240)
            or type(skill["steps"]) is not list
            or not 1 <= len(skill["steps"]) <= 10
            or any(type(s) is not str or s not in L2_SKILL_STEPS
                   for s in skill["steps"])
            or type(skill["max_actions"]) is not int
            or not len(skill["steps"]) <= skill["max_actions"] <= 10
            or skill["stop_condition"] != "GOAL_OR_SOURCE_CHANGE"
            or skill["on_failure"] != "ESCALATE"):
        raise R12Rejected("L2_SHADOW_SKILL_INVALID")
    return choice


def _local_endpoint(endpoint: str) -> None:
    parsed = urlsplit(endpoint)
    if (parsed.scheme != "http"
            or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            or parsed.path != "/v1/chat/completions"
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.port is None):
        raise R12Rejected("ONLY_EXPLICIT_LOCAL_LLAMACPP_ENDPOINT_ALLOWED")


def propose_shadow(projection: dict[str, Any], *, endpoint: str,
                   model: str, record_dir: Path, timeout: float = 120.0,
                   transport: Any = None,
                   source_still_current: Any = None) -> dict[str, Any]:
    if not _require_str(model, 200) or not 1 <= timeout <= 300:
        raise R12Rejected("MODEL_OR_TIMEOUT_INVALID")
    _local_endpoint(endpoint)
    context = projection["l2_context"]
    if (projection["classification"] !=
            "DEV_R12_AUDITED_NATURAL_EXPERIENCE_VIEW"
            or context["world_is_terminated"] is not True
            or context["action_authority"] != "NONE_POST_WORLD_READ_ONLY"):
        raise R12Rejected("MODEL_REQUIRES_AUDITED_TERMINATED_WORLD")
    instruction = (
        "You are RelaySelf L2. You may choose to continue an old method, "
        "try something, observe, abstain, or propose an optional conditional "
        "Skill. Do not force a Skill or pretend to know hidden outcomes. "
        "This is a POST-WORLD, READ-ONLY reflection; no physical Action can "
        "be issued and proposed Skills are not installed. Use only supplied "
        "experience_ids. Keep uncertainty honest. Return strict JSON."
    )
    request = {
        "model": model, "temperature": 0, "max_tokens": 512,
        "reasoning_effort": "none", "cache_prompt": False,
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(
                context, ensure_ascii=False, allow_nan=False,
            )},
        ],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "r12_l2_shadow_skill", "strict": True, "schema": l2_schema(),
        }},
    }
    if record_dir.exists():
        raise R12Rejected("RAW_RECORD_DIR_ALREADY_EXISTS")
    record_dir.mkdir(parents=True, mode=0o700)
    req_bytes = _canonical(request)
    (record_dir / "request.raw.json").write_bytes(req_bytes + b"\n")
    # The only network operation. No retry; no native World/S49 path.
    if transport is None:
        def transport(payload: bytes) -> bytes:
            http = Request(
                endpoint, data=payload, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urlopen(http, timeout=timeout) as response:
                return response.read()
    response_bytes = transport(req_bytes)
    if not isinstance(response_bytes, bytes):
        raise R12Rejected("MODEL_RESPONSE_NOT_RAW_BYTES")
    (record_dir / "response.raw.json").write_bytes(response_bytes)
    try:
        wire = json.loads(response_bytes)
        answer = wire["choices"][0]
        if (answer["finish_reason"] != "stop"
                or answer["message"].get("reasoning_content")):
            raise R12Rejected("MODEL_TRUNCATED_OR_REASONING_NOT_DISABLED")
        choice = json.loads(answer["message"]["content"])
        validate_l2_choice(choice, context)
    except (KeyError, TypeError, IndexError, json.JSONDecodeError) as exc:
        raise R12Rejected("MODEL_RESPONSE_UNVERIFIED") from exc
    if source_still_current is not None and not source_still_current():
        raise R12Rejected("ORIGINAL_SOURCE_CHANGED_BEFORE_SHADOW_RETENTION")
    # Durable, non-executable candidate only. The file may later be read by
    # a separate retention experiment; it is NOT an owner Memory/Habit commit.
    result = {
        "classification": "DEV_R12_L2_SHADOW_REFLECTION",
        "world_uuid": context["world_uuid"],
        "native_session_id": context["native_session_id"],
        "experience_source_sha256": projection["source_sha256"],
        "l2_context_sha256": _sha(_canonical(context)),
        "raw_request_sha256": _sha(req_bytes),
        "raw_response_sha256": _sha(response_bytes),
        "decision": choice["decision"],
        "reason": choice["reason"],
        "evidence_ids": choice["evidence_ids"],
        "shadow_skill": choice["skill"],
        "shadow_retention_status": (
            "CANDIDATE_ONLY_NOT_INSTALLED" if choice["skill"] is not None
            else "NO_SKILL_PROPOSED"
        ),
        "real_world_actions": 0, "learning_updates": 0,
        "memory_owner_writes": 0, "habit_updates": 0, "skill_installs": 0,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }
    (record_dir / "shadow_candidate.json").open("x", encoding="utf-8").write(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    return result


def replay_retained_shadow(projection: dict[str, Any],
                           record_dir: Path) -> dict[str, Any]:
    """Independently recheck original Model raw and source before shadow reuse."""
    try:
        original = json.loads((record_dir / "shadow_candidate.json").read_bytes())
        request_raw = (record_dir / "request.raw.json").read_bytes()
        response_raw = (record_dir / "response.raw.json").read_bytes()
        request = json.loads(request_raw)
        response = json.loads(response_raw)
        answer = response["choices"][0]
        choice = json.loads(answer["message"]["content"])
        context = projection["l2_context"]
        validate_l2_choice(choice, context)
        if (
            original["classification"] != "DEV_R12_L2_SHADOW_REFLECTION"
            or original["experience_source_sha256"] != projection["source_sha256"]
            or original["l2_context_sha256"] != _sha(_canonical(context))
            or original["world_uuid"] != context["world_uuid"]
            or original["native_session_id"] != context["native_session_id"]
            or original["raw_request_sha256"] != _sha(
                request_raw.removesuffix(b"\\n")
            )
            or original["raw_response_sha256"] != _sha(response_raw)
            or original["decision"] != choice["decision"]
            or original["reason"] != choice["reason"]
            or original["evidence_ids"] != choice["evidence_ids"]
            or original["shadow_skill"] != choice["skill"]
            or request["response_format"]["json_schema"]["strict"] is not True
            or request["response_format"]["json_schema"]["schema"] != l2_schema()
            or request["reasoning_effort"] != "none"
            or request["messages"][1]["content"] != json.dumps(
                context, ensure_ascii=False, allow_nan=False,
            )
            or answer["finish_reason"] != "stop"
            or answer["message"].get("reasoning_content")
            or original["real_world_actions"] != 0
            or original["learning_updates"] != 0
            or original["memory_owner_writes"] != 0
            or original["habit_updates"] != 0
            or original["skill_installs"] != 0
        ):
            raise R12Rejected("SHADOW_RAW_SOURCE_OR_RETENTION_MISMATCH")
    except (OSError, KeyError, ValueError, TypeError, IndexError) as exc:
        raise R12Rejected("SHADOW_RAW_SOURCE_REPLAY_REJECTED") from exc
    return {
        "classification": "DEV_R12_SHADOW_CANDIDATE_REPLAY_READ_ONLY",
        "source_status": "REPLAY_VERIFIED_NOT_LIVE",
        "shadow_skill": original["shadow_skill"],
        "original_world_uuid": context["world_uuid"],
        "original_native_session_id": context["native_session_id"],
        "authority": "NONE",
        "s49_actions": 0, "model_posts": 0, "memory_writes": 0,
        "learning_updates": 0, "skill_installs": 0,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=("project", "propose", "replay"), required=True)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--server-log", required=True, type=Path)
    p.add_argument("--event-journal", required=True, type=Path)
    p.add_argument("--nonmotion-fence", required=True, type=Path)
    p.add_argument("--motion-fence", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--endpoint")
    p.add_argument("--model")
    p.add_argument("--record-dir", type=Path)
    p.add_argument("--timeout", type=float, default=120.0)
    a = p.parse_args()
    source_paths = [
        a.report, a.server_log, a.event_journal,
        a.nonmotion_fence, a.motion_fence,
    ]
    originals = [path.read_bytes() for path in source_paths]
    projection = project_r11(
        report_bytes=originals[0], paper_bytes=originals[1],
        journal_bytes=originals[2], nonmotion_path=a.nonmotion_fence,
        motion_path=a.motion_fence,
    )
    if any(path.read_bytes() != raw
           for path, raw in zip(source_paths, originals)):
        raise R12Rejected("SOURCE_CHANGED_BEFORE_OUTPUT")
    if a.out.exists() or a.out.parent in {x.parent for x in source_paths}:
        raise R12Rejected("OUTPUT_MUST_BE_EXCLUSIVE_AND_SEPARATE_FROM_ORIGINALS")
    if a.phase == "propose":
        if (a.record_dir is None or a.endpoint is None or a.model is None
                or a.record_dir.parent in {x.parent for x in source_paths}):
            raise R12Rejected("EXPLICIT_INDEPENDENT_MODEL_RECORD_DIR_REQUIRED")
        if os.environ.get("R12_L2_POSTWORLD_DEV_ONLY") != "1":
            raise R12Rejected("NO_EXPLICIT_R12_MODEL_GRANT")
        result = propose_shadow(
            projection, endpoint=a.endpoint, model=a.model,
            record_dir=a.record_dir, timeout=a.timeout,
            source_still_current=lambda: all(
                path.read_bytes() == raw
                for path, raw in zip(source_paths, originals)
            ),
        )
    elif a.phase == "replay":
        if (a.record_dir is None
                or a.record_dir.parent in {x.parent for x in source_paths}):
            raise R12Rejected("REPLAY_RECORD_DIR_REQUIRED")
        result = replay_retained_shadow(projection, a.record_dir)
    else:
        result = projection
    if any(path.read_bytes() != raw
           for path, raw in zip(source_paths, originals)):
        raise R12Rejected("SOURCE_CHANGED_DURING_R12")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True,
                  indent=2, allow_nan=False)
        stream.write("\n")
    print(result["classification"])


if __name__ == "__main__":
    main()
