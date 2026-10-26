"""DEV-only generated Node bridge: original S49 effects remain one-owner."""

from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_dash_client_cap_dev import (
    BRIDGE_SOURCE,
    instrument_backward_sneak_dev,
    remove_backward_sneak_dev,
)


def test_second_original_back_effect_adds_sneak_only_in_disposable_bridge(tmp_path):
    original = BRIDGE_SOURCE.read_bytes()
    target = tmp_path / "client_cap.jsonl"
    generated = instrument_backward_sneak_dev(target)
    try:
        assert generated != BRIDGE_SOURCE
        assert generated.parent == BRIDGE_SOURCE.parent
        source = generated.read_text(encoding="utf-8")
        assert source.count("dashClientCapDevBackCount += 1") == 1
        assert source.count("dashClientCapDevBackCount === 2") == 1
        assert source.count("bot.setControlState('sneak', true)") == 1
        assert source.count("emitEffectResult(command, 'applied')") >= 1
        assert source.count("dev_back_action_overrun") == 1
        assert "source_authenticated_by_file_alone: false" in source
        assert str(target) in source
        assert not target.exists()  # Source generation is not an Action.
        with pytest.raises(BoundaryRejected):
            remove_backward_sneak_dev(Path(__file__))
    finally:
        remove_backward_sneak_dev(generated)
    assert not generated.exists()
    assert BRIDGE_SOURCE.read_bytes() == original


def test_generator_rejects_nonfresh_receipt(tmp_path):
    receipt = tmp_path / "existing.jsonl"
    receipt.write_text("historic")
    with pytest.raises(BoundaryRejected):
        instrument_backward_sneak_dev(receipt)
