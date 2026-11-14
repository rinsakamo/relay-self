"""#855 P0B ticket bridge fault injection (no Minecraft process involved)."""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest

from experiments.p0b_paper_ticket_dev import (
    PaperTicketRefusal,
    arm_paper_ticket_before_attack,
)

ACTOR = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ZOMBIE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
WORLD = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def _opts(tmp_path: Path):
    request_dir = tmp_path / "requests"
    ack_dir = tmp_path / "acks"
    request_dir.mkdir()
    ack_dir.mkdir()
    return request_dir, ack_dir


def _params(req, ack, **kw):
    data = {
        "request_dir": req, "ack_dir": ack, "world_id": WORLD,
        "branch_id": "branch-dev", "action_id": "attack-parent-1",
        "native_session_id": "native-1",
        "actor_uuid": ACTOR, "target_uuid": ZOMBIE, "timeout_s": 0.5,
    }
    data.update(kw)
    return data


async def _server_write_ack(request_dir: Path, ack_dir: Path, *, mutate=None):
    for _ in range(80):
        files = list(request_dir.glob("*.request"))
        if files:
            request = files[0]
            data = dict(line.split("=", 1) for line in request.read_text().splitlines())
            data["registered_at_tick"] = "105"
            data["server_ack_ref"] = "paper:ticket-ack:" + data["nonce"] + ":105"
            if mutate:
                mutate(data)
            (ack_dir / f"{data['nonce']}.ack").write_text(
                "".join(f"{k}={v}\n" for k, v in sorted(data.items()))
            )
            return
        await asyncio.sleep(0.005)
    raise AssertionError("ticket registration never emitted request")


def test_server_ack_received_before_possible_physical_issue(tmp_path):
    request, ack = _opts(tmp_path)

    async def exercise():
        client = asyncio.create_task(
            arm_paper_ticket_before_attack(**_params(request, ack))
        )
        await _server_write_ack(request, ack)
        ticket = await client
        assert ticket.registered_at_tick == 105
        assert ticket.actor_uuid == ACTOR
        assert ticket.target_uuid == ZOMBIE
        assert ticket.action_id == "attack-parent-1"
        assert str(uuid.UUID(ticket.nonce)) == ticket.nonce
        assert ticket.server_ack_ref.startswith("paper:ticket-ack:")
        assert len(list(request.glob("*.request"))) == 1
        assert len(list(ack.glob("*.ack"))) == 1
    asyncio.run(exercise())


@pytest.mark.parametrize("case", ["wrong-action", "wrong-target", "wrong-session", "wrong-world"])
def test_foreign_ack_refused_before_native_issue(tmp_path, case):
    request, ack = _opts(tmp_path)

    def bad(data):
        key, value = {
            "wrong-action": ("action_id", "attack-another"),
            "wrong-target": ("target_uuid", ACTOR),
            "wrong-session": ("native_session_id", "native-reused"),
            "wrong-world": ("world_id", ZOMBIE),
        }[case]
        data[key] = value

    async def exercise():
        client = asyncio.create_task(
            arm_paper_ticket_before_attack(**_params(request, ack))
        )
        await _server_write_ack(request, ack, mutate=bad)
        with pytest.raises(PaperTicketRefusal, match="ACK differs"):
            await client
    asyncio.run(exercise())


def test_ack_timeout_does_not_auto_issue_or_retry(tmp_path):
    request, ack = _opts(tmp_path)

    async def exercise():
        with pytest.raises(PaperTicketRefusal, match="ACK timeout"):
            await arm_paper_ticket_before_attack(
                **_params(request, ack, timeout_s=0.10)
            )
    asyncio.run(exercise())
    assert len(list(request.glob("*.request"))) == 1
    assert not list(ack.glob("*.ack"))


def test_missing_spool_or_invalid_id_refuses_without_creating_requests(tmp_path):
    request, ack = _opts(tmp_path)

    async def exercise():
        with pytest.raises(PaperTicketRefusal, match="invalid actor_uuid"):
            await arm_paper_ticket_before_attack(
                **_params(request, ack, actor_uuid="invalid-uuid")
            )
        with pytest.raises(PaperTicketRefusal, match="directories missing"):
            await arm_paper_ticket_before_attack(
                **_params(tmp_path / "nonexistent", ack)
            )
    asyncio.run(exercise())
    assert not list(request.iterdir())


def test_malformed_or_duplicate_ack_refused(tmp_path):
    request, ack = _opts(tmp_path)

    async def exercise():
        client = asyncio.create_task(
            arm_paper_ticket_before_attack(**_params(request, ack))
        )
        await _server_write_ack(request, ack, mutate=lambda d: d.update(
            registered_at_tick="notatick"
        ))
        with pytest.raises(PaperTicketRefusal, match="tick malformed"):
            await client
    asyncio.run(exercise())
