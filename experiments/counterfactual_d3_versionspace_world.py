"""CF-D3 compositional horizon-two version-space WORLD MECHANICAL fixture.

An offline deterministic, source-bound and evaluation-only apparatus; never
imports models, Mineflayer, network clients, Action owners, or a live server.
Frozen design: #427; parent scientific study #421 G3 stays underdetermined.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from itertools import permutations

VERSION = "CF-D3-COMPOSITIONAL-VERSIONSPACE-v1"
EXPECTED_MANIFEST_SHA256 = (
    "1390326e9dc2ea753d33291e62e076249309ce2d60204608d3d911b16e246eb3"
)
RULES = ("AND", "OR", "XOR", "NAND", "NOR", "XNOR")
ACTIONS = ("DIRECT", "DETOUR", "SCOUT")
STRATA = (
    "IDENTIFIED", "OUTCOME_EQUIVALENT", "DECISION_EQUIVALENT",
    "DECISION_AMBIGUOUS", "INCONSISTENT",
)

_CASES = (
    ("I_AND", "AND", ("001:00",), "000", "IDENTIFIED"),
    ("I_NAND", "NAND", ("001:11",), "000", "IDENTIFIED"),
    ("O_OR", "OR", ("001:01",), "000", "OUTCOME_EQUIVALENT"),
    ("O_NOR", "NOR", ("001:10",), "000", "OUTCOME_EQUIVALENT"),
    ("D_AND", "AND", ("000:00",), "011", "DECISION_EQUIVALENT"),
    ("D_NAND", "NAND", ("011:10",), "001", "DECISION_EQUIVALENT"),
    ("A_AND", "AND", ("011:01",), "000", "DECISION_AMBIGUOUS"),
    ("A_XNOR", "XNOR", ("011:01",), "000", "DECISION_AMBIGUOUS"),
)
_CORRUPT = (
    "INVALID_CONFLICTING_EPISODES", "AND",
    ("000:00", "000:11"), "001", "INCONSISTENT",
)

_MANIFEST: dict[str, object] = {
    "version": VERSION,
    "actions": list(ACTIONS),
    "rule_family": list(RULES),
    "hazard_rule": (
        "two independent ordered future hazards h1=gate(u,v), h2=gate(v,w)"
    ),
    "direct": {"ticks": 2, "damage_per_hazard": 8},
    "detour": {"ticks": 5, "damage": 0},
    "scout": {
        "observe": "h1 exactly after 1 tick",
        "followup": "if h1==0 DIRECT path, else DETOUR path",
        "total_ticks_if_h1_0": 3,
        "total_ticks_if_h1_1": 6,
    },
    "terminal_utility": "20*goalReached - totalTicks - 8*(hazardHits)",
    "evaluator_only": [
        "trueRule", "sourceSession", "heldout h1/h2",
        "future consequence vector", "case ID",
    ],
    "visible_source": [
        "present three cue bits", "the rule-family hypothesis list",
        "source-qualified past DIRECT episode cue + ordered hazard observations",
        "known action mechanics and shared utility",
    ],
    "prior": (
        "uniform over version space of admissible rules; empty if inconsistent"
    ),
    "test_cases": [
        {
            "case": identifier,
            "truth_rule": rule,
            "training": [
                {"cues": item[:3], "observed": item[4:]}
                for item in history
            ],
            "test_cues": cues,
            "expected_stratum": stratum,
        }
        for identifier, rule, history, cues, stratum in _CASES
    ],
    "negative_case": {
        "case": _CORRUPT[0],
        "truth_rule": _CORRUPT[1],
        "training": [
            {"cues": item[:3], "observed": item[4:]}
            for item in _CORRUPT[2]
        ],
        "test_cues": _CORRUPT[3],
        "expected_stratum": _CORRUPT[4],
    },
    "future_science_calls": 0,
    "status": "MECHANICAL_ONLY_NOT_A_MODEL_VALUE_CLAIM",
}


_ACTION_CONTRACT = {
    "DIRECT": {"ticks": 2, "damagePerHazard": 8},
    "DETOUR": {"ticks": 5, "damage": 0},
    "SCOUT": {
        "observe": "h1", "waitTicks": 1,
        "followup": "if h1==0 DIRECT else DETOUR",
    },
}


class D3ContractError(ValueError):
    """Frozen evidence, source, or World contract violation."""


@dataclass(frozen=True)
class Case:
    """World/evaluator-only subject; never pass to a model or chooser."""

    case_id: str
    true_rule: str
    history: tuple[str, ...]
    test_cues: str
    expected_stratum: str


@dataclass(frozen=True)
class Episode:
    """Trusted previously *observed* DIRECT result, not an oracle proposal."""

    source_session: str
    cues: str
    observed: str


@dataclass(frozen=True)
class Consequence:
    """Result from a separate controlled do(action) World intervention."""

    action: str
    ticks: int
    health_loss: int
    observed_trace: tuple[int, ...]
    utility: int


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
    except (ValueError, TypeError, OverflowError) as exc:
        raise D3ContractError("invalid JSON identity") from exc


def frozen_manifest() -> dict[str, object]:
    return json.loads(_canonical(_MANIFEST))


def manifest_sha256(value: object | None = None) -> str:
    raw = _canonical(frozen_manifest() if value is None else value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def assert_manifest(value: object | None = None) -> None:
    if manifest_sha256(value) != EXPECTED_MANIFEST_SHA256:
        raise D3ContractError("CF-D3 manifest identity drift")


def _binary_string(value: object, n: int) -> str:
    if type(value) is not str or len(value) != n or any(
        char not in "01" for char in value
    ):
        raise D3ContractError("invalid Boolean cue/observation")
    return value


def _rule(rule: str, x: int, y: int) -> int:
    if rule == "AND":
        return x & y
    if rule == "OR":
        return x | y
    if rule == "XOR":
        return x ^ y
    if rule == "NAND":
        return 1 - (x & y)
    if rule == "NOR":
        return 1 - (x | y)
    if rule == "XNOR":
        return 1 - (x ^ y)
    raise D3ContractError("rule not in frozen family")


def future_hazards(rule: str, cues: str) -> tuple[int, int]:
    _binary_string(cues, 3)
    u, v, w = (int(c) for c in cues)
    return _rule(rule, u, v), _rule(rule, v, w)


def all_cases() -> tuple[Case, ...]:
    return tuple(Case(*item) for item in _CASES)


def negative_case() -> Case:
    return Case(*_CORRUPT)


def _trusted_case(case: Case) -> None:
    if not isinstance(case, Case) or case not in all_cases():
        raise D3ContractError("not a qualified first-source World case")


def trusted_episodes(case: Case) -> tuple[Episode, ...]:
    _trusted_case(case)
    return tuple(
        Episode(case.case_id, raw[:3], raw[4:])
        for raw in case.history
    )


def _verify_episode(case: Case, episode: Episode) -> None:
    if not isinstance(episode, Episode):
        raise D3ContractError("episode lacks trusted owner type")
    if episode.source_session != case.case_id:
        raise D3ContractError("past episode source-session mismatch")
    if (
        _binary_string(episode.cues, 3) == case.test_cues
        or _binary_string(episode.observed, 2)
        != "".join(str(h) for h in future_hazards(case.true_rule, episode.cues))
    ):
        raise D3ContractError("forged, future, or contradictory prior observation")
    if episode not in trusted_episodes(case):
        raise D3ContractError("unrecognized prior episode")


def predictor_evidence(
    case: Case, episode_records: tuple[Episode, ...] | None = None,
) -> dict[str, object]:
    """No truth rule, hidden current hazards, case/session ID, or oracle."""
    _trusted_case(case)
    episodes = trusted_episodes(case) if episode_records is None else episode_records
    if not isinstance(episodes, tuple) or episodes != trusted_episodes(case):
        raise D3ContractError("episode list does not match trusted lineage")
    for episode in episodes:
        _verify_episode(case, episode)
    return {
        "presentCues": case.test_cues,
        "hypothesisFamily": list(RULES),
        "pastDirectEpisodes": [
            {"cues": item.cues, "observedHazards": item.observed}
            for item in episodes
        ],
        "actionContract": json.loads(_canonical(_ACTION_CONTRACT)),
        "terminalUtility": "20*reached - ticks - damage",
    }


def assert_source_bound(case: Case, evidence: object) -> None:
    """Required independent World-side proof before evidence is admitted."""
    expected = predictor_evidence(case)
    if _canonical(evidence) != _canonical(expected):
        raise D3ContractError("source-bound evidence mismatch or oracle leakage")


def _parse_evidence(
    evidence: object,
) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Pure model-side shape check, without accessing any evaluator truth."""
    if not isinstance(evidence, dict):
        raise D3ContractError("evidence must be object")
    cues = _binary_string(evidence.get("presentCues"), 3)
    episodes = evidence.get("pastDirectEpisodes")
    if not isinstance(episodes, list):
        raise D3ContractError("prior episodes missing")
    parsed: list[tuple[str, str]] = []
    for item in episodes:
        if not isinstance(item, dict) or set(item) != {
            "cues", "observedHazards"
        }:
            raise D3ContractError("wrong episode schema")
        previous = _binary_string(item["cues"], 3)
        observed = _binary_string(item["observedHazards"], 2)
        if previous == cues:
            raise D3ContractError("training/test cue leakage")
        parsed.append((previous, observed))
    expectation = {
        "presentCues": cues,
        "hypothesisFamily": list(RULES),
        "pastDirectEpisodes": [
            {"cues": former, "observedHazards": obs}
            for former, obs in parsed
        ],
        "actionContract": _ACTION_CONTRACT,
        "terminalUtility": "20*reached - ticks - damage",
    }
    if _canonical(evidence) != _canonical(expectation):
        raise D3ContractError("non-admissible field or changed action contract")
    return cues, tuple(parsed)


