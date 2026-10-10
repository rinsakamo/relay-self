"""Single-command RelaySelf *demo*, not a new cognition owner or scientific gate.

--smoke runs a three-epoch synthetic, typed S10/S11 continuity example.
--run-disposable invokes the ALREADY IMPLEMENTED S49 native 3-decision/two-Action
World host, under explicit consent, and converts its actual receipt into JSONL.

In particular, a S49 native Action OUTCOME is not verified goal success,
learned native Habit, L2 counterfactual competence or backend STOP ACK.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.learning import (
    FeedbackDirection,
    LearningFeedback,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance

CONFIRM = "SELF-DEMO-I-OWN-DISPOSABLE-WORLD"
SOURCE_SMOKE = "SYNTHETIC_SMOKE_ONLY"
SOURCE_NATIVE = "S49_REAL_MINEFLAYER_RECEIPT"
EXPECTED_DECISIONS = ("WAIT", "MOVE_AWAY", "MOVE_AWAY")


class DemoRejected(ValueError):
    """No fabricated physical, cognitive, or retained authority is allowed."""


def _row(kind: str, source: str, **fields: object) -> dict[str, object]:
    return {"kind": kind, "source_type": source, **fields}


def smoke_trace() -> tuple[dict[str, object], ...]:
    """Exercise existing S10 owner + S11 read over three *synthetic* epochs."""
    p = Provenance("self-demo-smoke-operator", "fixed-offline-cues")
    state = LearningPreferenceState(
        "risk_weight", 3, 0, 10, 0, p,
    )
    repertoire = HabitRepertoire(
        "self-demo-preconfigured-safe-only", 0,
        (HabitRule(
            "preconfigured-safe-wait",
            (CueFeature("safety", "safe"),),
            "WAIT", 1, p,
        ),),
        p,
    )
    rows: list[dict[str, object]] = [
        _row("start", SOURCE_SMOKE, session="synthetic-session-1",
             retained_revision=state.revision, habit_origin="PRECONFIGURED_NOT_LEARNED",
             real_actions=0, model_calls=0)
    ]
    # Fixed, clearly synthetic World source: none of these observations attest
    # an actual Minecraft move or independently proven real-world goal.
    for epoch, witness in enumerate(("safe", "threat", "safe"), start=1):
        cue = HabitCue(
            f"smoke-cue-{epoch}", (CueFeature("safety", witness),), p
        )
        selection = select_habit(repertoire, cue)
        chosen = (
            selection.selected_candidate_ref
            if selection.status is HabitSelectionStatus.SELECTED
            else "FLEE" if witness == "threat" else "ABSTAIN"
        )
        path = (
            "PRECONFIGURED_HABIT" if selection.status is HabitSelectionStatus.SELECTED
            else "CHEAP_L0_TEST_CHOICE" if witness == "threat"
            else "DEFER"
        )
        rows.append(_row(
            "epoch", SOURCE_SMOKE, epoch=epoch, present=witness,
            cognition_path=path, choice=chosen, retained_revision=state.revision,
            actual_world_action="NONE", issued_action=False,
        ))
        if epoch == 2:
            # Synthetic feedback is explicitly marked as a fixture and a
            # separately given owner authority is needed even in this smoke.
            feedback = LearningFeedback(
                "smoke-test-feedback-2", state.target_id,
                FeedbackDirection.INCREASE, p,
                consequence_ref="synthetic-escape-fixture-2",
            )
            proposal = propose_learning_update(
                state, feedback, LearningUpdateRule("smoke-step", 1, 1),
            )
            grant = LearningUpdateAuthority(
                "smoke-local-update-grant", state.target_id, p,
            )
            committed = commit_learning_update(
                state, proposal, grant, provenance=p,
            )
            if committed.new_state.revision != state.revision + 1:
                raise DemoRejected("S10 owner revision did not advance")
            rows.append(_row(
                "synthetic_feedback", SOURCE_SMOKE, epoch=epoch,
                observed_outcome="FIXTURE_ONLY_NOT_PHYSICAL",
                update_issued_by="EXPLICIT_SMOKE_OWNER_GRANT",
                prior_revision=state.revision,
                new_revision=committed.new_state.revision,
                prior_value=state.value, new_value=committed.new_state.value,
                production_habit_granted=False,
            ))
            state = committed.new_state
    rows.append(_row(
        "summary", SOURCE_SMOKE, decisions=3, actual_world_actions=0,
        real_model_calls=0, retained_revision=state.revision,
        synthetic_learning_updates=1, native_goal_attested=False,
        production_habit_granted=False,
    ))
    return tuple(rows)


def project_native_report(report: dict[str, object]) -> tuple[dict[str, object], ...]:
    """Normalize a completed real S49 run; cannot mint absent source receipts."""
    if not isinstance(report, dict):
        raise DemoRejected("typed native report required")
    decisions = report.get("decisions")
    actions = report.get("actual_native_actions")
    probes = report.get("source_pair_trace")
    session = report.get("session_id")
    if (report.get("milestone") != "S49" or report.get("status") != "PASS"
            or report.get("classification")
            != "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED"
            or not isinstance(session, str) or not session
            or not isinstance(decisions, list) or len(decisions) != 3
            or not isinstance(actions, list) or len(actions) != 2
            or not isinstance(probes, list) or len(probes) != 3
            or report.get("real_model_calls") != 0
            or report.get("learning_in_world") is not False):
        raise DemoRejected("source run not complete or mixed with new evidence")
    if tuple(d.get("selected") for d in decisions if isinstance(d, dict)) != EXPECTED_DECISIONS:
        raise DemoRejected("actual native decisions do not match S49 owner")
    if any(not isinstance(d, dict) for d in decisions):
        raise DemoRejected("missing typed native decision")
    if any(not isinstance(a, dict) for a in actions):
        raise DemoRejected("missing typed native Action closure")
    if any(not isinstance(v, dict) for v in probes):
        raise DemoRejected("missing paired native probe source")

    outcome_for_event = {a.get("event_seq"): a for a in actions}
    if (len(outcome_for_event) != 2
            or any(a.get("terminal") != "outcome"
                   or a.get("source") != session
                   or not isinstance(a.get("movement_m"), (int, float))
                   or isinstance(a.get("movement_m"), bool)
                   or not 0.05 <= a["movement_m"] < 16
                   or not isinstance(a.get("action"), str)
                   or not a["action"]
                   for a in actions)):
        raise DemoRejected("invalid native issued Action OUTCOME")
    event_seq = [d.get("event_seq") for d in decisions]
    if (any(type(v) is not int or v < 0 for v in event_seq)
            or len(set(event_seq)) != 3 or event_seq != sorted(event_seq)
            or set(outcome_for_event) != set(event_seq[1:])
            or len({a["action"] for a in actions}) != 2):
        raise DemoRejected("stale, foreign or duplicate native Action event")
    if (any(p.get("event_seq") != d.get("event_seq")
            or p.get("probe_seq") != d.get("probe_seq")
            or type(d.get("probe_seq")) is not int
            or d.get("probe_seq") <= d["event_seq"]
            for p, d in zip(probes, decisions, strict=True))
            or any(d.get("issued") is not (i > 0)
                   for i, d in enumerate(decisions))):
        raise DemoRejected("uncorrelated native Present source or Action")

    rows = [_row(
        "start", SOURCE_NATIVE, session=session, minecraft_version=report.get("minecraft_version"),
        mineflayer_version=report.get("mineflayer_version"), retained_origin=report.get("retained_origin"),
        retained_learning_during_live_run=False,
    )]
    for i, (d, evidence) in enumerate(zip(decisions, probes, strict=True), start=1):
        rows.append(_row(
            "native_observation", SOURCE_NATIVE, epoch=i, session=session,
            event_seq=d["event_seq"], probe_seq=d["probe_seq"],
            target_entity_id=d["entity_id"], target_distance_m=d["distance_m"],
            native_probe_entities=evidence.get("probe_entities"),
        ))
        rows.append(_row(
            "decision", SOURCE_NATIVE, epoch=i, cognition_path="L0_WORLD",
            selected=d["selected"], real_model_calls=0,
            issued_native_action=d["issued"], retained_origin=report.get("retained_origin"),
        ))
        if d["issued"]:
            a = outcome_for_event[d["event_seq"]]
            rows.append(_row(
                "native_action_outcome", SOURCE_NATIVE, epoch=i,
                action_id=a["action"], terminal=a["terminal"],
                world_source_session=a["source"],
                movement_m=a["movement_m"],
                goal_success_attested=False, signed_negative_z=False,
                retained_update=False,
            ))
    rows.append(_row(
        "summary", SOURCE_NATIVE, decisions=3, native_terminal_actions=2,
        real_model_calls=0, in_world_learning_updates=0,
        production_habit_granted=False, signed_goal_labels=0,
        server_exit=report.get("server_exit"),
    ))
    return tuple(rows)


def _write_trace(path: Path | None, rows: tuple[dict[str, object], ...]) -> None:
    encoded = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                      for row in rows)
    if path is None:
        sys.stdout.write(encoded)
        return
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise DemoRejected("trace destination must be a regular file")
    if not path.parent.is_dir():
        raise DemoRejected("trace parent directory must already exist")
    # Refuse to overwrite retained evidence from a previous owned run.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    sys.stdout.write(encoded)


async def _run_disposable(report_path: Path, server_log: Path) -> int:
    # Existing exact S49 host is the *only* issuer. No duplicated event loop,
    # no new Game Action code or arbitrary LLM output -> Action mapping.
    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    previous = os.environ.get("S49_REAL_SERVER_CI")
    os.environ["S49_REAL_SERVER_CI"] = "1"
    try:
        return await qualify(report_path, server_log)
    finally:
        if previous is None:
            os.environ.pop("S49_REAL_SERVER_CI", None)
        else:
            os.environ["S49_REAL_SERVER_CI"] = previous


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RelaySelf one-command demo: 3 native L0 decisions or an offline S10/S11 smoke",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true", help="synthetic 3-epoch S10/S11 demo")
    mode.add_argument("--run-disposable", action="store_true",
                      help="explicitly start owned disposable Mojang server and S49 bot")
    parser.add_argument("--confirm", help="required exact consent for disposable world")
    parser.add_argument("--output-dir", type=Path, help="pre-existing output directory")
    args = parser.parse_args(argv)

    if args.run_disposable:
        if args.confirm != CONFIRM:
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="OPERATOR_CONSENT_REQUIRED",
                expected_confirmation=CONFIRM, actual_actions=0,
            ), sort_keys=True))
            return 2
        if args.output_dir is None or not args.output_dir.is_dir() or args.output_dir.is_symlink():
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="OUTPUT_DIRECTORY_NOT_PREPARED",
                actual_actions=0,
            ), sort_keys=True))
            return 2
        if not shutil.which("java") or not shutil.which("node"):
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="JAVA_AND_NODE_REQUIRED",
                actual_actions=0,
            ), sort_keys=True))
            return 2
        if os.environ.get("NODE_OPTIONS"):
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="NODE_SHIM_NOT_ALLOWED",
                actual_actions=0,
            ), sort_keys=True))
            return 2
        report_file = args.output_dir / "native_report.json"
        server_log = args.output_dir / "minecraft_server.log"
        trace_file = args.output_dir / "self_trace.jsonl"
        if any(path.exists() or path.is_symlink()
               for path in (report_file, server_log, trace_file)):
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="EVIDENCE_ALREADY_EXISTS",
                actual_actions=0,
            ), sort_keys=True))
            return 2
        try:
            code = asyncio.run(_run_disposable(report_file, server_log))
            if code != 0:
                print(json.dumps(_row(
                    "unknown", SOURCE_NATIVE, reason="NATIVE_OWNER_DID_NOT_QUALIFY",
                    native_report=str(report_file), action_outcome="UNKNOWN",
                ), sort_keys=True))
                return code
            result = json.loads(report_file.read_text(encoding="utf-8"))
            _write_trace(trace_file, project_native_report(result))
            return 0
        except (DemoRejected, OSError, RuntimeError, ValueError) as exc:
            print(json.dumps(_row(
                "unknown", SOURCE_NATIVE, reason=type(exc).__name__,
                signed_goal_labels=0, production_habit_granted=False,
            ), sort_keys=True))
            return 1

    if args.smoke:
        _write_trace(None, smoke_trace())
        return 0
    print(json.dumps(_row(
        "ready", "NO_WORLD_USED", mode="DRY_RUN",
        actions_issued=0, model_calls=0,
        next="--smoke or --run-disposable with explicit --confirm and --output-dir",
        warning="Native is existing S49 three-event test-world behavior, not a full autonomous Self 1.0",
    ), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
