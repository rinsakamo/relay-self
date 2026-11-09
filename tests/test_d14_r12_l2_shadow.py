"""R12 read-only natural experience -> bounded L2 shadow negative controls."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import bug0_d14_r12_l2_shadow as r12


def _context() -> dict:
    return {
        "world_uuid": "test-world", "native_session_id": "test-session",
        "world_is_terminated": True, "action_authority": "NONE_POST_WORLD_READ_ONLY",
        "experience_events": [
            {"experience_id": "e1", "event_kind": "LIFE_DECISION"},
            {"experience_id": "e2", "event_kind": "LIFE_ACTION"},
        ],
    }


def _skill() -> dict:
    return {
        "name": "guarded retreat", "cue": "zombie nearby, retreat viable",
        "steps": [
            {
                "action": "MOVE_AWAY", "guard": "S49_NATIVE_MOVE_CANDIDATE",
                "binding": "NATIVE_S49_MOVE_SOURCE", "repeat": 1,
                "if_unavailable": "STOP",
            },
            {
                "action": "WAIT", "guard": "ALWAYS", "binding": "NONE",
                "repeat": 1, "if_unavailable": "SKIP",
            },
        ], "max_actions": 3,
        "stop_condition": "GOAL_OR_SOURCE_CHANGE",
        "on_failure": "ESCALATE",
    }


def _choice(skill: bool = True) -> dict:
    return {
        "decision": "PROPOSE_SKILL" if skill else "DEFER",
        "reason": "conditional candidate, outcome not proven",
        "evidence_ids": ["e1", "e2"] if skill else [],
        "skill": _skill() if skill else None,
    }


def test_valid_optional_skill_and_abstention() -> None:
    assert r12.validate_l2_choice(_choice(), _context())["skill"]["max_actions"] == 3
    assert r12.validate_l2_choice(_choice(False), _context())["skill"] is None


@pytest.mark.parametrize("change", [
    lambda c: c.update(evidence_ids=["fabricated"]),
    lambda c: c.update(evidence_ids=["e1", "e1"]),
    lambda c: c.update(extra_authority=True),
    lambda c: c.update(decision="EXECUTE_NOW"),
    lambda c: c.update(reason=""),
    lambda c: c.update(skill=None),
    lambda c: c["skill"].update(steps=["TP_TO_ZOMBIE"]),
    lambda c: c["skill"].update(max_actions=True),
    lambda c: c["skill"].update(max_actions=1),
    lambda c: c["skill"].update(on_failure="RETRY_UNTIL_SUCCESS"),
    lambda c: c["skill"].update(cue=""),
])
def test_wrong_skill_or_fabricated_evidence_fails(change) -> None:
    value = _choice()
    change(value)
    with pytest.raises(r12.R12Rejected):
        r12.validate_l2_choice(value, _context())


def test_no_skill_otherwise() -> None:
    value = _choice()
    value["decision"] = "CONTINUE"
    with pytest.raises(r12.R12Rejected, match="NON_SKILL"):
        r12.validate_l2_choice(value, _context())


@pytest.mark.parametrize("endpoint", [
    "https://127.0.0.1:8080/v1/chat/completions",
    "http://remote.example:8080/v1/chat/completions",
    "http://127.0.0.1:8080/v1/completions",
    "http://127.0.0.1:8080/v1/chat/completions?foo=bar",
    "http://foo@127.0.0.1:8080/v1/chat/completions",
])
def test_nonlocal_or_different_api_rejected(endpoint: str) -> None:
    with pytest.raises(r12.R12Rejected, match="ONLY_EXPLICIT"):
        r12._local_endpoint(endpoint)


def test_postworld_proposal_persists_shadow_not_installed(tmp_path: Path) -> None:
    observed = []
    def fake_transport(payload: bytes) -> bytes:
        request = json.loads(payload)
        observed.append(request)
        assert request["response_format"]["json_schema"]["strict"] is True
        assert request["reasoning_effort"] == "none"
        model_input = json.loads(request["messages"][1]["content"])
        catalog = model_input["action_catalog"]
        assert catalog["scope"] == "POST_WORLD_L2_REFERENCE_ONLY"
        assert [entry["action"] for entry in catalog["entries"]] == [
            "MOVE_AWAY", "ATTACK", "EAT", "REST", "WAIT",
        ]
        assert catalog["no_implicit_action_grant"] is True
        return json.dumps({"choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps(_choice()), "reasoning_content": None},
        }]}).encode()

    projection = {
        "classification": "DEV_R12_AUDITED_NATURAL_EXPERIENCE_VIEW",
        "source_sha256": {"original": "a"},
        "l2_context": _context(),
    }
    out = tmp_path / "raw"
    report = r12.propose_shadow(
        projection, endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="gemma-test", record_dir=out, transport=fake_transport,
    )
    assert len(observed) == 1
    assert report["shadow_retention_status"] == "CANDIDATE_ONLY_NOT_INSTALLED"
    assert report["real_world_actions"] == 0
    assert report["skill_installs"] == 0
    assert report["memory_owner_writes"] == 0
    assert (out / "request.raw.json").exists()
    assert (out / "response.raw.json").exists()
    assert (out / "shadow_candidate.json").exists()
    replay = r12.replay_retained_shadow(projection, out)
    assert replay["classification"] == "DEV_R12_SHADOW_CANDIDATE_REPLAY_READ_ONLY"
    assert replay["authority"] == "NONE"
    assert replay["model_posts"] == 0
    with pytest.raises(r12.R12Rejected, match="ALREADY_EXISTS"):
        r12.propose_shadow(
            projection, endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="gemma-test", record_dir=out, transport=fake_transport,
        )
    assert len(observed) == 1


def test_source_observation_only_and_paper_is_not_l2_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = {
        "original_s49_session_id": "s1",
        "c1_intent_experiences": 0, "model_posts": 0,
        "learning_updates": 0, "skill_installs": 0,
    }
    decision = {
        "session_id": "s1", "native_seq": 30, "native_request_id": "native-30",
        "cycle": 1, "intent_id": "i1", "food": 16, "health": 20,
        "selected": "WAIT", "r11_item_type_from_native": "UNKNOWN",
    }
    action = {
        "session_id": "s1", "action_id": "a1", "kind": "ATTACK",
        "terminal": "outcome", "native_target_hurt_event_seen": False,
        "zombie_kill_attested": False,
    }
    journal = "\n".join(json.dumps({
        "kind": kind, "native_observation": row,
    }) for kind, row in (
        ("LIFE_DECISION", decision), ("LIFE_ACTION", action),
    )).encode()
    n = tmp_path / "nonmotion.json"
    m = tmp_path / "motion.json"
    n.write_bytes(b"nonmotion")
    m.write_bytes(b"motion")
    monkeypatch.setattr(r12.OriginalS49NonMotionFence, "restore",
                        lambda *args, **kwargs: object())
    monkeypatch.setattr(r12.OriginalS49PhysicalFence, "restore",
                        lambda *args, **kwargs: object())
    monkeypatch.setattr(r12, "audit_active", lambda *args, **kwargs: {
        "status": "PASS_DEV",
        "r11_natural_day_opt_in": True,
        "world_uuid": "w1", "eventual_reason": "WORLD_TICK_LIMIT_REACHED",
        "life_decisions": 1, "original_s49_actions": 1,
        "classification": "SOURCE_AUDITED",
    })
    monkeypatch.setattr(r12, "inspect_r11_natural_day", lambda *args: {
        "status": "PAPER_SOURCE_ONLY", "full_day_horizon_survived": True,
        "paper_pickup_event_count_not_inventory_proof": 11,
    })
    result = r12.project_r11(
        report_bytes=json.dumps(report).encode(),
        paper_bytes=b"PAPER_OMNISCIENT_ROTTEN_FLESH_LOCATIONS",
        journal_bytes=journal, nonmotion_path=n, motion_path=m,
    )
    assert result["total_source_events"] == 2
    context = result["l2_context"]
    assert context["action_authority"] == "NONE_POST_WORLD_READ_ONLY"
    assert "PAPER_OMNISCIENT" not in json.dumps(context)
    assert "11" not in json.dumps(context)
    assert context["experience_events"][-1]["epistemic_status"] == (
        "S49_S16_OUTCOME_NOT_PHYSICAL_GOAL_PROOF"
    )


def test_independent_source_audit_failure_never_becomes_experience(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    n, m = tmp_path / "nonmotion", tmp_path / "motion"
    n.write_bytes(b"n")
    m.write_bytes(b"m")
    monkeypatch.setattr(r12.OriginalS49NonMotionFence, "restore",
                        lambda *args, **kwargs: object())
    monkeypatch.setattr(r12.OriginalS49PhysicalFence, "restore",
                        lambda *args, **kwargs: object())
    def refuse(*args, **kwargs):
        raise ValueError("FORGED_ORIGINAL")
    monkeypatch.setattr(r12, "audit_active", refuse)
    with pytest.raises(r12.R12Rejected, match="R11_ORIGINAL_SOURCE_AUDIT"):
        r12.project_r11(
            report_bytes=b"{}", paper_bytes=b"paper", journal_bytes=b"{}",
            nonmotion_path=n, motion_path=m,
        )


def test_invalid_l2_response_is_preserved_but_not_retained(
    tmp_path: Path,
) -> None:
    projection = {
        "classification": "DEV_R12_AUDITED_NATURAL_EXPERIENCE_VIEW",
        "source_sha256": {},
        "l2_context": _context(),
    }
    response = {"choices": [{
        "finish_reason": "stop",
        "message": {"content": json.dumps({
            **_choice(), "evidence_ids": ["invented"]
        })},
    }]}
    out = tmp_path / "one"
    with pytest.raises(r12.R12Rejected, match="FABRICATED"):
        r12.propose_shadow(
            projection, endpoint="http://localhost:8080/v1/chat/completions",
            model="gemma-test", record_dir=out,
            transport=lambda raw: json.dumps(response).encode(),
        )
    assert (out / "response.raw.json").exists()
    assert not (out / "shadow_candidate.json").exists()


def test_raw_replay_detects_tampered_retained_file(tmp_path: Path) -> None:
    projection = {
        "classification": "DEV_R12_AUDITED_NATURAL_EXPERIENCE_VIEW",
        "source_sha256": {"original": "b"},
        "l2_context": _context(),
    }
    out = tmp_path / "raw"
    def fake_transport(payload: bytes) -> bytes:
        return json.dumps({"choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps(_choice(False))},
        }]}).encode()
    r12.propose_shadow(
        projection, endpoint="http://localhost:8080/v1/chat/completions",
        model="local", record_dir=out, transport=fake_transport,
    )
    saved = json.loads((out / "shadow_candidate.json").read_text())
    saved["shadow_skill"] = _skill()
    (out / "shadow_candidate.json").write_text(json.dumps(saved))
    with pytest.raises(r12.R12Rejected, match="SHADOW_RAW_SOURCE_REPLAY_REJECTED"):
        r12.replay_retained_shadow(projection, out)


def test_stale_model_catalog_blocks_post_before_raw_dir(tmp_path: Path) -> None:
    context = _context()
    context["action_catalog"] = {"version": "fabricated"}
    projection = {
        "classification": "DEV_R12_AUDITED_NATURAL_EXPERIENCE_VIEW",
        "source_sha256": {},
        "l2_context": context,
    }
    posts = []
    def never_post(raw: bytes) -> bytes:
        posts.append(raw)
        return b"{}"
    with pytest.raises(r12.R12Rejected, match="CATALOG_STALE"):
        r12.propose_shadow(
            projection, endpoint="http://127.0.0.1:8080/v1/chat/completions",
            model="gemma", record_dir=tmp_path / "raw",
            transport=never_post,
        )
    assert posts == []
    assert not (tmp_path / "raw").exists()


def test_l2_skill_schema_is_typed_not_bare_action_names() -> None:
    schema = r12.l2_schema()
    branches = schema["properties"]["skill"]["anyOf"]
    step = branches[0]["properties"]["steps"]["items"]
    assert step["type"] == "object"
    assert set(step["required"]) == {
        "action", "guard", "binding", "repeat", "if_unavailable",
    }
    assert step["additionalProperties"] is False
