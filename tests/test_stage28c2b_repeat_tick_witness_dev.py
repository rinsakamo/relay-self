"""Stage28c2b: opt-in multiple fresh Paper nonce ACKs within ONE owned boot.

Existing default one-shot policy remains strict. Synthetic plugin spool only.
"""
from __future__ import annotations

import threading
import uuid

import pytest

from relay_self.paper_tick_witness_dev import (
    PaperMainThreadTickReader,
    PaperTickWitnessError,
)
from test_paper_tick_witness_dev import WORLD_UUID, _run_witness, _spool


def _sample(reader, root, log, session, boot, *, tick):
    worker = threading.Thread(
        target=_run_witness,
        args=(root, log),
        kwargs={"boot": boot, "tick": str(tick)},
    )
    worker.start()
    try:
        return reader(session)
    finally:
        worker.join(timeout=4)
        assert not worker.is_alive()


def test_stage28c2b_optin_same_paper_boot_can_read_twice_for_boot_and_stop(tmp_path):
    root = _spool(tmp_path)
    log = {"value": b""}
    reader = PaperMainThreadTickReader(
        spool_dir=root, expected_world_uuid=WORLD_UUID,
        read_owned_log=lambda _sid: log["value"], timeout_seconds=0.5,
        allow_repeated_same_boot=True,
    )
    session = "paper-owned-" + str(uuid.uuid4())
    boot = str(uuid.uuid4())
    initial = _sample(reader, root, log, session, boot, tick=3)
    final = _sample(reader, root, log, session, boot, tick=25)
    assert initial.server_session_id == final.server_session_id == session
    assert initial.tick == 3
    assert final.tick == 25
    assert initial.source_ref != final.source_ref
    assert reader._seen_sessions[session] == boot
    assert reader._last_ticks[session] == 25


@pytest.mark.parametrize("failure", ["regressed-tick", "changed-boot", "other-session-same-boot"])
def test_stage28c2b_repeated_tick_refuses_untrusted_clock(
    tmp_path, failure,
):
    root = _spool(tmp_path)
    log = {"value": b""}
    reader = PaperMainThreadTickReader(
        spool_dir=root, expected_world_uuid=WORLD_UUID,
        read_owned_log=lambda _sid: log["value"], timeout_seconds=0.4,
        allow_repeated_same_boot=True,
    )
    session = "paper-owned-" + str(uuid.uuid4())
    boot = str(uuid.uuid4())
    assert _sample(reader, root, log, session, boot, tick=10).tick == 10
    if failure == "regressed-tick":
        other_boot, other_session, tick = boot, session, 9
    elif failure == "changed-boot":
        other_boot, other_session, tick = str(uuid.uuid4()), session, 11
    else:
        other_boot, other_session, tick = boot, "paper-owned-" + str(uuid.uuid4()), 11
    with pytest.raises(PaperTickWitnessError, match="stale/foreign"):
        _sample(reader, root, log, other_session, other_boot, tick=tick)


def test_stage28c2b_repeated_policy_optin_must_be_boolean(tmp_path):
    root = _spool(tmp_path)
    with pytest.raises(PaperTickWitnessError):
        PaperMainThreadTickReader(
            spool_dir=root, expected_world_uuid=WORLD_UUID,
            read_owned_log=lambda _: b"", allow_repeated_same_boot="yes",
        )
