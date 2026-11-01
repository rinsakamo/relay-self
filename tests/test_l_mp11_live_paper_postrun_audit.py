"""Postrun prefix-source reconciliation, synthetic fixtures only."""
from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from test_self_body_s50_l2_mp11_paper_audit import segment
from tools import l_mp11_live_paper_postrun_audit as post

WORLD = "original-constant-world-uuid"
SUBJECT = "subject-constant-uuid"
SESSION = "session"
ACTIONS = ("s49-native-move-11", "s49-native-move-18", "s49-native-move-26")


def fake_originals():
    raws = []
    prior = b""
    for i, action in enumerate(ACTIONS):
        text = segment(f"{action}-{SESSION}", "GRASS_BLOCK", start=100+i*100)
        prior += ("\n".join(text) + "\n").encode()
        raws.append(prior)
    typed = [
        {"action_id": action, "native_seq": i*25}
        for i, action in enumerate(ACTIONS, 1)
    ]
    observations = [{
        "action_id": action,
        "native_s16_seq": typed[i]["native_seq"],
        "paper_first_tick": 100+i*100,
        "paper_last_tick": 107+i*100,
        "paper_prefix_length": len(raws[i]),
        "paper_prefix_sha256": hashlib.sha256(raws[i]).hexdigest(),
        "visible_previous_trials": i+1,
        "source_status": "LIVE_PAPER_PREFIX_UNSEALED_S49_TYPED_S16_CLAIM",
        "l2_calls": 0,
        "l2_request_id": f"l-mp11-live:{WORLD}:after-{i+1}",
    } for i, action in enumerate(ACTIONS)]
    report = {
        "mp11_g2": {"typed_s16_actions": typed},
        "l_mp11_live_prefix": {
            "status": "PROVISIONAL_LIVE_PREFIX_READ_ONLY",
            "observations": observations,
            "l2_open_calls": 0,
            "learning_admissions": 0,
            "action_issuers_added": 0,
        },
    }
    return report, raws[-1]


def fake_review(report, original, *, expected_l2_calls=0):
    assert expected_l2_calls in (0, 2)
    assert isinstance(report, dict) and original.endswith(b"\n")
    return {
        "paper_world_uuid": WORLD,
        "session_id": SESSION,
        "s49_actions": 3,
        "per_action_wait_tick_ranges": [[100, 107], [200, 207], [300, 307]],
    }


def test_three_snapshots_reconcile_with_final_original(monkeypatch):
    monkeypatch.setattr(post, "review", fake_review)
    report, original = fake_originals()
    result = post.audit_live_prefixes(report, original)
    assert result["classification"] == (
        "L_MP11_LIVE_PREFIX_POSTRUN_SOURCE_RECONCILED_DEV_ONLY"
    )
    assert result["all_live_prefix_sha_match_final_original"] is True
    assert len(result["source_observations"]) == 3
    assert result["real_l2_calls"] == 0
    assert result["true_live_sample_clock_independently_attested"] is False
    assert result["qualification"] == "NO_GO"


@pytest.mark.parametrize("bad", [
    "alter_original", "wrong_prefix", "wrong_length", "wrong_native",
    "wrong_tick", "future_action", "wrong_request", "model_called",
    "model_called_in_row", "learning", "issuer", "qualified", "reordered",
    "missing", "duplicate", "stale_prefix",
])
def test_unsafe_live_claim_or_replay_rejected(monkeypatch, bad):
    monkeypatch.setattr(post, "review", fake_review)
    report, original = fake_originals()
    report = deepcopy(report)
    r = report["l_mp11_live_prefix"]
    p = r["observations"]
    if bad == "alter_original":
        original = original.replace(b"tick=100", b"tick=101", 1)
    elif bad == "wrong_prefix":
        p[0]["paper_prefix_sha256"] = "a"*64
    elif bad == "wrong_length":
        p[0]["paper_prefix_length"] -= 1
    elif bad == "wrong_native":
        p[1]["native_s16_seq"] = 9
    elif bad == "wrong_tick":
        p[1]["paper_first_tick"] = 300
    elif bad == "future_action":
        p[0]["action_id"] = ACTIONS[2]
    elif bad == "wrong_request":
        p[1]["l2_request_id"] = "fake"
    elif bad == "model_called":
        r["l2_open_calls"] = 1
    elif bad == "model_called_in_row":
        p[1]["l2_calls"] = 1
    elif bad == "learning":
        r["learning_admissions"] = 1
    elif bad == "issuer":
        r["action_issuers_added"] = 1
    elif bad == "qualified":
        p[0]["source_status"] = "INDEPENDENTLY_CERTIFIED_ONLINE"
    elif bad == "reordered":
        p[0], p[1] = p[1], p[0]
    elif bad == "missing":
        p.pop()
    elif bad == "duplicate":
        p[2] = deepcopy(p[1])
    elif bad == "stale_prefix":
        p[1]["paper_prefix_length"] = p[0]["paper_prefix_length"]
    with pytest.raises(post.LivePostrunRejected):
        post.audit_live_prefixes(report, original)


def test_separate_independent_g3_original_audit_required(monkeypatch):
    def reject(*_, **kwargs):
        raise ValueError("G3 original S16/Paper audit failed")
    monkeypatch.setattr(post, "review", reject)
    report, original = fake_originals()
    with pytest.raises(ValueError, match="original"):
        post.audit_live_prefixes(report, original)


def test_two_live_open_proposals_reconcile_with_previous_original_source(
    monkeypatch,
):
    monkeypatch.setattr(post, "review", fake_review)
    report, original = fake_originals()
    rows = report["l_mp11_live_prefix"]["observations"]
    report["l_mp11_live_prefix"]["l2_open_calls"] = 2
    for row in rows[:2]:
        row["l2_calls"] = 1
    report["l_mp11_live_l2"] = {
        "validated_open_calls": 2,
        "attempts": 2,
        "proposals": [
            {
                "source_last_action_id": row["action_id"],
                "source_last_prefix_sha256": row["paper_prefix_sha256"],
                "source_world_uuid": WORLD,
                "source_session_id": SESSION,
                "request_id": row["l2_request_id"],
                "source_prior_count": i+1,
                "provider_source": "llama.cpp",
                "action_authority": False,
                "next_test_owner_approved": False,
                "learning_admissions": 0,
                "l0_promotions": 0,
            } for i, row in enumerate(rows[:2])
        ],
        "experiments_selected_and_executed_by_l2": 0,
        "new_action_issuers": 0,
        "learning_admissions": 0,
        "l0_promotions": 0,
    }
    assert post.audit_live_prefixes(report, original)["real_l2_calls"] == 2
    for case in ("wrong_proposal_sha", "wrong_request", "wrong_count"):
        bad = deepcopy(report)
        if case == "wrong_proposal_sha":
            bad["l_mp11_live_l2"]["proposals"][0][
                "source_last_prefix_sha256"
            ] = "a" * 64
        elif case == "wrong_request":
            bad["l_mp11_live_l2"]["proposals"][1][
                "request_id"
            ] = "foreign"
        else:
            bad["l_mp11_live_prefix"]["l2_open_calls"] = 0
        with pytest.raises(post.LivePostrunRejected):
            post.audit_live_prefixes(bad, original)
