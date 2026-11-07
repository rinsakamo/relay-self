"""D6-D6 DEV: independent vanilla RNG World samples for genuine zero -> next ATTACK.

Never rerun an original World or Action. A second fresh Paper World may start
ONLY after the previous distinct World has a FULL independent native/Paper/
original S49 ATTACK+MOVE ledger audit, clean Java/Node cleanup and evidence
hashes. We STOP sampling when a real zero->new-generation ATTACK is proven.
Up to four independent disposable DEV Worlds, not an unlimited Self policy.

The existing original S49 Action owner and original run/post implementations
are reused completely unchanged; this orchestrator never issues an Action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


class NaturalZeroSampleRejected(RuntimeError):
    """One real World/sample is not fully clean; do not start a new World."""


def judge_independent_sample(report: dict, attestation: dict) -> dict:
    """Requires the original independent Paper/native/dual-journal audit first."""
    if (
        not isinstance(report, dict) or not isinstance(attestation, dict)
        or report.get("status") != "PASS_DEV"
        or attestation.get("status") != "PASS_DEV"
        or report.get("node_exit") != 0
        or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
        or report.get("d6_multigen_source_natural_drop_rng_unchanged") is not True
        or report.get("d6_multigen_operator_forced_zero") is not False
        or attestation.get("operator_forced_zero_not_vanilla_rng") is not False
        or attestation.get("same_supervisor_retained") is not True
        or attestation.get("all_real_respawns_world_600_ticks") is not True
        or attestation.get("unresolved_nonmotion") is not False
        or attestation.get("unresolved_motion") is not False
        or attestation.get("no_eat_after_move") is not True
        or not isinstance(report.get("d6_multigen_generations"), list)
        or not report["d6_multigen_generations"]
        or attestation.get("completed_original_s49_kill_generations")
           != len(report["d6_multigen_generations"])
        or attestation.get("original_attack_count", 0) < 1
    ):
        raise NaturalZeroSampleRejected(
            "vanilla sample cannot be advanced without original fully closed source"
        )
    epochs = report["d6_multigen_generations"]
    amounts = [e.get("real_rotten_count") for e in epochs]
    if (
        amounts != attestation.get("natural_counts")
        or any(type(n) is not int or not 0 <= n <= 2 for n in amounts)
        or not isinstance(attestation.get("paper_world_uuid"), str)
        or not isinstance(attestation.get("session_id"), str)
        or not attestation["paper_world_uuid"]
        or not attestation["session_id"]
    ):
        raise NaturalZeroSampleRejected(
            "independent original Paper vanilla loot counts do not agree"
        )
    zero_then_attack = any(
        epochs[i]["real_rotten_count"] == 0
        and epochs[i+1]["generation"] == epochs[i]["generation"] + 1
        and epochs[i+1]["native_zombie_id"] != epochs[i]["native_zombie_id"]
        and epochs[i+1]["paper_zombie_uuid"] != epochs[i]["paper_zombie_uuid"]
        and epochs[i]["respawn_tick"] - epochs[i]["death_tick"] == 600
        and isinstance(epochs[i+1]["action_ids"], list)
        and bool(epochs[i+1]["action_ids"])
        and epochs[i+1]["death_tick"] > epochs[i]["respawn_tick"]
        for i in range(len(epochs)-1)
    )
    # Full corroboration (S16 terminal, native ID, killed by Self, 600tick
    # independent Paper respawn and 3/4 original Intent rearms) is performed
    # by bug0_d6_multigen_post.audit BEFORE this read-only adjudicator.
    if zero_then_attack and attestation["original_attack_count"] < 2:
        raise NaturalZeroSampleRejected("second authentic S49 ATTACK not closed")
    if not zero_then_attack and not (
        amounts[0] > 0
        and len(epochs) == 1
        and attestation.get("original_move_count", 0) >= 1
        and attestation.get("natural_item_uuid")
        and attestation.get("classification")
           == "D6_MULTIGEN_FIRST_REAL_NATURAL_MOVE_PICKUP_EAT_FENCED_PASS"
    ):
        raise NaturalZeroSampleRejected(
            "neither verified natural-zero continuation nor fully closed "
            "genuine positive loot pickup; never start another World"
        )
    return {
        "paper_world_uuid": attestation["paper_world_uuid"],
        "native_session_id": attestation["session_id"],
        "natural_counts": amounts,
        "completed_generations": len(epochs),
        "original_s49_attack_count": attestation["original_attack_count"],
        "original_s49_move_count": attestation.get("original_move_count", 0),
        "genuine_natural_zero_to_new_s49_attack_proven": zero_then_attack,
        "classification": (
            "D6_D6_VANILLA_REAL_ZERO_NEXT_ORIGINAL_S49_ATTACK_PASS"
            if zero_then_attack
            else "D6_D6_INDEPENDENT_REAL_POSITIVE_PICKUP_ZERO_NOT_SEEN"
        ),
        "previous_world_clean_independently_attested": True,
        "vanilla_rng_unchanged": True,
        "two_file_global_exactly_once_proven": False,
        "self_eat_after_move": False,
    }


def _sha_manifest(folder: Path) -> None:
    files = sorted(p for p in folder.iterdir()
                   if p.is_file() and p.name != "SHA256SUMS.txt")
    text = "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
        for p in files
    )
    (folder / "SHA256SUMS.txt").write_text(text, encoding="utf8")


def _assert_grant(max_worlds: int, root: Path) -> None:
    if (
        type(max_worlds) is not int or not 1 <= max_worlds <= 4
        or os.environ.get("D6_VANILLA_REPLICATES_WORLD_ONLY") != "1"
        or os.environ.get("D6_NATURAL_MULTIGEN_WORLD_ONLY") != "1"
        or os.environ.get("D6_NATURAL_DROP_MOVE_WORLD_ONLY") != "1"
        or os.environ.get("S49_D5_NONMOTION_FENCE_DEV_ONLY") != "1"
        or os.environ.get("S49_REAL_SERVER_CI") != "1"
        or os.environ.get("BUG0_S49_D4_ONE_WORLD_ONLY") != "1"
        or os.environ.get("D6_CONTROLLED_ZERO_WORLD_ONLY") is not None
        or root.exists()
        or not root.parent.is_dir()
    ):
        raise NaturalZeroSampleRejected(
            "separate original S49 vanilla independent-World sample grant absent"
        )


def _call(*args: str) -> None:
    # Never retry nonzero or unknown original physical effects; subprocess
    # is the only owner of the original World and all original S49 Actions.
    completed = subprocess.run([sys.executable, "-B", *args], check=False)
    if completed.returncode != 0:
        raise NaturalZeroSampleRejected(
            f"original source process exited {completed.returncode}; no reissue"
        )


def run_independent_world_samples(root: Path, *, max_worlds: int = 4) -> dict:
    _assert_grant(max_worlds, root)
    root.mkdir(parents=False, exist_ok=False)
    samples: list[dict] = []
    unique_worlds: set[str] = set()
    unique_sessions: set[str] = set()
    unique_action_ids: set[str] = set()
    targeted = False
    failure = None
    try:
        for ordinal in range(1, max_worlds+1):
            # One directory = one fresh World, native session, Action IDs and
            # two original fsynced physical ledgers, never another attempt.
            folder = root / f"world_{ordinal:02d}"
            folder.mkdir(exist_ok=False)
            report = folder / "report.json"
            paper = folder / "paper_original.log"
            attack = folder / "original_nonmotion_fence.json"
            move = folder / "original_motion_fence.json"
            audit = folder / "independent_source_audit.json"
            try:
                _call(
                    "tools/bug0_d6_multigen_world.py",
                    "--report", str(report),
                    "--server-log", str(paper),
                    "--nonmotion-fence", str(attack),
                    "--motion-fence", str(move),
                )
                _call(
                    "tools/bug0_d6_multigen_post.py",
                    "--report", str(report),
                    "--server-log", str(paper),
                    "--nonmotion-fence", str(attack),
                    "--motion-fence", str(move),
                    "--out", str(audit),
                )
                original = json.loads(report.read_text(encoding="utf8"))
                independent = json.loads(audit.read_text(encoding="utf8"))
                result = judge_independent_sample(original, independent)
                wid = result["paper_world_uuid"]
                sid = result["native_session_id"]
                if wid in unique_worlds or sid in unique_sessions:
                    raise NaturalZeroSampleRejected(
                        "same Paper World or native Self session reappeared"
                    )
                unique_worlds.add(wid)
                unique_sessions.add(sid)
                persisted = json.loads(attack.read_text(encoding="utf8"))
                # Do not assume a new World yields new IDs solely from the
                # folder path; original S49 action IDs must be disjoint.
                for row in persisted.get("actions", []):
                    action_id = row["action_id"]
                    if action_id in unique_action_ids:
                        raise NaturalZeroSampleRejected(
                            "original S49 physical ATTACK ID reused across independent Worlds"
                        )
                    unique_action_ids.add(action_id)
                result["ordinal"] = ordinal
                samples.append(result)
                print(json.dumps(result, sort_keys=True), flush=True)
                if result["genuine_natural_zero_to_new_s49_attack_proven"]:
                    targeted = True
                    break
            finally:
                _sha_manifest(folder)
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        summary = {
            "status": "FAIL_DEV" if failure else "PASS_DEV",
            "classification": (
                "D6_D6_VANILLA_ZERO_NEXT_S49_REAL_WORLD_PASS"
                if targeted and not failure else
                "D6_D6_BOUNDED_INDEPENDENT_RNG_NO_ZERO_OBSERVED"
                if not failure else
                "D6_D6_WORLD_SOURCE_OR_ACTION_UNQUALIFIED_NO_REISSUE"
            ),
            "world_budget": max_worlds,
            "independent_worlds_completed": len(samples),
            "genuine_vanilla_zero_to_next_s49_attack_proven": targeted,
            "normal_vanilla_rng_not_modified": True,
            "product_self_policy_limit_changed": False,
            "prior_world_action_reissued": False,
            "stop_on_uncertain_original_action": True,
            "original_global_exactly_once_proven": False,
            "qualification": "NO_GO",
            "science": "NOT_RUN",
            "samples": samples,
            "failure": failure,
        }
        (root / "sample_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf8",
        )
        _sha_manifest(root)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--max-worlds", type=int, default=4)
    args = parser.parse_args()
    result = run_independent_world_samples(
        args.evidence_dir, max_worlds=args.max_worlds,
    )
    print("D6_D6_INDEPENDENT_VANILLA_RNG_RESULT=" + result["classification"])
    print("D6_D6_GENUINE_ZERO_THEN_NEXT_ORIGINAL_S49_PROVEN="
          + str(result["genuine_vanilla_zero_to_next_s49_attack_proven"]))


if __name__ == "__main__":
    main()
