"""One-shot physical MP6 changed-body challenge; original S49 only Action owner.

No retry / no qualification / no learning / no other Minecraft Worlds. The run
is only enabled by a dedicated one-use GitHub workflow push token.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from adapters.mineflayer.l23_paper_live_assets import L23PaperAssets, verify_paper_assets
from adapters.mineflayer.self_body_s50_l1_body_condition import verify_condition_config
from adapters.mineflayer.self_body_s50_l1_paper_local import check_local_paper_config

PAPER_SHA = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
CONFIRM = "MP6-SLOWNESS-II-ONE-FRESH-WORLD-DEV-NO-RETRY"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def original_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def port_free() -> bool:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", 25565))
        except OSError:
            return False
        return True


def verified_config(source: Path, target: Path) -> str:
    raw = source.read_text(encoding="utf-8")
    for key in (
        "dev-enabled", "s50-input-witness-dev", "s50-paper-local-forecast-dev",
        "s50-changed-body-condition-dev"
    ):
        off = f"{key}: false"
        if raw.count(off) != 1:
            raise ValueError(f"missing uniquely disabled MP5 source flag: {key}")
        raw = raw.replace(off, f"{key}: true")
    if "s50-tick-meter-dev:" in raw:
        raise ValueError("unexpected preconfigured S50 tick meter flag")
    raw = raw.replace("dev-enabled: true",
                      "dev-enabled: true\ns50-tick-meter-dev: true")
    target.write_text(raw, encoding="utf-8")
    digest = sha(target)
    check_local_paper_config(target, digest)
    verify_condition_config(target, digest)
    return digest


def parse_lines(path: Path) -> list[tuple[str, dict[str, str]]]:
    if not path.is_file():
        return []
    result = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = dict(part.split("=", 1) for part in line.split()
                      if part.count("=") == 1)
        result.append((line, fields))
    return result


def audit(root: Path, rc: int, expired: bool) -> dict:
    report_path = root / "s49-report.json"
    report = json.loads(report_path.read_text()) if report_path.is_file() else {}
    paper = root / "server.log"
    events = parse_lines(paper)
    raw_original = root / "paper-stdout-original.bin"
    raw_equal = raw_original.is_file() and paper.is_file() and (
        raw_original.read_bytes() == paper.read_bytes()
    )

    def with_kind(kind: str):
        return [(i, row) for i, (text, row) in enumerate(events)
                if kind + " marker_id=" in text]

    kinds = (
        "S50_DEV_LOCAL_MODEL_ARM", "S50_DEV_LOCAL_WAIT_ARMED",
        "S50_DEV_LOCAL_FORECAST_FIXED", "S50_DEV_LOCAL_FORECAST_SCORE",
        "S50_DEV_WAIT_TICK", "S50_DEV_INPUT_TICK",
    )
    found = {k: with_kind(k) for k in kinds}
    fixed = found["S50_DEV_LOCAL_FORECAST_FIXED"]
    scores = found["S50_DEV_LOCAL_FORECAST_SCORE"]
    wait = found["S50_DEV_WAIT_TICK"]
    arm = found["S50_DEV_LOCAL_MODEL_ARM"]
    journal = [json.loads(line) for line in
               (root / "prediction-original.jsonl").read_text().splitlines()] if (
                   root / "prediction-original.jsonl"
               ).is_file() else []
    host_fixed = [x for x in journal if x.get("kind") == "PREDICTION_FIXED"]
    ticket = next((x["ticket"] for x in journal
                   if x.get("kind") == "TARGET_FIXED"), None)

    chronological = len(arm) == 1 and len(wait) == 8 and len(fixed) == 7 and len(scores) == 7
    errors = []
    if chronological:
        arm_row = arm[0][1]
        model_sha = arm_row.get("ticket_sha256")
        slope = float(arm_row["slope"])
        chronological = (
            ticket is not None and ticket["ticket_sha256"] == model_sha
            and ticket["model"]["slope"] == slope
            and arm[0][0] < wait[0][0]
            and all(arm_row.get(k) == fixed[0][1].get(k)
                    for k in ("marker_id", "world", "subject_uuid"))
        )
        for i in range(7):
            index_t, sample_t = wait[i]
            index_next, sample_next = wait[i + 1]
            at_fixed, forecast = fixed[i]
            at_score, scored = scores[i]
            def displacement(sample):
                return math.dist(
                    [float(sample["from_" + axis]) for axis in "xyz"],
                    [float(sample[axis]) for axis in "xyz"],
                )
            observed = displacement(sample_t)
            actual = displacement(sample_next)
            prediction = float(forecast["predicted_m"])
            score_error = float(scored["abs_error_m"])
            valid = (
                index_t < at_fixed < index_next < at_score
                and int(forecast["prior_tick"]) == int(sample_t["tick"])
                and int(forecast["target_tick"]) == int(sample_next["tick"])
                and int(scored["target_tick"]) == int(sample_next["tick"])
                and scored["ticket_sha256"] == model_sha
                and forecast["ticket_sha256"] == model_sha
                and math.isclose(prediction, slope * observed, abs_tol=1e-12)
                and math.isclose(float(scored["actual_m"]), actual, abs_tol=1e-12)
                and math.isclose(float(scored["predicted_m"]), prediction, abs_tol=1e-12)
                and math.isclose(score_error, abs(prediction-actual), abs_tol=1e-12)
            )
            chronological = chronological and valid
            errors.append(score_error)
    else:
        chronological = False
    physical = [
        (i, fields) for i, (line, fields) in enumerate(events)
        if "S50_DEV_BODY_CONDITION_APPLIED marker_id=" in line
    ]
    effect_ticks = [
        (i, fields) for i, (line, fields) in enumerate(events)
        if "S50_DEV_BODY_CONDITION_TICK marker_id=" in line
    ]
    phys_record = physical[0][1] if len(physical) == 1 else {}
    original_condition_confirmed = (
        len(physical) == 1 and len(effect_ticks) == 8
        and len(found["S50_DEV_LOCAL_MODEL_ARM"]) == 1
        and len(found["S50_DEV_WAIT_TICK"]) == 8
        and physical[0][0] > found["S50_DEV_LOCAL_MODEL_ARM"][0][0]
        and physical[0][0] < found["S50_DEV_WAIT_TICK"][0][0]
        and all(e.get("condition") == "SLOWNESS_II"
                and e.get("amplifier") == "1" and e.get("active") == "true"
                for _, e in effect_ticks)
        and phys_record.get("condition") == "SLOWNESS_II"
        and phys_record.get("amplifier") == "1"
        and phys_record.get("status")
           == "EXPERIMENTER_PHYSICAL_INTERVENTION_PRE_S49_ACTION"
        and report.get("l1_paper_body_challenge", {}).get(
            "original_paper_effect_before_s49") is True
    )
    actions = report.get("actual_native_actions", [])
    movement = (
        actions[0].get("movement_m")
        if type(actions) is list and len(actions) == 1
        and isinstance(actions[0], dict) else None
    )
    baseline_m = 0.6269065734210615  # Prior MP5 original, not training source.
    shift = (
        movement is not None and math.isfinite(movement)
        and abs(movement - baseline_m) >= 0.06
    )
    original_motions = [
        math.dist(
            [float(row["from_" + a]) for a in "xyz"],
            [float(row[a]) for a in "xyz"],
        ) for _, row in wait
    ] if len(wait) == 8 else []
    zero_mae = (
        sum(abs(x) for x in original_motions[1:]) / 7
        if len(original_motions) == 8 else None
    )
    last_mae = (
        sum(abs(original_motions[i+1] - original_motions[i])
            for i in range(7)) / 7
        if len(original_motions) == 8 else None
    )
    train_mean = ticket.get("model", {}).get("trained_measured_mean_m") if ticket else None
    training_mean_mae = (
        sum(abs(x - train_mean) for x in original_motions[1:]) / 7
        if len(original_motions) == 8 and isinstance(train_mean, float) else None
    )
    source_ok = (
        original_condition_confirmed and
        rc == 0 and not expired and report.get("status") == "PASS"
        and report.get("node_exit") == 0 and report.get("server_exit") == 0
        and report.get("l1_paper_local_forecast", {}).get(
            "local_model_armed_before_action") is True
        and all(len(found[k]) == expected for k, expected in (
            ("S50_DEV_LOCAL_MODEL_ARM", 1),
            ("S50_DEV_LOCAL_WAIT_ARMED", 1),
            ("S50_DEV_LOCAL_FORECAST_FIXED", 7),
            ("S50_DEV_LOCAL_FORECAST_SCORE", 7),
            ("S50_DEV_WAIT_TICK", 8),
            ("S50_DEV_INPUT_TICK", 8),
        ))
        and len(host_fixed) == 7
        and raw_equal and chronological
    )
    return {
        "world_dev_pass": bool(source_ok),
        "condition_original_accepted_before_action": bool(original_condition_confirmed),
        "condition_paper_wait_samples": len(effect_ticks),
        "condition_physical": "SLOWNESS_II_REAL_PAPER_POTION_INTERVENTION",
        "native_move_m": movement,
        "prior_mp5_native_move_m": baseline_m,
        "absolute_native_move_shift_m": (
            abs(movement - baseline_m) if movement is not None else None
        ),
        "prespecified_native_shift_ge_0_06m": bool(shift),
        "distribution_shift": (
            "OBSERVED_DISTINCT_NATIVE_MOTION" if shift
            else "NOT_ESTABLISHED_BY_NATIVE_MOVE_METRIC"
        ),
        "host_original_report": {
            key: report.get(key) for key in (
                "status", "classification", "node_exit", "server_exit")
        },
        "launcher_exit": rc, "timeout": expired, "raw_stdout_identical": raw_equal,
        "paper_original_counts": {k: len(rows) for k, rows in found.items()},
        "host_original_forecasts": len(host_fixed),
        "pre_action_arm_and_seven_causal_callback_scores": bool(chronological),
        "local_model_mae_m": sum(errors) / 7 if len(errors) == 7 else None,
        "local_model_rmse_m": math.sqrt(sum(x*x for x in errors)/7)
        if len(errors) == 7 else None,
        "original_paper_wait_motions_m": original_motions,
        "zero_baseline_mae_m": zero_mae,
        "last_baseline_mae_m": last_mae,
        "training_mean_baseline_mae_m": training_mean_mae,
        "same_info_cheap": "MATHEMATICALLY_EQUIVALENT",
        "novel_generalization_proven": False,
        "experimenter_environment_intervention": True,
        "learning_admissions": 0, "goal": "UNDETERMINED",
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for key in ("output", "paper-jar", "plugin-jar", "config-default", "node-runtime"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.confirm != CONFIRM or not args.output.is_absolute():
        parser.error("one physical World requires explicit MP5 scope")
    if args.output.exists() or args.output.is_symlink():
        parser.error("fresh evidence directory required")
    args.output.mkdir(parents=True)
    node = args.node_runtime
    if not node.is_absolute() or node.is_symlink():
        raise ValueError("nonphysical Node runtime")
    pkg = json.loads((node / "node_modules/mineflayer/package.json").read_text())
    if pkg.get("version") != "4.39.0":
        raise ValueError("Mineflayer runtime mismatch")
    config = args.output / "mp5-active-config.yml"
    config_sha = verified_config(args.config_default, config)
    assets = L23PaperAssets(
        args.paper_jar, PAPER_SHA, args.plugin_jar, sha(args.plugin_jar),
        config, config_sha,
    )
    verified = verify_paper_assets(assets)
    if not port_free():
        raise RuntimeError("port 25565 not free before fresh World")
    original_json(args.output / "preflight.json", {
        "timestamp": timestamp(), "git_sha": os.environ.get("GITHUB_SHA"),
        "worlds_authorized": 1, "worlds_started": 0,
        "physical_assets": verified, "scope": "MP6_ONE_WORLD_SLOWNESS_II_BEFORE_ORIGINAL_S49",
    })
    if args.preflight_only:
        print("MP6_CHANGED_BODY_PREFLIGHT_OK physical_worlds_started=0")
        return 0
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": "src:tests:.", "PYTHONDONTWRITEBYTECODE": "1",
        "S49_REAL_SERVER_CI": "1",
        "RELAYSELF_RSEE_NODE_RUNTIME_ROOT": str(node),
        "RELAYSELF_S50_PACKET_WITNESS_DEV": str(
            args.output / "client-packet-original.jsonl"),
    })
    if env.get("NODE_OPTIONS"):
        raise RuntimeError("Node execution shim forbidden")
    cmd = [
        sys.executable, "-m", "adapters.mineflayer.self_body_s50_world_dev",
        "--report", str(args.output / "s49-report.json"),
        "--server-log", str(args.output / "server.log"),
        "--l16-capture-root", str(args.output / "capture"),
        "--l16-goal-target-x", "0", "--l16-goal-target-z", "0",
        "--l16-goal-tolerance-m", "0.49", "--l16-goal-stability-m", "0.05",
        "--l16-confirm", "L16-S49-FIRST-ACTION-ORIGINAL-DEV",
        "--l22-settling-probes", "6", "--selfbody-live-next-epoch-dev",
        "--selfbody-l1-motion-shadow-dev",
        "--l1-prediction-journal", str(args.output / "prediction-original.jsonl"),
        "--l1-paper-local-forecast-dev",
        "--l1-paper-body-challenge-dev",
        "--l23-paper-server-jar", str(args.paper_jar),
        "--l23-paper-server-sha256", PAPER_SHA,
        "--l23-paper-plugin-jar", str(args.plugin_jar),
        "--l23-paper-plugin-sha256", assets.plugin_sha256,
        "--l23-paper-config", str(config),
        "--l23-paper-config-sha256", config_sha,
    ]
    (args.output / "capture").mkdir()
    original_json(args.output / "WORLD_ATTEMPT_STARTED.json", {
        "timestamp": timestamp(), "git_sha": os.environ.get("GITHUB_SHA"),
        "original_host_argv": cmd, "retry": 0,
        "grant": "USER_L1_MOVEMENT_LANE_CONTINUING_20261101_MP6_1_WORLD",
    })
    rc, expired = 124, False
    with (args.output / "runner-original.stdout.log").open("xb") as source:
        child = subprocess.Popen(cmd, stdout=source, stderr=subprocess.STDOUT,
                                 env=env, start_new_session=True)
        try:
            rc = child.wait(timeout=240)
        except subprocess.TimeoutExpired:
            expired = True
            try:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=8)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
    verdict = audit(args.output, rc, expired)
    verdict["cleanup_port_rebind"] = port_free()
    verdict["worlds_started"] = 1
    verdict["world_dev_pass"] = verdict["world_dev_pass"] and verdict["cleanup_port_rebind"]
    original_json(args.output / "independent-mp5-dev-readback.json", verdict)
    print("MP6_CHANGED_BODY_ONE_WORLD_RESULT=" + json.dumps(verdict, sort_keys=True), flush=True)
    return 0 if verdict["world_dev_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
