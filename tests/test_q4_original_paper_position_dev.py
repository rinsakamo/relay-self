"""U18 Paper position readback CPU fixtures; never an actual World claim."""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from experiments.cognitive_physical_place_move_issue_dev import Stage27PlaceMoveReceipt
from relay_self.q4_original_paper_position_dev import (
    Q4OriginalPaperHold,
    _build_window,
    verify_original_q4_paper_position_window,
)
from relay_self.resident_paper_presence_join_dev import (
    PaperResidentEvent,
    parse_owned_paper_resident_trace,
)
from test_i_unified_i4a_place_lease_dev import _acks, _probes

BOOT = "a7aa5ea7-4f20-4358-bb4d-5dfdbe5b0f91"
WORLD = "d18bfb06-d4d5-4839-bc79-56ebf4813dd1"
ACTOR = "b75523ee-40d5-4ec0-bb3e-07f0728cf734"
PAPER = "paper-owned-u18"
NATIVE = "native-A"


def _case(monkeypatch, *, settled_tick=130, foreign_actor=False):
    from relay_self import q4_original_paper_position_dev as module

    def point(kind, tick, x, line):
        return PaperResidentEvent(
            kind, BOOT, tick, WORLD,
            "d0000000-0000-4000-8000-000000000001" if foreign_actor
            and kind == "PRESENT" else ACTOR,
            "RelaySelf", x, 64.0, 2.0, line,
        )

    events = (
        point("JOIN", 100, 1.0, 2),
        point("MOVE", 110, 1.5, 3),
        point("PRESENT", 120, 1.5, 4),
        point("PRESENT", settled_tick, 1.5, 5),
    )
    # Local source-shaped Paper transcript, not a launched Paper process.
    raw = (
        f"P0D_RESIDENT_READY boot={BOOT} source=PAPER_MAIN_THREAD version=1\n"
        + "".join(
            f"P0D_RESIDENT event={e.event} boot={e.boot_id} tick={e.tick} "
            f"world={e.world_uuid} actor={e.actor_uuid} name={e.name} "
            f"x={e.x} y={e.y} z={e.z} source=PAPER_MAIN_THREAD\n"
            for e in events
        )
    ).encode()
    trace = parse_owned_paper_resident_trace(
        owned_paper_session_id=PAPER, expected_world_uuid=WORLD,
        owned_paper_log=raw, log_ref="synthetic-test-only",
    )
    monkeypatch.setattr(module, "_owned_log_source", lambda *_args: (trace, raw))
    bridge = SimpleNamespace(
        paper=SimpleNamespace(owned_session_id=PAPER),
        configs={"A": SimpleNamespace(username="RelaySelf")},
        sessions={"A": SimpleNamespace(started=SimpleNamespace(session_id=NATIVE))},
    )
    look, start, stop = _acks(NATIVE, "place-A")
    initial, first, settled = _probes(NATIVE)
    receipt = Stage27PlaceMoveReceipt(
        "inv", "preset", "contract", "place-A", NATIVE,
        look, start, stop, initial, first, settled,
        0.5, "NATIVE_PLACE_MOVE_SETTLED", "0" * 64,
        (initial, first, settled),
    )
    return bridge, receipt


def test_u18_paper_position_window_uses_three_real_typed_log_events(monkeypatch):
    bridge, receipt = _case(monkeypatch)
    window = _build_window(bridge, "A", receipt)
    assert tuple(x.tick for x in window.receipts) == (110, 120, 130)
    assert all(x.source_ref.startswith("paper-owned-position:") for x in window.receipts)
    assert not window.causal_action_attested
    verify_original_q4_paper_position_window(bridge, "A", receipt, window)
    with pytest.raises(Q4OriginalPaperHold, match="typed Paper"):
        verify_original_q4_paper_position_window(
            bridge, "A", receipt,
            replace(window, receipts=tuple(replace(x, tick=x.tick + 1)
                                           for x in window.receipts)),
        )


