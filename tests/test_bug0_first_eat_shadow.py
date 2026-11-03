"""Bug-0 first-EAT initial source candidate; synthetic, no Minecraft launch."""
import asyncio
import inspect
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.bug0_first_eat_shadow import (
    Bug0FirstEatShadowRejected,
    inspect_bug0_first_eat_shadow,
)
from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.s51_eat_real_ci import qualify
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


def pair():
    first = s46.case()
    # Native fixture starts with one nearby zombie; first EAT requires the
    # explicitly observed bounded local registry to be empty.
    first = replace(
        first, snapshot=replace(
            first.snapshot,
            nearby_entities=(),
            nearby_entities_coverage=replace(
                first.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
        ),
    )
    current = replace(
        first, seq=first.seq + 1, request_id="bug0-first-eat-second-probe",
    )
    intent = IntentCommitment()
    intent.commit(
        "eat-when-hungry", objective="eat actual food if safe",
        at_ns=1, provenance=Provenance("bug0-dev-test", "intent"),
    )
    owner = NormalSessionActionExecutor(first.session_id, intent)
    return owner, first, current


def test_first_eat_from_fresh_no_move_s49_owner_is_only_a_nonissuing_candidate():
    owner, earlier, current = pair()
    observed = inspect_bug0_first_eat_shadow(owner, earlier, current)
    assert observed.session_id == owner.session_id
    assert observed.earlier_probe_seq == earlier.seq
    assert observed.current_probe_seq == current.seq
    assert observed.food_before == current.snapshot.food
    assert observed.candidate_item == "bread"
    assert observed.candidate_slot == 4
    assert observed.earlier_risk == "NO_NEARBY_ENTITY_OBSERVED"
    assert observed.current_risk == "NO_NEARBY_ENTITY_OBSERVED"
    assert observed.decision_status == "FOOD_SOURCE_CANDIDATE_NO_ACTION"
    assert not observed.independent_eat_grant_attested
    assert not observed.complete_idle_world_ticks_attested
    assert not observed.world_source_independently_attested
    assert not observed.physical_eat_authorized
    assert observed.native_eat_commands_issued == 0
    assert owner._count == 0
    assert owner._dispatched == set()
    assert owner.supervisor.open_actions == ()


@pytest.mark.parametrize("fault", (
    "stale-seq", "same-request", "wrong-session",
    "too-far-in-seq", "body-drift", "nearby-threat", "truncated-coverage",
    "no-food", "changed-inventory", "not-hungry", "prior-move", "already-issued",
    "pending-reconsideration", "non-probe", "no-health",
))
def test_reject_unqualified_first_eat_native_source_and_owner(fault):
    owner, earlier, current = pair()
    if fault == "stale-seq":
        current = replace(current, seq=earlier.seq)
    elif fault == "same-request":
        current = replace(current, request_id=earlier.request_id)
    elif fault == "wrong-session":
        current = replace(current, session_id="other-native-session")
    elif fault == "too-far-in-seq":
        current = replace(current, seq=earlier.seq + 33)
    elif fault == "body-drift":
        p = current.snapshot.position
        current = replace(
            current, snapshot=replace(
                current.snapshot, position=replace(p, x=p.x + 0.2),
            ),
        )
    elif fault == "nearby-threat":
        e = s46.case().snapshot.nearby_entities
        current = replace(
            current, snapshot=replace(
                current.snapshot, nearby_entities=e,
                nearby_entities_coverage=replace(
                    current.snapshot.nearby_entities_coverage, candidate_count=len(e),
                ),
            ),
        )
    elif fault == "truncated-coverage":
        e = s46.case().snapshot.nearby_entities
        cover = current.snapshot.nearby_entities_coverage
        added = tuple(
            replace(e[0], entity_id=e[0].entity_id + i)
            for i in range(cover.max_entities)
        )
        current = replace(
            current, snapshot=replace(
                current.snapshot, nearby_entities=added,
                nearby_entities_coverage=replace(
                    cover, truncated=True, candidate_count=cover.max_entities + 1,
                ),
            ),
        )
    elif fault == "no-food":
        current = replace(
            current, snapshot=replace(current.snapshot, inventory=()),
        )
    elif fault == "not-hungry":
        current = replace(
            current, snapshot=replace(current.snapshot, food=20),
        )
    elif fault == "prior-move":
        owner._post_move_settling_unqualified = True
    elif fault == "already-issued":
        owner._dispatched.add("prior-physical-action")
    elif fault == "pending-reconsideration":
        owner.intent.request_reconsideration(
            "eat-when-hungry", reason="danger",
            at_ns=2, provenance=Provenance("bug0-test", "urgent"),
        )
    elif fault == "non-probe":
        current = replace(current, kind="health", request_id=None)
    elif fault == "no-health":
        current = replace(
            current, snapshot=replace(current.snapshot, health=0),
        )
    with pytest.raises((Bug0FirstEatShadowRejected, ValueError)):
        inspect_bug0_first_eat_shadow(owner, earlier, current)
    assert not owner.supervisor.open_actions
    assert owner._count == 0


def test_s51_opt_in_first_eat_shadow_fails_before_java_without_dev_gate(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("S51_REAL_SERVER_CI", "1")
    monkeypatch.delenv("S51_BUG0_FIRST_EAT_SHADOW_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    result_path = tmp_path / "bug0-initial-shadow-report.json"
    rc = asyncio.run(qualify(
        result_path, tmp_path / "paper.log",
        bug0_first_eat_shadow=True,
    ))
    import json

    report = json.loads(result_path.read_text(encoding="utf-8"))
    assert rc == 2
    assert report["status"] == "BLOCKED"
    assert report["physical_java_started"] is False
    assert report["grant_consumed"] is False
    assert report["physical_eat_authorized"] is False
    assert report["actual_native_actions"] == []
    assert report["food_commands_issued"] == 0
    assert "explicit separate DEV gate" in report["error"]
    assert not (tmp_path / "paper.log").exists()


@pytest.mark.parametrize("food,source", (
    ("rotten_flesh", "inventory"), ("bread", "ground"),
    ("bread", "none"),
))
def test_first_eat_shadow_refuses_non_initial_inventory_mode(
    tmp_path, food, source,
):
    with pytest.raises(ValueError, match="requires bread/inventory"):
        asyncio.run(qualify(
            tmp_path / "invalid.json", tmp_path / "paper.log",
            food_item=food, food_source=source,
            bug0_first_eat_shadow=True,
        ))
    assert not (tmp_path / "invalid.json").exists()


def test_standard_s51_runner_remains_default_nonshadow():
    assert inspect.signature(qualify).parameters[
        "bug0_first_eat_shadow"
    ].default is False
