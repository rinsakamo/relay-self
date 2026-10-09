"""D4: pure 216-hypothesis counterfactual resource-gate instrument (#429).

No model inference, live Minecraft, learned Self state, or scientific authority.
All hidden source truth is kept separate from projected evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from itertools import product

MANIFEST_VERSION = "CF-D4-RESOURCE-GATE216-v1"
MANIFEST_SHA256 = "2f2f300f43f130ecfb84283fc685775e98a1cf8118209bcd9f4488dfd16173a3"
_MANIFEST = json.loads(r'''{"actions":["DIRECT","DETOUR","SCOUT"],"case_specs":[{"expected":"IDENTIFIED","id":"I_AND","test":"0001","train":["0000","0101"],"truth":["AND","AND","AND"]},{"expected":"IDENTIFIED","id":"I_NAND","test":"0001","train":["0000","0101"],"truth":["NAND","AND","AND"]},{"expected":"OUTCOME_EQUIVALENT","id":"O_SAFE","test":"0001","train":["0000","0101"],"truth":["OR","AND","AND"]},{"expected":"OUTCOME_EQUIVALENT","id":"O_HAZARD","test":"0001","train":["0000","0101"],"truth":["AND","AND","OR"]},{"expected":"DECISION_EQUIVALENT","id":"D_LOW","test":"0010","train":["0000","0001"],"truth":["AND","AND","OR"]},{"expected":"DECISION_EQUIVALENT","id":"D_HIGH","test":"0010","train":["0000","0001"],"truth":["AND","OR","OR"]},{"expected":"DECISION_AMBIGUOUS","id":"A_SAFE","test":"0100","train":["0000","0001"],"truth":["NOR","NOR","AND"]},{"expected":"DECISION_AMBIGUOUS","id":"A_HAZARD","test":"0100","train":["0000","0001"],"truth":["NAND","NAND","AND"]}],"claim_ceiling":"mechanical measurement and cheap-baseline dominance only","comparator":"exact finite hypothesis version-space 216, uniform posterior, deterministic tie fail-closed","cost_policy":"report hypothesis evaluations, gate evaluations, elapsed CPU separately; no model cost or physical run inferred","detour":{"damage":0,"ticks":7},"direct":{"damagePerHit":7,"ticks":3},"gates":["AND","OR","XOR","NAND","NOR","XNOR"],"hazards":"h_i=gate_i(bit_i,bit_(i+1)) for i=0,1,2","heldout_policy":"test != train, source-grounded episode h triples; no case ID, rule, or heldout truth in E_t","hypotheses":"ordered triplets from six gates, 6^3=216","model_calls":0,"scout":{"continue":{"ifH0=0":"direct for total 4 ticks, pay remaining h1/h2 damage","ifH0=1":"detour for total 8 ticks safe"},"inspectTicks":1,"reveal":"h0"},"utility":"20-ticks-7*hazardHits","version":"CF-D4-RESOURCE-GATE216-v1"}''')
GATES = tuple(_MANIFEST["gates"])
ACTIONS = tuple(_MANIFEST["actions"])
HYPOTHESES = tuple(product(GATES, repeat=3))


class D4ContractError(ValueError):
    """Invalid source, tampered evidence, or inadmissible World claim."""


@dataclass(frozen=True)
class SourceCase:
    case_id: str
    truth: tuple[str, str, str]
    training: tuple[str, str]
    test: str
    expected: str


@dataclass(frozen=True)
class SourceEpisode:
    session: str
    cue: str
    observed: str


@dataclass(frozen=True)
class Outcome:
    action: str
    ticks: int
    damage: int
    observation: tuple[int, ...]
    utility: int


@dataclass(frozen=True)
class EnumerationCost:
    hypotheses_tested: int
    episode_comparisons: int
    gate_evaluations: int


def canonical(value: object) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
    except (ValueError, TypeError, OverflowError) as exc:
        raise D4ContractError("uncanonicalizable JSON") from exc


def manifest() -> dict[str, object]:
    return json.loads(canonical(_MANIFEST))


def manifest_sha256(value: object | None = None) -> str:
    raw = canonical(manifest() if value is None else value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def assert_manifest(value: object | None = None) -> None:
    if manifest_sha256(value) != MANIFEST_SHA256:
        raise D4ContractError("D4 manifest drift")


def _bits(bits: object, count: int) -> str:
    if type(bits) is not str or len(bits) != count or any(b not in "01" for b in bits):
        raise D4ContractError("invalid ordered Boolean observation")
    return bits


def _gate(name: str, left: int, right: int) -> int:
    if name == "AND":
        return left & right
    if name == "OR":
        return left | right
    if name == "XOR":
        return left ^ right
    if name == "NAND":
        return 1 - (left & right)
    if name == "NOR":
        return 1 - (left | right)
    if name == "XNOR":
        return 1 - (left ^ right)
    raise D4ContractError("unsupported hypothesis operator")


def forecast(rule: tuple[str, str, str], cue: str) -> tuple[int, int, int]:
    _bits(cue, 4)
    if type(rule) is not tuple or len(rule) != 3 or any(g not in GATES for g in rule):
        raise D4ContractError("unqualified hypothesis triple")
    return tuple(
        _gate(rule[i], int(cue[i]), int(cue[i + 1])) for i in range(3)
    )


def qualified_cases() -> tuple[SourceCase, ...]:
    return tuple(
        SourceCase(
            spec["id"], tuple(spec["truth"]), tuple(spec["train"]),
            spec["test"], spec["expected"],
        ) for spec in _MANIFEST["case_specs"]
    )


def _qualified(case: SourceCase) -> None:
    if type(case) is not SourceCase or case not in qualified_cases():
        raise D4ContractError("unqualified World source")


def source_episodes(case: SourceCase) -> tuple[SourceEpisode, ...]:
    _qualified(case)
    return tuple(
        SourceEpisode(
            case.case_id, cue,
            "".join(str(h) for h in forecast(case.truth, cue)),
        ) for cue in case.training
    )


def evidence(
    case: SourceCase, supplied: tuple[SourceEpisode, ...] | None = None,
) -> dict[str, object]:
    """Model-facing E_t includes no evaluator rule, case or future oracle."""
    _qualified(case)
    rows = source_episodes(case) if supplied is None else supplied
    if type(rows) is not tuple or rows != source_episodes(case):
        raise D4ContractError("history/source lineage mismatch")
    if case.test in case.training or len(set(case.training)) != len(case.training):
        raise D4ContractError("train/test overlap")
    return {
        "currentCues": case.test,
        "candidateGates": list(GATES),
        "episodes": [{"cue": row.cue, "hazards": row.observed} for row in rows],
        "actions": {
            "DIRECT": {"ticks": 3, "damagePerHit": 7},
            "DETOUR": {"ticks": 7, "damage": 0},
            "SCOUT": {
                "inspectTicks": 1, "observes": "h0",
                "onZero": "direct-total-4-with-later-hazards",
                "onOne": "detour-total-8-no-damage",
            },
        },
        "utility": "20-ticks-damage",
    }


_PUBLIC_ACTIONS = {
    "DIRECT": {"ticks": 3, "damagePerHit": 7},
    "DETOUR": {"ticks": 7, "damage": 0},
    "SCOUT": {
        "inspectTicks": 1, "observes": "h0",
        "onZero": "direct-total-4-with-later-hazards",
        "onOne": "detour-total-8-no-damage",
    },
}


def parse_public(payload: object) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Pure input parser with no access to hidden World source."""
    if not isinstance(payload, dict):
        raise D4ContractError("source evidence must be an object")
    cue = _bits(payload.get("currentCues"), 4)
    rows = payload.get("episodes")
    if type(rows) is not list or len(rows) != 2:
        raise D4ContractError("exact two training episodes required")
    pairs: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"cue", "hazards"}:
            raise D4ContractError("unapproved memory projection")
        old, obs = _bits(row["cue"], 4), _bits(row["hazards"], 3)
        if old == cue:
            raise D4ContractError("training/test information leakage")
        pairs.append((old, obs))
    if pairs[0][0] == pairs[1][0]:
        # The two equal-cue contradictory-data case is separately classified
        # by an isolated version-space checker; production-source gate fails.
        raise D4ContractError("duplicate unqualified episode cues")
    expected = {
        "currentCues": cue, "candidateGates": list(GATES),
        "episodes": [{"cue": old, "hazards": obs} for old, obs in pairs],
        "actions": _PUBLIC_ACTIONS, "utility": "20-ticks-damage",
    }
    if canonical(payload) != canonical(expected):
        raise D4ContractError("unknown extra field or altered action contract")
    return cue, tuple(pairs)


