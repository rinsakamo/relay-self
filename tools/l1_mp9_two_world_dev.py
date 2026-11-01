"""MP9 paired disposable original S49/Paper DEV Worlds; fail closed.

Two sequential Worlds maximum, each original native S49 Action owned by the
existing host. No Self training, no physical qualification, no science claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
from pathlib import Path

from adapters.mineflayer.l23_paper_live_assets import L23PaperAssets, verify_paper_assets
from adapters.mineflayer.self_body_s50_l1_mp8_physical import attest_surface_lock
from adapters.mineflayer.self_body_s50_l1_mp8_transfer import MP5_SLOPE
from adapters.mineflayer.self_body_s50_l1_mp9_selector import (
    MP9Rejected,
    compare_pair,
    evaluate_frozen_shadow,
    freeze_from_paper_lock,
    train_mp8_only,
)
from tools.l1_mp7_ice_floor_world_dev import (
    PAPER_SHA,
    original_json,
    parse_lines,
    port_free,
    sha,
    timestamp,
    verified_config,
)

CONFIRM = "MP9-TWO-HELDOUT-MATERIAL-SHADOW-WORLDS-DEV-20261101"
PAPER_SIZE = 52811717
SURFACES = ("NORMAL", "ICE")


def rows_of(events: list[tuple[str, dict[str, str]]], kind: str):
    return [(n, values) for n, (line, values) in enumerate(events)
            if kind + " marker_id=" in line]


def _motion(row: dict[str, str]) -> float:
    return math.dist(
        [float(row["from_" + axis]) for axis in "xyz"],
        [float(row[axis]) for axis in "xyz"],
    )


def _must(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("MP8 original-source audit: " + message)


def review_world(root: Path, mode: str, rc: int, timed_out: bool) -> dict:
    original = root / "paper-stdout-original.bin"
    log = root / "server.log"
    report_path = root / "s49-report.json"
    _must(all(p.is_file() for p in (original, log, report_path)),
          "missing original Paper or S49 report")
    _must(original.read_bytes() == log.read_bytes(), "nonidentical original stdout")
    report = json.loads(report_path.read_text())
    _must(rc == 0 and not timed_out and report.get("status") == "PASS",
          "S49 failed or launcher ended abnormally")
    _must(report.get("node_exit") == 0 and report.get("server_exit") == 0,
          "owner cleanup failed")
    actions = report.get("actual_native_actions")
    _must(type(actions) is list and len(actions) == 1
          and actions[0].get("terminal") == "outcome",
          "one original S49 terminal required")
    _must(report.get("l1_paper_local_forecast", {}).get(
        "local_model_armed_before_action") is True, "Paper old prior not pre-armed")

    events = parse_lines(log)
    lock_rows = rows_of(events, "S50_DEV_SURFACE_LOCK")
    phase = rows_of(events, "M02_DEV_S50_PHASE")
    arm = rows_of(events, "S50_DEV_LOCAL_MODEL_ARM")
    waits = rows_of(events, "S50_DEV_WAIT_TICK")
    inputs = rows_of(events, "S50_DEV_INPUT_TICK")
    floors = rows_of(events, "S50_DEV_ICE_FLOOR_TICK")
    fixed = rows_of(events, "S50_DEV_LOCAL_FORECAST_FIXED")
    scores = rows_of(events, "S50_DEV_LOCAL_FORECAST_SCORE")
    origin = rows_of(events, (
        "S50_DEV_NORMAL_FLOOR_VERIFIED" if mode == "NORMAL"
        else "S50_DEV_ICE_FLOOR_APPLIED"
    ))
    # The original S49 host emits PRE_FORWARD and POST_CLEAR, not extra
    # diagnostic POST_FORWARD / PRE_CLEAR phases. Preserve real source scope.
    _must(len(lock_rows) == len(arm) == len(origin) == 1
          and len(phase) == 2
          and {row.get("phase") for _, row in phase}
              == {"PRE_FORWARD", "POST_CLEAR"},
          "missing unique preaction lock/old prior/original Paper phases")
    _must(all(len(v) == n for v, n in ((waits, 8), (inputs, 8), (floors, 8),
                                        (fixed, 7), (scores, 7))),
          "missing Paper eight samples and seven prediction pairs")
    before_action = next((n for n, fields in phase
                          if fields.get("phase") == "PRE_FORWARD"), -1)
    after_clear = next((n for n, fields in phase
                        if fields.get("phase") == "POST_CLEAR"), -1)
    lock_index, raw_lock = lock_rows[0]
    _must(before_action < arm[0][0] < origin[0][0] <= lock_index
          < after_clear < waits[0][0],
          "Paper model/ground preaction or post-clear/WAIT order wrong")
    marker = raw_lock["marker_id"]
    world = raw_lock["world"]
    subject = raw_lock["subject_uuid"]
    lock = attest_surface_lock(
        original.read_bytes(), marker=marker, world=world,
        subject_uuid=subject, mode=mode,
    )
    _must(report.get("mp8_matched_surface", {}).get(
        "preaction_surface_source") == lock, "host cannot substitute Paper lock")
    expected_material = "GRASS_BLOCK" if mode == "NORMAL" else "PACKED_ICE"
    expected_mode = "GRASS_BLOCK_5X5_READONLY" if mode == "NORMAL" else "PACKED_ICE_5X5"
    previous_tick = None
    motions = []
    for i, (row_num, row) in enumerate(waits):
        tick = int(row["tick"])
        _must(row["world"] == world and row["marker_id"] == marker
              and int(row["index"]) == i + 1, "WAIT original subject/ordinal mismatch")
        if previous_tick is not None:
            _must(tick == previous_tick + 1, "nonconsecutive real World ticks")
        previous_tick = tick
        motions.append(_motion(row))
        floor_idx, floor_row = floors[i]
        input_idx, input_row = inputs[i]
        _must(row_num < floor_idx < (waits[i+1][0] if i < 7 else len(events))
              and row_num < input_idx < (waits[i+1][0] if i < 7 else len(events))
              and floor_row["world"] == world
              and floor_row["subject_uuid"] == subject
              and floor_row["marker_id"] == marker
              and floor_row["floor_material"] == expected_material
              and floor_row["mode"] == expected_mode
              and int(floor_row["tick"]) == tick,
              "Paper actual underfoot surface/identity/tick mismatch")
    for i in range(7):
        _, observed = waits[i]
        _, future = waits[i+1]
        index_fixed, prediction = fixed[i]
        index_score, score = scores[i]
        _must(waits[i][0] < index_fixed < waits[i+1][0] < index_score
              and int(prediction["prior_tick"]) == int(observed["tick"])
              and int(prediction["target_tick"]) == int(future["tick"])
              and int(score["target_tick"]) == int(future["tick"])
              and prediction["ticket_sha256"] == score["ticket_sha256"]
              and prediction["world"] == score["world"] == world
              and prediction["subject_uuid"] == score["subject_uuid"] == subject
              and math.isclose(float(prediction["predicted_m"]),
                               MP5_SLOPE * motions[i], abs_tol=1e-12)
              and math.isclose(float(score["actual_m"]), motions[i+1],
                               abs_tol=1e-12),
              "seven original prequential forecasts were not authenticated")
    return {
        "classification": "DEV_ORIGINAL_PAPER_SOURCE_AUDITED",
        "mode": mode, "lock": lock, "motions_m": motions,
        "native_move_m": actions[0]["movement_m"],
        "subject_uuid": subject, "world_uuid": world,
        "world_seed": lock["seed"], "marker": marker,
        "source_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "eight_wait_ticks": 8, "seven_original_forecast_scores": 7,
        "model_frozen_before_action": True,
        "new_model_applied_to_action": False,
        "self_learning_admissions": 0,
    }


def compare_original_states(normal: dict, ice: dict) -> dict:
    a, b = normal["lock"], ice["lock"]
    # Do not claim exact timing sameness: world tick and event time can differ.
    equality = ("seed", "subject_uuid", "original_material",
                "blocks_verified", "floor_x", "floor_y", "floor_z",
                "on_ground", "food", "game_mode")
    mismatch = [k for k in equality if a.get(k) != b.get(k)]
    # Floating point sampled pose/velocity requires predeclared tolerances.
    tolerance = {
        "x": .015, "y": .015, "z": .015,
        "yaw": .05, "pitch": .05,
        "vx": .03, "vy": .03, "vz": .03, "health": .01,
    }
    delta = {k: abs(float(a[k]) - float(b[k])) for k in tolerance}
    mismatch.extend(k for k in tolerance if delta[k] > tolerance[k])
    if normal["world_uuid"] == ice["world_uuid"]:
        mismatch.append("world_uuid_NOT_DISTINCT")
    return {
        "matched": not mismatch, "mismatches": mismatch,
        "predeclared_tolerances": tolerance, "actual_deltas": delta,
        "world_ticks_not_forced_equal": [a["full_time"], b["full_time"]],
        "seed": a["seed"], "ground_pre_intervention": "GRASS_BLOCK_5X5",
        "source": "ACTUAL_INDEPENDENT_ORIGINAL_PAPER_LOCK_RECORDS",
        "caveat": "Matching sampled state not identical trajectory or randomized causal proof",
    }


def run_one(parent: Path, mode: str, *, paper: Path, plugin: Path,
            config_default: Path, node: Path, prior_sha: str,
            mp10_revision_dev: bool = False) -> tuple[int, bool]:
    out = parent / mode.lower()
    out.mkdir()
    cfg = out / "mp9-active-config.yml"
    config_sha = verified_config(config_default, cfg)
    cfg_abs = cfg.resolve()
    assets = L23PaperAssets(paper, PAPER_SHA, plugin, sha(plugin), cfg_abs, config_sha)
    verify_paper_assets(assets)
    (out / "capture").mkdir()
    env = dict(os.environ)
    env.update({
        "PYTHONPATH": "src:tests:.", "PYTHONDONTWRITEBYTECODE": "1",
        "S49_REAL_SERVER_CI": "1",
        "RELAYSELF_RSEE_NODE_RUNTIME_ROOT": str(node),
        "RELAYSELF_S50_PACKET_WITNESS_DEV": str(out / "client-packet-original.jsonl"),
    })
    if env.get("NODE_OPTIONS"):
        raise ValueError("MP8 Node shim forbidden")
    args = [
        sys.executable, "-m", "adapters.mineflayer.self_body_s50_world_dev",
        "--report", str(out / "s49-report.json"),
        "--server-log", str(out / "server.log"),
        "--l16-capture-root", str(out / "capture"),
        "--l16-goal-target-x", "0", "--l16-goal-target-z", "0",
        "--l16-goal-tolerance-m", "0.49", "--l16-goal-stability-m", "0.05",
        "--l16-confirm", "L16-S49-FIRST-ACTION-ORIGINAL-DEV",
        "--l22-settling-probes", "6",
        "--selfbody-live-next-epoch-dev", "--selfbody-l1-motion-shadow-dev",
        "--l1-prediction-journal", str(out / "prediction-original.jsonl"),
        "--l1-paper-local-forecast-dev", "--l1-paper-ice-floor-dev",
        "--l1-mp8-surface-mode", mode, "--l1-mp9-shadow-dev",
        *([] if not mp10_revision_dev else ["--l1-mp10-revision-dev"]),
        "--l23-paper-server-jar", str(paper),
        "--l23-paper-server-sha256", PAPER_SHA,
        "--l23-paper-plugin-jar", str(plugin),
        "--l23-paper-plugin-sha256", sha(plugin),
        "--l23-paper-config", str(cfg_abs),
        "--l23-paper-config-sha256", config_sha,
    ]
    original_json(out / "WORLD_ATTEMPT_STARTED.json", {
        "time": timestamp(), "attempt": 1, "mode": mode,
        "old_normal_coefficient": MP5_SLOPE,
        "prior_mp8_readback_sha": prior_sha,
        "mp8_frozen_prior_before_world": True,
        "original_host_argv": args,
        "effects": "NEW_DISPOSABLE_PAPER_WORLD_AND_ONE_ORIGINAL_S49_ACTION",
        "qualification": "NO_GO", "science": "NOT_RUN",
    })
    rc, timed_out = 124, False
    with (out / "host-original.stdout.log").open("xb") as log:
        child = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                                 env=env, start_new_session=True)
        try:
            rc = child.wait(timeout=250)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=8)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
    return rc, timed_out


def main() -> int:
    p = argparse.ArgumentParser()
    for key in ("output", "paper-jar", "plugin-jar", "config-default", "node-runtime"):
        p.add_argument("--" + key, required=True, type=Path)
    p.add_argument("--confirm", required=True)
    p.add_argument("--preflight-only", action="store_true")
    args = p.parse_args()
    if (args.confirm != CONFIRM or not args.output.is_absolute()
            or args.output.exists() or args.output.is_symlink()):
        p.error("MP9 requires fresh absolute root and dedicated DEV release")
    args.output.mkdir(parents=True)
    try:
        _must(port_free(), "physical World port not free before experiment")
        _must(args.paper_jar.is_file() and sha(args.paper_jar) == PAPER_SHA,
              "pinned official Paper SHA mismatch")
        _must(args.paper_jar.stat().st_size == PAPER_SIZE, "Paper size mismatch")
        _must(args.node_runtime.is_absolute() and not args.node_runtime.is_symlink(),
              "Node runtime not absolute or symlinked")
        pkg = json.loads(
            (args.node_runtime / "node_modules/mineflayer/package.json").read_text())
        _must(pkg.get("version") == "4.39.0", "invalid Mineflayer runtime")
        prior = train_mp8_only()
        _must(prior.pairs_per_surface == 7, "MP8 prior has missing training pairs")
        # Freeze BOTH environment models before either heldout World exists.
        original_json(args.output / "MP9_PRE_WORLD_PRIOR_ORIGINAL.json", {
            "time": timestamp(), "run_head": os.environ.get("GITHUB_SHA"),
            "source": prior.__dict__,
            "worlds": ["NORMAL", "ICE"],
            "world_seed_name": "RelaySelf-MP9-Heldout-20261101",
            "source_freeze_before_both_worlds": True,
            "model_selection": "PAPER_ORIGINAL_SURFACE_LOCK_PRE_ACTION",
            "predeclared_margin_m": .001,
            "cheap_material_rule_equivalent": True,
            "no_training_admission_or_policy_change": True,
            "max_disposable_worlds": 2, "max_original_s49_actions": 2,
            "qualification": "NO_GO", "science": "NOT_RUN",
        })
        if args.preflight_only:
            print("MP9_HELDOUT_PREFLIGHT_OK worlds_started=0", flush=True)
            return 0

        accepted = {}
        selected_scores = {}
        for mode in SURFACES:
            _must(port_free(), "port not rebound before heldout World")
            rc, timed_out = run_one(
                args.output, mode, paper=args.paper_jar, plugin=args.plugin_jar,
                config_default=args.config_default, node=args.node_runtime,
                prior_sha=prior.source_sha1,
            )
            _must(port_free(), "original World/port not released")
            readback = review_world(args.output / mode.lower(), mode, rc, timed_out)
            original_json(args.output / mode.lower() / "mp9-physical-source-audit.json",
                          readback)
            report = json.loads(
                (args.output / mode.lower() / "s49-report.json").read_text())
            shadow = report.get("mp9_surface_shadow", {})
            _must(shadow.get("status") == "SURFACE_MODEL_FROZEN_PRE_ACTION",
                  "original host did not freeze preaction selection")
            ticket = freeze_from_paper_lock(prior, readback["lock"], mode=mode)
            _must(shadow.get("ticket") == ticket.__dict__,
                  "source-bound host selection does not match Paper target")
            journal = [
                json.loads(line)
                for line in (args.output / mode.lower() /
                             "prediction-original.jsonl").read_text().splitlines()
            ]
            frozen = [x for x in journal if x.get("kind") == "MP9_SHADOW_SELECTION_FIXED"]
            wait_observed = [x for x in journal if x.get("kind") == "OBSERVED"]
            _must(len(frozen) == 1
                  and frozen[0].get("ticket") == ticket.__dict__
                  and len(wait_observed) == 8
                  and frozen[0]["host_monotonic_ns"]
                      < wait_observed[0]["host_monotonic_ns"],
                  "host original journal did not freeze model before WAIT source")
            score = evaluate_frozen_shadow(
                prior, ticket, motions=readback["motions_m"],
                verified_surface=("GRASS_BLOCK" if mode == "NORMAL" else "PACKED_ICE"),
            )
            original_json(args.output / mode.lower() / "mp9-heldout-shadow-score.json",
                          score)
            accepted[mode] = readback
            selected_scores[mode] = score

        physical_match = compare_original_states(
            accepted["NORMAL"], accepted["ICE"],
        )
        original_json(args.output / "MP9_PHYSICAL_PAIR_AUDIT.json", physical_match)
        _must(physical_match["matched"], "the two new Worlds differ in sampled initial state")
        result = compare_pair(selected_scores["NORMAL"], selected_scores["ICE"])
        result.update({
            "original_paper_pair_audit": "DEV_MATCHED_PREACTION_SAMPLED",
            "source_frozen_before_both_worlds": True,
            "host_per_target_selected_before_original_action": True,
            "original_native_actions": 2,
            "actual_disposable_worlds": 2,
            "same_info_material_rule_equivalent": True,
            "unique_l1_advantage": False,
            "goal": "UNDETERMINED",
            "physical_qualification": "NO_GO",
            "science": "NOT_RUN",
        })
        original_json(args.output / "MP9_FINAL_DEV_READBACK.json", result)
        print("MP9_HELDOUT_TWO_WORLD_RESULT=" + json.dumps(result, sort_keys=True),
              flush=True)
        return 0
    except (ValueError, OSError, KeyError, MP9Rejected) as exc:
        original_json(args.output / "MP9_FAILED_OR_UNMATCHED_ORIGINAL.json", {
            "time": timestamp(), "reason": f"{type(exc).__name__}: {exc}",
            "status": "DEV_FAIL_NOT_TRANSFER",
            "qualification": "NO_GO", "science": "NOT_RUN",
        })
        print("MP9_HELDOUT_FAILED=" + str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
