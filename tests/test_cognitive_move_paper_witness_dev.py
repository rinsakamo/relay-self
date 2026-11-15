"""Synthetic offline contracts for independent Paper main-thread MOVE tick proof.

No Paper/JVM/Mineflayer process is started; these are adversarial fixtures,
not a substitute for real Paper artifacts and owned log readback.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition
from experiments.cognitive_move_paper_witness_dev import (
    PaperMoveWitnessError,
    _properties,
    qualify_paper_move_trace,
)

BOOT = "ac2c628e-8c26-46a4-9a7c-2dc9ebc30d60"
NONCE = "2129ed8b-2003-498b-8259-a7fd360d4a0f"
WORLD = "3197b8cf-c132-4cd9-990c-58d9c956d274"
ACTOR = "bbf036f3-732c-40d3-bb9b-c44309d971f4"
ACTION = "cognitive-move-one"
SESSION = "native-A"


def _data(*, arm=100, stop=110, drift=0, moved=.6):
    before = [
        ("boot_id", BOOT), ("nonce", NONCE), ("world_uuid", WORLD),
        ("actor_uuid", ACTOR), ("action_id", ACTION),
        ("native_session_id", SESSION), ("arm_tick", str(arm)),
        ("stop_mark_tick", str(stop)), ("source", "PAPER_MAIN_THREAD"),
    ]
    coords = []
    for n in range(arm, stop + 17):
        x = 0 if n == arm else moved if n >= stop else .4
        if n > stop + 8:
            x += (n - (stop + 8)) * drift
        coords.append(("sample", f"{n},{x},64.0,0.0"))
    payload = "".join(f"{k}={v}\n" for k, v in before + coords).encode()
    log = (
        f"[P0M] P0M_READY boot={BOOT} source=PAPER_MAIN_THREAD\n"
        f"[P0M] P0M_ARM nonce={NONCE} boot={BOOT} action={ACTION}"
        f" actor={ACTOR} world={WORLD} tick={arm}\n"
        f"[P0M] P0M_STOP_MARK nonce={NONCE} boot={BOOT} tick={stop}\n"
        f"[P0M] P0M_COMPLETE nonce={NONCE} boot={BOOT}"
        f" tick={stop+16} source=PAPER_MAIN_THREAD\n"
    ).encode()
    return payload, log


def _qualified(raw, log, **overrides):
    kw = dict(
        nonce=NONCE, world_uuid=WORLD, actor_uuid=ACTOR,
        action_id=ACTION, native_session_id=SESSION,
        native_start=MineflayerPosition(0, 64, 0),
        native_target=MineflayerPosition(3, 64, 0),
        paper_owned_log=log,
    )
    kw.update(overrides)
    return qualify_paper_move_trace(raw, **kw)


def test_mainthread_paper_tick_window_joins_native_and_detects_stability():
    raw, log = _data()
    proof = _qualified(raw, log)
    assert proof.source == "PAPER_MAIN_THREAD"
    assert proof.action_id == ACTION
    assert proof.arm_tick == 100
    assert proof.stop_mark_tick == 110
    assert proof.stable_start_tick == 118
    assert proof.stable_end_tick == 126
    assert proof.paper_targetward_progress_m == pytest.approx(.6)
    assert proof.paper_residual_max_m == 0
    assert proof.paper_position_stable_8_ticks is True
    assert proof.native_stop_ack_attributed is False
    assert proof.physical_arrival_attested is False
    assert len(proof.raw_sha256) == 64


@pytest.mark.parametrize("mismatch", [
    "nonce", "world_uuid", "actor_uuid", "action_id",
    "native_session_id", "native_start", "paper_owned_log",
])
def test_foreign_native_paper_action_and_log_never_join(mismatch):
    raw, log = _data()
    wrong = {
        "nonce": "17d68c5b-d59f-4b82-922e-500b17c97885",
        "world_uuid": "10edb04c-1484-4364-b4ce-a1d516851939",
        "actor_uuid": "9ab080e6-0e99-4c1e-b6a1-ea6b05646d9a",
        "action_id": "wrong-move-action",
        "native_session_id": "native-other",
        "native_start": MineflayerPosition(1.0, 64, 0),
        "paper_owned_log": b"[P0M] alien process log\n",
    }[mismatch]
    with pytest.raises(PaperMoveWitnessError):
        _qualified(raw, log, **{mismatch: wrong})


@pytest.mark.parametrize("change", [
    "missing_tick", "duplicate_sample", "stale_tick", "early_stop",
    "premature_finish", "wrong_source", "duplicate_field", "unknown_field",
    "bad_y", "nan_sample", "insufficient_progress", "drifting",
    "missing_ready", "missing_mark", "wrong_boot_log", "out_of_order_log",
])
def test_adversarial_paper_trace_cannot_forge_settling(change):
    raw, log = _data()
    if change == "missing_tick":
        raw = raw.replace(b"sample=115,0.6,64.0,0.0\n", b"")
    elif change == "duplicate_sample":
        raw += b"sample=126,0.6,64.0,0.0\n"
    elif change == "stale_tick":
        raw = raw.replace(b"stop_mark_tick=110", b"stop_mark_tick=100")
    elif change == "early_stop":
        raw = raw.replace(b"stop_mark_tick=110", b"stop_mark_tick=99")
    elif change == "premature_finish":
        raw = raw.split(b"sample=126,")[0]
    elif change == "wrong_source":
        raw = raw.replace(b"source=PAPER_MAIN_THREAD", b"source=MINEFLAYER")
    elif change == "duplicate_field":
        raw += b"source=PAPER_MAIN_THREAD\n"
    elif change == "unknown_field":
        raw += b"authorized=true\n"
    elif change == "bad_y":
        raw = raw.replace(b"sample=122,0.6,64.0,0.0", b"sample=122,0.6,65.0,0.0")
    elif change == "nan_sample":
        raw = raw.replace(b"sample=122,0.6,64.0,0.0", b"sample=122,nan,64.0,0.0")
    elif change == "insufficient_progress":
        raw, log = _data(moved=.1)
    elif change == "drifting":
        raw, log = _data(drift=.03)
    elif change == "missing_ready":
        log = log.replace(b"P0M_READY", b"P0M_UNREADY")
    elif change == "missing_mark":
        log = log.replace(b"P0M_STOP_MARK", b"P0M_UNKNOWN")
    elif change == "wrong_boot_log":
        log = log.replace(BOOT.encode(), b"00000000-0000-4000-8000-000000000000")
    elif change == "out_of_order_log":
        log = b"\n".join(reversed(log.strip().splitlines())) + b"\n"
    with pytest.raises(PaperMoveWitnessError):
        _qualified(raw, log)


def test_arm_ack_has_no_stop_proof_and_samples_cannot_be_added_to_arm():
    raw, _ = _data()
    first = raw.split(b"stop_mark_tick=")[0]
    f, sample = _properties(first, trace=False)
    assert f["nonce"] == NONCE
    assert sample == ()
    with pytest.raises(PaperMoveWitnessError):
        _properties(raw, trace=False)


def test_noncanonical_uuid_is_refused_without_disk_action():
    raw, log = _data()
    with pytest.raises(PaperMoveWitnessError):
        _qualified(raw, log, nonce=NONCE.upper())
