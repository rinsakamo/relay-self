"""S2-B original S49 L0/Intent exact-epoch witness, NO MODEL (DEV).

Reuses S2-A's genuine single S49 runner and original S16 callback. An
extra read-only owner_epoch_readonly hook executes BEFORE existing live_probe,
then the already-built S2-A input is bound to that same native Python object.
This does not submit to S60, call Gemma or grant Action/Learning authority.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Awaitable, Callable

from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s537_s2a_l2_read_port import S2ASourceBoundObserver
from adapters.mineflayer.s537_s2b_original_owner_epoch import (
    S2BOriginalOwnerEpochBinder,
)
from tools.s537_s1_live_wb_m_dev import (
    _M_PIN,
    _WB_PIN,
    _original_owner_module,
)
from tools.s537_s2a_original_readonly_dev import run_s2a_original_dev


class S2BOwnerWitnessObserver(S2ASourceBoundObserver):
    """Original S49 epoch tap + original S2-A WB and S16, read-only."""

    def __init__(self) -> None:
        super().__init__(enabled=True)
        self.binder = S2BOriginalOwnerEpochBinder()
        self.bound = []

    def owner_epoch(self, reading, host, intent) -> None:
        self.binder.note_original_epoch(reading, host, intent)

    def observe(self, reading: MineflayerObservation) -> None:
        super().observe(reading)
        self.bound.append(self.binder.bind(self._inputs[-1], reading))

    def owner_epoch_readout(self) -> dict[str, object]:
        original = self.binder.bounded_row()
        s2a = self.s2a_readout()
        rows = [
            {
                "native_probe_seq": read.source_input.probe_seq,
                "request_id": read.source_input.request_id,
                "intent_id": read.intent_id,
                "intent_generation": read.context.intent_revision,
                "retained_revision": read.context.retained_revision,
                "preceding_action_id": read.source_input.preceding_action_id,
            }
            for read in self.bound
        ]
        accepted = (
            original["status"] == "RECORDED"
            and s2a["status"] == "RECORDED"
            and len(rows) == len(s2a["inputs"])
            and len(rows) == len(original["epochs"])
            and all(
                row["native_probe_seq"] == source["probe_seq"]
                and row["request_id"] == source["request_id"]
                and row["native_probe_seq"] == original_epoch["native_probe_seq"]
                and row["intent_generation"] == original_epoch["intent_generation"]
                and row["retained_revision"] == original_epoch["retained_revision"]
                for row, source, original_epoch in zip(
                    rows, s2a["inputs"], original["epochs"], strict=True,
                )
            )
        )
        return {
            "schema": "S537_S2B_S49_ORIGINAL_OWNER_READ_ONLY_DEV_V1",
            "status": "RECORDED" if accepted else "DEFERRED",
            "reason": (
                "original_owner_identity_and_same_predecision_input"
                if accepted else "owner_source_or_s16_not_admitted"
            ),
            "original_owner": original,
            "s2a_status": s2a["status"],
            "epoch_contexts": rows,
            "source_attested": False,
            "model_calls": 0,
            "s60_submissions": 0,
            "new_native_reads": 0,
            "new_action_issues": 0,
            "learning_updates": 0,
            "action_authority": False,
        }


async def run_s2b_owner_witness_dev(
    *,
    original_qualify: Callable[..., Awaitable[int]],
    report_path: Path,
    server_log: Path,
    observer: S2BOwnerWitnessObserver,
) -> tuple[int, dict[str, object]]:
    """One original S49 run with additional default-OFF read-only source tap."""
    async def same_original(*args, **kwargs):
        return await original_qualify(
            *args, owner_epoch_readonly=observer.owner_epoch, **kwargs,
        )

    code, s2a = await run_s2a_original_dev(
        original_qualify=same_original, report_path=report_path,
        server_log=server_log, observer=observer,
    )
    try:
        owner_readout = observer.owner_epoch_readout()
    except (ValueError, TypeError, AttributeError, KeyError):
        owner_readout = {
            "status": "DEFERRED",
            "reason": "original_owner_readback_failed",
        }
    accepted = (
        code == 0
        and s2a.get("status") == "RECORDED"
        and owner_readout["status"] == "RECORDED"
    )
    return code, {
        "schema": "S537_S2B_ORIGINAL_OWNER_EPOCH_RUN_DEV_V1",
        "status": "RECORDED" if accepted else "DEFERRED",
        "s2a_status": s2a.get("status"),
        "s2a": s2a,
        "owner_epoch": owner_readout,
        "model_calls": 0,
        "s60_submissions": 0,
        "source_attested": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only S2-B original owner context DEV; no Gemma",
    )
    parser.add_argument("--m-owner-dir", type=Path, required=True)
    parser.add_argument("--wb-owner-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--s2b-report", type=Path, required=True)
    parser.add_argument("--live-world-dev", action="store_true")
    args = parser.parse_args()
    if not (
        args.live_world_dev
        and os.environ.get("S537_S2B_OWNER_WITNESS_DEV_ONLY") == "1"
        and os.environ.get("S49_REAL_SERVER_CI") == "1"
        and os.environ.get("S49_COMPLETED_L0_DEV_ONLY") == "1"
        and not os.environ.get("NODE_OPTIONS")
    ):
        print(json.dumps({
            "status": "BLOCKED", "reason": "owner_witness_dev_gate_missing",
        }))
        return 2
    files = (args.report, args.server_log, args.s2b_report)
    if (
        any(
            not p.is_absolute() or p.is_symlink() or p.exists()
            or not p.parent.is_dir() or p.parent.is_symlink()
            for p in files
        )
        or len({str(p.resolve()) for p in files}) != 3
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "fresh_output_required"}))
        return 2
    try:
        _original_owner_module(
            root=args.m_owner_dir, ref=_M_PIN,
            relative="experiments/metabolism_s49_owner_admission.py",
            module_name="experiments.metabolism_s49_owner_admission",
        )
        _original_owner_module(
            root=args.wb_owner_dir, ref=_WB_PIN,
            relative="src/relay_self/self_cognition_slice.py",
            module_name="relay_self.self_cognition_slice",
        )
    except (OSError, ValueError, subprocess.SubprocessError, ImportError) as exc:
        print(json.dumps({
            "status": "BLOCKED", "reason": "pinned_original_owner_unavailable",
            "detail": type(exc).__name__,
        }))
        return 2

    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    observer = S2BOwnerWitnessObserver()
    code, result = asyncio.run(run_s2b_owner_witness_dev(
        original_qualify=qualify, report_path=args.report,
        server_log=args.server_log, observer=observer,
    ))
    args.s2b_report.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "s2b_report": str(args.s2b_report),
    }))
    return 0 if code == 0 and result["status"] == "RECORDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
