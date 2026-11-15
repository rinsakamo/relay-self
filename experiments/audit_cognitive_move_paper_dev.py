"""Replay a MOVE/Paper DEV evidence bundle without contacting World or LLM.

This tool never starts Paper, issues a physical action or authenticates an
operator-provided server log. It independently rechecks source-qualified,
hashed WAL/native/Paper originals before marking a *DEV* evidence join.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.python_protocol import MineflayerPosition
from experiments.cognitive_move_paper_witness_dev import (
    _properties,
    qualify_paper_move_trace,
)
from relay_self.physical_action_journal import PhysicalActionJournal


class MoveEvidenceAuditError(ValueError):
    """One or more original artifacts are absent, foreign or internally inconsistent."""


def _expect(ok: bool, message: str) -> None:
    if not ok:
        raise MoveEvidenceAuditError(message)


def _position(data: object) -> MineflayerPosition:
    _expect(isinstance(data, dict) and set(data) == {"x", "y", "z"},
            "position needs exactly XYZ")
    _expect(all(type(v) in (int, float) and math.isfinite(v)
                for v in data.values()), "native position not finite")
    return MineflayerPosition(data["x"], data["y"], data["z"])


def _xyz(values: object) -> MineflayerPosition:
    _expect(type(values) is list and len(values) == 3,
            "stored WAL XYZ list missing")
    return _position(dict(zip(("x", "y", "z"), values)))


def _read(path: Path, max_bytes: int) -> bytes:
    _expect(not path.is_symlink() and path.is_file(), "missing/unsafe original evidence file")
    _expect(0 < path.stat().st_size <= max_bytes, "evidence file exceeds bounded size")
    data = path.read_bytes()
    _expect(0 < len(data) <= max_bytes, "inconsistent original artifact")
    return data


def audit_move_paper_bundle(
    evidence: dict[str, object],
    *,
    journal: PhysicalActionJournal,
    raw_trace: bytes,
    raw_paper_log: bytes,
    expected_self_id: str,
    expected_actor_uuid: str,
    expected_world_uuid: str,
    expected_username: str,
) -> dict[str, object]:
    """Independent offline replay. A passing bundle is NEVER QUAL or real-world proof."""
    _expect(isinstance(evidence, dict), "CLI evidence must be one JSON object")
    _expect(evidence.get("evidence_class") == "REAL_LLM_AND_NATIVE_WORLD_DEV_ATTEMPT",
            "missing completed DEV evidence status")
    _expect(evidence.get("qualification") == "NOT_CLAIMED",
            "unexpected QUAL status in DEV evidence")
    _expect(
        evidence.get("status") == "NATIVE_MOVE_PROGRESS_STOP_READBACK_DEV_ONLY"
        and evidence.get("physical_move_dev_selected") is True
        and evidence.get("initial_skill_ir") == "MOVE@1"
        and evidence.get("initial_skill_step_status") == "PROPOSED_NOT_ISSUED"
        and evidence.get("initial_skill_evaluation_status") == "YIELD_EVALUATION"
        and evidence.get("action_outcome_count") == 1
        and evidence.get("physical_journal_unresolved") is False,
        "completed original MOVE/L0/WAL evidence not established",
    )
    _expect(
        evidence.get("paper_move_position_stable_8_ticks") is True
        and evidence.get("native_move_paper_settled_attested") is False
        and evidence.get("native_move_arrival_attested") is False,
        "Paper stability not independently recorded or overclaimed",
    )
    _expect(
        evidence.get("physical_fence") == "PREISSUE_WAL_MOVE_DEV"
        and evidence.get("physical_actionport_preissue_wal") == "FSYNC_CAS_MOVE_DEV",
        "original action did not use shared preissue MOVE WAL",
    )
    _expect(journal._body["self_id"] == expected_self_id and not journal.unresolved,
            "foreign Self / unresolved journal")
    rows = list(journal.records)
    _expect(
        rows and evidence.get("physical_journal_records") == rows,
        "original Self WAL differs from CLI evidence",
    )
    row = rows[-1]
    _expect(
        row["status"] == "NATIVE_MOVE_PROGRESS_STOP_READBACK"
        and row["capability"] == "MOVE",
        "last physical event is not closed bounded MOVE",
    )
    action_id = row["action_id"]
    _expect(
        evidence.get("physical_move_parent_action_id") == action_id
        and row["session_id"] == evidence.get("world_session")
        and evidence.get("native_actions") == [
            {"action_id": action_id, "state": "outcome"},
        ],
        "MOVE native parent/World/ActionLifecycle mismatch",
    )
    selected = evidence.get("selected")
    target = evidence.get("move_target")
    _expect(isinstance(selected, dict) and isinstance(target, dict),
            "missing original selected MOVE or source-bound geometry")
    _expect(
        selected.get("skill_id") == "MOVE"
        and selected.get("skill_version") == 1
        and selected.get("goal_id") == "EXPLORE_WORLD"
        and selected.get("target_ref") == row["target_ref"]
        and target.get("target_ref") == row["target_ref"]
        and target.get("scope") == {
            "self_id": expected_self_id,
            "world_session_id": row["session_id"],
        },
        "L1 selected target / original Self/World scope mismatch",
    )
    _expect(
        target.get("native_seq") == row["probe_seq"]
        and target.get("native_request_id") == row["probe_request_id"]
        and target.get("native_probe_provenance", {}).get("reference")
        == row["source_ref"],
        "L1 selected native probe not preserved in original WAL",
    )
    _expect(
        _position(target["native_position"]) == _xyz(row["motion"]["start"])
        and _position(target["destination_position"]) == _xyz(row["motion"]["target"]),
        "selected geometry differs from persisted native MOVE source",
    )
    native_effects = evidence.get("native_effect_receipts")
    _expect(type(native_effects) is list and len(native_effects) == 3,
            "all three typed native MOVE ACKs required")
    for effect, step, kind, seq in zip(
        native_effects,
        ("look", "forward", "stop"),
        ("look", "set_control", "clear_controls"),
        row["effect_seqs"],
    ):
        _expect(
            type(effect) is dict
            and effect.get("action_id") == action_id + "-" + step
            and effect.get("effect") == kind
            and effect.get("result") == "applied"
            and effect.get("session_id") == row["session_id"]
            and effect.get("native_seq") == seq,
            "native MOVE effect receipt uncorrelated with WAL",
        )
    observed = evidence.get("native_move_progress_observation")
    afters = evidence.get("native_move_stop_probes")
    _expect(
        type(observed) is dict and type(afters) is list and len(afters) == 2,
        "full native progress/STOP observations missing",
    )
    for item, seq, pos in (
        (observed, row["motion"]["progress_seq"], row["motion"]["progress"]),
        (afters[0], row["motion"]["stop_probe_seqs"][0],
         row["motion"]["stop_probe_positions"][0]),
        (afters[1], row["motion"]["stop_probe_seqs"][1],
         row["motion"]["stop_probe_positions"][1]),
    ):
        _expect(
            type(item) is dict
            and item.get("evidence_format") == "TYPED_DECODED_MINEFLAYER_OBSERVATION_V1"
            and type(item.get("observation")) is dict,
            "native STOP decoded source record malformed",
        )
        obs = item["observation"]
        _expect(
            obs.get("session_id") == row["session_id"]
            and obs.get("seq") == seq
            and _position(obs["snapshot"]["position"]) == _xyz(pos),
            "native STOP geometry/source does not match WAL",
        )
    _expect(
        observed["observation"].get("kind") == "move"
        and all(item["observation"].get("kind") == "probe" for item in afters)
        and afters[0]["observation"].get("request_id") == action_id + "-after-stop-00"
        and afters[1]["observation"].get("request_id") == action_id + "-after-stop-01",
        "native MOVEMENT / STOP readbacks have wrong source requests",
    )
    _expect(type(raw_trace) is bytes and type(raw_paper_log) is bytes,
            "original Paper trace and owned log bytes required")
    fields, _ = _properties(raw_trace, trace=True)
    _expect(
        fields["action_id"] == action_id
        and fields["native_session_id"] == row["session_id"],
        "Paper trace claimed another native Action/session",
    )
    paper = qualify_paper_move_trace(
        raw_trace, nonce=fields["nonce"],
        world_uuid=expected_world_uuid, actor_uuid=expected_actor_uuid,
        action_id=action_id, native_session_id=row["session_id"],
        native_start=_xyz(row["motion"]["start"]),
        native_target=_xyz(row["motion"]["target"]),
        paper_owned_log=raw_paper_log,
        expected_username=expected_username,
    )
    _expect(
        evidence.get("paper_move_tick_proof") == asdict(paper)
        and paper.actor_name_joined is True
        and paper.paper_position_stable_8_ticks is True,
        "replayed Paper tick evidence differs from original CLI proof",
    )
    _expect(
        float(evidence.get("native_move_progress_m", -1)) >= .25
        and 0 <= float(evidence.get("native_move_stop_residual_m", -1)) <= .05,
        "native movement/STOP qualification not retained",
    )
    return {
        "classification": "PAPER_8TICK_POSITION_STABILITY_DEV_BUNDLE_RECHECKED",
        "qualifying_real_world": False,
        "independent_process_and_actor_authentication": False,
        "causal_paper_stop_ack_attested": False,
        "checkpoint_resume_authorized": False,
        "world_session_id": row["session_id"],
        "self_id": expected_self_id,
        "action_id": action_id,
        "paper_world_uuid": expected_world_uuid,
        "paper_actor_uuid": expected_actor_uuid,
        "paper_login_name": expected_username,
        "paper_boot_id": paper.boot_id,
        "paper_arm_tick": paper.arm_tick,
        "paper_stop_mark_tick": paper.stop_mark_tick,
        "paper_stable_start_tick": paper.stable_start_tick,
        "paper_stable_end_tick": paper.stable_end_tick,
        "paper_stable_max_3d_drift_m": paper.paper_residual_max_m,
        "paper_raw_trace_sha256": paper.raw_sha256,
        "paper_owned_log_sha256": hashlib.sha256(raw_paper_log).hexdigest(),
        "journal_digest": journal.digest,
        "status": "OFFLINE_REAUDIT_ONLY_NO_REAL_WORLD_QUAL_CLAIM",
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only MOVE/Paper DEV artifact re-audit")
    for flag in ("evidence", "wal", "paper-trace", "paper-owned-log",
                 "self-id", "actor-uuid", "world-uuid", "mc-username"):
        p.add_argument("--" + flag, required=True)
    p.add_argument("--output", help="write immutable JSON audit result")
    args = p.parse_args()
    try:
        source = _read(Path(args.evidence), 2_000_000)
        evidence = json.loads(source)
        wal_raw = _read(Path(args.wal), 2_000_000)
        journal = PhysicalActionJournal.restore(Path(args.wal), self_id=args.self_id)
        result = audit_move_paper_bundle(
            evidence, journal=journal,
            raw_trace=_read(Path(args.paper_trace), 16384),
            raw_paper_log=_read(Path(args.paper_owned_log), 8_000_000),
            expected_self_id=args.self_id,
            expected_actor_uuid=args.actor_uuid,
            expected_world_uuid=args.world_uuid,
            expected_username=args.mc_username,
        )
        result["evidence_json_sha256"] = hashlib.sha256(source).hexdigest()
        result["wal_json_sha256"] = hashlib.sha256(wal_raw).hexdigest()
        if args.output:
            output = Path(args.output)
            _expect(not output.exists() and not output.is_symlink(),
                    "audit result must be new immutable path")
            with output.open("x", encoding="utf-8") as file:
                json.dump(result, file, indent=2, sort_keys=True, allow_nan=False)
                file.write("\n")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as exc:
        print(json.dumps({
            "classification": "HOLD_EVIDENCE_INSUFFICIENT",
            "qualifying_real_world": False,
            "error": f"{type(exc).__name__}: {str(exc)[:280]}",
        }), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