def version_space(evidence: object) -> tuple[str, ...]:
    """Cheapest rule enumeration using exclusively permitted source data."""
    _, episodes = _parse_evidence(evidence)
    return tuple(
        rule for rule in RULES
        if all(
            "".join(str(h) for h in future_hazards(rule, cues)) == observed
            for cues, observed in episodes
        )
    )


def intervene(case: Case, action: str) -> Consequence:
    """Offline independent action; case is immutable and not changed."""
    _trusted_case(case)
    if type(action) is not str or action not in ACTIONS:
        raise D3ContractError("unknown intervention")
    h1, h2 = future_hazards(case.true_rule, case.test_cues)
    if action == "DIRECT":
        ticks, damage, trace = 2, 8 * (h1 + h2), (h1, h2)
    elif action == "DETOUR":
        ticks, damage, trace = 5, 0, ()
    elif h1 == 0:
        ticks, damage, trace = 3, 8 * h2, (h1, h2)
    else:
        ticks, damage, trace = 6, 0, (h1,)
    return Consequence(action, ticks, damage, trace, 20 - ticks - damage)


def independent_interventions(
    case: Case, order: tuple[str, ...] = ACTIONS,
) -> dict[str, Consequence]:
    """Fresh source immutable; no shared state or guessed unchosen truth."""
    _trusted_case(case)
    if (
        type(order) is not tuple or len(order) != 3
        or any(type(action) is not str for action in order)
        or set(order) != set(ACTIONS)
    ):
        raise D3ContractError("not exactly one of each intervention")
    return {action: intervene(case, action) for action in order}