def assert_source(case: SourceCase, payload: object) -> None:
    """Trust owner check, distinct from structurally valid model input."""
    if canonical(evidence(case)) != canonical(payload):
        raise D4ContractError("source-bound World history mismatch")


def version_space(payload: object) -> tuple[tuple[tuple[str, str, str], ...], EnumerationCost]:
    """Fully enumerable cheap rule baseline, with exact deterministic work counters."""
    _, pairs = parse_public(payload)
    admissible: list[tuple[str, str, str]] = []
    comparisons = 0
    for rule in HYPOTHESES:
        compatible = True
        for cue, observed in pairs:
            comparisons += 1
            if "".join(str(x) for x in forecast(rule, cue)) != observed:
                compatible = False
                break
        if compatible:
            admissible.append(rule)
    return tuple(admissible), EnumerationCost(
        hypotheses_tested=len(HYPOTHESES),
        episode_comparisons=comparisons,
        gate_evaluations=3 * comparisons,
    )


def potential(hazards: tuple[int, int, int], action: str) -> Outcome:
    if type(hazards) is not tuple or len(hazards) != 3 or any(
        type(h) is not int or h not in (0, 1) for h in hazards
    ):
        raise D4ContractError("invalid prospective hazard evidence")
    if action not in ACTIONS or type(action) is not str:
        raise D4ContractError("invalid action")
    h0, h1, h2 = hazards
    if action == "DIRECT":
        ticks, damage, trace = 3, 7 * (h0 + h1 + h2), hazards
    elif action == "DETOUR":
        ticks, damage, trace = 7, 0, ()
    elif h0 == 0:
        ticks, damage, trace = 4, 7 * (h1 + h2), hazards
    else:
        ticks, damage, trace = 8, 0, (h0,)
    return Outcome(action, ticks, damage, trace, 20 - ticks - damage)


