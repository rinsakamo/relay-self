"""W4 observation-only DEV: local lifetime join, not a World grant.

Read-only association of an existing PREWORLD inventory, typed Node probes,
the original Java collector's marker and post-shutdown local receipt.
Caller-supplied timestamps/order and owner-produced receipts are NOT an
independent witness or actual Java/Node process-custody qualification.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyDevReadback,
    ObservationOnlyRawWorldMarker,
)
from adapters.mineflayer.self_world_observation_only_entry import (
    ObservationOnlyEntryInventory,
)
from adapters.mineflayer.self_world_stage_w3_capture import (
    W3CaptureRejected,
    audit_w3_sealed_stdout,
)


class ObservationOnlyLifetimeBlocked(ValueError):
    """One local source or teardown binding is absent or inconsistent."""


@dataclass(frozen=True, slots=True)
class ObservationOnlyLocalLifetime:
    schema: str
    exact_head: str
    session_id: str
    before_seq: int
    after_seq: int
    local_world_marker_sha256: str
    local_game_time: int
    classification: str = "LOCAL_PRODUCER_LIFETIME_ONLY"
    node_stdout_scope: str = "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP"
    java_console_scope: str = "SINGLE_JAVA_COLLECTOR_LOCAL_CONTENT"
    external_grant_verified: bool = False
    external_owner_attested: bool = False
    external_source_qualified: bool = False
    actual_pid_port_disposal_attested: bool = False
    physical_run_permitted: bool = False
    qualification_approved: bool = False
    science_qualified: bool = False
    action_count: int = 0
    outcome_count: int = 0
    s10_update_count: int = 0


def join_observation_only_local_lifetime(
    *, inventory: ObservationOnlyEntryInventory,
    readback: ObservationOnlyDevReadback,
    marker: ObservationOnlyRawWorldMarker,
    close: dict[str, Any], node_raw_root: Path,
) -> ObservationOnlyLocalLifetime:
    """Reconcile content boundaries without instantiating or owning a Process.

    Source types are exact to prevent fake subclass flags from granting access.
    Any successful join still reports NO physical World, grant, S10 or science
    qualification. There is deliberately no runner/callback/confirm argument.
    """
    if (
        type(inventory) is not ObservationOnlyEntryInventory
        or inventory.schema != "W4_OBSERVATION_ONLY_PREWORLD_INVENTORY_V1"
        or inventory.disposition != "PREWORLD_BLOCKED"
        or re.fullmatch(r"[0-9a-f]{40}", inventory.exact_head) is None
        or re.fullmatch(r"[0-9a-f]{64}", inventory.jar_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", inventory.bridge_sha256) is None
        or inventory.target_version != "1.21.8"
        or inventory.binding_scope != "LOCAL_CHECKOUT_AND_OPERATOR_SUPPLIED_JAR_PIN_ONLY"
        or any(getattr(inventory, field) is not False for field in (
            "java_process_launched", "node_process_launched",
            "world_provisioned", "external_grant_verified",
            "external_source_qualified", "physical_run_permitted",
            "science_qualified",
        ))
        or any(type(getattr(inventory, field)) is not int
               or getattr(inventory, field) != 0 for field in (
                   "action_count", "outcome_count", "s10_update_count",
               ))
    ):
        raise ObservationOnlyLifetimeBlocked("unqualified PREWORLD inventory")
    if (
        type(readback) is not ObservationOnlyDevReadback
        or not readback.session_id
        or readback.scope != "SYNTHETIC_OR_LOCAL_CONSOLE_NOT_EXTERNAL_CUSTODY"
        or type(readback.spawn_seq) is not int
        or type(readback.after_seq) is not int
        or type(readback.before_seq) is not int
        or not 0 <= readback.spawn_seq < readback.before_seq < readback.after_seq
        or re.fullmatch(r"[0-9a-f]{64}", readback.marker_raw_sha256) is None
        or readback.before_source != f"{readback.session_id}:{readback.before_seq}"
        or readback.after_source != f"{readback.session_id}:{readback.after_seq}"
        or any(getattr(readback, field) is not False for field in (
            "physical_run_permitted", "qualification_approved", "science_qualified",
        ))
        or any(type(getattr(readback, field)) is not int
               or getattr(readback, field) != 0 for field in (
                   "action_count", "outcome_count", "s10_update_count",
               ))
    ):
        raise ObservationOnlyLifetimeBlocked("unqualified typed Node observation")
    if (
        type(marker) is not ObservationOnlyRawWorldMarker
        or marker.raw_sha256 != readback.marker_raw_sha256
        or type(marker.local_game_time) is not int
        or marker.local_game_time < 0
        or marker.local_game_time != readback.marker_local_game_time
        or type(marker.raw_start_byte) is not int or marker.raw_start_byte < 0
        or type(marker.raw_end_byte) is not int
        or marker.raw_end_byte <= marker.raw_start_byte
        or marker.local_collector_only is not True
        or marker.external_world_attested is not False
    ):
        raise ObservationOnlyLifetimeBlocked("collector marker not bound to Node window")
    if (
        type(close) is not dict
        or close.get("schema") != "W4_OBSERVATION_ONLY_LOCAL_CLOSE_DEV_V1"
        or close.get("classification") != "LOCAL_PRODUCER_CLOSE_ONLY"
        or type(close.get("errors")) is not list
        or close["errors"] != []
        or type(close.get("node_exit")) is not int or close["node_exit"] != 0
        or type(close.get("java_exit")) is not int or close["java_exit"] != 0
        or close.get("java_stop_requested") is not True
        or close.get("java_collector_settled") is not True
        or any(close.get(flag) is not False for flag in (
            "external_custody_qualified", "physical_run_permitted",
            "science_qualified",
        ))
        or any(type(close.get(field)) is not int or close[field] != 0 for field in (
            "action_count", "outcome_count", "s10_update_count",
        ))
    ):
        raise ObservationOnlyLifetimeBlocked("local Node/Java/collector close not complete")
    receipt = close.get("node_stdout_receipt")
    if not isinstance(node_raw_root, Path) or not node_raw_root.is_absolute():
        raise ObservationOnlyLifetimeBlocked("absolute original W3 raw root required")
    try:
        audit = audit_w3_sealed_stdout(node_raw_root)
    except (W3CaptureRejected, OSError) as exc:
        raise ObservationOnlyLifetimeBlocked("unaltered local Node raw archive missing") from exc
    if receipt != audit:
        raise ObservationOnlyLifetimeBlocked("Node close receipt differs from audited raw bytes")
    if (
        type(receipt) is not dict
        or receipt.get("schema") != "relay-self-w3-node-stdout-v0"
        or receipt.get("scope") != "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP"
        or receipt.get("status") != "COMPLETE_NODE_STDOUT"
        or receipt.get("session_id") != readback.session_id
        or type(receipt.get("first_seq")) is not int or receipt["first_seq"] != 0
        or type(receipt.get("last_seq")) is not int
        or receipt["last_seq"] <= readback.after_seq
        or type(receipt.get("shutdown_ack_count")) is not int
        or receipt["shutdown_ack_count"] != 1
        or receipt.get("eof_observed") is not True
        or type(receipt.get("process_exit_code")) is not int
        or receipt["process_exit_code"] != 0
        or receipt.get("seal_reason") != "clean_shutdown"
        or receipt.get("capture_fault") is not None
        or any(receipt.get(flag) is not False for flag in (
            "minecraft_tcp_packets_attested",
            "external_source_independence_attested",
            "s10_commit_permitted", "physical_wait_permitted",
            "science_qualified",
        ))
    ):
        raise ObservationOnlyLifetimeBlocked("raw Node receipt not bound to observation")
    return ObservationOnlyLocalLifetime(
        schema="W4_OBSERVATION_ONLY_LOCAL_LIFETIME_JOIN_V1",
        exact_head=inventory.exact_head, session_id=readback.session_id,
        before_seq=readback.before_seq, after_seq=readback.after_seq,
        local_world_marker_sha256=marker.raw_sha256,
        local_game_time=marker.local_game_time,
    )
