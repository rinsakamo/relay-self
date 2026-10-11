"""S2 offline source-bound read-only L1/S60 L2 integration contracts.

All native frames and Action receipts are synthetic; no Minecraft or LLM POST.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.self_s2_candidates import (
    S2CandidateRejected,
    S2ReadOnlyCandidates,
    preconfigured_wait_repertoire,
)
from relay_self.world_conditioned_choice import select_world_conditioned_choice
from test_self_continuous_host import _fixture


def _choices():
    retained, near, far, near_event, far_event = s42._pair()
    return (
        select_world_conditioned_choice(
            far, retained, expected_session_id=far.observation.session_id,
            expected_entity_id=far.entity_id,
        ),
        select_world_conditioned_choice(
            near, retained, expected_session_id=near.observation.session_id,
            expected_entity_id=near.entity_id,
        ),
        far_event, near_event,
    )


def test_existing_s11_far_wait_and_near_abstain_never_authorize():
    far, near, far_event, near_event = _choices()
    reader = S2ReadOnlyCandidates(
        far.session_id, preconfigured_wait_repertoire(),
    )
    # S42 fixture orders near then far; choose distinct safe sequence manually.
    a = reader.review(near, near_event.seq)
    b = reader.review(far, far_event.seq)
    assert a.l1_status == "no_match"
    assert a.l1_candidate is None
    assert a.effective_selection == "MOVE_AWAY"
    assert b.l1_status == "selected"
    assert b.l1_candidate == "WAIT"
    assert b.effective_selection == "WAIT"
    assert not b.action_authorized_by_l1
    assert not b.learned_habit_claimed
    assert not b.l2_used_for_action
    assert b.l1_repertoire_revision == 0
    with pytest.raises(S2CandidateRejected, match="fresh"):
        reader.review(far, far_event.seq)


def test_foreign_or_authority_claims_are_rejected():
    far, _, far_event, _ = _choices()
    reader = S2ReadOnlyCandidates(far.session_id, preconfigured_wait_repertoire())
    with pytest.raises(S2CandidateRejected):
        reader.review(replace(far, session_id="other-native-session"), far_event.seq)
    with pytest.raises(S2CandidateRejected):
        reader.review(replace(far, action_authorized=True), far_event.seq)


def test_s2_works_inside_s1_driver_without_changing_physical_action(tmp_path):
    driver, probe, grant, execute, requests, source = _fixture(tmp_path)
    advisor = S2ReadOnlyCandidates(
        driver.host.session_id, preconfigured_wait_repertoire(),
    )
    seen = []

    async def l2_probe(reading):
        seen.append((reading.session_id, reading.seq))
        # Read-only callback, no native frame reads and no Action permissions.
        return None

    outcome = asyncio.run(driver.run(
        probe=probe, grant=grant, on_action=execute,
        on_candidate=advisor.review, on_l2_probe=l2_probe,
    ))
    assert outcome["events"] == 2
    assert outcome["action_requests"] == outcome["closed_outcomes"] == 1
    assert requests == [1, 3]
    assert source.calls == 2
    rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    reviews = [r for r in rows if r["kind"] == "l1_candidate_review"]
    assert len(reviews) == 2
    assert [r["l1_candidate"] for r in reviews] == ["WAIT", None]
    assert [r["effective_selection"] for r in reviews] == ["WAIT", "MOVE_AWAY"]
    assert all(r["l1_authorized_actions"] == 0 for r in reviews)
    assert len([r for r in rows if r["kind"] == "l2_probe_observed"]) == 2
    assert len([r for r in rows if r["kind"] == "action_outcome"]) == 1
    assert seen == [(driver.host.session_id, 2), (driver.host.session_id, 4)]


def test_untrusted_l1_candidate_cannot_override_l0(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)
    result = asyncio.run(driver.run(
        probe=probe, grant=grant, on_action=execute,
        on_candidate=lambda choice, seq: {
            "claimed_action_grant": True, "selection": "MOVE_AWAY",
        },
    ))
    assert result["action_requests"] == result["closed_outcomes"] == 1
    rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert len([x for x in rows if x["kind"] == "l1_candidate_unavailable"]) == 2
    assert not any(x["kind"] == "l1_candidate_review" for x in rows)


def test_l2_exception_does_not_prevent_l0_survival(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)

    async def unavailable(_):
        raise RuntimeError("backend not owned")

    result = asyncio.run(driver.run(
        probe=probe, grant=grant, on_action=execute,
        on_l2_probe=unavailable,
    ))
    assert result["closed_outcomes"] == 1
    rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    rejected = [x for x in rows if x["kind"] == "l2_probe_unavailable"]
    assert len(rejected) == 2
    assert all(x["used_as_action"] is False for x in rejected)
    assert not any(x.get("backend_stop_ack") is True for x in rows)


def test_s2_l2_is_not_implicitly_started_from_default_cli(monkeypatch, capsys):
    from adapters.mineflayer import self_s1_runtime
    monkeypatch.setattr(
        self_s1_runtime.asyncio, "run",
        lambda _: pytest.fail("dry-run started model or World"),
    )
    assert self_s1_runtime.main([]) == 0
    assert json.loads(capsys.readouterr().out)["model_calls"] == 0


def test_forged_l1_source_does_not_replace_actual_s49_action(tmp_path):
    driver, probe, grant, execute, _, _ = _fixture(tmp_path)
    candidates = S2ReadOnlyCandidates(
        driver.host.session_id, preconfigured_wait_repertoire(),
    )

    def wrong_origin(choice, event_seq):
        view = candidates.review(choice, event_seq)
        return replace(view, l1_source="foreign-source:99")

    summary = asyncio.run(driver.run(
        probe=probe, grant=grant, on_action=execute,
        on_candidate=wrong_origin,
    ))
    assert summary["closed_outcomes"] == 1
    rows = [
        json.loads(line)
        for line in (tmp_path / "events.jsonl").read_text().splitlines()
    ]
    assert len([x for x in rows if x["kind"] == "l1_candidate_unavailable"]) == 2
    assert not any(x["kind"] == "l1_candidate_review" for x in rows)


def test_s11_does_not_accept_preconfigured_move_action_repertoire():
    from relay_self.habit import CueFeature, HabitRepertoire, HabitRule
    from relay_self.provenance import Provenance

    p = Provenance("offline-test-owner", "unsafe-cue-repertoire")
    unsafe = HabitRepertoire(
        "unqualified-move", 0,
        (HabitRule("move", (CueFeature("native_threat_band", "near"),),
                   "MOVE_AWAY", 1, p),), p,
    )
    with pytest.raises(S2CandidateRejected, match="safe-only"):
        S2ReadOnlyCandidates("world-1", unsafe)