def intervention(case: SourceCase, action: str) -> Outcome:
    """Evaluation-only, no mutation and no physical action."""
    _qualified(case)
    return potential(forecast(case.truth, case.test), action)


def all_interventions(
    case: SourceCase, order: tuple[str, str, str] = ACTIONS,
) -> dict[str, Outcome]:
    if type(order) is not tuple or len(order) != 3 or set(order) != set(ACTIONS):
        raise D4ContractError("incomplete independent-intervention permutation")
    return {action: intervention(case, action) for action in order}


def stratum(payload: object) -> str:
    cue, _ = parse_public(payload)
    versions, _ = version_space(payload)
    if not versions:
        return "INCONSISTENT"
    if len(versions) == 1:
        return "IDENTIFIED"
    outcomes = {
        tuple(potential(forecast(rule, cue), action) for action in ACTIONS)
        for rule in versions
    }
    if len(outcomes) == 1:
        return "OUTCOME_EQUIVALENT"
    def _top(three: tuple[Outcome, ...]) -> int:
        values = tuple(o.utility for o in three)
        best = max(values)
        if values.count(best) != 1:
            raise D4ContractError("hindsight outcome tie")
        return values.index(best)
    if len({_top(v) for v in outcomes}) == 1:
        return "DECISION_EQUIVALENT"
    return "DECISION_AMBIGUOUS"


def cheap_expected_utilities(payload: object) -> dict[str, Fraction]:
    cue, _ = parse_public(payload)
    versions, _ = version_space(payload)
    if not versions:
        raise D4ContractError("INCONSISTENT: cannot infer a World")
    return {
        action: Fraction(
            sum(potential(forecast(rule, cue), action).utility for rule in versions),
            len(versions),
        ) for action in ACTIONS
    }


def cheap_choice(payload: object) -> str:
    utilities = cheap_expected_utilities(payload)
    maximum = max(utilities.values())
    winners = [action for action, value in utilities.items() if value == maximum]
    if len(winners) != 1:
        raise D4ContractError("ambiguous decision: no uniquely best option")
    return winners[0]


assert_manifest()
