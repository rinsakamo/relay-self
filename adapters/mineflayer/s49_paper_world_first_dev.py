"""Explicit disposable S49/Paper/P1 DEV runner: one original S49 owner.

Opt-in adapter around the ORIGINAL S49 qualify() and its existing cleanup.
Only the server asset/config and read-only post-Action observer are replaced.
R qualification, V science, and production P1 state are never updated.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import socket
import time
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from adapters.mineflayer import s49_normal_session_real_ci as original
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _fresh_asset
from adapters.mineflayer.s31a_real_server_ci import BOT_USERNAME
from adapters.mineflayer.s49_p1_l0_capability_dev import compare_body_capability_l0_dev
from adapters.mineflayer.s49_p1_l0_fresh_pair_dev import review_postwait_fresh_l0_input_dev
from adapters.mineflayer.s49_p1_l0_gait_candidate_dev import (
    evaluate_fatigue_aware_fresh_candidate_dev,
)
from adapters.mineflayer.s49_p1_l0_near_decide_dev import decide_bounded_near_move_dev
from adapters.mineflayer.s49_p1_l0_sensitivity_dev import compare_p1_knockdown_dev
from adapters.mineflayer.s49_p1_l0_shadow_dev import preview_postwait_l0_dev
from adapters.mineflayer.s49_p1_postwait_native_dev import (
    compose_postwait_native_self_world_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import (
    compose_s49_p1_dev_self_body,
    compose_s49_p1_postwait_native_dev,
)
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from experiments.fatigue_p1 import FatigueProfile
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant

OBSERVER_CONFIG = Path(__file__).parent / "s49_paper_wait_observer_dev" / (
    "src/main/resources/config.yml"
)
CONFIRM = "S49-P1-DEV-DISPOSABLE-PAPER-WORLD"
SCHEMA = "S49_PAPER_WORLD_FIRST_DEV_V1"


class S49PaperDevBlocked(RuntimeError):
    """Invalid or unsafe disposable Paper development run."""


def offline_uuid(player: str) -> str:
    """Java UUID.nameUUIDFromBytes('OfflinePlayer:' + name) for an offline bot."""
    if player != BOT_USERNAME:
        raise S49PaperDevBlocked("unexpected player identity")
    data = bytearray(hashlib.md5(("OfflinePlayer:" + player).encode()).digest())
    data[6] = (data[6] & 0x0f) | 0x30
    data[8] = (data[8] & 0x3f) | 0x80
    return str(UUID(bytes=bytes(data)))


def _fresh_output(directory: Path) -> None:
    if (not directory.is_absolute() or directory.exists()
            or not directory.parent.is_dir()
            or directory.is_symlink()
            or any(p.is_symlink() for p in directory.parents)
            or any((p / ".git").exists() for p in directory.parents)
            or os.environ.get("NODE_OPTIONS")):
        raise S49PaperDevBlocked("fresh isolated output and unshimmed Node required")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 25565))
    directory.mkdir(mode=0o700)


async def _await_complete(paper_log: Path, offset: int, *, timeout: float = 15) -> str:
    """Poll the already-owned Paper console file, without adding a new reader."""
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if paper_log.is_file() and not paper_log.is_symlink():
            with paper_log.open("rb") as stream:
                stream.seek(offset)
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise S49PaperDevBlocked("Paper observer output window too large")
            window = raw.decode("utf-8")
            if "S49_OBSERVER_DENIED" in window or "S49_DEV_BACK_WAIT_ABORT" in window:
                raise S49PaperDevBlocked("Paper observer denied or aborted")
            if "S49_OBSERVER_COMPLETE " in window:
                return window
        await asyncio.sleep(0.15)
    raise S49PaperDevBlocked("Paper observer never completed eight ticks")


async def run(
    output_dir: Path, paper_jar: Path, paper_sha: str,
    observer_jar: Path, observer_sha: str, *, confirmation: str,
    fresh_target_distance: int = 2,
) -> int:
    """One new Paper World, original S49 two MOVE actions, one post-WAIT sample."""
    report = {
        "schema": SCHEMA,
        "classification": "DEV_ONLY",
        "status": "BLOCKED",
        "world_status": "NOT_RUN",
        "qualification_go": False,
        "science_go": False,
        "p1_production_state_updated": False,
    }
    created = False
    try:
        if confirmation != CONFIRM:
            raise S49PaperDevBlocked("explicit disposable DEV confirmation required")
        if type(fresh_target_distance) is not int or fresh_target_distance not in (2, 10):
            raise S49PaperDevBlocked("fresh DEV threat distance must be exactly 2 or 10 blocks")
        paper_jar = _fresh_asset(paper_jar, paper_sha)
        observer_jar = _fresh_asset(observer_jar, observer_sha)
        if paper_jar.resolve() == observer_jar.resolve():
            raise S49PaperDevBlocked("server and plugin must be separate JARs")
        _fresh_output(output_dir)
        created = True
        report.update(
            paper_jar_sha256=paper_sha,
            observer_jar_sha256=observer_sha,
            observer_mode="POST_ACTION_ONE_SHOT_DEFAULT_OFF_OUTSIDE_THIS_DEV",
        )
        paper_log = output_dir / "paper_server.log"
        original_report = output_dir / "original_s49_report.json"
        observed = {
            "server": None, "window": None, "count": 0, "postwait": None,
            "fresh_event": None, "fresh_probe": None,
            "fresh_trace": [],
        }
        # This mutable list is retained even if original qualify() stops:
        # failed World DEV runs preserve the observer's bounded event diagnostics.
        report["postwait_fresh_event_trace_dev"] = observed["fresh_trace"]
        unpatched_config = original._write_config
        unpatched_ready = original._ready_server
        original_executor = original.NormalSessionActionExecutor

        def paper_fetch(target: Path) -> dict:
            shutil.copyfile(paper_jar, target)
            return {"runtime": "PAPER_1_21_8_DISPOSABLE_DEV",
                    "paper_asset_sha256": paper_sha}

        def paper_config(root: Path) -> None:
            unpatched_config(root)
            plugin_dir = root / "plugins"
            plugin_dir.mkdir(exist_ok=False)
            shutil.copyfile(observer_jar, plugin_dir / "s49-wait-observer-dev.jar")
            config_dir = plugin_dir / "RelayS49WaitObserverDev"
            config_dir.mkdir()
            config = OBSERVER_CONFIG.read_text(encoding="utf-8")
            if (config.count("enabled: false") != 1
                    or config.count("expected-player-name: RelaySelf") != 1):
                raise S49PaperDevBlocked("unexpected Paper observer config")
            (config_dir / "config.yml").write_text(
                config.replace("enabled: false", "enabled: true"),
                encoding="utf-8",
            )

        async def paper_ready(*args):
            result = await unpatched_ready(*args)
            observed["server"] = result[0]
            report["world_status"] = "PAPER_SERVER_STARTED"
            return result

        class OriginalS49WithPassivePaperDEV(original_executor):
            async def execute(self, *args, **kwargs):
                receipt = await super().execute(*args, **kwargs)
                observed["count"] += 1
                if observed["count"] != 2:
                    return receipt
                # The original S16 receipts are already completed; this
                # callback does not issue another Minecraft native Action.
                capture_native_action_evidence(receipt.consequence)
                server = observed["server"]
                if server is None or server.stdin is None:
                    raise S49PaperDevBlocked("original S49 server no longer owned")
                # Native clear ACK is not a server-effective release tick.
                # Give the server time to settle before the independent
                # Paper idle observation; the delay itself admits no ticks.
                await asyncio.sleep(0.5)
                offset = paper_log.stat().st_size if paper_log.exists() else 0
                original._command(
                    server, "relays49observe "
                    + receipt.terminal.action_id + " "
                    + self.session_id + " " + offline_uuid(BOT_USERNAME),
                )
                await server.stdin.drain()
                observed["window"] = await _await_complete(paper_log, offset)
                (output_dir / "paper_observer_window.log").write_text(
                    observed["window"], encoding="utf-8",
                )
                # The original host awaits on_action_request → executor.execute;
                # it cannot also receive on this same session until we return.
                # Use the SAME original session and its existing correlated
                # probe helper. No second receiver/task, issuer or Action.
                if (not args or args[0].started.session_id != self.session_id
                        or self.supervisor.open_actions):
                    raise S49PaperDevBlocked(
                        "post-WAIT native read requires closed original owner"
                    )
                request_id = (
                    f"s49-postwait:{self.session_id}:{receipt.terminal.action_id}"
                )
                observed["postwait"] = await original._correlated_observe(
                    args[0], request_id,
                )
                # DEV-only STAGING: after (never during) the Paper WAIT
                # window, cause one new external World entity event. No
                # second reader, Self Action or original L0 permission.
                pre = observed["postwait"]
                prior_zombies = {
                    e.entity_id for e in pre.snapshot.nearby_entities
                    if e.name == "zombie"
                }
                original._command(server, "kill @e[type=minecraft:zombie]")
                await server.stdin.drain()
                # Two-phase external World stimulus: a Paper "Killed"
                # console line does not prove Mineflayer's entity registry
                # has dropped the old target yet. First wait until the
                # original single JSONL reader OBSERVES no zombie, then
                # summon. Previous run showed overlapping 2-zombie
                # entitySpawn before the stale entity disappeared.
                clear_deadline = time.monotonic() + 12.0
                cleared_seq = None
                for _ in range(100):
                    remaining = clear_deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        frame = await asyncio.wait_for(
                            args[0].receive(), timeout=remaining,
                        )
                    except TimeoutError:
                        break
                    if not isinstance(frame, original.MineflayerObservation):
                        if isinstance(frame, original.MineflayerEntityHurt):
                            continue
                        raise S49PaperDevBlocked("unexpected native clear frame")
                    zombies = [
                        e for e in frame.snapshot.nearby_entities
                        if e.name == "zombie"
                    ]
                    observed["fresh_trace"].append({
                        "stage": "CLEAR_OLD", "seq": frame.seq,
                        "kind": frame.kind,
                        "zombie_ids": [e.entity_id for e in zombies],
                    })
                    if (frame.seq > pre.seq and not zombies
                            and not frame.snapshot.nearby_entities_coverage.truncated):
                        cleared_seq = frame.seq
                        break
                if cleared_seq is None:
                    raise S49PaperDevBlocked("old zombie never cleared from native source")

                # Only after native clear is observed may a new single
                # stimulus be issued by the external DEV World operator.
                original._command(
                    server,
                    "execute at RelaySelf run summon minecraft:zombie "
                    f"~{fresh_target_distance} ~ ~ "
                    "{NoAI:1b,Silent:1b,PersistenceRequired:1b,"
                    "Invulnerable:1b}",
                )
                await server.stdin.drain()
                deadline = time.monotonic() + 12.0
                for _ in range(100):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        frame = await asyncio.wait_for(
                            args[0].receive(), timeout=remaining,
                        )
                    except TimeoutError:
                        observed["fresh_trace"].append({
                            "stage": "SPAWN_NEW", "status": "SOURCE_WAIT_TIMED_OUT",
                        })
                        break
                    if not isinstance(frame, original.MineflayerObservation):
                        if isinstance(frame, original.MineflayerEntityHurt):
                            continue
                        raise S49PaperDevBlocked("unexpected post-WAIT native frame")
                    zombies = [
                        e for e in frame.snapshot.nearby_entities
                        if e.name == "zombie"
                    ]
                    observed["fresh_trace"].append({
                        "stage": "SPAWN_NEW", "seq": frame.seq,
                        "kind": frame.kind,
                        "zombie_ids": [e.entity_id for e in zombies],
                    })
                    if frame.seq <= cleared_seq or frame.kind != "entities":
                        continue
                    if (len(zombies) == 1
                            and zombies[0].entity_id not in prior_zombies
                            and not frame.snapshot.nearby_entities_coverage.truncated):
                        observed["fresh_event"] = frame
                        break
                if observed["fresh_event"] is None:
                    raise S49PaperDevBlocked("no fresh single-target native event after WAIT")
                fresh_req = (
                    f"s49-postwait-event:{self.session_id}:"
                    f"{observed['fresh_event'].seq}"
                )
                observed["fresh_probe"] = await original._correlated_observe(
                    args[0], fresh_req,
                )
                return receipt

        # Scoped DEV adaptation: no edits to original qualify(), S49 executor
        # implementation, frozen Action authorization, or original cleanup.
        with (patch.dict(os.environ, {"S49_REAL_SERVER_CI": "1"}),
              patch.object(original, "_fetch_official_server", paper_fetch),
              patch.object(original, "_write_config", paper_config),
              patch.object(original, "_ready_server", paper_ready),
              patch.object(original, "NormalSessionActionExecutor",
                           OriginalS49WithPassivePaperDEV)):
            rc = await original.qualify(original_report, paper_log)
        report["original_s49_rc"] = rc
        report["postwait_fresh_target_distance_m"] = fresh_target_distance
        report["original_s49_action_count"] = observed["count"]
        report["world_status"] = "CLOSED_WITH_ORIGINAL_S49_CLEANUP"
        if rc != 0 or observed["count"] != 2 or observed["window"] is None:
            raise S49PaperDevBlocked("original S49 or Paper observer did not complete")
        source = json.loads(original_report.read_text(encoding="utf-8"))
        if (source.get("node_exit") != 0 or source.get("server_exit") != 0):
            raise S49PaperDevBlocked("original Java/Node cleanup not successful")
        # No arbitrary initial fatigue. The last original S49 MOVE's
        # verified geometric distance drives P1's MOVE debit. The gap to
        # Paper BEGIN remains unmodeled, not silently filled with WAIT.
        self_body_handoff, p1 = compose_s49_p1_dev_self_body(
            source, observed["window"], expected_player_uuid=offline_uuid(BOT_USERNAME),
            profile=FatigueProfile(enabled=True, initial=0.0),
        )
        # A *model hypothesis* for next Cognition, not a new native Present,
        # true fatigue reading, actuator grant or persisted resource state.
        next_cognition = self_body_handoff.next_cognition_readback()
        if observed["postwait"] is None:
            raise S49PaperDevBlocked("no original-session post-WAIT native probe")
        actual_next_body, actual_next_cognition = compose_s49_p1_postwait_native_dev(
            self_body_handoff, p1,
            source["actual_native_actions"][-1],
            observed["postwait"],
            expected_request_id=(
                f"s49-postwait:{source['session_id']}:{p1['action_id']}"
            ),
        )
        if (actual_next_body.observation is None
                or actual_next_cognition["extra_native_probes"] != 1):
            raise S49PaperDevBlocked("native next cognition Present missing")
        world_body_join = compose_postwait_native_self_world_dev(
            actual_next_body, observed["postwait"],
        )
        if (not world_body_join["world_body_same_object"]
                or world_body_join["native_seq"] != actual_next_cognition["native_seq"]
                or world_body_join["native_request_id"]
                != actual_next_cognition["native_request_id"]
                or world_body_join["p1_model_sensor_pct"]
                != actual_next_cognition["p1_dev_hypothesis_sensor_pct"]):
            raise S49PaperDevBlocked("postwait SelfWorld/SelfBody source mismatch")
        # Reuse the same frozen synthetic S19 owner used by the original
        # S49 runner. This replays a read-only S42 choice from the one
        # already obtained native probe; there is NO entities-event pair,
        # independent Action grant or actual ReactiveL0.decide().
        _, frozen_commit, _, _, _, _ = await asyncio.to_thread(original.s19._epoch_one)
        shadow_l0 = preview_postwait_l0_dev(
            actual_next_body, observed["postwait"],
            self_body_handoff, p1,
            FatigueProfile(enabled=True, initial=0.0),
            frozen_commit.new_state,
        )
        if (shadow_l0["fresh_action_grant_issued"] is not False
                or shadow_l0["actual_reactive_l0_decide_called"] is not False
                or shadow_l0["native_seq"] != actual_next_cognition["native_seq"]
                or shadow_l0["after_wait_p1_model_efficiency_pct"]
                != actual_next_cognition["p1_dev_hypothesis_capability_pct"]):
            raise S49PaperDevBlocked("next-epoch L0 shadow source mismatch")
        # A bounded optional Cognition comparison, not a second L0 route
        # or a physical MOVE command. Same native probe; after-MOVE value is
        # explicitly counterfactual to the actual post-WAIT World geometry.
        capability_choice = compare_body_capability_l0_dev(
            actual_next_body, observed["postwait"],
            self_body_handoff, p1,
            FatigueProfile(enabled=True, initial=0.0),
            frozen_commit.new_state,
        )
        if (capability_choice["native_seq"] != shadow_l0["native_seq"]
                or capability_choice["s42_selection_unchanged"]
                != shadow_l0["original_s42_selection"]
                or capability_choice["new_action_grant_issued"] is not False
                or capability_choice["actual_native_actions_added"] != 0):
            raise S49PaperDevBlocked("post-WAIT capability candidate source mismatch")
        # Same original native/Paper source under a second, explicitly
        # uncalibrated fatigue rate. This is DEV sensitivity, not another
        # World session, model authority, or action issuer.
        rate_sensitivity = compare_p1_knockdown_dev(
            source, observed["window"], observed["postwait"],
            expected_player_uuid=offline_uuid(BOT_USERNAME),
            retained=frozen_commit.new_state,
        )
        if (rate_sensitivity["native_seq"] != capability_choice["native_seq"]
                or rate_sensitivity["s42_original_selection"]
                != capability_choice["s42_selection_unchanged"]
                or rate_sensitivity["baseline_l0_capability_candidate"]
                != capability_choice["after_wait_on_actual_postwait_world_model"]
                or rate_sensitivity["stress_fatigue_after_wait"]
                <= rate_sensitivity["baseline_fatigue_after_wait"]
                or rate_sensitivity["new_action_issuers"] != 0
                or rate_sensitivity["real_action_count_added"] != 0):
            raise S49PaperDevBlocked("same-World fatigue knockdown not source bound")
        if observed["fresh_event"] is None or observed["fresh_probe"] is None:
            raise S49PaperDevBlocked("post-WAIT native L0 pair absent")
        _, original_owner, _, _, _, _ = await asyncio.to_thread(original.s19._epoch_one)
        fresh_pair = review_postwait_fresh_l0_input_dev(
            observed["fresh_event"], observed["fresh_probe"],
            prior_postwait_probe=observed["postwait"],
            body=actual_next_body,
            handoff=self_body_handoff,
            p1_reviewed=p1,
            profile=FatigueProfile(enabled=True, initial=0.0),
            retained=original_owner.new_state,
        )
        if (fresh_pair["fresh_event_seq"] <= actual_next_cognition["native_seq"]
                or fresh_pair["fresh_probe_seq"] <= fresh_pair["fresh_event_seq"]
                or fresh_pair["original_l0_decide_called"] is not False
                or fresh_pair["new_action_issued"] is not False
                or fresh_pair["bounded_dev_shadow_l0_action_requests"] != 0
                or fresh_pair["bounded_dev_shadow_l0_decide_called"]
                != (fresh_pair["fresh_s42_selection"] == "WAIT")
                or (fresh_target_distance == 10
                    and fresh_pair["fresh_s42_selection"] != "WAIT")
                or (fresh_target_distance == 2
                    and fresh_pair["fresh_s42_selection"] != "MOVE_AWAY")):
            raise S49PaperDevBlocked("post-WAIT fresh native L0 source invalid")
        # A logical one-use DEV shadow grant from this explicit operator
        # wrapper; NOT an S49 NormalActionAuthorization. No native physical
        # MOVE is dispatched and the original completed host remains closed.
        near_request = None
        if fresh_target_distance == 2:
            fresh_event = observed["fresh_event"]
            fresh_probe = observed["fresh_probe"]
            shadow_grant = L0ActionGrant(
                authority_id=(
                    f"dev-shadow-only:{source['session_id']}:{fresh_event.seq}"
                ),
                action_id=(
                    f"dev-shadow-no-dispatch:{source['session_id']}:{fresh_event.seq}"
                ),
                intent_id="escape-threat",
                session_id=source["session_id"],
                event_seq=fresh_event.seq,
                probe_seq=fresh_probe.seq,
                entity_id=fresh_pair["fresh_zombie_entity_id"],
                granted=True,
                provenance=Provenance(
                    "dev-independent-shadow-only-not-s49-issuer",
                    f"{source['session_id']}:event-{fresh_event.seq}:operator-scoped-dev",
                ),
            )
            near_request = decide_bounded_near_move_dev(
                fresh_event, fresh_probe,
                prior_postwait_probe=observed["postwait"],
                body=actual_next_body,
                handoff=self_body_handoff,
                p1_reviewed=p1,
                profile=FatigueProfile(enabled=True, initial=0.0),
                retained=original_owner.new_state,
                operator_shadow_grant=shadow_grant,
            )
            if (near_request["fresh_event_seq"] != fresh_pair["fresh_event_seq"]
                    or near_request["fresh_probe_seq"] != fresh_pair["fresh_probe_seq"]
                    or near_request["normal_action_executor_called"] is not False
                    or near_request["physical_action_issued"] is not False
                    or near_request["bounded_dev_l0_action_requests"] != 1):
                raise S49PaperDevBlocked("bounded near request source/authority mismatch")
        # Optional DEV-only cognition candidate: revalidate BOTH P1
        # model profiles against the SAME real fresh native event/probe.
        # No original L0.decide(), grant, or additional physical Action.
        gait_candidate = evaluate_fatigue_aware_fresh_candidate_dev(
            source, observed["window"], observed["postwait"],
            observed["fresh_event"], observed["fresh_probe"],
            expected_player_uuid=offline_uuid(BOT_USERNAME),
            retained=original_owner.new_state,
        )
        if (gait_candidate["fresh_event_seq"] != fresh_pair["fresh_event_seq"]
                or gait_candidate["fresh_probe_seq"] != fresh_pair["fresh_probe_seq"]
                or gait_candidate["fresh_s42_selection_unchanged"]
                != fresh_pair["fresh_s42_selection"]
                or gait_candidate["new_action_issued"] is not False
                or gait_candidate["new_action_grant_issued"] is not False):
            raise S49PaperDevBlocked("same-world gait candidate source mismatch")
        if (p1["dev_fatigue_recovered"] <= 0
                or p1["dev_fatigue_before"] <= 0
                or p1["dev_move"] is None
                or p1["dev_move"]["fatigue_accumulated"] <= 0):
            raise S49PaperDevBlocked("last MOVE distance did not produce P1 DEV debit/recovery")
        report.update(
            status="PASS",
            classification="DEV_WORLD_OBSERVED_MOVE_DISTANCE_TO_WAIT_P1_MODEL",
            original_s49_session_id=source["session_id"],
            world_status="DISPOSABLE_PAPER_COMPLETED_AND_CLEANED",
            p1=p1,
            self_body_dev=next_cognition,
            next_cognition_native_dev=actual_next_cognition,
            next_self_world_dev=world_body_join,
            next_l0_shadow_dev=shadow_l0,
            next_l0_capability_dev=capability_choice,
            next_l0_sensitivity_dev=rate_sensitivity,
            next_l0_fresh_pair_dev=fresh_pair,
            next_l0_gait_candidate_dev=gait_candidate,
            next_l0_near_decide_dev=near_request,
        )
        report["p1"]["world_run_verified"] = True
        report["p1"]["status"] = "DEV_WORLD_OBSERVED_MOVE_DISTANCE_WAIT_REPLAY"
        return 0
    except asyncio.CancelledError:
        report["status"] = "CANCELLED"
        raise
    except (Exception, OSError) as exc:
        report.update(status="BLOCKED_OR_FAILED",
                      reason=f"{type(exc).__name__}: {exc}")
        return 2
    finally:
        if created:
            # Reuse original S49's own process cleanup; never perform
            # second terminate/reap on a process owned by qualify().
            with (output_dir / "world_first_dev_report.json").open("x") as stream:
                json.dump(report, stream, sort_keys=True, indent=2)
                stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="S49 original / Paper / P1 disposable DEV")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--observer-jar", type=Path, required=True)
    parser.add_argument("--observer-sha256", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument(
        "--fresh-target-distance", type=int, choices=(2, 10), default=2,
        help="Post-WAIT external DEV zombie stimulus in blocks; only 2 or 10",
    )
    args = parser.parse_args(argv)
    return asyncio.run(run(
        args.output_dir, args.paper_jar, args.paper_sha256,
        args.observer_jar, args.observer_sha256,
        confirmation=args.confirm,
        fresh_target_distance=args.fresh_target_distance,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
