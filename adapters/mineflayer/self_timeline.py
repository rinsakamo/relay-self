"""Read-only Self product event timeline for terminals and a future RelayUI.

Projects ALREADY-COMPLETED S49 + optional L2 and retained Memory receipts.
Never starts Mineflayer/llama.cpp, issues an Action, signs a World goal,
updates Memory/Habit, or claims network/server/GGUF source attestation.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from adapters.mineflayer.self_demo import project_native_report
from relay_self.persistent_cognition import PersistentCognition, load_persistent_cognition

SCHEMA = "relay-self.product.cognition-timeline.v1"
MAX_SOURCE_BYTES = 2_000_000


class TimelineRejected(ValueError):
    """A report, model sidecar or retained snapshot failed source alignment."""


def timeline(
    report: dict[str, Any], *,
    live_l2: dict[str, Any] | None = None,
    memory: PersistentCognition | None = None,
) -> tuple[dict[str, Any], ...]:
    """Pure cross-owner VIEW of one completed session; no new decision owner."""
    original = project_native_report(report)
    first = original[0]
    sid = first["session"]
    observations = [r for r in original if r["kind"] == "native_observation"]
    decisions = [r for r in original if r["kind"] == "decision"]
    actions = [r for r in original if r["kind"] == "native_action_outcome"]
    if len(observations) != 3 or len(decisions) != 3 or len(actions) != 2:
        raise TimelineRejected("incomplete S49 owner projection")
    def event(kind: str, **values: Any) -> dict[str, Any]:
        return {"schema": SCHEMA, "kind": kind, "session": sid, **values}
    rows: list[dict[str, Any]] = [
        event("session", source="S49_COMPLETED_REPORT",
              authority="REPORTED_NOT_INDEPENDENTLY_ATTESTED",
              source_frame_status=first["frame_format"],
              minecraft_started_by_viewer=False, model_started_by_viewer=False,
              recorded_world_goals_signed=0),
    ]
    for index, (obs, choice) in enumerate(zip(observations, decisions, strict=True)):
        epoch = index + 1
        distance = obs["target_distance_m"]
        if (type(distance) not in (float, int) or not math.isfinite(distance)
                or not 0 < distance <= 16):
            raise TimelineRejected("invalid native geometric observation")
        rows.append(event(
            "present", epoch=epoch, source="S49_WORLD_PROBE",
            event_seq=obs["event_seq"], probe_seq=obs["probe_seq"],
            target_distance_m=distance, entity_id=obs["target_entity_id"],
            physical_source_attestation="NOT_INDEPENDENTLY_VERIFIED",
        ))
        rows.append(event(
            "selection", epoch=epoch, level="L0", owner="S49_NATIVE_L0",
            candidate=choice["selected"], issued_action=choice["issued_native_action"],
            l2_action_authority=False, learned_habit_authority=False,
        ))
        if choice["issued_native_action"]:
            item = next(a for a in actions if a["epoch"] == epoch)
            rows.append(event(
                "action_outcome", epoch=epoch, owner="ORIGINAL_S49_S16",
                action_id=item["action_id"], terminal=item["terminal"],
                observed_movement_m=item["movement_m"],
                original_decoded_frames_retained=item["action_frames_complete"],
                spatial_goal_success="UNKNOWN",
                signed_negative_feedback=False, learning_update=False,
            ))

    if live_l2 is not None:
        if not isinstance(live_l2, dict):
            raise TimelineRejected("live L2 sidecar must be one typed object")
        count = live_l2.get("model_attempts")
        from_seq = live_l2.get("source_world_seq")
        latest = live_l2.get("latest_world_seq")
        text = live_l2.get("text_observation_only")
        text_seq = live_l2.get("text_source_seq")
        obs_seqs = [r["probe_seq"] for r in observations]
        if (live_l2.get("kind") != "l2_live_observer"
                or live_l2.get("source_type") != "SELF_DEMO_S60B1_LIVE_L2"
                or live_l2.get("session") != sid
                or live_l2.get("native_l0_action_owner") != "S49_NATIVE_EXISTING"
                or type(count) is not int or count not in (0, 1)
                or latest not in obs_seqs
                or (from_seq is not None and from_seq not in obs_seqs)
                or (count == 1 and from_seq is None)
                or (count == 0 and from_seq is not None)
                or (from_seq is not None and from_seq > latest)
                or type(live_l2.get("authorized_actions")) is not int
                or live_l2["authorized_actions"] != 0
                or live_l2.get("learning_updates") != 0
                or live_l2.get("habit_grants") != 0
                or live_l2.get("l2_used_as_action") is not False
                or live_l2.get("backend_stop_ack") is not False
                or live_l2.get("gpu_release_verified") is not False
                or live_l2.get("model_binary_identity_verified") is not False
                or live_l2.get("text_current") is not (
                    isinstance(text, str) and bool(text) and text_seq == latest
                )):
            raise TimelineRejected("foreign, stale or over-privileged L2 sidecar")
        if text is not None and (not isinstance(text, str) or len(text) > 1000):
            raise TimelineRejected("unbounded/untyped model output")
        if text is not None and (text_seq != from_seq or count != 1):
            raise TimelineRejected("model text belongs to a different World generation")
        rows.append(event(
            "l2_observer", level="L2",
            source="S60B1_OWNER_REPORTED_ONLY",
            model_attempts=count, source_world_seq=from_seq,
            latest_world_seq=latest,
            status=str(live_l2.get("status", "UNCONFIRMED"))[:96],
            text_untrusted=text,
            text_current=live_l2["text_current"],
            model_actions_authorized=0,
            backend_stop_ack_verified=False, gpu_release_verified=False,
            temporal_L0_L2_overlap_independently_verified=False,
            display_order="SUMMARY_ONLY_NOT_REAL_TIME_CAUSAL_SEQUENCE",
        ))

    stored = None
    if memory is not None:
        if not isinstance(memory, PersistentCognition):
            raise TimelineRejected("typed PersistentCognition Memory required")
        if (memory.identity.self_id != f"self-demo-{sid}"
                or len(memory.memories) != 2
                or memory.appraisal_dispositions):
            raise TimelineRejected("foreign or authority-extended Memory snapshot")
        expected = {a["action_id"]: a for a in actions}
        seen: set[str] = set()
        for item in memory.memories:
            if (item.source_provenance.source != "self-demo-projected-S49-report"
                    or item.integration_provenance.source != "self-demo-operator"):
                raise TimelineRejected("Memory provenance does not match product observation")
            try:
                val = json.loads(item.content)
            except ValueError as exc:
                raise TimelineRejected("invalid stored observation") from exc
            aid = val.get("action_id") if isinstance(val, dict) else None
            if (aid not in expected or aid in seen
                    or item.memory_id != f"observed:{sid}:{aid}"):
                raise TimelineRejected("foreign/replayed retained Action")
            ref = expected[aid]
            if (val.get("session") != sid
                    or val.get("type") != "S49_OBSERVED_ACTION_OUTCOME"
                    or val.get("terminal") != "outcome"
                    or val.get("movement_m") != ref["movement_m"]
                    or val.get("goal_success_attested") is not False
                    or val.get("learning_feedback_qualified") is not False
                    or val.get("action_frames_complete") is not ref["action_frames_complete"]
                    or val.get("execution_evidence_sha256")
                    != ref["execution_evidence_sha256"]):
                raise TimelineRejected("Memory does not match source Action outcome")
            seen.add(aid)
        if seen != set(expected):
            raise TimelineRejected("missing retained episode")
        stored = len(seen)
        rows.append(event(
            "memory", owner="ORIGINAL_PERSISTENT_COGNITION",
            observed_action_episodes=stored,
            learning_preferences_changed=False, habit_acquisition_verified=False,
            goal_success_signed=False,
        ))

    rows.append(event(
        "summary", decisions=3, native_action_outcomes=2,
        observed_memory_episodes=stored,
        l2_sidecar_present=live_l2 is not None,
        actual_new_minecraft_actions=0, actual_new_model_requests=0,
        world_goal_success_attested=False,
        production_habit_promoted=False,
    ))
    return tuple(rows)


def _read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
        raise TimelineRejected("source must be a bounded existing regular file")
    return json.loads(path.read_text(encoding="utf-8"))


def _show(rows: tuple[dict[str, Any], ...], fmt: str) -> str:
    if fmt == "jsonl":
        return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    parts = ["RelaySelf | native-report timeline (view only; no physical attestation)"]
    for r in rows:
        kind = r["kind"]
        if kind == "present":
            parts.append(
                f"  Epoch {r['epoch']}: zombie {r['target_distance_m']:.2f} m "
                f"(source probe #{r['probe_seq']})"
            )
        elif kind == "selection":
            parts.append(f"    {r['level']} → {r['candidate']}")
        elif kind == "action_outcome":
            parts.append(
                f"    S16 → {r['terminal']}, movement {r['observed_movement_m']:.3f} m; "
                "goal UNKNOWN"
            )
        elif kind == "l2_observer":
            parts.append(
                f"  L2 → {r['status']} ({r['model_attempts']} model attempts, "
                "no Action authority; temporal overlap unverified)"
            )
        elif kind == "memory":
            parts.append(
                f"  Memory → {r['observed_action_episodes']} retained observations "
                "(no verified learning/Habit)"
            )
    parts.append("View-only: no World changes, inferred goals, or model-to-Action binding.")
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Display existing Self cognition without running it")
    p.add_argument("--native-report", type=Path, required=True)
    p.add_argument("--live-l2", type=Path)
    p.add_argument("--memory", type=Path)
    p.add_argument("--format", choices=["text", "jsonl", "html"], default="text")
    p.add_argument("--output", type=Path,
                   help="fresh .html file path required when --format html")
    args = p.parse_args(argv)
    try:
        if (args.format == "html") is not (args.output is not None):
            raise TimelineRejected("HTML requires an output path, other formats use stdout")
        native = _read_json(args.native_report)
        l2 = None
        if args.live_l2 is not None:
            data = args.live_l2
            if data.is_symlink() or not data.is_file() or data.stat().st_size > MAX_SOURCE_BYTES:
                raise TimelineRejected("source L2 sidecar absent or oversized")
            lines = data.read_text(encoding="utf-8").splitlines()
            if len(lines) != 1:
                raise TimelineRejected("exactly one L2 sidecar is required")
            l2 = json.loads(lines[0])
        mem = None
        if args.memory is not None:
            if (args.memory.is_symlink() or not args.memory.is_file()
                    or args.memory.stat().st_size > MAX_SOURCE_BYTES):
                raise TimelineRejected("Memory snapshot untrusted or oversized")
            mem = load_persistent_cognition(args.memory)
        result = timeline(native, live_l2=l2, memory=mem)
        if args.format == "html":
            from adapters.mineflayer.self_timeline_html import render_html

            target = args.output
            if (target.suffix.lower() != ".html" or target.is_symlink()
                    or target.exists() or not target.parent.is_dir()
                    or target.parent.is_symlink()):
                raise TimelineRejected("new local .html file in existing folder required")
            content = render_html(result)
            with target.open("x", encoding="utf-8") as stream:
                stream.write(content)
            print(json.dumps({
                "schema": SCHEMA, "status": "VIEW_WRITTEN",
                "output": str(target), "world_actions_issued": 0,
                "model_requests_issued": 0,
            }, sort_keys=True))
        else:
            print(_show(result, args.format), end="")
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
        print(json.dumps({
            "schema": SCHEMA, "status": "UNDETERMINED", "reason": "SOURCE_REJECTED",
            "world_actions_issued": 0, "model_requests_issued": 0,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
