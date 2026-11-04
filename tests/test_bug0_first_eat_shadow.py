"""Bug-0 first-EAT initial source candidate; synthetic, no Minecraft launch."""
import asyncio
import inspect
from dataclasses import replace

import pytest

import test_bug0_s49_s51_eat_handoff as prior_handoff
import test_feature_s46_eat as s46
from adapters.mineflayer.bug0_first_eat_shadow import (
    Bug0FirstEatShadowRejected,
    inspect_bug0_first_eat_shadow,
    handoff_authorized_first_eat,
)
from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from relay_self.action import ActionState
from relay_self.eat_hunger import EatCursor
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
    elif fault == "changed-inventory":
        old = current.snapshot.inventory[0]
        current = replace(
            current, snapshot=replace(
                current.snapshot, inventory=(replace(old, count=old.count + 1),),
            ),
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


def test_existing_s51_runner_shadow_path_never_sends_eat_with_scripted_originals(
    tmp_path, monkeypatch,
):
    """Script original World I/O: exercise real S51 branch, but spawn no World."""
    import json
    from types import SimpleNamespace

    import adapters.mineflayer.s51_eat_real_ci as s51

    owner, earlier, fresh = pair()
    del owner
    calls = []
    monkeypatch.setenv("S51_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S51_BUG0_FIRST_EAT_SHADOW_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)

    class FakeStdin:
        async def drain(self):
            return None

    class FakeServer:
        stdin = FakeStdin()
        pid = 127
        returncode = 0

    class FakeSession:
        started = SimpleNamespace(session_id=earlier.session_id)
        _process = SimpleNamespace(pid=128)

        async def shutdown(self, *, timeout_s=10):
            calls.append("shutdown")
            return 0

    class FakeSessionType:
        @staticmethod
        async def launch(*args, **kwargs):
            calls.append("existing-session-launch-shape")
            return FakeSession()

    class FakeLedger:
        body = SimpleNamespace(tick=0, energy=9)
        config = SimpleNamespace(basal_cost=0.1, food_energy=4)

        def __init__(self, *args, **kwargs):
            pass

        def decide(self, read):
            assert read is earlier
            return SimpleNamespace(
                kind="EAT", eat_choice=SimpleNamespace(item_name="bread"),
                sensor_reading=7.0,
            )

    def fake_official(jar_path):
        jar_path.write_bytes(b"synthetic-test-never-run")
        return {"synthetic_bootstrap_only": True}

    def fake_config(root):
        (root / "server.properties").write_text("synthetic-test=true\n")

    async def fake_ready(*args, **kwargs):
        calls.append("no-physical-java")
        return FakeServer(), None, None

    async def no_effect(*args, **kwargs):
        return None

    async def fake_probe(session, request_id):
        assert isinstance(session, FakeSession)
        calls.append(("native-original-shape", request_id))
        return earlier if "s51-hunger-native" in request_id else fresh

    def fake_command(server, command):
        calls.append(("server-stage-only", command))

    monkeypatch.setattr(s51, "_fetch_official_server", fake_official)
    monkeypatch.setattr(s51, "_write_config", fake_config)
    monkeypatch.setattr(s51, "_ready_server", fake_ready)
    monkeypatch.setattr(s51, "_recording_session_type", lambda *_: FakeSessionType)
    monkeypatch.setattr(s51, "_await_spawn", no_effect)
    monkeypatch.setattr(s51, "_shutdown_server", no_effect)
    monkeypatch.setattr(s51, "_correlated_observe", fake_probe)
    monkeypatch.setattr(s51, "_command", fake_command)
    monkeypatch.setattr(s51, "B0EnergyLedger", FakeLedger)

    report_path = tmp_path / "shadow.json"
    rc = asyncio.run(s51.qualify(
        report_path, tmp_path / "paper.log",
        bug0_first_eat_shadow=True,
    ))
    report = json.loads(report_path.read_text())
    assert rc == 0 and report["status"] == "PASS"
    assert report["classification"] == (
        "BUG0_FIRST_EAT_NATIVE_SHADOW_NO_ACTION_DEV_ONLY"
    )
    assert report["bug0_first_eat_shadow"]["candidate_item"] == "bread"
    assert report["actual_native_actions"] == []
    assert report["food_commands_issued"] == 0
    assert report["physical_eat_authorized"] is False
    assert report["m_energy_credited"] is False
    assert report["grant_consumed"] is False
    assert calls.count("shutdown") == 1
    assert not any(
        isinstance(call, tuple) and any(
            name in call[1] for name in ("equip_item", "consume_held")
        )
        for call in calls
    )
    assert (tmp_path / "shadow.native.jsonl").is_file()
    assert (tmp_path / "shadow.commands.jsonl").is_file()


def test_first_eat_supplied_owner_grants_delegate_to_same_s49_s51_supervisor():
    """Scripted native receipts only; source pairing + actual S51 verification."""
    owner, earlier, current = pair()
    shadow = inspect_bug0_first_eat_shadow(owner, earlier, current)
    choice = EatCursor(current.session_id).choose(current)
    propose, issue = prior_handoff.grants(
        current, choice, owner.intent.current_intent.intent_id,
        action_id="bug0-initial-original-owner-eat",
    )
    session = prior_handoff.ScriptedNativeSession(current, propose.action_id)
    observed = asyncio.run(handoff_authorized_first_eat(
        owner, session, earlier, current, shadow, propose, issue,
    ))
    assert observed.terminal is owner.supervisor.get(propose.action_id)
    assert observed.terminal.state is ActionState.OUTCOME
    assert observed.outcome.food_before == 7
    assert observed.outcome.food_after == 12
    assert observed.outcome.count_before == 2
    assert observed.outcome.count_after == 1
    assert session.commands == [
        ("equip", propose.action_id + "-equip", "bread"),
        ("consume", propose.action_id + "-consume"),
        ("observe", propose.action_id + "-after-eating-00"),
    ]
    assert owner.supervisor.open_actions == ()
    assert owner._count == 1
    assert owner._dispatched == {propose.action_id}
    assert owner._post_move_settling_unqualified is False
    # No second issuer was allocated by this one-time handoff.


@pytest.mark.parametrize("fault", (
    "missing-propose", "missing-issue", "wrong-action",
    "wrong-intent", "wrong-session", "wrong-native-probe",
    "wrong-request", "wrong-item", "wrong-slot",
    "stale-native-shadow", "wrong-owner", "prior-move",
    "shadow-candidate-tampered",
))
def test_first_eat_handoff_rejects_missing_grant_and_changed_world(fault):
    owner, earlier, current = pair()
    shadow = inspect_bug0_first_eat_shadow(owner, earlier, current)
    choice = EatCursor(current.session_id).choose(current)
    propose, issue = prior_handoff.grants(
        current, choice, owner.intent.current_intent.intent_id,
    )
    session = prior_handoff.ScriptedNativeSession(current, propose.action_id)
    if fault == "missing-propose":
        propose = None
    elif fault == "missing-issue":
        issue = None
    elif fault == "wrong-action":
        issue = replace(issue, action_id="foreign-physical-action")
    elif fault == "wrong-intent":
        issue = replace(issue, intent_id="foreign-intent")
    elif fault == "wrong-session":
        issue = replace(issue, session_id="foreign-world")
    elif fault == "wrong-native-probe":
        issue = replace(issue, probe_seq=current.seq + 1)
    elif fault == "wrong-request":
        issue = replace(issue, probe_request_id="old-probe")
    elif fault == "wrong-item":
        issue = replace(issue, food_item="rotten_flesh")
    elif fault == "wrong-slot":
        issue = replace(issue, food_slot=choice.item_slot + 1)
    elif fault == "stale-native-shadow":
        current = replace(
            current, snapshot=replace(current.snapshot, food=8),
        )
    elif fault == "wrong-owner":
        owner = pair()[0]
        owner.intent.complete(
            "eat-when-hungry", reason="terminal",
            at_ns=2, provenance=Provenance("test", "terminated"),
        )
    elif fault == "prior-move":
        owner._post_move_settling_unqualified = True
    elif fault == "shadow-candidate-tampered":
        shadow = replace(shadow, candidate_item="rotten_flesh")
    with pytest.raises((Bug0FirstEatShadowRejected, ValueError)):
        asyncio.run(handoff_authorized_first_eat(
            owner, session, earlier, current, shadow, propose, issue,
        ))
    assert session.commands == []
    assert owner.supervisor.open_actions == ()
    assert owner._count == 0


def test_first_eat_handoff_is_not_automatically_called_by_s51_shadow():
    # Code-path contract: the S51 runner must not call the optional
    # capability without owner-supplied attestable PROPOSE+ISSUE grants.
    import inspect

    import adapters.mineflayer.s51_eat_real_ci as s51

    source = inspect.getsource(s51.qualify)
    assert "handoff_authorized_first_eat(" not in source
    assert "IssuedEatingExecutor().execute(" in source  # legacy S51 path
