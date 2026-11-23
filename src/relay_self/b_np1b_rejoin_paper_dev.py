"""Paper half of rejoin qualification; callers must bind all inputs to their owners.

This does not itself qualify a current composite source. Native and Paper clocks
remain independent; only ordering within the owned Paper stream is checked.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.resident_paper_presence_join_dev import (
    ResidentPaperJoinError,
    join_resident_paper_presence,
    parse_owned_paper_resident_trace,
)
from relay_self.stage28c2b_native_paper_body_link_dev import paper_tick_ack_matches


@dataclass(frozen=True, slots=True)
class RejoinPaperEvidence:
    log_sha256: str
    presence_boot_id: str
    a_quit_line: int
    a_join_line: int
    a_present_line: int
    b_present_line: int


def verify_rejoin_paper(*, log: bytes, world, tick: PaperTickReceipt,
                        paper_boot_id: str, presence_boot_id: str,
                        a_name: str, b_name: str, a_actor: str, b_actor: str,
                        a_logout, a_relogin, original_b_native: str,
                        surviving_b_native: str, historical_log_sha256: str,
                        historical_tick: int) -> RejoinPaperEvidence:
    """Check a single rejoin in bytes already read from the original Paper owner."""
    match = re.fullmatch(
        r'paper-main-thread:p0d:([A-Za-z0-9-]+):([A-Za-z0-9-]+):sha256:[a-f0-9]{64}',
        tick.source_ref,
    ) if type(tick) is PaperTickReceipt else None
    if (match is None or match.group(1) != paper_boot_id
            or tick.server_session_id != world.paper_session_id
            or type(tick.tick) is not int or tick.tick <= historical_tick
            or not paper_tick_ack_matches(source_ref=tick.source_ref, boot_id=paper_boot_id,
                session_id=world.paper_session_id, world_id=world.world_id,
                tick=tick.tick, log=log)):
        raise ResidentPaperJoinError('fresh Paper tick ACK unavailable')
    trace = parse_owned_paper_resident_trace(
        owned_paper_session_id=world.paper_session_id, expected_world_uuid=world.world_id,
        owned_paper_log=log, log_ref='owned-paper-sha256:' + hashlib.sha256(log).hexdigest(),
    )
    decision = join_resident_paper_presence(
        trace=trace, world=world, a_name=a_name, b_name=b_name, a_logout=a_logout,
        a_relogin=a_relogin, original_b_native=original_b_native,
        surviving_b_native=surviving_b_native,
    )
    lines = log.splitlines(keepends=True)
    prefixes = [i for i in range(1, len(lines) + 1)
                if hashlib.sha256(b''.join(lines[:i])).hexdigest() == historical_log_sha256]
    ack = (f'P0D_TICK_ACK nonce={match.group(2)} boot={paper_boot_id} '
           f'session={world.paper_session_id} world={world.world_id} '
           f'tick={tick.tick} source=PAPER_MAIN_THREAD').encode()
    ack_lines = [i + 1 for i, line in enumerate(lines) if ack in line]
    a = [e for e in trace.events if e.name == a_name]
    b = [e for e in trace.events if e.name == b_name]
    quit_event = next(e for e in a if e.event == 'QUIT')
    join_event = next(e for e in a[1:] if e.event == 'JOIN')
    present = [e for e in a if e.event in ('PRESENT', 'MOVE') and e.line > join_event.line]
    b_present = [e for e in b if e.event in ('PRESENT', 'MOVE')
                 and quit_event.line < e.line < join_event.line]
    if (trace.boot_id != presence_boot_id or decision.a_actor_uuid != a_actor
            or decision.b_actor_uuid != b_actor or len(prefixes) != 1
            or len(ack_lines) != 1 or quit_event.line <= prefixes[0]
            or not any(e.event in ('PRESENT', 'MOVE') and e.line < quit_event.line for e in a)
            or not present or not b_present
            or any(e.event in ('PRESENT', 'MOVE') and quit_event.line < e.line < join_event.line
                   for e in a)
            or any(e.line >= ack_lines[0] or e.tick > tick.tick for e in trace.events)):
        raise ResidentPaperJoinError('Paper rejoin history or ordering mismatch')
    return RejoinPaperEvidence(trace.lines_sha256, trace.boot_id, quit_event.line,
                               join_event.line, present[-1].line, b_present[-1].line)
