"""Independent V Lane *offline* adjudication of pinned L1 branch on V-owned fixtures.

L1 is imported from its unchanged detached checkout. The cheap tag/episode
reference oracle below is V-owned, NOT L1's self-aliasing cheap_tag_baseline.
No user World evidence, physical goal, LLM, habit or learning is qualified.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

L1_HEAD = "40db58d548ea31c4a70acabcc71b0954c7b6ce42"
L1_BLOB = "326d4f14e2addc465f97ff452572865f3494325d"
SCHEMA = "RELAYSELF_V1_L1_CHEAP_PARITY_READONLY"


class AuditRejected(ValueError):
    """Unsupported sibling, source, or independent reference inconsistency."""


def checked_l1_root(root: Path) -> None:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise AuditRejected("existing absolute nonsymlink sibling root required")
    path = root / "src/relay_self/experience_bridge.py"
    if path.is_symlink() or not path.is_file():
        raise AuditRejected("missing original L1 bridge source")
    for args, expected in [
        (["rev-parse", "HEAD"], L1_HEAD),
        (["hash-object", "src/relay_self/experience_bridge.py"], L1_BLOB),
    ]:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True,
            check=False, timeout=15,
        )
        if result.returncode != 0 or result.stdout.strip() != expected:
            raise AuditRejected("L1 exact branch/source bytes are not pinned")
    changed = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True, text=True, check=False, timeout=15,
    )
    if changed.returncode != 0 or changed.stdout.strip():
        raise AuditRejected("L1 checkout tracked source modified")


def cheap_scan(snapshot: Any, query: Any) -> tuple[str, tuple[str, ...], tuple[str, ...], int]:
    """V's independent elementary episode/tag oracle; no L1 retrieval code.

    Designed ONLY for verified, source-shaped S16 episodes created below.
    Consistent source-identity/revision/digest/cue gate, no success interpretation.
    """
    candidates = []
    stale = False
    unverified = False
    inspected = len(snapshot.memories)
    for memory in snapshot.memories:
        item = json.loads(memory.content)
        if item["schema"] != "L1_SOURCE_EPISODE_V1":
            raise AuditRejected("foreign serialized episode")
        if item["session_id"] != query.session_id:
            continue
        if not set(item["cue_tags"]).issubset(query.cue_tags):
            continue
        revision = item["world_revision"]
        if revision > query.world_revision or query.world_revision - revision > query.max_revision_lag:
            stale = True
            continue
        if item["evidence_sha256"] not in query.admitted_evidence_sha256:
            unverified = True
            continue
        candidates.append((memory.memory_id, item))
    if not candidates:
        return (
            "unverified" if unverified else "stale" if stale else "unknown",
            (), (), inspected,
        )
    ids = tuple(sorted(mid for mid, _ in candidates))
    successful_terminal = [item for _, item in candidates if item["disposition"] == "outcome"]
    grouped: dict[tuple[str, tuple[str, ...]], set[tuple[str, str]]] = {}
    for item in successful_terminal:
        grouped.setdefault(
            (item["action_ref"], tuple(item["cue_tags"])), set()
        ).add((item["source_status"], item["reason_code"]))
    if any(len(v) > 1 for v in grouped.values()):
        return "contradictory", ids, (), inspected
    if len(successful_terminal) != len(candidates):
        return "reconsider", ids, (), inspected
    return (
        "recall", ids, tuple(sorted({x["action_ref"] for x in successful_terminal})),
        inspected,
    )


def evaluate(root: Path) -> dict[str, Any]:
    """Read L1 sibling once and validate equal-source cheap parity by separate code."""
    checked_l1_root(root)
    from relay_self import experience_bridge as l1
    from relay_self.action import ActionEvent, ActionLifecycle, ActionState
    from relay_self.action_outcome import ActionOutcomeDisposition, ActionOutcomeInterpretation
    from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
    from relay_self.provenance import Provenance

    original = Path(l1.__file__).resolve()
    if original != (root / "src/relay_self/experience_bridge.py").resolve():
        raise AuditRejected("import not from pinned L1 branch")

    source = Provenance("V1_OFFLINE_SOURCE_SHAPED_ONLY", "never_physical_world")
    def episode(action_id: str, reason: str = "observed_execution",
                *, unknown: bool = False, digest: str = "a" * 64):
        start = ActionLifecycle(
            action_id, "skill-v", "intent-v",
            (ActionEvent(ActionState.PROPOSED, 1, source),),
        )
        issued = start.authorize(
            at_ns=2, provenance=source, authority="v-fixture-grant",
        ).issue(at_ns=3, deadline_ns=100, provenance=source)
        action = (
            issued.mark_unknown(at_ns=4, provenance=source) if unknown
            else issued.record_outcome(at_ns=4, provenance=source)
        )
        result = ActionOutcomeInterpretation(
            action_id=action_id, binding_id="binding-v", action_ref="MOVE_BACKWARD",
            skill_execution_id="skill-v", intent_id="intent-v",
            session_id="v-fixture-session",
            source_status="unknown" if unknown else "executed",
            disposition=(
                ActionOutcomeDisposition.UNKNOWN if unknown
                else ActionOutcomeDisposition.OUTCOME
            ),
            reason_code=reason, world_provenance=source, provenance=source,
        )
        return l1.qualify_episode(
            action, result, world_revision=1, evidence_sha256=digest,
            cue_tags=("near_zombie", "night"),
            hypothesis="unverified forecast only" if not unknown else None,
        )
    def snapshot(*episodes):
        p = PersistentCognition(IdentitySpecification("v-fixture-self", ("observe",), source))
        for item in episodes:
            p = l1.retain_observation(p, item, integration_provenance=source)
        return p

    def query(**changes):
        d = {
            "session_id": "v-fixture-session", "world_revision": 1,
            "cue_tags": ("near_zombie", "night"),
            "admitted_evidence_sha256": frozenset({"a" * 64, "b" * 64}),
            "max_revision_lag": 0,
        }
        d.update(changes)
        return l1.ReuseQuery(**d)

    first = episode("v-action-1")
    normal = snapshot(first)
    unknown = snapshot(episode("v-action-unknown", unknown=True))
    contradiction = snapshot(
        first, episode("v-action-2", "observed_collision", digest="b" * 64)
    )
    cases = [
        ("retention_off", snapshot(), query(), "unknown"),
        ("qualified_reuse", normal, query(), "recall"),
        ("foreign_session", normal, query(session_id="foreign"), "unknown"),
        ("future_revision", normal, query(world_revision=0), "stale"),
        ("missing_source_admission", normal,
         query(admitted_evidence_sha256=frozenset()), "unverified"),
        ("wrong_tag", normal, query(cue_tags=("other",)), "unknown"),
        ("unknown_action", unknown, query(), "reconsider"),
        ("contradictory_source", contradiction, query(), "contradictory"),
    ]
    findings = []
    for name, state, q, wanted in cases:
        # Both arms receive identical original Memory + query + Action vocabulary.
        expected = cheap_scan(state, q)
        actual = l1.retrieve_experience(state, q)
        observed = (
            actual.status.value, actual.memory_ids,
            actual.observed_action_refs, actual.examined,
        )
        if expected != observed or observed[0] != wanted:
            raise AuditRejected("independent cheap reference disagrees: " + name)
        if actual.status.value == "recall" and (
            actual.reason != "observation_only_not_goal_or_learning"
            or not actual.observed_action_refs
        ):
            raise AuditRejected("recall illegally promoted to a learned goal")
        if hasattr(actual, "action_authorization") or hasattr(actual, "goal_success"):
            raise AuditRejected("read-only hint contains Action/goal authority")
        findings.append({"case": name, "status": observed[0], "same_cheap_result": True})

    return {
        "schema": SCHEMA, "l1_head": L1_HEAD, "l1_blob": L1_BLOB,
        "source": "V_OWNED_SOURCE_SHAPED_FIXTURE_NOT_WORLD",
        "test_cases": findings,
        "source_matched_cheap_parity": "8_OF_8",
        "learned_advantage": "NOT_DEMONSTRATED",
        "qualified_physical_actions": 0, "model_requests": 0,
        "science_qualified": False, "physical_execution_authorized": False,
        "terminal": "L1_SOURCE_SHAPED_CHEAP_PARITY_ONLY",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l1-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        output = evaluate(args.l1_root)
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (AuditRejected, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "terminal": "L1_AUDIT_BLOCKED",
            "error": type(exc).__name__ + ":" + str(exc),
            "science_qualified": False, "physical_execution_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
