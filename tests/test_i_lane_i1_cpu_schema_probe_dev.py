"""I1 partial CPU Schema readout: synthetic original native/Paper only."""
from dataclasses import replace

import pytest

import relay_self.i_lane_i1_cpu_schema_probe_dev as module
from relay_self.bd1b_owner_source_dev import BD1bSourceHold
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _call(case, self_id="A"):
    return module.prepare_i1_cpu_schema_probe(
        bridge=case[1], boot=case[2], world=case[3], links=case[4],
        self_id=self_id,
    )


def test_original_source_to_bounded_cpu_schema_without_action_catalog(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    before = _files(case[1])
    a, b = _call(case, "A"), _call(case, "B")
    for result, sid in ((a, "A"), (b, "B")):
        assert result.original.present.source.self_id == sid
        assert result.percept.scope.self_id == sid
        assert result.percept.source == case[1].owners[sid].current_worldbody_observation.provenance
        assert result.percept.targets == ()  # no capability/target fabrication
        assert result.schema.options == ()
        assert "EXPLORE_WORLD" in {goal.goal_id for goal in result.schema.goals}
        assert tuple(entry for _, entry in result.l1_proposal.numbered) == (
            "ESCALATE_L2", "DEFER",
        )
        assert result.model_invoked is False
        assert result.action_issue_authorized is False
    assert a.percept.scope != b.percept.scope
    assert _files(case[1]) == before


def test_no_eligible_exploration_need_does_not_generate_it(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=False)
    readout = _call(case)
    assert readout.percept.exploration_need is False
    assert "EXPLORE_WORLD" not in {goal.goal_id for goal in readout.schema.goals}
    assert readout.schema.options == ()


def test_observation_replaced_during_schema_computation_rejected(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    original = module.cpu_schema_epoch

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        owner = case[1].owners["A"]
        probe = owner.current_worldbody_observation
        owner.current_worldbody_observation = replace(probe, seq=probe.seq + 1)
        return result

    monkeypatch.setattr(module, "cpu_schema_epoch", changed)
    with pytest.raises((BD1bSourceHold, module.I1CPUProbeHold)):
        _call(case)


def test_native_generation_change_and_owner_fence_refused(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    world = case[3]
    with pytest.raises(BD1bSourceHold):
        module.prepare_i1_cpu_schema_probe(
            bridge=case[1], boot=case[2], world=replace(world, epoch=world.epoch + 1),
            links=case[4], self_id="A",
        )
    case[1].cognitive_work.fence_self("A")
    with pytest.raises(BD1bSourceHold):
        _call(case)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(20.0, 20), (18, 18), (17.25, None), (-1, None), (21, None)],
)
def test_native_food_is_not_rounded_or_fabricated(value, expected):
    assert module._exact_food(value) == expected
