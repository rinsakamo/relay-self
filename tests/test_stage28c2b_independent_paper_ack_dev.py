"""Stage28c2b: independent Paper main-thread ACK file/body/owned-log proof."""
from __future__ import annotations

import hashlib

import pytest

from experiments.stage28c2b_independent_rejoin_audit_dev import (
    Stage28c2bIndependentAuditHold,
    _verify_main_thread_ack,
)


def _source(tmp_path):
    folder = tmp_path / "plugins" / "P0BRecorder" / "p0d-ticks" / "acks"
    folder.mkdir(parents=True)
    boot = "boot-123"
    nonce = "nonce-456"
    session = "paper-owned-789"
    world_id = "f9221410-b99e-417d-98f4-e98938586472"
    tick = 17
    body = (
        f"boot_id={boot}\nnonce={nonce}\npaper_tick={tick}\n"
        f"server_session_id={session}\nsource=PAPER_MAIN_THREAD\n"
        f"world_uuid={world_id}\n"
    ).encode()
    (folder / (nonce + ".ack")).write_bytes(body)
    ref = (
        f"paper-main-thread:p0d:{boot}:{nonce}:sha256:"
        + hashlib.sha256(body).hexdigest()
    )
    log = (
        f"[P0BRecorder] P0D_TICK_ACK nonce={nonce} boot={boot} "
        f"session={session} world={world_id} tick={tick} "
        "source=PAPER_MAIN_THREAD\n"
    ).encode()
    return dict(
        executable=tmp_path, paper_session=session, world_id=world_id,
        boot_id=boot, ref=ref, tick=tick, paper_stdout=log,
    )


def test_stage28c2b_independent_ack_source_exact_bytes(tmp_path):
    arguments = _source(tmp_path)
    _verify_main_thread_ack(**arguments)


@pytest.mark.parametrize("failure", [
    "wrong-boot", "changed-tick", "wrong-log",
    "changed-raw-ack", "missing-ack", "wrong-session",
])
def test_stage28c2b_forged_ack_never_qualifies(tmp_path, failure):
    arguments = _source(tmp_path)
    source = (
        tmp_path / "plugins" / "P0BRecorder" / "p0d-ticks"
        / "acks" / "nonce-456.ack"
    )
    if failure == "wrong-boot":
        arguments["boot_id"] = "old-boot"
    elif failure == "changed-tick":
        arguments["tick"] = 18
    elif failure == "wrong-log":
        arguments["paper_stdout"] = b"no matching owned Paper source"
    elif failure == "changed-raw-ack":
        source.write_bytes(source.read_bytes().replace(b"paper_tick=17", b"paper_tick=19"))
    elif failure == "missing-ack":
        source.unlink()
    else:
        arguments["paper_session"] = "paper-owned-foreign"
    with pytest.raises(Stage28c2bIndependentAuditHold):
        _verify_main_thread_ack(**arguments)
