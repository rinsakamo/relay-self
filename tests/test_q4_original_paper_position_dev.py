"""U18 Paper position readback CPU fixtures; never an actual World claim."""
from __future__ import annotations

import hashlib
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
    OwnedPaperResidentTrace,
    PaperResidentEvent,
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
        point("JOIN", 100, 1.0, 1),
        point("MOVE", 110, 1.5, 2),
        point("PRESENT", 120, 1.5, 3),
        point("PRESENT", settled_tick, 1.5, 4),
    )
    raw = b"synthetic-original-Paper-source-fixture\n"
    trace = OwnedPaperResidentTrace(
        PAPER, BOOT, WORLD, hashlib.sha256(raw).hexdigest(),
        events, "synthetic-test-only",
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
