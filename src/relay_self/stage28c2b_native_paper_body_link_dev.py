"""Stage28c2b: link ORIGINAL native probe owners to independent Paper presence.

These are distinct clock domains:
- Bukkit.getCurrentTick() is a process-local Paper tick.
- Mineflayer snapshot.time.day * 24000 + time_of_day is World day time.
They must not be numerically compared or offset. This verification only
prepares a source-linked body receipt; it does not grant a Skill or L1.
"""
from __future__ import annotations

import hashlib
import re

from relay_self.owned_paper_world_dev import OwnedPaperWorld, PaperTickReceipt
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.resident_paper_presence_join_dev import (
    parse_owned_paper_resident_trace,
)
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28ForkPaperEpoch,
    Stage28NativePaperBodyLink,
)
from relay_self.world_resident_lifecycle_dev import Presence, WorldLifetime


class Stage28NativePaperLinkHold(RuntimeError):
    """Independent native/Paper presence provenance incomplete: HOLD."""


def i1_complete_owned_paper_prefix(raw: bytes, *, ack_marker: bytes) -> bytes:
    """Project ONLY a full-line immutable Paper stdout prefix for I1 DEV.

    The original owned Paper log remains untouched. Its live last bytes can
    contain a console prompt without a newline after the ACK. Those bytes
    are NOT line-complete evidence and must not be hashed as an I1 Paper
    observation. The existing independent auditor continues to require a
    digest of a complete newline-terminated raw byte prefix.

    The projection never fabricates a newline, normalizes whitespace,
    edits ACK bytes or searches across the incomplete suffix. An ACK still
    being written is HOLD, even if its text occurs in the raw live log.
    """
    if type(raw) is not bytes or type(ack_marker) is not bytes or not ack_marker:
        raise Stage28NativePaperLinkHold("original I1 Paper log/ACK bytes required")
    if len(raw) > 64 * 1024 * 1024:
        raise Stage28NativePaperLinkHold("I1 Paper stdout source unbounded")
    last_line_end = raw.rfind(b"\n")
    if last_line_end < 0:
        raise Stage28NativePaperLinkHold("I1 Paper witness lacks any complete line")
    prefix = raw[:last_line_end + 1]
    if ack_marker not in prefix:
        raise Stage28NativePaperLinkHold(
            "I1 Paper ACK not wholly observed within a complete stdout line"
        )
    # Non-terminated suffix is deliberately not consumed as evidence. It
    # remains frozen byte-for-byte in the owned original log at STOP.
    return prefix


