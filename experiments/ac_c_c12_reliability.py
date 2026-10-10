"""C12 offline World: source-only sensor calibration and cheap route selection.

No LLM/GPU/physical Minecraft, persistent Self authority, or paid World sensing.
The "source receipt" is in-memory object identity, not cryptographic attestation.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("ac_c_c12_manifest.json")
MANIFEST_SHA = "963e8a495a89ec4b7a4cd03b1d5a275c1acbb717bf925dcdccfb3be043733685"
ARMS = (
    "FROZEN_GROUP", "ADAPT_GROUP", "FROZEN_MAJORITY", "L1_MAJORITY",
    "STATIC_RELIABILITY_GATE", "LEARNED_RELIABILITY_GATE",
    "SIMPLE_R_THRESHOLD", "DISAGREEMENT_GATE", "FIXED_FUSION",
    "LEARNED_FUSION", "NO_FEEDBACK_GROUP", "EVALUATOR_ORACLE",
)
FROZEN = ("FROZEN_GROUP", "FROZEN_MAJORITY", "NO_FEEDBACK_GROUP")
COST = {
    "L1_GROUP": (1, 1),
    "L1_MAJORITY": (1, 2),
    "FIXED_FUSION": (1, 3),
    "LEARNED_FUSION": (1, 4),
    "EVALUATOR_ORACLE": (1, 1),
    "ABSTAIN": (0, 0),
}


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def config() -> dict:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if canonical_hash(data) != MANIFEST_SHA:
        raise ValueError("C12_PREREGISTERED_MANIFEST_DRIFT")
    return data


@dataclass(frozen=True)
class HiddenCase:
    session: str
    epoch: str
    group: int
    prefix: int
    cues: tuple[int, int, int]
    z: int
    blocked: bool
    exact_available: bool
    health: int
    deadline: int
    hunger: int
    threat: bool


@dataclass(frozen=True)
class E0:
    session: str
    revision: int
    group: int
    prefix: int
    cues: tuple[int, int, int]
    health: int
    deadline: int
    hunger: int
    threat: bool


@dataclass(frozen=True)
class Terminal:
    session: str
    e0_hash: str
    mode: str
    physical_action: int
    moved: bool
    feedback_type: str
    label_z: int | None
    terminal_rev: int


def generate(seed: int) -> tuple[HiddenCase, ...]:
    m = config()
    rng = random.Random(seed)
    items = []
    for epoch in m["epochs"]:
        for idx in range(m["n_per_epoch"]):
            g = rng.randrange(2)
            z = int(rng.random() < m["hidden_z_p1"][epoch][g])
            r = m["cue_reliability"][epoch]
            bits = tuple(z if rng.random() < r else 1-z for _ in range(3))
            # Opaque identity: never embed epoch, seed or sequence into public E0.
            sid = hashlib.sha256(
                f"AC-C12-{seed}-{len(items)}".encode()
            ).hexdigest()[:24]
            items.append(HiddenCase(
                sid, epoch, g, rng.randrange(4), bits, z,
                rng.random() < m["world"]["obstruction_p"],
                rng.random() < m["world"]["terminal_exact_z_probability"],
                rng.choice(m["world"]["health"]),
                rng.choice(m["world"]["deadline"]),
                rng.choice(m["world"]["hunger"]),
                rng.random() < m["world"]["threat_p"],
            ))
    return tuple(items)


def viable(e: E0, mode: str) -> bool:
    return (
        mode in COST and mode != "ABSTAIN" and e.revision == 0
        and e.health > 2 and e.deadline >= COST[mode][0]
    )


@dataclass
class Retention:
    group_labels: dict[int, deque[int]] = field(default_factory=dict)
    cue_matches: deque[int] = field(default_factory=lambda: deque(maxlen=24))
    updated_sessions: set[str] = field(default_factory=set)

    def group_p1(self, g: int) -> float:
        h = self.group_labels.get(g, ())
        return (1 + sum(h)) / (2 + len(h))

    def group_bit(self, g: int) -> int:
        return int(self.group_p1(g) > 0.5)

    def reliability(self) -> float:
        c = config()["learning"]
        n = len(self.cue_matches)
        k = c["cue_reliability_pseudocount"]
        estimate = (sum(self.cue_matches) + k*c["cue_reliability_prior"]) / (
            3*n + k
        )
        low, high = c["cue_estimate_clamp"]
        return max(low, min(high, estimate))

    def accept(self, e: E0, terminal: Terminal) -> bool:
        if e.session in self.updated_sessions:
            raise ValueError("C12_DUPLICATE_SOURCE_UPDATE")
        if terminal.session != e.session:
            raise ValueError("C12_FOREIGN_FEEDBACK")
        self.updated_sessions.add(e.session)
        if terminal.feedback_type == "MISSING":
            if terminal.label_z is not None:
                raise ValueError("C12_MISSING_LABEL_SPOOF")
            return False
        if terminal.feedback_type != "EXACT" or terminal.label_z not in (0, 1):
            raise ValueError("C12_FAKE_WORLD_LABEL")
        g = e.group
        self.group_labels.setdefault(g, deque(maxlen=config()["learning"]["z_window_per_group"]))
        self.group_labels[g].append(terminal.label_z)
        self.cue_matches.append(sum(bit == terminal.label_z for bit in e.cues))
        return True

    def signature(self) -> tuple:
        return (
            tuple(tuple(self.group_labels.get(g, ())) for g in (0, 1)),
            tuple(self.cue_matches),
        )


class World:
    def __init__(self, case: HiddenCase):
        self._case = case
        self._issued: Terminal | None = None
        self._consumed = False
        self._retained = False
        self._zguess: int | None = None

    def e0(self) -> E0:
        c = self._case
        return E0(c.session, 0, c.group, c.prefix, c.cues,
                  c.health, c.deadline, c.hunger, c.threat)

    def issue(self, e: E0, mode: str, zguess: int) -> Terminal:
        if self._issued is not None:
            raise ValueError("C12_DUPLICATE_ISSUE")
        if e != self.e0() or not viable(e, mode) or zguess not in (0, 1):
            raise ValueError("C12_UNAUTHORIZED_ACTION")
        self._zguess = zguess
        moved = zguess == self._case.z and not self._case.blocked
        self._issued = Terminal(
            e.session, canonical_hash(asdict(e)), mode,
            (e.prefix.bit_count() & 1) ^ zguess, moved,
            "EXACT" if self._case.exact_available else "MISSING",
            self._case.z if self._case.exact_available else None, 1,
        )
        return self._issued

    def consume(self, e: E0, mode: str, receipt: Terminal) -> Terminal:
        if (self._consumed or receipt is not self._issued or e != self.e0()
                or receipt.session != e.session
                or receipt.e0_hash != canonical_hash(asdict(e))
                or receipt.mode != mode or receipt.terminal_rev != 1):
            raise ValueError("C12_FORGED_OR_REPLAYED_TERMINAL")
        self._consumed = True
        return receipt

    def retain(self, e: E0, r: Terminal, state: Retention, enabled: bool) -> bool:
        if (self._retained or not self._consumed or r is not self._issued
                or e != self.e0()):
            raise ValueError("C12_PREMATURE_OR_DUPLICATE_RETENTION")
        self._retained = True
        return state.accept(e, r) if enabled else False

    def evaluate(self) -> tuple[bool, bool]:
        # Evaluator-only; never call before consume+retain or inside any policy.
        if not self._retained or self._zguess is None:
            raise ValueError("C12_NO_COMPLETE_WORLD_TRANSACTION")
        return self._zguess == self._case.z, bool(self._issued.moved)


def fusion(p1: float, reliability: float, cues: tuple[int, int, int]) -> int:
    if not 0 < p1 < 1 or not 0 < reliability < 1:
        raise ValueError("C12_INVALID_PUBLIC_CUE_MODEL")
    odds = math.log(p1/(1-p1))
    lr = math.log(reliability/(1-reliability))
    return int(odds + sum((1 if b else -1)*lr for b in cues) > 0)


def accuracy_majority(r: float) -> float:
    return 3*r*r - 2*r*r*r


def select(e: E0, state: Retention, arm: str,
           *, warmup: bool) -> tuple[str, int]:
    if arm not in ARMS:
        raise ValueError("C12_UNKNOWN_ARM")
    if not viable(e, "L1_GROUP"):
        return "ABSTAIN", 0
    p1 = state.group_p1(e.group)
    group_bit = int(p1 > .5)
    majority = int(sum(e.cues) >= 2)
    if warmup or arm in ("FROZEN_GROUP", "ADAPT_GROUP", "NO_FEEDBACK_GROUP"):
        return "L1_GROUP", group_bit
    if arm in ("FROZEN_MAJORITY", "L1_MAJORITY"):
        return "L1_MAJORITY", majority
    if arm in ("STATIC_RELIABILITY_GATE", "LEARNED_RELIABILITY_GATE"):
        r = (config()["policies"]["static_r"] if arm == "STATIC_RELIABILITY_GATE"
             else state.reliability())
        gap = (accuracy_majority(r)-max(p1, 1-p1))
        work_difference = (
            COST["L1_MAJORITY"][1]-COST["L1_GROUP"][1]
        )
        choose_majority = (
            (config()["score"]["correct"]-config()["score"]["wrong"])*gap >
            -config()["score"]["per_all_work"]*work_difference
        )
        return ("L1_MAJORITY", majority) if choose_majority else ("L1_GROUP", group_bit)
    if arm == "SIMPLE_R_THRESHOLD":
        return (("L1_GROUP", group_bit) if state.reliability() <
                config()["policies"]["simple_r_threshold"] else ("L1_MAJORITY", majority))
    if arm == "DISAGREEMENT_GATE":
        return (("L1_MAJORITY", majority) if e.cues[0] != group_bit
                else ("L1_GROUP", group_bit))
    if arm in ("FIXED_FUSION", "LEARNED_FUSION"):
        r = (config()["policies"]["static_r"] if arm == "FIXED_FUSION"
             else state.reliability())
        return arm, fusion(p1, r, e.cues)
    if arm == "EVALUATOR_ORACLE":
        raise ValueError("C12_NO_EVALUATOR_ACCESS_IN_SOURCE_SELECTOR")
    raise AssertionError("C12_UNHANDLED_POLICY")


def trajectory(seed: int, arm: str) -> dict:
    m = config()
    if seed not in m["seeds"]["calibration"] + m["seeds"]["heldout"]:
        raise ValueError("C12_UNFROZEN_SEED")
    if arm not in ARMS:
        raise ValueError("C12_UNKNOWN_ARM")
    state = Retention()
    trace = []
    frozen_warmup = None
    for case in generate(seed):
        warmup = case.epoch == "warmup"
        if not warmup and frozen_warmup is None:
            frozen_warmup = state.signature()
        world = World(case)
        e = world.e0()
        p1 = state.group_p1(e.group)
        r_est = state.reliability()
        oracle = arm == "EVALUATOR_ORACLE" and not warmup and viable(e, "L1_GROUP")
        mode, guess = (
            ("EVALUATOR_ORACLE", case.z) if oracle
            else select(e, state, arm, warmup=warmup)
        )
        true_decision = None
        moved = False
        admitted_exact = False
        if mode != "ABSTAIN":
            receipt = world.consume(e, mode, world.issue(e, mode, guess))
            admitted_exact = world.retain(
                e, receipt, state,
                enabled=(warmup or arm not in FROZEN+("EVALUATOR_ORACLE",)),
            )
            # Only the offline evaluator receives these true outcomes.
            true_decision, moved = world.evaluate()
        ticks, work = COST[mode]
        selector_work = (
            0 if warmup or mode == "ABSTAIN"
            else m["selector_work"][arm]
        )
        score = (
            m["score"]["correct"] if true_decision is True
            else m["score"]["wrong"] if true_decision is False
            else m["score"]["abstain"]
        )
        score += (m["score"]["per_all_work"]*(work+selector_work)
                  + m["score"]["per_tick"]*ticks)
        trace.append({
            "session": e.session, "epoch": case.epoch,
            "mode": mode, "guess": guess if mode != "ABSTAIN" else None,
            "correct": true_decision, "moved": moved,
            "admitted_exact": admitted_exact, "work": work,
            "selector_work": selector_work, "ticks": ticks,
            "utility_quarters": round(score*4),
            "p_group_before": p1, "r_est_before": r_est,
            "r_est_after": state.reliability(),
            "source_sig_after": state.signature(),
        })
    if frozen_warmup is None:
        raise AssertionError("C12_WARMUP_MISSING")
    phases = {}
    for ep in m["epochs"]:
        sub = [x for x in trace if x["epoch"] == ep]
        assert len(sub) == m["n_per_epoch"]
        phases[ep] = {
            "correct": sum(x["correct"] is True for x in sub),
            "wrong": sum(x["correct"] is False for x in sub),
            "abstain": sum(x["correct"] is None for x in sub),
            "moved": sum(x["moved"] for x in sub),
            "exact": sum(x["admitted_exact"] for x in sub),
            "group_choices": sum(x["mode"] == "L1_GROUP" for x in sub),
            "majority_choices": sum(x["mode"] == "L1_MAJORITY" for x in sub),
            "mode_counts": dict(sorted(Counter(x["mode"] for x in sub).items())),
            "work": sum(x["work"] for x in sub),
            "selector_work": sum(x["selector_work"] for x in sub),
            "ticks": sum(x["ticks"] for x in sub),
            "utility_quarters": sum(x["utility_quarters"] for x in sub),
            "end_r_mean": sub[-1]["r_est_after"],
        }
    return {
        "seed": seed, "arm": arm, "warmup_signature": frozen_warmup,
        "phases": phases, "trace": tuple(trace),
    }


def report() -> dict:
    m = config()
    all_results = [
        trajectory(seed, arm)
        for seed in m["seeds"]["calibration"] + m["seeds"]["heldout"]
        for arm in ARMS
    ]
    keys = (
        "correct", "wrong", "abstain", "moved", "exact",
        "group_choices", "majority_choices", "work", "selector_work",
        "ticks", "utility_quarters",
    )
    summary = {}
    for split, seeds in m["seeds"].items():
        summary[split] = {}
        for arm in ARMS:
            rr = [x for x in all_results if x["seed"] in seeds and x["arm"] == arm]
            summary[split][arm] = {
                k: sum(x["phases"][ep][k] for x in rr for ep in m["epochs"][1:])
                for k in keys
            }
            summary[split][arm]["per_phase_correct"] = {
                ep: sum(x["phases"][ep]["correct"] for x in rr)
                for ep in m["epochs"]
            }
            # Offline evaluation-only calibration vs generator (NO learner access).
            summary[split][arm]["mean_end_cue_reliability"] = {
                ep: round(sum(x["phases"][ep]["end_r_mean"] for x in rr)/len(rr), 4)
                for ep in m["epochs"]
            }
            summary[split][arm]["mean_abs_calibration_error"] = {
                ep: round(sum(abs(x["phases"][ep]["end_r_mean"] -
                                  m["cue_reliability"][ep]) for x in rr)/len(rr), 4)
                for ep in m["epochs"]
            }
    paired = {}
    for seed in m["seeds"]["heldout"]:
        subset = {
            arm: next(x for x in all_results if x["arm"] == arm and x["seed"] == seed)
            for arm in ARMS
        }
        assert len({tuple(x["session"] for x in r["trace"]) for r in subset.values()}) == 1
        assert len({r["warmup_signature"] for r in subset.values()}) == 1
        # All updating arms consume the exact same exogenous label stream, so
        # their retained source states MUST stay identical across all episodes.
        normal = subset["ADAPT_GROUP"]["trace"]
        for arm in ARMS:
            trial = subset[arm]["trace"]
            assert all(
                x["source_sig_after"] == y["source_sig_after"]
                for x, y in zip(trial, normal)
                if arm not in FROZEN+("EVALUATOR_ORACLE",)
            )
        paired[str(seed)] = {
            "calibrated_minus_majority": sum(
                subset["LEARNED_RELIABILITY_GATE"]["phases"][ep]["correct"] -
                subset["L1_MAJORITY"]["phases"][ep]["correct"]
                for ep in m["epochs"][1:]
            ),
            "calibrated_minus_group": sum(
                subset["LEARNED_RELIABILITY_GATE"]["phases"][ep]["correct"] -
                subset["ADAPT_GROUP"]["phases"][ep]["correct"]
                for ep in m["epochs"][1:]
            ),
            "calibrated_minus_static": sum(
                subset["LEARNED_RELIABILITY_GATE"]["phases"][ep]["correct"] -
                subset["STATIC_RELIABILITY_GATE"]["phases"][ep]["correct"]
                for ep in m["epochs"][1:]
            ),
        }
    result = {"manifest_sha256": MANIFEST_SHA, "summary": summary, "paired": paired}
    result["result_sha256"] = canonical_hash(result)
    return result


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, ensure_ascii=False))
