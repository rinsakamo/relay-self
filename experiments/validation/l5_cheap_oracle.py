"""V independent strongest-cheap-null review for frozen L5 contextual shadow.

An exact two-feature table is a cheap mechanism using the SAME observations
as L5. This offline synthetic test must never be cited as physical causality.
L5 fixture imports are local to the optional CLI; V pure controls have no L5.
"""
from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

FEATURES = ("alpha", "beta")
ACTIONS = ("OPTION_A", "OPTION_B")
L5_HEAD = "17c5357fd5625274ee567ad979b780e77bf7b1e7"
S11_HEAD = "69a150cc6f687e5b379713ba4c5e0ba2de60b38f"


class CheapOracleRejected(ValueError):
    """Original source-shape or a claimed two-feature contrast drifted."""


@dataclass(frozen=True)
class SourceShapedSample:
    session: str
    action: str
    tags: tuple[str, ...]
    success: bool
    evidence_sha256: str
    goal_sha256: str


def cheap_two_feature_table(
    rows: Iterable[SourceShapedSample],
    *, features: tuple[str, str] = FEATURES,
    actions: tuple[str, str] = ACTIONS,
) -> dict[tuple[bool, bool], str]:
    """Independent cross-multiplication of success fractions, no L5 policy call."""
    if (not isinstance(features, tuple) or len(features) != 2
            or features[0] == features[1]
            or not isinstance(actions, tuple) or len(actions) != 2
            or actions[0] == actions[1]):
        raise CheapOracleRejected("exact two-feature, two-action cheap policy required")
    records = tuple(rows)
    if len(records) != 16:
        raise CheapOracleRejected("frozen synthetic balanced 16-episode test only")
    seen_sessions: set[str] = set()
    seen_digests: set[str] = set()
    cells: dict[tuple[bool, bool], dict[str, list[int]]] = defaultdict(
        lambda: {a: [0, 0] for a in actions}
    )
    for row in records:
        if (not isinstance(row, SourceShapedSample)
                or not isinstance(row.session, str) or not row.session
                or row.session in seen_sessions
                or row.action not in actions or type(row.success) is not bool
                or not isinstance(row.tags, tuple)
                or row.tags != tuple(sorted(set(row.tags)))
                or not all(isinstance(t, str) for t in row.tags)
                or not all(isinstance(sha, str) and len(sha) == 64
                           and all(c in "0123456789abcdef" for c in sha)
                           for sha in (row.evidence_sha256, row.goal_sha256))
                or row.evidence_sha256 == row.goal_sha256
                or row.evidence_sha256 in seen_digests
                or row.goal_sha256 in seen_digests):
            raise CheapOracleRejected("unqualified or duplicated synthetic row")
        seen_sessions.add(row.session)
        seen_digests.update((row.evidence_sha256, row.goal_sha256))
        cell = (features[0] in row.tags, features[1] in row.tags)
        cells[cell][row.action][0] += int(row.success)
        cells[cell][row.action][1] += 1
    mapping: dict[tuple[bool, bool], str] = {}
    for a in (False, True):
        for b in (False, True):
            scores = cells.get((a, b))
            if scores is None:
                raise CheapOracleRejected("missing two-feature context")
            win_a, n_a = scores[actions[0]]
            win_b, n_b = scores[actions[1]]
            if n_a < 2 or n_b < 2 or win_a * n_b == win_b * n_a:
                raise CheapOracleRejected("missing balanced or discriminating samples")
            mapping[(a, b)] = actions[0] if win_a * n_b > win_b * n_a else actions[1]
    return mapping


def review_l5_fixture() -> dict[str, Any]:
    """Import untouched L5's own original synthetic fixture for comparison."""
    import test_contextual_shadow as owner_fixture  # pinned sibling only

    from relay_self.contextual_shadow import ContextualStatus

    cognition, labels, admission = owner_fixture.setup_experience()
    by_id = {m.memory_id: json.loads(m.content) for m in cognition.memories}
    rows = []
    for label in labels:
        data = by_id[label.observed_memory_id]
        if (data["evidence_sha256"] not in admission.admitted_action_sha256
                or label.goal_source_sha256 not in admission.admitted_goal_sha256
                or data["schema"] != "L1_SOURCE_EPISODE_V1"
                or data["source_status"] != "executed"
                or data["disposition"] != "outcome"):
            raise CheapOracleRejected("actual pinned fixture memory source not admitted")
        rows.append(SourceShapedSample(
            session=data["session_id"], action=data["action_ref"],
            tags=tuple(data["cue_tags"]), success=label.goal_reached,
            evidence_sha256=data["evidence_sha256"],
            goal_sha256=label.goal_source_sha256,
        ))
    cheap = cheap_two_feature_table(rows)
    comparisons = 0
    for a in (False, True):
        for b in (False, True):
            # Synthetic same heldout source pointer, each novel cue/context.
            tags = tuple(sorted(
                (("alpha",) if a else ())
                + (("beta",) if b else ())
                + ("novel_cue",)
            ))
            shadow = owner_fixture.review(
                cognition, labels, admission,
                observation=owner_fixture.current(tags=tags),
            )
            if (shadow.proposed_action_ref != cheap[(a, b)]
                    or shadow.goal_improvement_attested
                    or shadow.memory_causal_benefit_established
                    or shadow.action_authority
                    or shadow.habit_grants or shadow.learning_updates):
                raise CheapOracleRejected("L5 mismatched same-source cheap oracle or privilege")
            if (a, b) == (True, True) and (
                shadow.status is not ContextualStatus.SHADOW_DIFFERENCE
                or shadow.proposed_action_ref != "OPTION_B"
                or shadow.original_no_memory_ref != "OPTION_A"
            ):
                raise CheapOracleRejected("distinct synthetic shadow contrast changed")
            comparisons += 1
    return {
        "schema": "RELAYSELF_V_L5_STRONG_CHEAP_NULL_V1",
        "l5_exact_head": L5_HEAD,
        "s11_exact_head": S11_HEAD,
        "source_class": "PINNED_L5_SYNTHETIC_FIXTURE_NOT_REAL_WORLD",
        "independent_cheap_policy": "SAME_TRAINING_TWO_FEATURE_FOUR_CELL_RATE_LOOKUP",
        "training_source_shaped_episodes": len(rows),
        "paired_s10_world_outcomes": 0,
        "heldout_original_goal_receipts": 0,
        "paired_s11_original_action_vocabulary": False,
        "four_contexts_tested": comparisons,
        "cheap_matches_l5_all_contexts": True,
        "memory_shifts_shadow_ref": True,
        "physical_goal_effect": "NOT_MEASURED",
        "learning_mechanism_advantage_over_strongest_cheap": False,
        "s11_action_authorized": False,
        "scientific_g3": "NO_GO",
        "classification": "V_L5_TWO_FEATURE_CHEAP_NULL_REPRODUCES_CONTEXTUAL_SHADOW",
    }


def main() -> int:
    try:
        print(json.dumps(review_l5_fixture(), sort_keys=True))
        return 0
    except (CheapOracleRejected, ImportError, KeyError, TypeError) as exc:
        print(json.dumps({
            "classification": "V_L5_CHEAP_NULL_SOURCE_REJECTED",
            "reason_type": type(exc).__name__,
            "science_qualified": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
