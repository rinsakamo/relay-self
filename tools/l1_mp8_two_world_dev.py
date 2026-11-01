"""MP8 paired disposable original S49/Paper DEV Worlds; fail closed.

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
from adapters.mineflayer.self_body_s50_l1_mp8_transfer import (
    MP5_SLOPE,
    TargetSetup,
    freeze_matched_pair,
    score_pair,
    train_from_mp7,
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

CONFIRM = "MP8-TWO-FRESH-MATCHED-WORLDS-DEV-20261101"
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
    _must(len(lock_rows) == len(arm) == len(origin) == 1 and len(phase) == 4,
          "missing unique preaction lock/old prior/Paper phase")
    _must(all(len(v) == n for v, n in ((waits, 8), (inputs, 8), (floors, 8),
                                        (fixed, 7), (scores, 7))),
          "missing Paper eight samples and seven prediction pairs")
    before_action = next((n for n, fields in phase
                          if fields.get("phase") == "PRE_FORWARD"), -1)
    after_action = next((n for n, fields in phase
                         if fields.get("phase") == "POST_FORWARD"), -1)
    after_clear = next((n for n, fields in phase
                        if fields.get("phase") == "POST_CLEAR"), -1)
    lock_index, raw_lock = lock_rows[0]
    _must(before_action < arm[0][0] < origin[0][0] <= lock_index < after_action
          < after_clear < waits[0][0],
          "Paper condition/model/Action causal order wrong")
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
            config_default: Path, node: Path, prior_sha: str) -> tuple[int, bool]:
    out = parent / mode.lower()
    out.mkdir()
    cfg = out / "mp8-active-config.yml"
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
        "--l1-mp8-surface-mode", mode,
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
        "prior_mp7_readback_sha": prior_sha,
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
        p.error("fresh output and explicit MP8 two-World DEV scope required")
    args.output.mkdir(parents=True)
    try:
        _must(port_free(), "physical World port 25565 not free")
        _must(args.paper_jar.is_file() and sha(args.paper_jar) == PAPER_SHA,
              "official Paper SHA mismatch")
        _must(args.paper_jar.stat().st_size == PAPER_SIZE, "Paper size mismatch")
        _must(args.node_runtime.is_absolute() and not args.node_runtime.is_symlink(),
              "Node runtime not owned and absolute")
        package = json.loads(
            (args.node_runtime / "node_modules/mineflayer/package.json").read_text())
        _must(package.get("version") == "4.39.0", "wrong native Mineflayer version")
        prior = train_from_mp7()
        _must(prior.sample_pairs == 7, "incomplete MP7 prior training source")
        # One frozen prior and mode/plan ticket before either World is created.
        original_json(args.output / "MP8_PRE_WORLD_PLAN.json", {
            "time": timestamp(), "run_head": os.environ.get("GITHUB_SHA"),
            "prior": prior.__dict__, "worlds": ["NORMAL", "ICE"],
            "seed": "RelaySelf-MP8-Matched-Surface-20261101",
            "tp": [0.5, -58, 0.5, 0, 0],
            "frozen_prior_before_world": True,
            "mp8_ice_l1_same_information_cheap_equivalent": True,
            "max_worlds": 2, "max_native_actions": 2,
            "no_training_or_l0_action_change": True,
        })
        if args.preflight_only:
            print("MP8_PAIRED_PREFLIGHT_OK worlds_started=0", flush=True)
            return 0
        accepted = {}
        for mode in SURFACES:
            _must(port_free(), "port not rebound between independent Worlds")
            rc, expired = run_one(args.output, mode, paper=args.paper_jar,
                                  plugin=args.plugin_jar,
                                  config_default=args.config_default,
                                  node=args.node_runtime,
                                  prior_sha=prior.source_git_blob_sha)
            _must(port_free(), "World process/port remains after shutdown")
            review = review_world(args.output / mode.lower(), mode, rc, expired)
            original_json(args.output / mode.lower() / "mp8-original-source-review.json",
                          review)
            accepted[mode] = review
        matched = compare_original_states(accepted["NORMAL"], accepted["ICE"])
        original_json(args.output / "MP8_PHYSICAL_PAIR_AUDIT.json", matched)
        _must(matched["matched"], "physical preaction matched-state condition FAIL")
        # A postrun *diagnostic* target identity ticket: frozen prior was already
        # committed preworld. This does NOT pretend future world UUIDs were known.
        def target(mode: str):
            row = accepted[mode]
            digest = hashlib.sha256(json.dumps(
                {"seed": matched["seed"], "ground": matched["ground_pre_intervention"],
                 "pose_tolerances": matched["predeclared_tolerances"],
                 "confirmed_matched": True}, sort_keys=True).encode()).hexdigest()
            action_digest = hashlib.sha256(b"MP8_ORIGINAL_S49_MOVE_BACKWARD_V1").hexdigest()
            return TargetSetup(
                world_uuid=row["world_uuid"], subject_uuid=row["subject_uuid"],
                seed=matched["seed"], condition="NORMAL" if mode == "NORMAL" else "PACKED_ICE",
                matched_state_sha256=digest,
                native_action_spec_sha256=action_digest,
            )
        ticket = freeze_matched_pair(prior, target("NORMAL"), target("ICE"))
        scoring = score_pair(ticket,
                            normal_motions=accepted["NORMAL"]["motions_m"],
                            ice_motions=accepted["ICE"]["motions_m"])
        s = scoring["score"]
        delta = s["ice_old_model_mae_m"] - s["ice_updated_model_mae_m"]
        improvement = (delta >= .005
                       and s["normal_old_model_mae_m"] <=
                           s["normal_wrong_ice_model_mae_m"])
        scoring["model_source_frozen_pre_world"] = True
        scoring["target_identity_ticket_postrun_not_pre_world"] = True
        scoring["observed_transfer_diagnostic"] = (
            "ICE_HOLDOUT_IMPROVEMENT_DEV_ONLY" if improvement
            else "NO_ICE_TRANSFER_ADVANTAGE_OBSERVED"
        )
        scoring["original_paper_pair_audit"] = "DEV_MATCHED_PREACTION_SAMPLED"
        scoring["ice_mae_improvement_m"] = delta
        scoring["causal_effect_science_qualified"] = False
        original_json(args.output / "MP8_PAIRED_DEV_RESULT.json", scoring)
        print("MP8_PAIRED_DEV_RESULT=" + json.dumps(scoring, sort_keys=True),
              flush=True)
        return 0
    except Exception as exc:
        original_json(args.output / "MP8_FAILURE.json", {
            "error": f"{type(exc).__name__}: {exc}",
            "classification": "DEV_FAILED_OR_UNMATCHED_NO_TRANSFER_CLAIM",
            "qualification": "NO_GO", "science": "NOT_RUN",
            "time": timestamp(),
        })
        print("MP8_PAIRED_DEV_FAILED=" + str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
