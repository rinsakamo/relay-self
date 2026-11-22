"""S1/S2 invariant adversaries against B's WAL, never a real issuer."""
from types import SimpleNamespace

import pytest

from relay_self.i_unified_physical_source_dev import (
    IUnifiedPhysicalHold,
    _distinct_runs,
    _read_wal,
    capture_i_unified_s1_cpu,
)
from relay_self.physical_action_journal import PhysicalActionJournal


def _row(intent="intent-1", skill="skill-1", action="a1", status="NATIVE_MOVE_SETTLED",
         session="native-A"):
    return {
        "session_id": session,
        "intent_id": intent,
        "skill_execution_id": skill,
        "action_id": action,
        "status": status,
    }


def test_s1_s2_distinct_terminal_intent_skill_action():
    s1 = (_row(),)
    s2 = (_row(intent="intent-2", skill="skill-2", action="a2"),)
    assert _distinct_runs(s1, s2, "native-A")
    assert not _distinct_runs(s1, s2, "native-B")
    for altered in (
        (_row(intent="intent-1", skill="skill-2", action="a2"),),
        (_row(intent="intent-2", skill="skill-1", action="a2"),),
        (_row(intent="intent-2", skill="skill-2", action="a1"),),
        (_row(intent="intent-2", skill="skill-2", action="a2",
              status="PREPARED_UNRESOLVED"),),
        (_row(intent="intent-2", skill="skill-2", action="a2",
              session="foreign-native"),),
    ):
        assert not _distinct_runs(s1, altered, "native-A")
    assert not _distinct_runs(s1, (), "native-A")


def test_original_b_wal_empty_and_foreign_are_never_s2_admitted(tmp_path):
    journal = PhysicalActionJournal.create(tmp_path / "one.json", self_id="A")
    with pytest.raises(IUnifiedPhysicalHold):
        _read_wal(journal, "A")
    with pytest.raises(IUnifiedPhysicalHold):
        _read_wal(journal, "B")
    with pytest.raises(IUnifiedPhysicalHold):
        capture_i_unified_s1_cpu(
            bridge=SimpleNamespace(cognitive_work=None, owners={}),
            self_id="A", journal=journal,
        )