def link_recovered_a_b_native_paper_body(
    *,
    bridge: OwnedResidentPhysicalBridge,
    paper: OwnedPaperWorld,
    boot: Stage28ForkPaperEpoch,
    forbidden_native_sessions: frozenset[str],
    i1_require_complete_paper_prefix: bool = False,
) -> tuple[WorldLifetime, tuple[Stage28NativePaperBodyLink, ...]]:
    """Read *live owned* Paper + original A/B native sources, no physical issue.

    Must execute after both original bridge.login() completed and before their
    logout. Requires two Paper player JOINs and a later PRESENT/MOVE each.
    A fresh Paper main-thread tick nonce ACK brackets those events in this
    same owned process; its boot ID is separate from the resident plugin's
    boot ID, though both log from the same owned process.

    Original bridge.login already captures native spawn+correlated probe
    through the owned native child. The returned NativeLoginEvidence is an
    owner claim; this cross-check requires actual live sessions and Paper
    witness bytes before that claim can be adopted for later L1 eligibility.
    """
    if (
        not isinstance(bridge, OwnedResidentPhysicalBridge)
        or not isinstance(paper, OwnedPaperWorld)
        or not isinstance(boot, Stage28ForkPaperEpoch)
        or type(i1_require_complete_paper_prefix) is not bool
        or type(forbidden_native_sessions) is not frozenset
        or any(type(s) is not str or not s for s in forbidden_native_sessions)
        or not set(boot.historical_native_sessions).issubset(
            forbidden_native_sessions
        )
        or bridge.paper is not paper
        or bridge.lifecycle.world.world_id != boot.source_world_id
        or bridge.lifecycle.world.branch_id != boot.fork_branch_id
        or bridge.lifecycle.world.paper_session_id != boot.paper_session_id
        or bridge.lifecycle.world.epoch != boot.world_epoch
        or bridge.lifecycle.self_roster != ("A", "B")
        or tuple(sorted(bridge.sessions)) != ("A", "B")
        or tuple(sorted(bridge.last_login_evidence)) != ("A", "B")
        or bridge.forbidden_native_sessions != forbidden_native_sessions
        or not bridge.physical.observation_only
        or bridge.physical.active_action_ids
        or bridge.inference_lane is not None
    ):
        raise Stage28NativePaperLinkHold("original A/B owner or fork/Paper scope mismatch")
    for sid in ("A", "B"):
        session = bridge.sessions[sid]
        evidence = bridge.last_login_evidence[sid]
        owner = bridge.owners[sid]
        if (
            bridge.lifecycle.view(sid).status is not Presence.ONLINE
            or session.started.session_id != evidence.native_session_id
            or session.started.session_id in forbidden_native_sessions
            or session.process_returncode is not None
            or type(session.owned_child_pid) is not int
            or session.owned_child_pid <= 0
            or bridge.physical.current_native_sessions[sid]
            != evidence.native_session_id
            or bridge.cognitive_work is None
            or bridge.cognitive_work.owners[sid] is not owner
            or bridge.cognitive_work.current_scope(sid)[1]
            != evidence.native_session_id
            or owner.native_session_id != evidence.native_session_id
            or owner.fresh_native_observation_required
            or evidence.world_id != boot.source_world_id
            or evidence.branch_id != boot.fork_branch_id
            or evidence.paper_session_id != boot.paper_session_id
            or evidence.world_epoch != boot.world_epoch
            or not evidence.observation_ref or not evidence.new_native_source_verified
            or not evidence.physical_wal_clear or not evidence.stale_gpu_fenced
            or not evidence.stale_transport_fenced
            or evidence.action_issue_authorized
        ):
            raise Stage28NativePaperLinkHold(
                "one original Self native, probe, owner or WAL source unqualified"
            )
    if bridge.sessions["A"].started.session_id == bridge.sessions["B"].started.session_id:
        raise Stage28NativePaperLinkHold("A/B live native collision")

    try:
        # Prove both Paper presence events occurred BEFORE a new owner-bound
        # tick ACK in the SAME Paper Popen; log is read *again* after ACK.
        tick = paper.tick_readback(boot.paper_session_id)
        log = paper.read_owned_log(boot.paper_session_id)
        process = paper._assert_owned()
    except (OSError, ValueError, RuntimeError) as exc:
        raise Stage28NativePaperLinkHold("live Paper tick/readback unavailable") from exc
    if (
        type(tick) is not PaperTickReceipt
        or tick.server_session_id != boot.paper_session_id
        or type(tick.tick) is not int or tick.tick < boot.boot_tick
        or not tick.source_ref.startswith(
            "paper-main-thread:p0d:" + boot.paper_boot_id + ":"
        )
        or process.pid != boot.paper_pid
    ):
        raise Stage28NativePaperLinkHold("Paper tick not from original new boot")
    nonce = re.fullmatch(
        r"paper-main-thread:p0d:([A-Za-z0-9-]+):([A-Za-z0-9-]+):sha256:[a-f0-9]{64}",
        tick.source_ref,
    )
    if nonce is None or nonce.group(1) != boot.paper_boot_id:
        raise Stage28NativePaperLinkHold("new Paper tick nonce source invalid")
    marker = (
        f"P0D_TICK_ACK nonce={nonce.group(2)} boot={boot.paper_boot_id} "
        f"session={boot.paper_session_id} world={boot.source_world_id} "
        f"tick={tick.tick} source=PAPER_MAIN_THREAD"
    )
    if i1_require_complete_paper_prefix:
        # The original Paper Popen is already verified, and the original
        # bytes remain in its attached .log. Only the I1 bounded read-only
        # CPU path requires a line-complete digest for independent replay.
        # Default Stage28 linkage stays byte-identical.
        log = i1_complete_owned_paper_prefix(
            log, ack_marker=marker.encode("utf-8"),
        )
    if marker not in log.decode("utf-8", errors="replace"):
        raise Stage28NativePaperLinkHold("new Paper post-native ACK missing from owned log")
    digest = hashlib.sha256(log).hexdigest()
    try:
        trace = parse_owned_paper_resident_trace(
            owned_paper_session_id=boot.paper_session_id,
            expected_world_uuid=boot.source_world_id,
            owned_paper_log=log,
            log_ref=(
                "paper-owned-log:" + boot.paper_session_id
                + ":sha256:" + digest
            ),
        )
    except (ValueError, RuntimeError) as exc:
        raise Stage28NativePaperLinkHold("Paper resident provenance cannot be parsed") from exc
    # Independent resident plugin uses a different plugin-boot UUID than
    # TickWitness. Both come from the SAME owned Paper Popen stdout.
    if not trace.boot_id or trace.paper_session_id != boot.paper_session_id:
        raise Stage28NativePaperLinkHold("foreign Paper resident boot")
    links: list[Stage28NativePaperBodyLink] = []
    actors: set[str] = set()
    for sid in ("A", "B"):
        expected_name = bridge.configs[sid].username
        events = [event for event in trace.events if event.name == expected_name]
        if (
            not events or events[0].event != "JOIN"
            or len([event for event in events if event.event == "JOIN"]) != 1
            or any(event.event == "QUIT" for event in events)
            or not any(event.event in ("PRESENT", "MOVE")
                       and event.line > events[0].line for event in events)
            or len({event.actor_uuid for event in events}) != 1
            or events[0].actor_uuid in actors
            or events[0].tick < boot.boot_tick
            or events[-1].tick > tick.tick
        ):
            raise Stage28NativePaperLinkHold(
                "Paper independent JOIN/PRESENT clock/order incomplete"
            )
        actors.add(events[0].actor_uuid)
        native = bridge.last_login_evidence[sid]
        links.append(Stage28NativePaperBodyLink(
            self_id=sid,
            native_session_id=native.native_session_id,
            native_probe_ref=native.observation_ref,
            native_world_time_tick=native.observed_world_tick,
            paper_session_id=boot.paper_session_id,
            tick_boot_id=boot.paper_boot_id,
            presence_boot_id=trace.boot_id,
            paper_observed_tick=events[-1].tick,
            paper_tick_source_ref=tick.source_ref,
            paper_log_sha256=digest,
            paper_actor_uuid=events[0].actor_uuid,
        ))
    # Advance the current lifecycle with a *Paper* clock, never native time.
    current = bridge.lifecycle.world_tick(
        paper_session_id=boot.paper_session_id,
        tick=tick.tick,
        source_ref=tick.source_ref,
    )
    return current, tuple(links)
