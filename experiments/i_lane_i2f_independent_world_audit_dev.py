"""I2f independent NEW original A/B World + dual L2/L1 raw source audit.

Run in a separate fresh process *after* the owned World has fully exited.
Does not load the model, launch World, POST, mutate cognition or issue Action.
It independently reads original archived v3 A/B, original Native stdin/out,
owned Paper ACKs/log, the two real llama entity bodies, durable Owner delta,
and revalidates GGUF file identity. Fails closed on missing/partial source.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    parse_mineflayer_line,
)
from experiments.i_lane_i1_independent_cpu_audit_dev import _paper_prefixes
from experiments.i_lane_i2e_independent_dual_model_audit_dev import (
    independently_audit_i2e_model_bundle,
)
from experiments.stage24g_model_gate_dev import PINNED_STAGE24G_GGUF_SHA256
from experiments.stage28c2b_independent_rejoin_audit_dev import (
    _sha,
    _verify_main_thread_ack,
    independently_audit_recovered_real_rejoin,
)
from relay_self.i_lane_i2f_future_source_pins_dev import (
    I2fFutureSourcePins,
    read_i2f_future_source_pins,
)


class I2fIndependentWorldHold(RuntimeError):
    """Original new-v3 Source, World, model or Self attribution not proven."""


_I1_REF = re.compile(r"i1-original-sense-[0-9a-f]{32}\Z")


def _model_native_correlation(
    *, report: dict, evidence: Path, executable: Path, raw_dir: Path,
) -> dict:
    """Independently correlate model's frozen actual source to native/Paper."""
    model = json.loads((raw_dir / "i2e-dual-model-report.json").read_bytes())
    frozen = model.get("handoff")
    if type(frozen) is not dict:
        raise I2fIndependentWorldHold("original source-bound I2 handoff missing")
    sid = model.get("self_id")
    if sid != "A" or frozen.get("self_id") != "A":
        raise I2fIndependentWorldHold("original A-only model adoption scope missing")
    paper = report["paper_boot"]
    if (
        frozen.get("paper_session_id") != paper["paper_session_id"]
        or frozen.get("native_session_id")
        != report["native_login_evidence"]["A"]["native_session_id"]
        or frozen.get("resident_epoch") !=
        model["open_l2_ticket"]["self_epoch"]
        or frozen.get("paper_log_sha256") is None
        or frozen.get("paper_tick_source_ref") is None
        or frozen.get("model_invoked") is not False
        or frozen.get("action_issue_authorized") is not False
        or frozen.get("status") != "NO_QUALIFIED_EXPLORATION_GOAL"
    ):
        raise I2fIndependentWorldHold("model source invented new original Native/Paper")
    paper_frozen = (evidence / "prestop-paper-resident-owned.log").read_bytes()
    hashes = _paper_prefixes(paper_frozen)
    prefix = hashes.get(frozen["paper_log_sha256"])
    if prefix is None:
        raise I2fIndependentWorldHold("source Paper log prefix absent from original Popen")
    raw_paper = (
        evidence / (paper["paper_session_id"] + ".log")
    ).read_bytes()
    if raw_paper[:prefix] != paper_frozen[:prefix]:
        raise I2fIndependentWorldHold("original Paper prefix no longer identical")
    # Paper time is distinct from Native World day clock. Do not fabricate
    # ACK by re-reading newest Paper tick rather than the frozen ref.
    paper_tick_source = frozen["paper_tick_source_ref"]
    match = re.fullmatch(
        r"paper-main-thread:p0d:([A-Za-z0-9-]+):"
        r"([A-Za-z0-9-]+):sha256:[a-f0-9]{64}",
        paper_tick_source,
    )
    if match is None or match.group(1) != paper["paper_boot_id"]:
        raise I2fIndependentWorldHold("Paper tick source boot not original")
    # Independently parse the archived Paper plugin ACK nonce and require
    # the exact original Popen stdout witness, not the latest paper tick.
    nonce = match.group(2)
    ack_path = (
        executable / "plugins" / "P0BRecorder" / "p0d-ticks"
        / "acks" / (nonce + ".ack")
    )
    try:
        ack_rows = ack_path.read_text(encoding="utf-8").splitlines()
        ack = dict(line.split("=", 1) for line in ack_rows)
        if len(ack_rows) != len(ack):
            raise ValueError("duplicate Paper ACK rows")
        _verify_main_thread_ack(
            executable, paper_session=paper["paper_session_id"],
            world_id=paper["source_world_id"],
            boot_id=paper["paper_boot_id"],
            ref=paper_tick_source,
            tick=int(ack["paper_tick"]), paper_stdout=raw_paper,
        )
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        raise I2fIndependentWorldHold("model Paper nonce/source not archived") from exc
    a = report["native_login_evidence"]["A"]
    native = a["native_session_id"]
    stdout = evidence / f"native-RelayA-{native}.jsonl"
    stdin = evidence / f"native-commands-RelayA-{native}.jsonl"
    if (
        _sha(stdout) != report["raw_native_file_sha256"]["RelayA"]
        or _sha(stdin) != report["raw_native_command_file_sha256"]["RelayA"]
        or stdout.stat().st_size > 32 * 1024 * 1024
        or stdin.stat().st_size > 128 * 1024
    ):
        raise I2fIndependentWorldHold("original A raw native session changed")
    request = frozen["native_request_id"]
    if type(request) is not str or _I1_REF.fullmatch(request) is None:
        raise I2fIndependentWorldHold("model prompt did not use original read-only probe")
    observations = []
    for line in stdout.read_bytes().splitlines():
        found = parse_mineflayer_line(line.decode("utf-8"))
        if (
            found.session_id == native
            and isinstance(found, MineflayerObservation)
            and found.kind == "probe"
            and found.request_id == request
        ):
            observations.append(found)
    if (
        len(observations) != 1
        or observations[0].seq != frozen["native_seq"]
        or observations[0].snapshot.time is None
    ):
        raise I2fIndependentWorldHold("model-cited A Native observation not in raw stdout")
    commands = [
        json.loads(line) for line in stdin.read_bytes().splitlines()
    ]
    if (
        not commands or any(
            type(row) is not dict or set(row) != {"type", "request_id"}
            or row["type"] != "observe"
            for row in commands
        )
        or len({row["request_id"] for row in commands}) != len(commands)
        or sum(row["request_id"] == request for row in commands) != 1
        or commands[-1]["request_id"] != request
    ):
        raise I2fIndependentWorldHold("model source is not last genuine native A stdin probe")
    # B is observed from its original Native session, but never adopts A.
    b = report["native_login_evidence"]["B"]
    b_commands = evidence / (
        f"native-commands-RelayB-{b['native_session_id']}.jsonl"
    )
    if (
        _sha(b_commands) != report["raw_native_command_file_sha256"]["RelayB"]
        or any(
            row.get("type") != "observe"
            for row in (json.loads(line) for line in b_commands.read_bytes().splitlines())
        )
    ):
        raise I2fIndependentWorldHold("foreign/physical Native command in B session")
    return {
        "original_a_native_request_id": request,
        "native_seq": frozen["native_seq"],
        "original_paper_prefix_sha256": frozen["paper_log_sha256"],
        "paper_prefix_bytes": prefix,
        "owner_self": sid,
    }