def _hypothesis_consequences(
    rule: str, cues: str,
) -> dict[str, Consequence]:
    """A hypothesized future, **not** a grounded World observation."""
    # The identical action math is deliberately cheap and explicit here.
    h1, h2 = future_hazards(rule, cues)
    return {
        "DIRECT": Consequence("DIRECT", 2, 8 * (h1 + h2), (h1, h2),
                              18 - 8 * (h1 + h2)),
        "DETOUR": Consequence("DETOUR", 5, 0, (), 15),
        "SCOUT": (
            Consequence("SCOUT", 3, 8 * h2, (h1, h2), 17 - 8 * h2)
            if h1 == 0 else Consequence("SCOUT", 6, 0, (h1,), 14)
        ),
    }


def full_information_choice(rule: str, cues: str) -> str:
    score = _hypothesis_consequences(rule, cues)
    top = max(s.utility for s in score.values())
    winners = [a for a, consequence in score.items() if consequence.utility == top]
    if len(winners) != 1:
        raise D3ContractError("reference full-information tie")
    return winners[0]


def identifiability_stratum(evidence: object) -> str:
    """Classify epistemic sufficiency without looking at the true hidden rule."""
    cues, _ = _parse_evidence(evidence)
    compatible = version_space(evidence)
    if not compatible:
        return "INCONSISTENT"
    if len(compatible) == 1:
        return "IDENTIFIED"
    possible = [
        tuple(_hypothesis_consequences(r, cues)[a] for a in ACTIONS)
        for r in compatible
    ]
    if len(set(possible)) == 1:
        return "OUTCOME_EQUIVALENT"
    if len({full_information_choice(r, cues) for r in compatible}) == 1:
        return "DECISION_EQUIVALENT"
    return "DECISION_AMBIGUOUS"


def bayes_utilities(evidence: object) -> dict[str, Fraction]:
    """Exact uniform-version-space arithmetic; strongest cheap baseline."""
    cues, _ = _parse_evidence(evidence)
    compatible = version_space(evidence)
    if not compatible:
        raise D3ContractError("INCONSISTENT: no admissible forecast")
    return {
        a: Fraction(
            sum(_hypothesis_consequences(r, cues)[a].utility
                for r in compatible), len(compatible)
        )
        for a in ACTIONS
    }


def bayes_choice(evidence: object) -> str:
    scores = bayes_utilities(evidence)
    top = max(scores.values())
    winners = [a for a, s in scores.items() if s == top]
    if len(winners) != 1:
        raise D3ContractError("unknown / tied expected decision")
    return winners[0]


def predictive_hazard_probabilities(evidence: object) -> tuple[Fraction, Fraction]:
    """Mechanically calibrated two-step beliefs, not model inference."""
    cues, _ = _parse_evidence(evidence)
    compatible = version_space(evidence)
    if not compatible:
        raise D3ContractError("INCONSISTENT: no forecast")
    return tuple(
        Fraction(sum(future_hazards(r, cues)[i] for r in compatible),
                 len(compatible))
        for i in (0, 1)
    )


def ordered_action_permutations() -> tuple[tuple[str, ...], ...]:
    return tuple(permutations(ACTIONS))


assert_manifest()
