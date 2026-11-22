"""Readout representation only; no model or World claims."""
import pytest

from relay_self.c_lane_evaluation_readout_dev import (
    AxisStatus,
    EvaluationAxis,
    EvaluationCandidate,
    EvaluationReadout,
    EvaluationStep,
    interpret_evaluation_step,
)
from relay_self.relay_engine import BoundedChoice, DecisionStatus


def step(axis):
    return EvaluationStep(axis, (
        EvaluationCandidate(BoundedChoice("1", "Observed movement"), ("wal:action-1",)),
        EvaluationCandidate(BoundedChoice("2", "UNKNOWN"), ()),
    ), "2")


def test_readout_keeps_selection_and_sources_and_unknown():
    axes = tuple(interpret_evaluation_step(
        step(axis), status=DecisionStatus.RESOLVED,
        choice_id="2" if axis is EvaluationAxis.SKILL_EFFECTIVENESS else "1",
    ) for axis in EvaluationAxis)
    result = EvaluationReadout("task", "self", "world", 1, "skill", ("action-1",),
                               "a" * 64, axes)
    assert result.axes[0].evidence_refs == ("wal:action-1",)
    assert result.axes[1].status is AxisStatus.UNKNOWN
    assert not result.axes[1].unresolved
    assert result.complete
    assert result.axes[1].selected_description == "UNKNOWN"


def test_unresolved_and_unoffered_cannot_become_success():
    s = step(EvaluationAxis.GOAL_PROGRESS)
    assert interpret_evaluation_step(s, status=DecisionStatus.UNRESOLVED,
                                     choice_id=None).unresolved
    with pytest.raises(ValueError):
        interpret_evaluation_step(s, status=DecisionStatus.RESOLVED, choice_id="9")
    with pytest.raises(ValueError):
        interpret_evaluation_step(s, status=DecisionStatus.UNRESOLVED, choice_id="1")


def test_mixed_unresolved_preserves_other_axes_but_is_not_complete():
    axes = tuple(interpret_evaluation_step(
        step(axis),
        status=(DecisionStatus.UNRESOLVED if axis is EvaluationAxis.INFORMATION_GAIN
                else DecisionStatus.RESOLVED),
        choice_id=(None if axis is EvaluationAxis.INFORMATION_GAIN else
                   "2" if axis is EvaluationAxis.SKILL_EFFECTIVENESS else "1"),
    ) for axis in EvaluationAxis)
    result = EvaluationReadout("task", "self", "world", 1, "skill", ("action-1",),
                               "a" * 64, axes)
    assert not result.complete
    assert [a.status for a in result.axes][:3] == [
        AxisStatus.RESOLVED, AxisStatus.UNKNOWN, AxisStatus.UNRESOLVED,
    ]
    assert result.axes[0].evidence_refs == ("wal:action-1",)


def test_substantive_candidate_requires_source():
    with pytest.raises(ValueError):
        EvaluationStep(EvaluationAxis.INFORMATION_GAIN, (
            EvaluationCandidate(BoundedChoice("1", "learned"), ()),
            EvaluationCandidate(BoundedChoice("2", "UNKNOWN"), ()),
        ), "2")
