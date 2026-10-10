"""C7 source-weighted, revocable policy capsules under ambiguous World outcomes.

This is an isolated zero-model toy experiment. Paid DIAGNOSTIC obtains World
information; it does not model LLM compute depth or actual resource joules.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("ac_c_c7_manifest.json")
MANIFEST_SHA = "0d612d88d4a480abbe1a4cffb61e5a016a61ecc52b25109fce58c9f7ab895fbf"
MODES = ("CHEAP", "DIAGNOSTIC")
COST = {"CHEAP": (1, 1), "DIAGNOSTIC": (3, 4)}
ARMS = (
    "STATIC_CAPSULE", "NAIVE_WEAK_AS_EXACT", "STRICT_EXACT_ONLY",
    "WEIGHTED_GUARD", "POSTERIOR_GATE", "CHEAP_HISTORY", "PAID_ONLY",
    "NO_FEEDBACK_CAPSULE", "EVALUATOR_ORACLE",
)


def digest(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def frozen_manifest() -> dict:
    m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if digest(m) != MANIFEST_SHA:
        raise ValueError("C7_FROZEN_MANIFEST_MISMATCH")
    return m


@dataclass(frozen=True)
class Case:
    session: str
    epoch: str
    group: int
    prefix: int
    hidden_z: int
    feedback_kind: str
    feedback_vote: int | None
    deadline: int
    health: int
    hunger: int
    threat: bool
    scan_available: bool

    @property
    def target(self) -> int:
        return (self.prefix.bit_count() % 2) ^ self.hidden_z


@dataclass(frozen=True)
class Evidence:
    session: str
    revision: int
    group: int
    prefix: int
    deadline: int
    health: int
    hunger: int
    threat: bool
    scan_available: bool


@dataclass(frozen=True)
class Receipt:
    session: str
    e0_digest: str
    mode: str
    terminal_revision: int
    feedback_kind: str
    feedback_vote: int | None
    paid_diagnostic_z: int | None


@dataclass(frozen=True)
class Capsule:
    group: int
    predicted_z: int
    revision: int
    source_session: str


def cases(seed: int) -> tuple[Case, ...]:
    m = frozen_manifest()
    rng = random.Random(seed)
    out = []
    for epoch in m["epochs"]:
        for index in range(m["episodes_per_epoch"][epoch]):
            group = rng.randrange(2)
            hidden_z = int(rng.random() < m["hidden_z_p1"][epoch][group])
            draw = rng.random()
            if draw < m["world"]["feedback_exact_probability"]:
                kind, vote = "EXACT", hidden_z
            elif draw < (m["world"]["feedback_exact_probability"] +
                         m["world"]["feedback_weak_probability"]):
                kind = "WEAK"
                vote = hidden_z if rng.random() < m["world"]["weak_vote_accuracy"] else 1 - hidden_z
            else:
                kind, vote = "MISSING", None
            out.append(Case(
                session=f"c7:{seed}:{epoch}:{index}", epoch=epoch, group=group,
                prefix=rng.randrange(4), hidden_z=hidden_z,
                feedback_kind=kind, feedback_vote=vote,
                deadline=rng.choice(m["world"]["deadline_values"]),
                health=rng.choice(m["world"]["health_values"]),
                hunger=rng.choice(m["world"]["hunger_values"]),
                threat=rng.random() < m["world"]["threat_probability"],
                scan_available=rng.random() < m["world"]["scan_available_probability"],
            ))
    return tuple(out)


def viable(e: Evidence, mode: str) -> bool:
    if e.revision != 0 or mode not in MODES:
        return False
    ticks = COST[mode][0]
    if ticks > e.deadline or (mode == "DIAGNOSTIC" and not e.scan_available):
        return False
    exposed = int(e.threat and ticks >= 3)
    return e.health > exposed + (2 if mode == "CHEAP" else 0)


class World:
    """An in-memory trusted source of exactly one consumed terminal receipt."""

    def __init__(self, case: Case):
        self._case = case
        self._issued: Receipt | None = None
        self._consumed = False
        self._retained = False
        self._chosen: int | None = None

    def evidence(self) -> Evidence:
        c = self._case
        return Evidence(
            c.session, 0, c.group, c.prefix, c.deadline, c.health,
            c.hunger, c.threat, c.scan_available,
        )

    def issue(self, e: Evidence, mode: str, *, predicted_z: int = 0) -> Receipt:
        if self._issued is not None:
            raise ValueError("DUPLICATE_WORLD_TERMINAL")
        if e != self.evidence():
            raise ValueError("FOREIGN_OR_STALE_E0")
        if not viable(e, mode):
            raise ValueError("MODE_NOT_ADMITTED")
        if predicted_z not in (0, 1) or (mode != "CHEAP" and predicted_z != 0):
            raise ValueError("UNPAID_HIDDEN_INFORMATION")
        # Paid exact observation occurs only after mechanism admission.
        z = predicted_z if mode == "CHEAP" else self._case.hidden_z
        self._chosen = (e.prefix.bit_count() % 2) ^ z
        self._issued = Receipt(
            e.session, digest(asdict(e)), mode,
            1 if mode == "CHEAP" else 2,
            self._case.feedback_kind, self._case.feedback_vote,
            self._case.hidden_z if mode == "DIAGNOSTIC" else None,
        )
        return self._issued

    def consume(self, e: Evidence, receipt: Receipt, mode: str) -> Receipt:
        if (self._consumed or self._issued is not receipt
                or e != self.evidence() or receipt.session != e.session
                or receipt.e0_digest != digest(asdict(e))
                or receipt.mode != mode
                or receipt.terminal_revision != (1 if mode == "CHEAP" else 2)):
            raise ValueError("INVALID_OR_REPLAYED_WORLD_RECEIPT")
        self._consumed = True
        return receipt

    def retain(
        self, e: Evidence, receipt: Receipt, state: PolicyState, arm: str,
        *, warmup: bool, from_capsule: bool, index: int,
    ) -> dict:
        if (not self._consumed or self._retained
                or self._issued is not receipt or e != self.evidence()):
            raise ValueError("UNCONSUMED_OR_FORGED_OR_DUPLICATE_FEEDBACK")
        if receipt.feedback_kind not in ("EXACT", "WEAK", "MISSING"):
            raise ValueError("INVALID_FEEDBACK_KIND")
        if receipt.feedback_kind == "MISSING" and receipt.feedback_vote is not None:
            raise ValueError("SPOOFED_MISSING_LABEL")
        if receipt.feedback_kind in ("EXACT", "WEAK") and receipt.feedback_vote not in (0, 1):
            raise ValueError("INVALID_FEEDBACK_LABEL")
        self._retained = True
        if not warmup and arm in ("STATIC_CAPSULE", "NO_FEEDBACK_CAPSULE", "EVALUATOR_ORACLE"):
            return {"revoked": False, "recompiled": False, "lag": None, "quality": "SUPPRESSED"}
        return state.update(e, receipt, arm, warmup=warmup, from_capsule=from_capsule, index=index)

    def evaluate(self) -> tuple[bool, int, int]:
        """Evaluator only: never call in selectors or retention."""
        if not self._consumed or self._chosen is None:
            raise ValueError("NO_TERMINAL_ACTION")
        good = self._chosen == self._case.target
        exposure = int(self._case.threat and COST[self._issued.mode][0] >= 3)
        return good, 2 * int(not good) + exposure, exposure


@dataclass
class PolicyState:
    history: dict[int, deque[tuple[int, float, str, str]]] = field(default_factory=dict)
    capsules: dict[int, Capsule] = field(default_factory=dict)
    capsule_strikes: dict[int, deque[tuple[float, bool]]] = field(default_factory=dict)
    last_source: dict[int, str] = field(default_factory=dict)
    epoch_exact_since_revocation: dict[int, int] = field(default_factory=dict)
    first_opposite: dict[int, int] = field(default_factory=dict)
    revocation_index: dict[int, int] = field(default_factory=dict)
    revisions: dict[int, int] = field(default_factory=dict)

    def posterior(self, group: int) -> tuple[float, int]:
        vals = self.history.get(group, ())
        weights = sum(weight for _, weight, _, _ in vals)
        ones = sum(v * weight for v, weight, _, _ in vals)
        p1 = (1 + ones) / (2 + weights)
        return max(p1, 1 - p1), int(p1 > 0.5)

    def exact_in_recent(self, group: int) -> int:
        return sum(kind == "EXACT" for _, _, kind, _ in self.history.get(group, ()))

    def certify(self, group: int, *, postrev: bool) -> bool:
        m = frozen_manifest()
        needed = (m["retention"]["recompile_exact_post_revocation"] if postrev
                  else m["retention"]["warmup_qualification_exact"])
        if postrev and self.epoch_exact_since_revocation.get(group, 0) < needed:
            return False
        if self.exact_in_recent(group) < needed:
            return False
        certainty, z = self.posterior(group)
        if certainty < m["retention"]["qualification_confidence"]:
            return False
        revision = self.revisions.get(group, 0) + 1
        self.revisions[group] = revision
        self.capsules[group] = Capsule(group, z, revision, self.last_source[group])
        self.capsule_strikes[group] = deque(maxlen=6)
        self.first_opposite.pop(group, None)
        return True

    def certify_warmup(self) -> dict[str, bool]:
        return {str(group): self.certify(group, postrev=False) for group in (0, 1)}

    def update(
        self, e: Evidence, receipt: Receipt, arm: str, *,
        warmup: bool, from_capsule: bool, index: int,
    ) -> dict:
        cfg = frozen_manifest()
        if receipt.mode == "DIAGNOSTIC":
            quality, vote, weight = "EXACT", receipt.paid_diagnostic_z, 1.0
        elif receipt.feedback_kind == "EXACT":
            quality, vote, weight = "EXACT", receipt.feedback_vote, 1.0
        elif receipt.feedback_kind == "WEAK":
            quality, vote, weight = "WEAK", receipt.feedback_vote, 0.25
        else:
            quality, vote, weight = "MISSING", None, 0.0
        if (quality != "MISSING" and vote not in (0, 1)) or (
            quality == "MISSING" and vote is not None
        ):
            raise ValueError("INVALID_TYPED_SOURCE_OBSERVATION")
        # NAIVE is the explicit unsafe scientific comparator; weak evidence
        # is laundered into strong confidence ONLY inside this arm.
        accepted_quality = quality
        if arm == "NAIVE_WEAK_AS_EXACT" and quality == "WEAK":
            accepted_quality, weight = "EXACT", 1.0
        result = {"revoked": False, "recompiled": False, "lag": None, "quality": quality}
        if accepted_quality != "MISSING":
            self.history.setdefault(e.group, deque(maxlen=cfg["retention"]["window"])).append(
                (vote, weight, accepted_quality, e.session)
            )
            self.last_source[e.group] = e.session
        if warmup or arm not in ("NAIVE_WEAK_AS_EXACT", "STRICT_EXACT_ONLY", "WEIGHTED_GUARD"):
            return result
        capsule = self.capsules.get(e.group)
        if from_capsule:
            if capsule is None or receipt.mode != "CHEAP":
                raise ValueError("UNQUALIFIED_CAPSULE_RETENTION")
            is_opposite = vote is not None and vote != capsule.predicted_z
            strike_weight = 0.0 if not is_opposite else (
                1.0 if accepted_quality == "EXACT" else 0.25
            )
            is_actual_exact_opposite = bool(is_opposite and quality == "EXACT")
            strikes = self.capsule_strikes.setdefault(e.group, deque(maxlen=6))
            strikes.append((strike_weight, is_actual_exact_opposite))
            if strike_weight and e.group not in self.first_opposite:
                self.first_opposite[e.group] = index
            if arm == "NAIVE_WEAK_AS_EXACT":
                recent = list(strikes)[-cfg["guard"]["naive_recent_executed_capsule_cheap"]:]
                revoke = sum(w >= 1.0 for w, _ in recent) >= cfg["guard"]["naive_revocation_hard_opposites"]
            elif arm == "STRICT_EXACT_ONLY":
                recent = list(strikes)[-cfg["guard"]["strict_recent_executed_capsule_cheap"]:]
                revoke = sum(a for _, a in recent) >= cfg["guard"]["strict_revocation_exact_opposites"]
            else:
                recent = list(strikes)[-cfg["guard"]["weighted_recent_executed_capsule_cheap"]:]
                revoke = (
                    sum(w for w, _ in recent)
                    >= cfg["guard"]["weighted_contradictory_weight_at_least"]
                    and any(is_hard for _, is_hard in recent)
                )
            if revoke:
                result["revoked"] = True
                result["lag"] = index - self.first_opposite.pop(e.group, index)
                self.capsules.pop(e.group)
                self.capsule_strikes[e.group].clear()
                self.revocation_index[e.group] = index
                self.epoch_exact_since_revocation[e.group] = 0
            elif not any(w > 0 for w, _ in strikes):
                self.first_opposite.pop(e.group, None)
        elif capsule is None and e.group in self.revocation_index:
            # Only feedback from a later transaction than revocation.
            if accepted_quality == "EXACT":
                self.epoch_exact_since_revocation[e.group] = (
                    self.epoch_exact_since_revocation.get(e.group, 0) + 1
                )
            if self.certify(e.group, postrev=True):
                result["recompiled"] = True
                self.epoch_exact_since_revocation[e.group] = 0
        return result


def fallback(e: Evidence, s: PolicyState) -> tuple[str, int, bool]:
    if viable(e, "DIAGNOSTIC"):
        return "DIAGNOSTIC", 0, False
    if viable(e, "CHEAP"):
        return "CHEAP", s.posterior(e.group)[1], False
    return "ABSTAIN", 0, False


def choose(e: Evidence, arm: str, s: PolicyState, *, warmup: bool) -> tuple[str, int, bool]:
    if arm not in ARMS:
        raise ValueError("UNFROZEN_ARM")
    if warmup:
        return fallback(e, s)
    if arm == "EVALUATOR_ORACLE":
        raise ValueError("HIDDEN_ORACLE_NOT_ADMITTED")
    if arm in ("STATIC_CAPSULE", "NAIVE_WEAK_AS_EXACT",
               "STRICT_EXACT_ONLY", "WEIGHTED_GUARD", "NO_FEEDBACK_CAPSULE"):
        capsule = s.capsules.get(e.group)
        if capsule is not None and viable(e, "CHEAP"):
            return "CHEAP", capsule.predicted_z, True
        return fallback(e, s)
    if arm == "POSTERIOR_GATE":
        confidence, bit = s.posterior(e.group)
        if confidence >= frozen_manifest()["retention"]["qualification_confidence"] and viable(e, "CHEAP"):
            return "CHEAP", bit, False
        return fallback(e, s)
    if arm == "CHEAP_HISTORY":
        if viable(e, "CHEAP"):
            return "CHEAP", s.posterior(e.group)[1], False
        return "ABSTAIN", 0, False
    if arm == "PAID_ONLY":
        return fallback(e, s)
    raise ValueError("UNKNOWN_ARM")


def trajectory(seed: int, arm: str) -> dict:
    cfg = frozen_manifest()
    if seed not in cfg["seeds"]["calibration"] + cfg["seeds"]["heldout"]:
        raise ValueError("UNFROZEN_SEED")
    if arm not in ARMS:
        raise ValueError("UNFROZEN_ARM")
    state = PolicyState()
    trace = []
    qualification = None
    for index, case in enumerate(cases(seed)):
        warmup = case.epoch == "warmup"
        if not warmup and qualification is None:
            qualification = state.certify_warmup()
        world = World(case)
        e = world.evidence()
        oracle_free = arm == "EVALUATOR_ORACLE" and not warmup and viable(e, "CHEAP")
        if oracle_free:
            mode, bit, used_capsule = "CHEAP", case.hidden_z, False
        else:
            mode, bit, used_capsule = choose(e, arm, state, warmup=warmup)
        selector_work = 0 if warmup else cfg["selector_work"][arm]
        change = {"revoked": False, "recompiled": False, "lag": None, "quality": "NO_ACTION"}
        if mode == "ABSTAIN":
            success, damage, exposure, revision = None, 0, 0, None
        elif oracle_free:
            # Never issue a source receipt with artificially free hidden z.
            success, damage, exposure, revision = True, 0, 0, 1
            change["quality"] = "PRIVILEGED_EVALUATOR"
        else:
            receipt = world.consume(e, world.issue(e, mode, predicted_z=bit), mode)
            change = world.retain(
                e, receipt, state, arm, warmup=warmup,
                from_capsule=used_capsule, index=index,
            )
            success, damage, exposure = world.evaluate()
            revision = receipt.terminal_revision
        ticks, work = COST.get(mode, (0, 0))
        u = cfg["objective"]
        score = (u["correct"] if success is True else
                 u["wrong"] if success is False else u["abstain"])
        score += u["per_work"] * (work + selector_work) + u["per_tick"] * ticks
        trace.append({
            "session": e.session, "epoch": case.epoch, "group": e.group, "mode": mode,
            "used_capsule": used_capsule, "quality": change["quality"],
            "success": success, "damage": damage, "exposure": exposure,
            "ticks": ticks, "mechanism_work": work, "selector_work": selector_work,
            "utility_tenths": round(10 * score), "revision": revision,
            "revoked": change["revoked"], "recompiled": change["recompiled"],
            "lag": change["lag"],
        })
    if qualification is None:
        raise AssertionError("MISSING_WARMUP")
    phases = {}
    for epoch in cfg["epochs"]:
        rows = [x for x in trace if x["epoch"] == epoch]
        assert len(rows) == cfg["episodes_per_epoch"][epoch]
        phases[epoch] = {
            "correct": sum(x["success"] is True for x in rows),
            "wrong": sum(x["success"] is False for x in rows),
            "abstain": sum(x["success"] is None for x in rows),
            "mechanism_work": sum(x["mechanism_work"] for x in rows),
            "selector_work": sum(x["selector_work"] for x in rows),
            "ticks": sum(x["ticks"] for x in rows),
            "utility_tenths": sum(x["utility_tenths"] for x in rows),
            "damage": sum(x["damage"] for x in rows),
            "capsule_uses": sum(x["used_capsule"] for x in rows),
            "revocations": sum(x["revoked"] for x in rows),
            "recompilations": sum(x["recompiled"] for x in rows),
            "outcome_kinds": dict(sorted(Counter(x["quality"] for x in rows).items())),
            "mechanism_counts": dict(sorted(Counter(x["mode"] for x in rows).items())),
        }
    return {"seed": seed, "arm": arm, "initial_qualification": qualification,
            "phases": phases, "trace": tuple(trace)}


def report() -> dict:
    cfg = frozen_manifest()
    records = [
        trajectory(seed, arm)
        for seed in cfg["seeds"]["calibration"] + cfg["seeds"]["heldout"]
        for arm in ARMS
    ]
    summary = {}
    for setname, seeds in cfg["seeds"].items():
        summary[setname] = {}
        for arm in ARMS:
            rr = [r for r in records if r["seed"] in seeds and r["arm"] == arm]
            summary[setname][arm] = {
                k: sum(r["phases"][epoch][k] for r in rr for epoch in ("shift", "return"))
                for k in ("correct", "wrong", "abstain", "mechanism_work",
                          "selector_work", "ticks", "utility_tenths", "damage",
                          "capsule_uses", "revocations", "recompilations")
            }
            summary[setname][arm]["initial_qualified"] = sum(
                v for r in rr for v in r["initial_qualification"].values()
            )
    phases = {
        arm: {
            ep: {
                k: sum(r["phases"][ep][k] for r in records if (
                    r["arm"] == arm and r["seed"] in cfg["seeds"]["heldout"]
                ))
                for k in ("correct", "wrong", "abstain", "mechanism_work",
                          "selector_work", "utility_tenths", "damage",
                          "capsule_uses", "revocations", "recompilations")
            } for ep in cfg["epochs"]
        } for arm in ARMS
    }
    pair = {}
    for seed in cfg["seeds"]["heldout"]:
        rows = {a: next(r for r in records if r["arm"] == a and r["seed"] == seed)
                for a in ARMS}
        ref = tuple(x["session"] for x in rows["WEIGHTED_GUARD"]["trace"])
        assert all(tuple(x["session"] for x in row["trace"]) == ref
                   for row in rows.values())
        pair[str(seed)] = {
            "weighted_minus_naive_correct": sum(
                rows["WEIGHTED_GUARD"]["phases"][ep]["correct"] -
                rows["NAIVE_WEAK_AS_EXACT"]["phases"][ep]["correct"]
                for ep in ("shift", "return")
            ),
            "weighted_minus_gate_correct": sum(
                rows["WEIGHTED_GUARD"]["phases"][ep]["correct"] -
                rows["POSTERIOR_GATE"]["phases"][ep]["correct"]
                for ep in ("shift", "return")
            ),
            "return_revocations_weighted": rows["WEIGHTED_GUARD"]["phases"]["return"]["revocations"],
            "return_revocations_naive": rows["NAIVE_WEAK_AS_EXACT"]["phases"]["return"]["revocations"],
            "weighted_revocation_lags": [
                x["lag"] for x in rows["WEIGHTED_GUARD"]["trace"] if x["revoked"]
            ],
        }
    result = {"manifest_sha256": MANIFEST_SHA, "summaries": summary,
              "heldout_phases": phases, "paired": pair}
    result["result_sha256"] = digest(result)
    return result


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, ensure_ascii=False))
