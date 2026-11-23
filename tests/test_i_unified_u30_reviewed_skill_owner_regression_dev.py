"""U30: preserve the original Owner's post-S1 reviewed Skill transition.

CPU-only lifecycle regression: no actual Gemma, Paper, Native, or MOVE.
S1 Action/WAL source validation belongs to the original I4a live anchor.
"""
from __future__ import annotations

import pytest

from relay_self.checkpointed_cognitive_runtime_dev import LiveCognitionCheckpointError
from relay_self.provenance import Provenance
from relay_self.skill import SkillState
from test_checkpointed_cognitive_runtime_dev import RuntimeFixture


def test_original_owner_reviewed_s1_cancel_then_release_intent(tmp_path):
    case = RuntimeFixture(tmp_path)
    owner = case.owners[1]  # Original B, registered in its cohort
    source = Provenance("u30-synthetic-owner", "B")
    original_wal = owner.files.physical_wal_file.read_bytes()
    owner.commit_intent("intent-B-s1", "EXPLORE_WORLD", 1000, source)
    owner.start_skill("skill-B-s1", "MOVE", 1001, source)

    terminal = owner.finish_reviewed_skill(
        "skill-B-s1", outcome=SkillState.CANCELLED,
        reason="bounded S1 ended; evaluate fresh intent",
        at_ns=1002, provenance=source,
    )

    assert terminal is owner.skills["skill-B-s1"]
    assert terminal.state is SkillState.CANCELLED
    assert owner.intent.current_intent is not None
    assert owner.intent.current_intent.intent_id == "intent-B-s1"
    with pytest.raises(LiveCognitionCheckpointError):
        owner.finish_reviewed_skill(
            "skill-B-s1", outcome=SkillState.CANCELLED,
            reason="must not terminalize twice",
            at_ns=1003, provenance=source,
        )

    owner.complete_intent(
        "intent-B-s1", reason="explicit reviewed terminal release",
        at_ns=1004, provenance=source,
    )
    assert owner.intent.current_intent is None
    assert owner.supervisor.open_actions == ()
    assert owner.files.physical_wal_file.read_bytes() == original_wal


def test_reviewed_skill_refuses_foreign_execution_without_wal_mutation(tmp_path):
    case = RuntimeFixture(tmp_path)
    owner = case.owners[1]
    source = Provenance("u30-synthetic-owner", "B")
    original_wal = owner.files.physical_wal_file.read_bytes()
    owner.commit_intent("intent-B-s1", "EXPLORE_WORLD", 1000, source)
    owner.start_skill("skill-B-s1", "MOVE", 1001, source)

    with pytest.raises(LiveCognitionCheckpointError):
        owner.finish_reviewed_skill(
            "other-skill", outcome=SkillState.CANCELLED,
            reason="foreign owner history", at_ns=1002,
            provenance=source,
        )

    assert owner.skills["skill-B-s1"].state is SkillState.STARTED
    assert owner.files.physical_wal_file.read_bytes() == original_wal
