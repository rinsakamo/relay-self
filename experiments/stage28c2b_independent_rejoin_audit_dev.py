"""Stage28c2b: independent, READ-ONLY audit of one recovered real Paper run.

This verifier MUST run in a fresh Python process after the runner exits.
It never starts Paper/native/Gemma, issues Actions or modifies any
immutable source. Its success is DEV source correlation, not SCIENCE/QUAL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
    parse_mineflayer_line,
)
from experiments.stage28c2b_real_recovered_rejoin_dev import (
    _FORK_BRANCH,
    _SOURCE_COMMITTED_SHA,
    _SOURCE_WORLD,
    inspect_real_recovered_sources,
)
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.resident_paper_presence_join_dev import (
    parse_owned_paper_resident_trace,
)
from relay_self.stage28c2b_execution_copy_dev import _inventory


class Stage28c2bIndependentAuditHold(RuntimeError):
    """Original Paper/native/typed owner source did not survive independent audit."""


def _sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise Stage28c2bIndependentAuditHold("audit evidence file missing/linked")
    h = hashlib.sha256()
    with path.open("rb") as f:
        while data := f.read(1024 * 1024):
            h.update(data)
    return h.hexdigest()


def _verify_main_thread_ack(
    executable: Path, *, paper_session: str, world_id: str,
    boot_id: str, ref: str, tick: int, paper_stdout: bytes,
) -> None:
    """Re-read original plugin ACK bytes, digest and exact owned Paper log."""
    match = re.fullmatch(
        r"paper-main-thread:p0d:([A-Za-z0-9-]+):"
        r"([A-Za-z0-9-]+):sha256:([a-f0-9]{64})",
        ref,
    )
    if (
        match is None or match.group(1) != boot_id
        or type(tick) is not int or tick < 0
    ):
        raise Stage28c2bIndependentAuditHold("Paper tick reference/clock invalid")
    nonce, digest = match.group(2), match.group(3)
    source = (
        Path(executable) / "plugins" / "P0BRecorder" / "p0d-ticks"
        / "acks" / (nonce + ".ack")
    )
    if _sha(source) != digest:
        raise Stage28c2bIndependentAuditHold("original Paper plugin ACK bytes changed")
    try:
        rows = source.read_text(encoding="utf-8").splitlines()
        fields = dict(line.split("=", 1) for line in rows)
    except (UnicodeError, ValueError) as exc:
        raise Stage28c2bIndependentAuditHold("Paper ACK not parseable") from exc
    if (
        len(rows) != len(fields)
        or set(fields) != {
            "boot_id", "nonce", "paper_tick",
            "server_session_id", "source", "world_uuid",
        }
        or fields["boot_id"] != boot_id
        or fields["nonce"] != nonce
        or fields["paper_tick"] != str(tick)
        or fields["server_session_id"] != paper_session
        or fields["source"] != "PAPER_MAIN_THREAD"
        or fields["world_uuid"] != world_id
    ):
        raise Stage28c2bIndependentAuditHold("Paper ACK bytes/owned source mismatch")
    marker = (
        "P0D_TICK_ACK nonce=" + nonce
        + " boot=" + boot_id
        + " session=" + paper_session
        + " world=" + world_id
        + " tick=" + str(tick)
        + " source=PAPER_MAIN_THREAD"
    )
    if marker.encode() not in paper_stdout:
        raise Stage28c2bIndependentAuditHold(
            "Paper ACK not reproduced in this original Popen stdout"
        )


def independently_audit_recovered_real_rejoin(
    result_path: Path, *, generation: Path, restored: Path,
    stage28b_evidence: Path, executable: Path,
    expected_gemma_posts: int = 0,
) -> dict:
    """Audit frozen stdout/probes/WAL, *not* only success summary booleans."""
    path = Path(result_path)
    report = json.loads(path.read_bytes())
    evidence = path.parent
    expected = (
        "REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING"
    )
    if (
        report.get("schema") != 1
        or report.get("classification") != expected
        or report.get("independent_audit_pass") is not False
        or report.get("original_world_uuid") != _SOURCE_WORLD
        or report.get("original_committed_sha256") != _SOURCE_COMMITTED_SHA
        or report.get("fork_branch_id") != _FORK_BRANCH
        or report.get("real_world_trials") != 1
        or type(expected_gemma_posts) is not int
        or expected_gemma_posts not in (0, 2)
        or report.get("real_gemma_post") != expected_gemma_posts
        or report.get("real_action_issued") != 0
        or report.get("real_peer_sent") != 0
        or report.get("physical_action_issue_authorized") is not False
        or report.get("fresh_l1_run") is not (expected_gemma_posts == 2)
        or report.get("cleanup_uncertain")
        or report.get("raw_source_audit_uncertain")
        or report.get("original_stage28b_reverified") is not True
    ):
        raise Stage28c2bIndependentAuditHold("capture was not terminal and effect-free")
    original, state = inspect_real_recovered_sources(
        generation, restored, stage28b_evidence,
    )
    inventory = "".join(
        f"{digest}  {name}\n" for name, digest in _inventory(Path(restored))
    ).encode()
    if (evidence / "execution-copy-prestart-SHA256SUMS").read_bytes() != inventory:
        raise Stage28c2bIndependentAuditHold("prestart copy or restored original differs")
    if (
        report.get("original_history") is None
        or report["original_history"]["historical_native_sessions"]
        != list(original.historical_native_sessions)
        or state.receipt.source_committed_sha256 != _SOURCE_COMMITTED_SHA
        or state.receipt.fork_branch_id != _FORK_BRANCH
    ):
        raise Stage28c2bIndependentAuditHold("old A/B cognitive/source lineage differs")
    paper_session = report.get("paper_session_id")
    paper_boot = report.get("paper_boot")
    stopped = report.get("paper_stopped")
    links = report.get("fresh_body_links")
    logins = report.get("native_login_evidence")
    pids = report.get("new_native_pids")
    natives = report.get("raw_native_file_sha256")
    if (
        type(paper_session) is not str
        or not paper_session.startswith("paper-owned-")
        or type(paper_boot) is not dict
        or paper_boot.get("paper_session_id") != paper_session
        or paper_boot.get("source_world_id") != _SOURCE_WORLD
        or paper_boot.get("fork_branch_id") != _FORK_BRANCH
        or paper_boot.get("committed_sha256") != _SOURCE_COMMITTED_SHA
        or paper_boot.get("old_ticks_directly_comparable") is not False
        or type(paper_boot.get("boot_tick")) is not int
        or type(paper_boot.get("paper_pid")) is not int
        or type(stopped) is not dict
        or stopped.get("old_server_session_id") != paper_session
        or stopped.get("process_exit_code") != 0
        or stopped.get("all_dimensions_saved") is not True
        or type(links) is not list or len(links) != 2
        or type(logins) is not dict or set(logins) != {"A", "B"}
        or type(pids) is not dict or set(pids) != {"A", "B"}
        or type(natives) is not dict or set(natives) != {"RelayA", "RelayB"}
    ):
        raise Stage28c2bIndependentAuditHold("original owned Paper/native receipt missing")
    if (
        len(set(pids.values())) != 2
        or set(pids.values()) & {paper_boot["paper_pid"]}
        or any(type(pid) is not int or pid <= 0 for pid in pids.values())
    ):
        raise Stage28c2bIndependentAuditHold("native/Paper PID collision")

    # Independent parser on the actual final owned-Paper stdout, rather
    # than trusting the runner's Python dataclass.
    final_paper = evidence / (paper_session + ".log")
    frozen = evidence / "prestop-paper-resident-owned.log"
    raw_paper = final_paper.read_bytes()
    if (
        _sha(frozen) != report.get("final_paper_resident_log_sha256")
        or not raw_paper.startswith(frozen.read_bytes())
        or b"Saved the game" not in raw_paper[len(frozen.read_bytes()):]
        or b"Stopping server" not in raw_paper[len(frozen.read_bytes()):]
    ):
        raise Stage28c2bIndependentAuditHold("Paper resident source not archived")
    full = parse_owned_paper_resident_trace(
        owned_paper_session_id=paper_session,
        expected_world_uuid=_SOURCE_WORLD,
        owned_paper_log=raw_paper,
        log_ref="paper-owned-original:" + paper_session + ":sha256:" + _sha(final_paper),
    )
    if full.boot_id != report.get("final_paper_resident_boot_id"):
        raise Stage28c2bIndependentAuditHold("Paper resident boot mismatched")
    for sid in ("A", "B"):
        name = "Relay" + sid
        events = [x for x in full.events if x.name == name]
        if (
            not events or events[0].event != "JOIN"
            or events[-1].event != "QUIT"
            or len([x for x in events if x.event == "JOIN"]) != 1
            or len([x for x in events if x.event == "QUIT"]) != 1
            or not any(x.event in ("PRESENT", "MOVE") for x in events)
            or len({x.actor_uuid for x in events}) != 1
        ):
            raise Stage28c2bIndependentAuditHold(
                "independent Paper A/B JOIN/PRESENT/QUIT incomplete"
            )
    link_map = {link["self_id"]: link for link in links}
    if set(link_map) != {"A", "B"}:
        raise Stage28c2bIndependentAuditHold("native/Paper A/B links not unique")
    if link_map["A"]["paper_actor_uuid"] == link_map["B"]["paper_actor_uuid"]:
        raise Stage28c2bIndependentAuditHold("Paper actors collided")
    old_ids = set(original.historical_native_sessions)
    live_ids = {logins[sid]["native_session_id"] for sid in ("A", "B")}
    if len(live_ids) != 2 or live_ids & old_ids:
        raise Stage28c2bIndependentAuditHold("historical native reused")
    for sid in ("A", "B"):
        link = link_map[sid]
        native = logins[sid]
        if (
            link["native_session_id"] != native["native_session_id"]
            or link["native_probe_ref"] != native["observation_ref"]
            or link["native_world_time_tick"] != native["observed_world_tick"]
            or link["paper_session_id"] != paper_session
            or link["tick_boot_id"] != paper_boot["paper_boot_id"]
            or link["presence_boot_id"] != full.boot_id
            or link["clocks_numerically_comparable"] is not False
            or link["physical_action_issue_authorized"] is not False
            or native["paper_session_id"] != paper_session
            or native["world_id"] != _SOURCE_WORLD
            or native["branch_id"] != _FORK_BRANCH
            or native["world_epoch"] != paper_boot["world_epoch"]
            or native["action_issue_authorized"] is not False
        ):
            raise Stage28c2bIndependentAuditHold("native/Paper body source disagreement")
        paper_events = [x for x in full.events if x.name == "Relay" + sid]
        if (
            link["paper_actor_uuid"] != paper_events[0].actor_uuid
            or not paper_events[0].tick <= link["paper_observed_tick"]
            or link["paper_observed_tick"] < paper_boot["boot_tick"]
        ):
            raise Stage28c2bIndependentAuditHold("Paper event tick/identity mismatch")
        # Verify original NEW child raw stdout independently, rather than
        # accepting the runner's NativeLoginEvidence booleans.
        source = evidence / (
            "native-Relay" + sid + "-" + native["native_session_id"] + ".jsonl"
        )
        if _sha(source) != natives["Relay" + sid]:
            raise Stage28c2bIndependentAuditHold("native probe stdout altered")
        found = []
        lines = source.read_bytes().splitlines()
        for raw in lines:
            decoded = parse_mineflayer_line(raw.decode("utf-8"))
            if decoded.session_id != native["native_session_id"]:
                raise Stage28c2bIndependentAuditHold("foreign original native stdout")
            if isinstance(decoded, MineflayerEffectResult):
                raise Stage28c2bIndependentAuditHold("physical effect in passive trial")
            if isinstance(decoded, MineflayerObservation) and decoded.kind == "probe":
                if decoded.request_id == native["observation_ref"]:
                    if decoded.snapshot.time is None:
                        raise Stage28c2bIndependentAuditHold(
                            "original native raw World clock absent"
                        )
                    day = decoded.snapshot.time
                    observed_time = day.day * 24000 + day.time_of_day
                    if observed_time != native["observed_world_tick"]:
                        raise Stage28c2bIndependentAuditHold(
                            "native World clock/raw stdout disagrees"
                        )
                    found.append(decoded)
        if len(found) != 1:
            raise Stage28c2bIndependentAuditHold(
                "exact original native request-correlated probe absent"
            )
        canonical_probe = json.loads(json.dumps(asdict(found[0])))
        if report.get("owner_worldbody_observations", {}).get(sid) != canonical_probe:
            raise Stage28c2bIndependentAuditHold("owner WorldBody differs from raw native probe")
        retirement = report["retirement_" + sid]
        if (
            retirement["self_id"] != sid
            or retirement["native_session_id"] != native["native_session_id"]
            or retirement["world_epoch"] != paper_boot["world_epoch"]
            or retirement["native_terminated"] is not True
            or retirement["physical_wal_clear"] is not True
            or retirement["physical_issuer_revoked"] is not True
            or retirement["no_physical_inflight"] is not True
            or retirement["stale_gpu_fenced"] is not True
            or retirement["peer_transport_drained"] is not True
            or retirement["action_issue_authorized"] is not False
        ):
            raise Stage28c2bIndependentAuditHold(
                "original native issuer/retirement incomplete"
            )
        source_cognition = load_persistent_cognition(
            Path(generation) / "selves" / sid / "cognition.json"
        )
        copied_cognition = load_persistent_cognition(
            Path(executable) / "selves" / sid / "cognition.json"
        )
        if source_cognition != copied_cognition:
            raise Stage28c2bIndependentAuditHold(
                "original persistent cognition was replaced on real rejoin"
            )
        # A returned native probe may update Present, but cannot rewrite
        # original historical typed owner cut or unknown Action journal.
        PhysicalActionJournal.restore(
            Path(executable) / "selves" / sid / "physical-wal.json", self_id=sid,
        ).require_clear()
    quiescence = report.get("world_only_quiescence")
    if (
        type(quiescence) is not dict
        or quiescence.get("checked_self_ids") != ["A", "B"]
        or quiescence.get("world_epoch") != paper_boot["world_epoch"]
        or any(quiescence.get(key) is not True for key in (
            "original_physical_issuer_closed", "native_sessions_absent",
            "no_unresolved_physical_actions", "all_gpu_epochs_retired",
            "pending_peer_messages_empty",
        ))
        or quiescence.get("action_issue_authorized") is not False
    ):
        raise Stage28c2bIndependentAuditHold("original owner quiescence incomplete")
    # Paper main-thread nonce refs and session boot must match actual log,
    # with separate Paper tick values from native World day time.
    for ref, tick in [
        (paper_boot["paper_tick_source_ref"], paper_boot["boot_tick"]),
        (stopped["tick_source_ref"], stopped["logical_tick"]),
        *[(link["paper_tick_source_ref"], report["new_world_process_tick"])
          for link in links],
    ]:
        _verify_main_thread_ack(
            Path(executable), paper_session=paper_session,
            world_id=_SOURCE_WORLD, boot_id=paper_boot["paper_boot_id"],
            ref=ref, tick=tick, paper_stdout=raw_paper,
        )
    return {
        "classification": "REAL_RESTORED_WORLD_ORIGINAL_A_B_NATIVE_REJOIN_WORLDBODY_DEV",
        "generation_id": report["original_generation"],
        "world_id": _SOURCE_WORLD, "fork_branch_id": _FORK_BRANCH,
        "paper_session_id": paper_session,
        "verified_native_sessions": sorted(live_ids),
        "native_world_time_is_not_paper_tick": True,
        "real_gemma_post": expected_gemma_posts, "real_action_issued": 0,
        "fresh_l1_run": expected_gemma_posts == 2,
        "physical_action_issue_authorized": False,
        "60s_autosave_attested": False,
        "qual_go": False, "science_run": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--stage28b-evidence", type=Path, required=True)
    parser.add_argument("--execution-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = independently_audit_recovered_real_rejoin(
            args.result, generation=args.generation, restored=args.restored,
            stage28b_evidence=args.stage28b_evidence,
            executable=args.execution_dir,
        )
        print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    except Exception as exc:
        print(
            f"STAGE28C2B_INDEPENDENT_AUDIT_HOLD={type(exc).__name__}:{exc}",
            file=sys.stderr, flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
