"""T1j DEV-only explicit STOP reauthorization + dual World reobservation.

An old STOP owner is never cleared. STOP ACK is bounded T1h DEV evidence;
this gate neither authenticates R sources nor reconstructs missing M0/P1 ticks.
Only the original S49 owner may consume a permit and create a fresh owner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ResumeDevRejected(ValueError):
    """No authority, fresh World evidence, or unresolved physical effect."""


@dataclass(frozen=True, slots=True)
class ResumeDevPermit:
    resume_id: str
    stop_id: str
    session_id: str
    next_action_id: str
    world: str
    player: str
    old_stop_ack_last_server_tick: int
    before_source_seq: int
    after_source_seq: int
    native_probe_seq: int
    after_world_tick: int
    unobserved_world_ticks: int
    classification: str = "DEV_EXPLICIT_REAUTHORIZE_REOBSERVED_GAP"
    original_owner_latch_retained: bool = True
    no_retrospective_m0_or_p1: bool = True
    p1_wait_qualified: bool = False
    native_source_independently_authenticated: bool = False


def _identifier(value: object, label: str) -> str:
    if (type(value) is not str or not 1 <= len(value) <= 128
            or not all(c.isascii() and (c.isalnum() or c in '-_') for c in value)):
        raise ResumeDevRejected(f"invalid {label}")
    return value


def _paper(frame: Any, session_id: str, world: str, player: str, *,
           after_seq: int, after_tick: int) -> dict:
    try:
        d, s, c = frame.data, frame.data['snapshot'], frame.data['control']
        admitted = (
            frame.session_id == session_id and type(frame.seq) is int
            and frame.seq > after_seq and d['status'] == 'ADMITTED'
            and d['assessment'] == 'NO_KNOWN_URGENT_SIGNAL'
            and type(s['tick']) is int and s['tick'] > after_tick
            and type(s['world_tick']) is int
            and s['world'] == world and s['player'] == player
            and type(s['boot']) is str and s['boot']
            and s['threats_complete'] is True and not s['threats']
            and type(s['input']) is int and s['input'] == 0
            and c['phase'] == 'CLEARED' and type(c['generation']) is int
            and int(d['challenge_sent_ns']) > int(c['since_ns'])
            and int(d['age_upper_ns']) < 150_000_000
            and 0 <= s['food'] <= 20 and s['health'] > 6
        )
    except (AttributeError, KeyError, ValueError, TypeError, OverflowError) as e:
        raise ResumeDevRejected('malformed T1j Paper source') from e
    if not admitted:
        raise ResumeDevRejected('stale/foreign/unsafe/not-idle T1j Paper source')
    return s


class S49DevResumeGate:
    """One-shot gate; a failed candidate cannot retry stale native evidence."""

    def __init__(self, *, stopped_owner: Any, frozen_ledger: Any,
                 unresolved_eat: bool = False, retired_action_ids=()):
        ack = getattr(stopped_owner, 'ack', None)
        ledger_frame = getattr(frozen_ledger, 'previous', None)
        if (unresolved_eat or getattr(frozen_ledger, 't1j_resumed_stop_id', None) is not None
                or ack is None or stopped_owner.failed
                or not stopped_owner.requested or stopped_owner.allows_action
                or not ack.high_level_dev_stop_ack
                or ack.full_tick_stillness_qualified
                or not ack.active_action_id
                or ack.session_id != stopped_owner.session_id
                or ack.stop_id != stopped_owner.stop_id
                or getattr(frozen_ledger, 'session_id', None) != ack.session_id
                or ledger_frame is None or getattr(ledger_frame, 'session_id', None) != ack.session_id):
            raise ResumeDevRejected('no resolved MOVE STOP and frozen ledger')
        s = ledger_frame.data['snapshot']
        if (s['world'] != ack.world or s['player'] != ack.player
                or type(s['world_tick']) is not int or type(s['tick']) is not int):
            raise ResumeDevRejected('frozen source does not bind stopped World')
        self.stopped_owner = stopped_owner
        self.frozen_ledger = frozen_ledger
        self.ack = ack
        self.freeze_world_tick = s['world_tick']
        self.freeze_source_seq = ledger_frame.seq
        self.retired_action_ids = frozenset(retired_action_ids)
        self.requested = None
        self.permit = None
        self.consumed = False
        self.rejected = False

    def authorize(self, *, authority: str, resume_id: str,
                  stop_id: str, session_id: str, next_action_id: str) -> None:
        if self.requested is not None or self.consumed or self.rejected:
            raise ResumeDevRejected('resume authorization already spent')
        if (authority != 'DEV_EXPLICIT_OPERATOR_REAUTHORIZE'
                or _identifier(resume_id, 'resume_id') == self.ack.stop_id
                or stop_id != self.ack.stop_id
                or session_id != self.ack.session_id
                or _identifier(next_action_id, 'next_action_id') != f't1j-{resume_id}-move'
                or next_action_id in self.retired_action_ids
                or next_action_id in {self.ack.active_action_id, self.ack.clear_action_id}):
            raise ResumeDevRejected('not newly bound explicit DEV reauthorization')
        self.requested = (resume_id, next_action_id)

    def reobserve(self, *, before: Any, native_probe: Any, after: Any,
                  expected_probe_request_id: str) -> ResumeDevPermit:
        if self.requested is None or self.permit is not None or self.consumed or self.rejected:
            raise ResumeDevRejected('no fresh unconsumed explicit DEV authorization')
        self.rejected = True  # one attempt; no test-to-success or stale replay
        old = self.stopped_owner
        if (old.failed or not old.requested or old.allows_action
                or old.ack is not self.ack
                or getattr(self.frozen_ledger, 'failed', False) is not True
                or getattr(self.frozen_ledger, 'pending_meal', None) is not None
                or getattr(self.frozen_ledger, 'active_action', None) is not None):
            raise ResumeDevRejected('old owner or ledger was mutated/unfrozen')
        if type(getattr(native_probe, 'seq', None)) is not int:
            raise ResumeDevRejected('invalid native probe sequence')
        first = _paper(before, self.ack.session_id, self.ack.world,
                       self.ack.player, after_seq=max(self.ack.clear_ack_seq,
                       self.freeze_source_seq), after_tick=self.ack.last_idle_tick)
        second = _paper(after, self.ack.session_id, self.ack.world,
                        self.ack.player, after_seq=native_probe.seq,
                        after_tick=first['tick'])
        if (native_probe.session_id != self.ack.session_id
                or type(native_probe.seq) is not int
                or native_probe.seq <= before.seq
                or native_probe.kind != 'probe'
                or native_probe.request_id != expected_probe_request_id
                or getattr(native_probe, 'provenance', None) is None
                or native_probe.provenance.source != 'mineflayer'
                or first['boot'] != second['boot']
                or second['world_tick'] <= first['world_tick']
                or second['world_tick'] <= self.freeze_world_tick
                or first['food'] != second['food']
                or native_probe.snapshot.food != second['food']
                or any(first[k] != second[k] for k in ('x', 'y', 'z'))
                or first['motion_blocks'] != second['motion_blocks']
                or before.data['control']['generation'] != after.data['control']['generation']):
            raise ResumeDevRejected('native/Paper post-STOP observations do not agree')
        resume_id, next_action_id = self.requested
        self.permit = ResumeDevPermit(
            resume_id=resume_id, stop_id=self.ack.stop_id,
            session_id=self.ack.session_id, next_action_id=next_action_id,
            world=self.ack.world, player=self.ack.player,
            old_stop_ack_last_server_tick=self.ack.last_idle_tick,
            before_source_seq=before.seq, after_source_seq=after.seq,
            native_probe_seq=native_probe.seq,
            after_world_tick=second['world_tick'],
            unobserved_world_ticks=second['world_tick'] - self.freeze_world_tick - 1,
        )
        self.rejected = False
        return self.permit

    def consume(self, permit: ResumeDevPermit) -> ResumeDevPermit:
        if (self.consumed or self.rejected or self.permit is None
                or permit is not self.permit or self.stopped_owner.ack is not self.ack
                or not self.stopped_owner.requested or self.stopped_owner.allows_action):
            raise ResumeDevRejected('forged/replayed DEV resume permit')
        if getattr(self.frozen_ledger, 't1j_resumed_stop_id', None) is not None:
            raise ResumeDevRejected('previous resume already consumed')
        self.frozen_ledger.t1j_resumed_stop_id = permit.stop_id
        self.consumed = True
        return permit
