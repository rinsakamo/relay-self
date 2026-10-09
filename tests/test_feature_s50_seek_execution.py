"""S50 explicit ISSUE and real session must precede a SEEK effect."""
import pytest

from adapters.mineflayer.seek_execution import (
    SeekConsequenceKind,
    SeekExecutionRejected,
    execute_seek_step,
)


def test_seek_consequence_labels_are_distinct():
    assert SeekConsequenceKind.ARRIVED is not SeekConsequenceKind.BLOCKED


@pytest.mark.parametrize("wrong", (None, "not-a-session", 1))
def test_seek_refuses_missing_issued_world_owner(wrong):
    import asyncio

    with pytest.raises(SeekExecutionRejected):
        asyncio.run(execute_seek_step(wrong, wrong, wrong, wrong))
