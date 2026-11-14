"""#857 DEV-only one-shot P0-B Paper observer ticket via local filesystem.

It performs zero Minecraft actions. A request is only an observational
nonce; the actual ATTACK still passes the original physical ActionPort/WAL.
Evidence is external and untrusted without the Paper log and raw receipts.
"""
from __future__ import annotations

import asyncio
import os
import re
import uuid
from pathlib import Path

from relay_self.attack_world_join_dev import ServerAttackTicket

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_ALLOWED = frozenset({
    "nonce", "world_id", "branch_id", "action_id", "native_session_id",
    "actor_uuid", "target_uuid",
})
_ACK = _ALLOWED | frozenset({"registered_at_tick", "server_ack_ref"})


class PaperTicketRefusal(ValueError):
    """No independently server-acknowledged preissue ticket was available."""


def _simple(name: str, value: str) -> None:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise PaperTicketRefusal(f"invalid {name} for DEV paper ticket")


def _fields(raw: str, keys: frozenset[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.splitlines():
        name, sep, value = line.partition("=")
        if sep != "=" or name in result or name not in keys:
            raise PaperTicketRefusal("invalid/duplicate Paper ticket field")
        _simple(name, value)
        result[name] = value
    if set(result) != keys:
        raise PaperTicketRefusal("incomplete Paper ticket acknowledgement")
    return result


async def arm_paper_ticket_before_attack(
    request_dir: Path,
    ack_dir: Path,
    *,
    world_id: str,
    branch_id: str,
    action_id: str,
    native_session_id: str,
    actor_uuid: str,
    target_uuid: str,
    timeout_s: float = 3.0,
) -> ServerAttackTicket:
    """Write a new exclusive request; await a server-created ACK BEFORE issue.

    The folders are created by the Paper plugin. This is an opt-in
    local-filesystem DEV bridge, not a grant or an Action emitter.
    """
    for name, value in (
        ("world_id", world_id), ("branch_id", branch_id),
        ("action_id", action_id), ("native_session_id", native_session_id),
        ("actor_uuid", actor_uuid), ("target_uuid", target_uuid),
    ):
        _simple(name, value)
    for name, value in (("actor_uuid", actor_uuid), ("target_uuid", target_uuid)):
        try:
            if str(uuid.UUID(value)) != value:
                raise ValueError("noncanonical UUID")
        except ValueError as exc:
            raise PaperTicketRefusal(f"invalid {name}") from exc
    if actor_uuid == target_uuid:
        raise PaperTicketRefusal("Paper ticket cannot target actor")
    if type(timeout_s) is not float or not 0 < timeout_s <= 10:
        raise PaperTicketRefusal("bounded timeout required")
    request_dir = Path(request_dir)
    ack_dir = Path(ack_dir)
    if (not request_dir.is_dir() or not ack_dir.is_dir()
            or request_dir.is_symlink() or ack_dir.is_symlink()):
        raise PaperTicketRefusal("Paper observer ticket directories missing")
    nonce = str(uuid.uuid4())
    fields = {
        "nonce": nonce, "world_id": world_id, "branch_id": branch_id,
        "action_id": action_id, "native_session_id": native_session_id,
        "actor_uuid": actor_uuid, "target_uuid": target_uuid,
    }
    request = request_dir / f"{nonce}.request"
    ack = ack_dir / f"{nonce}.ack"
    data = "".join(f"{k}={fields[k]}\n" for k in sorted(fields)).encode()
    fd = os.open(request, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        if ack.is_file() and not ack.is_symlink():
            # Server ACK is a separate file; never create/modify it here.
            try:
                fd = os.open(ack, os.O_RDONLY | os.O_NOFOLLOW)
                try:
                    body = os.read(fd, 16384).decode("utf-8")
                finally:
                    os.close(fd)
                received = _fields(body, _ACK)
                if any(received[key] != value for key, value in fields.items()):
                    raise PaperTicketRefusal("Paper ACK differs from proposed ticket")
                tick_text = received["registered_at_tick"]
                if not tick_text.isdecimal() or str(int(tick_text)) != tick_text:
                    raise PaperTicketRefusal("Paper ACK tick malformed")
                return ServerAttackTicket(
                    world_id=world_id, branch_id=branch_id,
                    action_id=action_id, native_session_id=native_session_id,
                    nonce=nonce, actor_uuid=actor_uuid, target_uuid=target_uuid,
                    registered_at_tick=int(tick_text),
                    server_ack_ref=received["server_ack_ref"],
                )
            except OSError as exc:
                raise PaperTicketRefusal("Paper ACK cannot be read") from exc
        await asyncio.sleep(0.05)
    raise PaperTicketRefusal("Paper ticket observer ACK timeout; no physical issue")
