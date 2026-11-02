"""S #537 S2-C original S49 → S2-A/B → existing S60-A/B1 async L2.

DEV-only, no model server startup, extra native read, Action, learning or
energy authority. The original S49 L0 never awaits model completion. Original
S16 closure invalidates the in-flight read-only advisory before it can apply.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Awaitable, Callable

from adapters.mineflayer.normal_action import (
    NormalActionClosedReadback,
    observe_closed_native_actions,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s60b1_loopback_adapter import LoopbackTransportConfig
from adapters.mineflayer.s537_s2b_gated_l2_shadow import S2BGatedL2Shadow
from tools.s537_s1_live_wb_m_dev import (
    _M_PIN,
    _WB_PIN,
    _original_owner_module,
    run_s1_owner_dev,
)
from tools.s537_s2b_original_owner_witness_dev import S2BOwnerWitnessObserver


class S2CAsyncObserver(S2BOwnerWitnessObserver):
    """Live original source witness plus exactly one S60-B1 HTTP attempt."""

    def __init__(self, config: LoopbackTransportConfig, *, timeout_s: float) -> None:
        super().__init__()
        self.shadow = S2BGatedL2Shadow(
            enabled=True, config=config, timeout_s=timeout_s,
        )
        self._timeout = timeout_s
        self._poll_task: asyncio.Task[None] | None = None
        self._poll_errors: list[str] = []
        self._poll_ticks = 0
        self._closure_invalidations = 0
        self._accepted_while_current: list[dict[str, object]] = []

    def observe(self, reading: MineflayerObservation) -> None:
        """S49 awaits only source bookkeeping, never any provider response."""
        super().observe(reading)
        source, read = self._inputs[-1], self.bound[-1]
        self.shadow.observe(source, owner_read=read)
        if self.shadow.model_attempts and self._poll_task is None:
            self._poll_task = asyncio.create_task(self._poll_backend())

    async def _poll_backend(self) -> None:
        deadline = time.monotonic() + self._timeout
        try:
            while time.monotonic() < deadline:
                current = self.shadow.poll()
                self._poll_ticks += 1
                if current is not None:
                    self._accepted_while_current.append({
                        "probe_seq": self.bound[-1].context.world_seq,
                        "advisory_text": current,
                        "read_only": True,
                    })
                    return
                if self.shadow.status in (
                    "EXPIRED_ORIGINAL_S16_WORLD_ADVANCED",
                    "EXPIRED_WORLD_ADVANCED", "DEFERRED_SOURCE_WITNESS_ERROR",
                    "STALE_OR_UNQUALIFIED_RESULT",
                ):
                    return
                await asyncio.sleep(0.025)
            # Tick once to register deadline; no forced backend-idle assertion.
            self.shadow.poll()
        except asyncio.CancelledError:
            raise
        except (ValueError, TypeError, RuntimeError) as exc:
            self._poll_errors.append(type(exc).__name__)
            self.shadow.fail_closed_on_source_error()

    def observe_closed(self, closed: NormalActionClosedReadback) -> None:
        """Original executor has already completed its S16 terminal."""
        before = len(self._closed)
        super().observe_closed(closed)
        if len(self._closed) != before + 1 or self._closed[-1] is not closed:
            self.shadow.fail_closed_on_source_error()
            return
        if not self.shadow.model_attempts:
            return
        try:
            context = self.binder.context_at_original_s16(closed)
            self.shadow.invalidate_on_original_s16(closed, new_context=context)
            self._closure_invalidations += 1
        except (ValueError, TypeError, RuntimeError) as exc:
            self._poll_errors.append(type(exc).__name__)
            self.shadow.fail_closed_on_source_error()

    async def close_shadow(self) -> dict[str, object]:
        if self._poll_task is not None and not self._poll_task.done():
            self._poll_task.cancel()
            await asyncio.gather(self._poll_task, return_exceptions=True)
        report = await self.shadow.close()
        return {
            **report,
            "poll_ticks": self._poll_ticks,
            "poll_errors": list(self._poll_errors),
            "original_s16_invalidations": self._closure_invalidations,
            "advisory_accepted_before_invalidation": list(
                self._accepted_while_current
            ),
            "l0_awaited_provider": False,
            "original_source_callback_errors": list(self.errors),
        }


async def run_s2c_live_shadow_dev(
    *, original_qualify: Callable[..., Awaitable[int]],
    report_path: Path, server_log: Path, observer: S2CAsyncObserver,
) -> tuple[int, dict[str, object]]:
    """One S49 run: no S2-A 'model=0' top-level report reused as total."""
    async def same_original(*args, **kwargs):
        return await original_qualify(
            *args, owner_epoch_readonly=observer.owner_epoch, **kwargs,
        )

    with observe_closed_native_actions(observer.observe_closed):
        code, s1 = await run_s1_owner_dev(
            original_qualify=same_original,
            report_path=report_path, server_log=server_log,
            observer=observer,
        )
    try:
        original = observer.owner_epoch_readout()
        s2a = observer.s2a_readout()
    except (ValueError, TypeError, AttributeError, KeyError):
        original = {"status": "DEFERRED", "reason": "ORIGINAL_OWNER_READBACK_REJECTED"}
        s2a = {"status": "DEFERRED"}
    s60 = await observer.close_shadow()
    valid_source = (
        code == 0 and s1.get("status") == "RECORDED"
        and original.get("status") == "RECORDED"
        and s2a.get("status") == "RECORDED"
        and s60["model_attempts"] == 1
        and s60["original_s16_invalidations"] >= 1
        and not s60["poll_errors"]
        and not s60["original_source_callback_errors"]
    )
    # A completed HTTP response is distinct from an attempted submission.
    # A stale response and an unconfirmed in-flight backend are not success.
    events = s60["transport_events"]
    return code, {
        "schema": "S537_S2C_S49_TO_S60_READ_ONLY_DEV_V1",
        "status": "RECORDED" if valid_source else "DEFERRED",
        "source_join_status": original.get("status", "DEFERRED"),
        "s49_s1": s1,
        "s2a": s2a,
        "owner_epoch": original,
        "s60": s60,
        "s60_submissions": s60["model_attempts"],
        "http_post_sent_observed": "SOCKET_POST_SENT" in events,
        "http_completion_observed": "HTTP_COMPLETION_OBSERVED" in events,
        "model_completed_and_current": (
            s60["status"] == "ADVISORY_CURRENT_READ_ONLY"
            and bool(s60["advisory_accepted_before_invalidation"])
        ),
        "model_process_identity_verified": False,
        "source_attested": False,
        "action_authority": False,
        "learning_authority": False,
        "new_native_reads": 0,
        "new_action_issues": 0,
        "learning_updates": 0,
        "energy_debits": 0,
        "backend_stop_ack": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser("S2-C one World, one existing S60 L2 shadow")
    parser.add_argument("--m-owner-dir", type=Path, required=True)
    parser.add_argument("--wb-owner-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--s2c-report", type=Path, required=True)
    parser.add_argument("--model-alias", required=True)
    parser.add_argument("--model-port", type=int, required=True)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--live-world-dev", action="store_true")
    args = parser.parse_args()
    if not (
        args.live_world_dev
        and os.environ.get("S537_S2C_LIVE_L2_DEV_ONLY") == "1"
        and os.environ.get("S49_REAL_SERVER_CI") == "1"
        and os.environ.get("S49_COMPLETED_L0_DEV_ONLY") == "1"
        and os.environ.get("GITHUB_ACTIONS") != "true"
        and not os.environ.get("NODE_OPTIONS")
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "s2c_live_l2_grant_missing"}))
        return 2
    files = (args.report, args.server_log, args.s2c_report)
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
        config = LoopbackTransportConfig(
            model=args.model_alias, port=args.model_port,
            max_tokens=args.max_tokens, whole_s=min(45.0, args.timeout_s),
            read_s=min(15.0, args.timeout_s),
        )
        if not 0 < args.timeout_s <= 60 or args.max_tokens > 256:
            raise ValueError("model budget out of bounds")
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
            "status": "BLOCKED", "reason": "source_or_model_spec_not_admitted",
            "detail": type(exc).__name__,
        }))
        return 2
    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    observer = S2CAsyncObserver(config, timeout_s=args.timeout_s)
    code, result = asyncio.run(run_s2c_live_shadow_dev(
        original_qualify=qualify,
        report_path=args.report, server_log=args.server_log,
        observer=observer,
    ))
    args.s2c_report.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "s2c_report": str(args.s2c_report),
        "s60_submissions": result["s60_submissions"],
        "http_completion_observed": result["http_completion_observed"],
    }))
    return 0 if code == 0 and result["status"] == "RECORDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