def independently_audit_i2f_original_world(
    *, result: Path, generation: Path, restored: Path,
    original_evidence: Path, executable: Path,
    pins: I2fFutureSourcePins,
) -> dict:
    """PASS only with BOTH original independent World and raw Model audits."""
    if not isinstance(pins, I2fFutureSourcePins):
        raise I2fIndependentWorldHold("immutable pinned new-v3 source required")
    report = json.loads(result.read_bytes())
    evidence = result.parent
    raw_dir = evidence / "i2f-original-dual-model"
    if (
        report.get("real_world_trials") != 1
        or report.get("real_gemma_post") != 2
        or report.get("model_post_attempted") != 2
        or report.get("i2f_future_source") is not True
        or report.get("i2f_dual_model_completed") is not True
        or report.get("physical_action_issue_authorized") is not False
        or report.get("real_action_issued") != 0
        or report.get("cleanup_uncertain")
        or report.get("raw_source_audit_uncertain")
    ):
        raise I2fIndependentWorldHold("original I2f World or model capture incomplete")
    # This original auditor verifies physical zero, Paper owned stdout and
    # nonce ACK files, each Native raw stdin/out and terminal WAL/retirement.
    base = independently_audit_recovered_real_rejoin(
        result, generation=generation, restored=restored,
        stage28b_evidence=original_evidence,
        executable=executable, expected_gemma_posts=2,
        expected_i1_cpu_sense=True, future_pins=pins,
    )
    if (
        base.get("classification")
        != "I2F_BASE_FUTURE_V3_ORIGINAL_NATIVE_PAPER_SOURCE_VERIFIED_DEV"
        or base.get("i2f_original_model_bundle_audited") is not True
        or base.get("i2f_real_world_model_qualified") is not False
        or base.get("real_action_issued") != 0
    ):
        raise I2fIndependentWorldHold("base native/Paper/Owner source not independently verified")
    bundle = independently_audit_i2e_model_bundle(raw_dir)
    if (
        bundle.get("self_id") != "A"
        or bundle.get("real_world_dev_pass") is not False
        or bundle.get("physical_action_count") != 0
        or report.get("i2f_model_result") != bundle.get("model_result")
    ):
        raise I2fIndependentWorldHold("raw L2/L1 adoption differs from real World report")
    gate_file = evidence / "i2f-model-preflight.json"
    gate = json.loads(gate_file.read_bytes())
    if (
        gate != report.get("i2f_model_gate")
        or gate.get("model_alias") != bundle.get("model_alias")
        or type(gate.get("llama_pid")) is not int
        or gate["llama_pid"] <= 1
        or gate.get("slot_count") != 1 or gate.get("slot_id") != 0
        or gate.get("gguf_sha256") != PINNED_STAGE24G_GGUF_SHA256
        or _sha(Path(gate["gguf_path"])) != PINNED_STAGE24G_GGUF_SHA256
        or bundle.get("backend_ref") != "i2f-pid-" + str(gate["llama_pid"])
        or type(gate.get("gpu_name")) is not str
        or "RTX 3060" not in gate["gpu_name"]
        or not re.fullmatch("[0-9a-f]{64}", gate.get("maps_sha256", ""))
        or not re.fullmatch("[0-9a-f]{64}", gate.get("native_cmdline_sha256", ""))
    ):
        raise I2fIndependentWorldHold("real model GGUF/PID/preflight identity unverified")
    idle = report.get("stage28c2c_backend_terminal_idle", {})
    if (
        idle.get("backend_ref") != bundle["backend_ref"]
        or idle.get("n_slots") != 1 or idle.get("slot_id") != 0
        or idle.get("is_processing") is not False
    ):
        raise I2fIndependentWorldHold("model terminal idle slot not archived")
    correlated = _model_native_correlation(
        report=report, evidence=evidence,
        executable=executable, raw_dir=raw_dir,
    )
    # Earlier reporter classification is pending audit; this audit alone
    # qualifies only a *scoped* new World DEV. No QUAL/SCIENCE or general
    # B/D/C Owner authority can be inferred.
    return {
        "classification": "I2F_NEW_V3_ORIGINAL_WORLD_L2_L1_SOURCE_AUDITED_DEV",
        "same_original_owner": True,
        "original_source_committed_sha256": pins.source_committed_sha256,
        "world_id": pins.source_world_id,
        "world_branch": pins.fork_branch_id,
        "verified_model_choice": bundle["model_result"],
        "world_and_model_raw_correlated": correlated,
        "original_native_paper_world_independently_verified": True,
        "real_world_dev_pass": True,
        "physical_action_count": 0,
        "qual_go": False,
        "science_run": False,
        "general_restored_schema_qualified": False,
        "independent_llama_packet_headers_attested": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--original-evidence", type=Path, required=True)
    parser.add_argument("--execution-dir", type=Path, required=True)
    parser.add_argument("--new-source-pins", type=Path, required=True)
    args = parser.parse_args()
    try:
        audited = independently_audit_i2f_original_world(
            result=args.result, generation=args.generation,
            restored=args.restored, original_evidence=args.original_evidence,
            executable=args.execution_dir,
            pins=read_i2f_future_source_pins(args.new_source_pins),
        )
        print(json.dumps(audited, sort_keys=True), flush=True)
        return 0
    except BaseException as exc:
        print(f"I2F_INDEPENDENT_WORLD_HOLD={type(exc).__name__}:{exc}",
              file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