@pytest.mark.parametrize("bad", ["short_stable", "foreign_actor"])
def test_u18_paper_source_refuses_unstable_or_foreign_actor(monkeypatch, bad):
    bridge, receipt = _case(
        monkeypatch, settled_tick=125 if bad == "short_stable" else 130,
        foreign_actor=bad == "foreign_actor",
    )
    with pytest.raises(Q4OriginalPaperHold):
        _build_window(bridge, "A", receipt)


def test_u18_original_paper_log_prefix_change_denies_rearm(monkeypatch):
    bridge, receipt = _case(monkeypatch)
    window = _build_window(bridge, "A", receipt)
    from relay_self import q4_original_paper_position_dev as module

    _case_source = module._owned_log_source(bridge, "A")
    monkeypatch.setattr(
        module, "_owned_log_source",
        lambda *_args: (_case_source[0], b"forged-prefix" + _case_source[1]),
    )
    with pytest.raises(Q4OriginalPaperHold, match="prefix changed"):
        verify_original_q4_paper_position_window(bridge, "A", receipt, window)


def test_u19_paper_prefix_fence_rejects_replayed_s1_samples(monkeypatch):
    """Synthetic Paper transcript: old S1 samples cannot satisfy a new S2."""
    bridge, receipt = _case(monkeypatch)
    from relay_self import q4_original_paper_position_dev as module

    _, raw = module._owned_log_source(bridge, "A")
    # Same owned Paper boot and JOIN, captured BEFORE the movement samples.
    pre_move = b"".join(raw.splitlines(keepends=True)[:2])
    distinct = _build_window(
        bridge, "A", receipt, after_log_prefix=pre_move,
    )
    assert tuple(p.tick for p in distinct.points) == (110, 120, 130)

    # After S1 is fully recorded, no additional Paper position can
    # retrospectively qualify S2 without fresh post-fence entries.
    with pytest.raises(Q4OriginalPaperHold, match="stable position"):
        _build_window(bridge, "A", receipt, after_log_prefix=raw)
    with pytest.raises(Q4OriginalPaperHold, match="prefix changed"):
        _build_window(
            bridge, "A", receipt,
            after_log_prefix=pre_move.replace(b"version=1", b"version=2"),
        )
    with pytest.raises(Q4OriginalPaperHold, match="prefix changed"):
        _build_window(bridge, "A", receipt, after_log_prefix=pre_move[:-1])


def test_u19_reverse_s2_observed_relative_to_pre_motor_position(monkeypatch):
    """Synthetic S2 can return to login, yet MUST have fresh Paper samples."""
    bridge, receipt = _case(monkeypatch)
    from adapters.mineflayer.python_protocol import MineflayerPosition
    from relay_self import q4_original_paper_position_dev as module

    _, original = module._owned_log_source(bridge, "A")
    def reverse(observation):
        return replace(
            observation,
            snapshot=replace(
                observation.snapshot,
                position=MineflayerPosition(1.0, 64.0, 2.0),
            ),
        )

    initial, first, settled = (
        reverse(receipt.initial_stop_probe),
        reverse(receipt.first_stable_probe),
        reverse(receipt.settled_probe),
    )
    returning = replace(
        receipt, initial_stop_probe=initial, first_stable_probe=first,
        settled_probe=settled, all_stop_probes=(initial, first, settled),
    )
    # All these lines are later than the frozen S1 Paper prefix.
    additional = "".join(
        f"P0D_RESIDENT event={kind} boot={BOOT} tick={tick} "
        f"world={WORLD} actor={ACTOR} name=RelaySelf "
        f"x=1.0 y=64.0 z=2.0 source=PAPER_MAIN_THREAD\\n"
        for kind, tick in (
            ("MOVE", 140), ("PRESENT", 150), ("PRESENT", 160)
        )
    ).replace("\\n", "\n").encode()
    updated = original + additional
    parsed = parse_owned_paper_resident_trace(
        owned_paper_session_id=PAPER, expected_world_uuid=WORLD,
        owned_paper_log=updated, log_ref="synthetic-test-only",
    )
    monkeypatch.setattr(module, "_owned_log_source", lambda *_: (parsed, updated))
    evidence = _build_window(
        bridge, "A", returning, after_log_prefix=original,
    )
    assert tuple(point.tick for point in evidence.points) == (140, 150, 160)
    assert evidence.points[0].x == 1.0
