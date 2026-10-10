"""C6: revocable, source-bound toy L1 decision capsules, not a production owner.

No actual LLM, GPU, Minecraft, Action authority, power sensor or new scheduler.
A paid World diagnostic returns an *additional* hidden bit, not L2 reasoning.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("ac_c_c6_manifest.json")
MANIFEST_SHA = "bd06b014b4f9827c20a3b4a410696d35a18d5d2df4fb3cfa796cf4f55dca0624"
MODES = ("CHEAP", "DIAGNOSTIC", "DEEP")
COST = {"CHEAP": (1, 1), "DIAGNOSTIC": (3, 4), "DEEP": (5, 7)}
ARMS = (
    "STATIC_CAPSULE", "GUARDED_CAPSULE", "POSTERIOR_GATE",
    "CHEAP_HISTORY", "PAID_ONLY", "GUARDED_NO_FEEDBACK",
    "EVALUATOR_ORACLE",
)


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def frozen_manifest() -> dict:
    content = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if canonical_hash(content) != MANIFEST_SHA:
        raise ValueError("C6_FROZEN_MANIFEST_DRIFT")
    return content


@dataclass(frozen=True)
class HiddenCase:
    session: str
    epoch: str
    group: int
    prefix: int
    hidden_z: int
    deadline: int
    health: int
    hunger: int
    threat: bool
    scan_available: bool

    @property
    def target(self) -> int:
        return (self.prefix.bit_count() & 1) ^ self.hidden_z


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
    evidence_digest: str
    mode: str
    chosen_action: int
    observed_target: int
    success: bool
    damage: int
    exposure: int
    terminal_revision: int


@dataclass(frozen=True)
class Capsule:
    group: int
    predicted_z: int
    revision: int
    source_session: str
    evidence_count: int
    certified: bool = True


def generate(seed: int) -> tuple[HiddenCase, ...]:
    cfg = frozen_manifest()
    rng = random.Random(seed)
    cases = []
    for epoch in cfg["epochs"]:
        for index in range(cfg["opportunities"][epoch]):
            group = rng.randrange(2)
            hidden_z = int(rng.random() < cfg["hidden_z_probability_1"][epoch][group])
            cases.append(HiddenCase(
                session=f"c6:{seed}:{epoch}:{index}", epoch=epoch, group=group,
                prefix=rng.randrange(4), hidden_z=hidden_z,
                deadline=rng.choice(cfg["world"]["deadline_values"]),
                health=rng.choice(cfg["world"]["health_values"]),
                hunger=rng.choice(cfg["world"]["hunger_values"]),
                threat=rng.random() < cfg["world"]["threat_probability"],
                scan_available=rng.random() < cfg["world"]["scan_availability"],
            ))
    return tuple(cases)


def viable(evidence: Evidence, mode: str) -> bool:
    if mode not in COST or evidence.revision != 0:
        return False
    ticks = COST[mode][0]
    if ticks > evidence.deadline:
        return False
    if mode == "DIAGNOSTIC" and not evidence.scan_available:
        return False
    if mode == "DEEP" and evidence.hunger <= 2:
        return False
    exposure = int(evidence.threat and ticks >= 3)
    possible_error_damage = 2 if mode == "CHEAP" else 0
    return evidence.health > exposure + possible_error_damage


class World:
    """Trust domain: one World-sourced, consumed terminal receipt per case."""

    def __init__(self, case: HiddenCase):
        self._case = case
        self._issued: Receipt | None = None
        self._consumed = False
        self._retained = False

    def evidence(self) -> Evidence:
        c = self._case
        return Evidence(
            c.session, 0, c.group, c.prefix, c.deadline,
            c.health, c.hunger, c.threat, c.scan_available,
        )

    def issue(self, evidence: Evidence, mode: str, *, predicted_z: int = 0) -> Receipt:
        if self._issued is not None:
            raise ValueError("DUPLICATE_TERMINAL")
        if evidence != self.evidence() or evidence.revision != 0:
            raise ValueError("FOREIGN_OR_STALE_EVIDENCE")
        if not viable(evidence, mode):
            raise ValueError("UNADMITTED_MODE")
        if predicted_z not in (0, 1) or (mode != "CHEAP" and predicted_z != 0):
            raise ValueError("UNPAID_INFORMATION")
        # Only paid World modes obtain the hidden z after the choice.
        z = predicted_z if mode == "CHEAP" else self._case.hidden_z
        action = (evidence.prefix.bit_count() & 1) ^ z
        correct = action == self._case.target
        exposure = int(evidence.threat and COST[mode][0] >= 3)
        damage = 2 * int(not correct) + exposure
        self._issued = Receipt(
            evidence.session, canonical_hash(asdict(evidence)), mode,
            action, self._case.target, correct, damage, exposure,
            1 if mode == "CHEAP" else 2,
        )
        return self._issued

    def consume(self, evidence: Evidence, receipt: Receipt, mode: str) -> Receipt:
        if (
            self._consumed or self._issued is not receipt
            or evidence != self.evidence()
            or receipt.session != evidence.session
            or receipt.evidence_digest != canonical_hash(asdict(evidence))
            or receipt.mode != mode
            or receipt.terminal_revision != (1 if mode == "CHEAP" else 2)
        ):
            raise ValueError("UNAUTHORIZED_OR_REPLAYED_WORLD_RECEIPT")
        self._consumed = True
        return receipt

    def retain(
        self, evidence: Evidence, receipt: Receipt,
        state: PolicyState, arm: str, *, warmup: bool,
        from_capsule: bool, opportunity: int,
    ) -> dict:
        if (
            not self._consumed or self._retained or self._issued is not receipt
            or evidence != self.evidence()
        ):
            raise ValueError("FORGED_OR_DUPLICATED_LEARNING_FEEDBACK")
        if arm not in ARMS:
            raise ValueError("UNKNOWN_ARM_FEEDBACK")
        self._retained = True
        if not warmup and arm in ("STATIC_CAPSULE", "GUARDED_NO_FEEDBACK",
                                  "EVALUATOR_ORACLE"):
            return {"revoked": False, "recompiled": False, "revocation_lag": None}
        return state.record_verified(evidence, receipt, arm=arm,
                                     from_capsule=from_capsule,
                                     opportunity=opportunity, warmup=warmup)


@dataclass
class PolicyState:
    history: dict[int, deque[int]] = field(default_factory=dict)
    capsule: dict[int, Capsule] = field(default_factory=dict)
    strikes: dict[int, deque[bool]] = field(default_factory=dict)
    label_count: dict[int, int] = field(default_factory=dict)
    last_verified_session: dict[int, str] = field(default_factory=dict)
    since_revocation: dict[int, int] = field(default_factory=dict)
    recent_first_wrong: dict[int, int] = field(default_factory=dict)
    revocation_at: dict[int, int] = field(default_factory=dict)
    revision_count: dict[int, int] = field(default_factory=dict)

    def posterior(self, group: int) -> tuple[float, int]:
        values = self.history.get(group, ())
        n1 = sum(values)
        p1 = (n1 + 1) / (len(values) + 2)
        return max(p1, 1 - p1), int(p1 > 0.5)

    def certify(self, group: int, source_session: str) -> bool:
        cfg = frozen_manifest()
        values = self.history.get(group, ())
        confidence, z = self.posterior(group)
        if (len(values) < cfg["training"]["required_group_labels"]
                or confidence < cfg["training"]["minimum_qualification_probability"]):
            return False
        revision = self.revision_count.get(group, 0) + 1
        self.revision_count[group] = revision
        self.capsule[group] = Capsule(
            group, z, revision, source_session, self.label_count.get(group, 0),
        )
        self.strikes[group] = deque(maxlen=cfg["guard"]["window_of_executed_cached_cheap"])
        return True

    def certify_warmup(self) -> dict[str, bool]:
        return {str(group): self.certify(
            group, self.last_verified_session.get(group, "")
        ) for group in (0, 1)}

    def record_verified(
        self, e: Evidence, receipt: Receipt, *, arm: str,
        from_capsule: bool, opportunity: int, warmup: bool,
    ) -> dict:
        z = receipt.observed_target ^ (e.prefix.bit_count() & 1)
        self.history.setdefault(e.group, deque(maxlen=12)).append(z)
        self.label_count[e.group] = self.label_count.get(e.group, 0) + 1
        self.last_verified_session[e.group] = e.session
        outcome = {"revoked": False, "recompiled": False, "revocation_lag": None}
        if warmup or arm != "GUARDED_CAPSULE":
            return outcome

        active = self.capsule.get(e.group)
        if from_capsule:
            if active is None or not active.certified or receipt.mode != "CHEAP":
                raise ValueError("UNQUALIFIED_CAPSULE_FEEDBACK")
            mismatched = z != active.predicted_z
            strikes = self.strikes.setdefault(
                e.group, deque(maxlen=4)
            )
            strikes.append(mismatched)
            if mismatched and e.group not in self.recent_first_wrong:
                self.recent_first_wrong[e.group] = opportunity
            if sum(strikes) >= frozen_manifest()["guard"]["contradictions_required"]:
                start = self.recent_first_wrong.pop(e.group, opportunity)
                outcome["revoked"] = True
                outcome["revocation_lag"] = opportunity - start
                self.capsule.pop(e.group)
                self.strikes[e.group].clear()
                self.revocation_at[e.group] = opportunity
                self.since_revocation[e.group] = 0
            elif not any(strikes):
                self.recent_first_wrong.pop(e.group, None)
        elif active is None and e.group in self.revocation_at:
            # Post-revocation observations only; never invent initial capsules.
            self.since_revocation[e.group] = self.since_revocation.get(e.group, 0) + 1
            if (
                self.since_revocation[e.group]
                >= frozen_manifest()["guard"]["needs_post_revocation_labels"]
                and self.certify(e.group, e.session)
            ):
                outcome["recompiled"] = True
                self.since_revocation[e.group] = 0
        return outcome


def paid_fallback(e: Evidence, state: PolicyState) -> tuple[str, int, bool]:
    for mode in ("DIAGNOSTIC", "DEEP"):
        if viable(e, mode):
            return mode, 0, False
    if viable(e, "CHEAP"):
        return "CHEAP", state.posterior(e.group)[1], False
    return "ABSTAIN", 0, False


def decide(e: Evidence, arm: str, state: PolicyState, *, warmup: bool) -> tuple[str, int, bool]:
    if arm not in ARMS:
        raise ValueError("INVALID_ARM")
    if warmup:
        return paid_fallback(e, state)
    if arm == "EVALUATOR_ORACLE":
        raise ValueError("ORACLE_OUTSIDE_ORDINARY_SELECTOR")
    active = state.capsule.get(e.group)
    if arm in ("GUARDED_CAPSULE", "STATIC_CAPSULE", "GUARDED_NO_FEEDBACK"):
        if active is not None and active.certified and viable(e, "CHEAP"):
            return "CHEAP", active.predicted_z, True
        return paid_fallback(e, state)
    if arm == "POSTERIOR_GATE":
        confidence, estimate = state.posterior(e.group)
        if confidence >= frozen_manifest()["training"]["minimum_qualification_probability"] and viable(e, "CHEAP"):
            return "CHEAP", estimate, False
        return paid_fallback(e, state)
    if arm == "CHEAP_HISTORY":
        return ("CHEAP", state.posterior(e.group)[1], False) if viable(e, "CHEAP") else (
            "ABSTAIN", 0, False
        )
    if arm == "PAID_ONLY":
        return paid_fallback(e, state)
    raise ValueError("UNKNOWN_POLICY")


def trajectory(seed: int, arm: str) -> dict:
    cfg = frozen_manifest()
    if seed not in cfg["seeds"]["heldout"] + cfg["seeds"]["calibration"]:
        raise ValueError("UNFROZEN_SEED")
    if arm not in ARMS:
        raise ValueError("UNFROZEN_ARM")
    state = PolicyState()
    trace = []
    initial_certification = None
    for index, case in enumerate(generate(seed)):
        warmup = case.epoch == "warmup"
        if not warmup and initial_certification is None:
            initial_certification = state.certify_warmup()
        world = World(case)
        e = world.evidence()
        if arm == "EVALUATOR_ORACLE" and not warmup:
            # Upper bound: free hidden z knowledge, never admitted for fair arms.
            if viable(e, "CHEAP"):
                mode, z, from_capsule = "CHEAP", case.hidden_z, False
            else:
                mode, z, from_capsule = paid_fallback(e, state)
        else:
            mode, z, from_capsule = decide(e, arm, state, warmup=warmup)
        selector_work = 0 if warmup else cfg["selectors"][arm]
        change = {"revoked": False, "recompiled": False, "revocation_lag": None}
        if mode == "ABSTAIN":
            correct = None
            damage = exposure = 0
            terminal_revision = None
        elif arm == "EVALUATOR_ORACLE" and not warmup and mode == "CHEAP":
            # Do not call ordinary World.issue with an unpaid hidden z bit.
            correct, damage, exposure, terminal_revision = True, 0, 0, 1
        else:
            if not viable(e, mode):
                raise AssertionError("VIABILITY_VIOLATION")
            receipt = world.consume(e, world.issue(e, mode, predicted_z=z), mode)
            correct, damage, exposure = receipt.success, receipt.damage, receipt.exposure
            terminal_revision = receipt.terminal_revision
            change = world.retain(
                e, receipt, state, arm,
                warmup=warmup, from_capsule=from_capsule, opportunity=index,
            )
        ticks, work = COST.get(mode, (0, 0))
        obj = cfg["objective"]
        score = (obj["correct"] if correct is True else
                 obj["wrong"] if correct is False else obj["abstain"])
        score += obj["per_work"] * (work + selector_work) + obj["per_tick"] * ticks
        trace.append({
            "session": e.session, "epoch": case.epoch, "group": e.group,
            "mode": mode, "from_capsule": from_capsule, "correct": correct,
            "work": work, "selector_work": selector_work, "ticks": ticks,
            "utility_tenths": round(score * 10),
            "damage": damage, "exposure": exposure, "receipt_revision": terminal_revision,
            "revoked": change["revoked"], "recompiled": change["recompiled"],
            "revocation_lag": change["revocation_lag"],
        })
    if initial_certification is None:
        raise AssertionError("WARMUP_MISSING")
    phases = {}
    for epoch in cfg["epochs"]:
        rows = [x for x in trace if x["epoch"] == epoch]
        if len(rows) != cfg["opportunities"][epoch]:
            raise AssertionError("EPOCH_LENGTH_MISMATCH")
        phases[epoch] = {
            "correct": sum(x["correct"] is True for x in rows),
            "wrong": sum(x["correct"] is False for x in rows),
            "abstain": sum(x["correct"] is None for x in rows),
            "mechanism_work": sum(x["work"] for x in rows),
            "selector_work": sum(x["selector_work"] for x in rows),
            "ticks": sum(x["ticks"] for x in rows),
            "utility_tenths": sum(x["utility_tenths"] for x in rows),
            "damage": sum(x["damage"] for x in rows),
            "exposure": sum(x["exposure"] for x in rows),
            "capsule_uses": sum(x["from_capsule"] for x in rows),
            "revocations": sum(x["revoked"] for x in rows),
            "recompilations": sum(x["recompiled"] for x in rows),
            "counts": dict(sorted(Counter(x["mode"] for x in rows).items())),
        }
    return {
        "seed": seed, "arm": arm, "initial_certification": initial_certification,
        "phases": phases, "trace": tuple(trace),
    }


def report() -> dict:
    cfg = frozen_manifest()
    records = [
        trajectory(seed, arm)
        for seed in cfg["seeds"]["calibration"] + cfg["seeds"]["heldout"]
        for arm in ARMS
    ]
    summaries = {}
    for group, seeds in cfg["seeds"].items():
        summaries[group] = {}
        for arm in ARMS:
            active = [r for r in records if r["seed"] in seeds and r["arm"] == arm]
            summaries[group][arm] = {
                k: sum(r["phases"][ep][k] for r in active for ep in ("shift", "return"))
                for k in ("correct", "wrong", "abstain", "mechanism_work",
                          "selector_work", "ticks", "utility_tenths", "damage",
                          "exposure", "capsule_uses", "revocations", "recompilations")
            }
            summaries[group][arm]["initial_certified"] = sum(
                v for r in active for v in r["initial_certification"].values()
            )
    phases = {
        arm: {
            ep: {
                k: sum(r["phases"][ep][k] for r in records if (
                    r["arm"] == arm and r["seed"] in cfg["seeds"]["heldout"]
                ))
                for k in ("correct", "wrong", "abstain", "mechanism_work", "selector_work",
                          "utility_tenths", "capsule_uses", "revocations", "recompilations")
            }
            for ep in cfg["epochs"]
        } for arm in ARMS
    }
    paired = {}
    for seed in cfg["seeds"]["heldout"]:
        static = next(r for r in records if r["seed"] == seed and r["arm"] == "STATIC_CAPSULE")
        guard = next(r for r in records if r["seed"] == seed and r["arm"] == "GUARDED_CAPSULE")
        gate = next(r for r in records if r["seed"] == seed and r["arm"] == "POSTERIOR_GATE")
        assert tuple(x["session"] for x in static["trace"]) == tuple(
            x["session"] for x in guard["trace"]
        ) == tuple(x["session"] for x in gate["trace"])
        paired[str(seed)] = {
            "guard_vs_static_changed_mode_or_capsule": sum(
                (a["mode"], a["from_capsule"]) != (b["mode"], b["from_capsule"])
                for a, b in zip(guard["trace"], static["trace"], strict=True)
                if a["epoch"] != "warmup"
            ),
            "guard_success_minus_static": sum(
                r["phases"][ep]["correct"] for ep in ("shift", "return")
                for r in (guard,)
            ) - sum(static["phases"][ep]["correct"] for ep in ("shift", "return")),
            "guard_success_minus_gate": sum(
                guard["phases"][ep]["correct"] - gate["phases"][ep]["correct"]
                for ep in ("shift", "return")
            ),
            "guard_revocation_lags": [
                x["revocation_lag"] for x in guard["trace"] if x["revoked"]
            ],
        }
    result = {"manifest_sha256": MANIFEST_SHA, "summaries": summaries,
              "heldout_phases": phases, "paired": paired}
    result["result_sha256"] = canonical_hash(result)
    return result


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, ensure_ascii=False))
