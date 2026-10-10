"""C14: source-attested signed goal witnesses and paid goal verification.

Synthetic World only. No direct hidden-z labels, no runtime Self/Minecraft,
LLM/GPU, real power, or production HABIT authority.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

MANIFEST = Path(__file__).with_name("ac_c_c14_manifest.json")
MANIFEST_SHA = "fc3495b6f2f280fd95bcd54830dd0a692869e2f5e69928bdb43d1b20e27d38cf"
ARMS = (
    "FROZEN_GROUP", "NO_FEEDBACK_GROUP", "POS_ONLY_GROUP",
    "SIGNED_GROUP", "FROZEN_MAJORITY", "SIGNED_MAJORITY",
    "POS_ONLY_GATE", "SIGNED_GATE", "SIGNED_VERIFY_ALWAYS",
    "SIGNED_VERIFY_SELECTIVE", "SIGNED_VERIFY_NO_RETENTION",
    "EVALUATOR_ORACLE",
)
FROZEN = {"FROZEN_GROUP", "NO_FEEDBACK_GROUP", "FROZEN_MAJORITY"}
POS_ONLY = {"POS_ONLY_GROUP", "POS_ONLY_GATE"}
VERIFYING = {"SIGNED_VERIFY_ALWAYS", "SIGNED_VERIFY_SELECTIVE", "SIGNED_VERIFY_NO_RETENTION"}


def digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def frozen() -> dict:
    x = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if digest(x) != MANIFEST_SHA:
        raise ValueError("C14_FROZEN_MANIFEST_DRIFT")
    return x


@dataclass(frozen=True)
class Case:
    session: str
    epoch: str
    group: int
    prefix: int
    cues: tuple[int, int, int]
    z: int
    obstructed: bool
    first_sensor_visible: bool
    verify_sensor_visible: bool
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
class FirstReceipt:
    session: str
    evidence_hash: str
    action_bit: int
    moved: bool
    goal_status: str
    revision: int


@dataclass(frozen=True)
class VerifyReceipt:
    session: str
    first_hash: str
    action_bit: int
    verified_goal_status: str
    revision: int


def cases(seed: int) -> tuple[Case, ...]:
    m = frozen()
    rng = random.Random(seed)
    result = []
    for epoch in m["epochs"]:
        for _ in range(m["n_per_epoch"]):
            group = rng.randrange(2)
            z = int(rng.random() < m["z_p1"][epoch][group])
            rel = m["cue_reliability"][epoch]
            cues = tuple(
                z if rng.random() < rel else 1-z for _ in range(3)
            )
            sid = hashlib.sha256(
                f"C14-Opaque-{seed}-{len(result)}".encode()
            ).hexdigest()[:24]
            result.append(Case(
                sid, epoch, group, rng.randrange(4), cues, z,
                rng.random() < m["world"]["obstructed_p"],
                rng.random() < m["world"]["goal_sensor_present_when_moved_p"],
                rng.random() < m["world"]["verify_goal_sensor_present_p"],
                rng.choice(m["world"]["health"]),
                rng.choice(m["world"]["deadline"]),
                rng.choice(m["world"]["hunger"]),
                rng.random() < m["world"]["threat_p"],
            ))
    return tuple(result)


def first_viable(e: E0) -> bool:
    return e.revision == 0 and e.health > 2 and e.deadline >= 1


def verify_viable(e: E0) -> bool:
    return (
        first_viable(e) and e.deadline >= 3 and e.hunger > 2
        and e.health > (3 if e.threat else 2)
    )


@dataclass
class Memory:
    group_z: dict[int, deque[int]] = field(default_factory=dict)
    cue_counts: deque[int] = field(default_factory=lambda: deque(maxlen=24))
    seen_sessions: set[str] = field(default_factory=set)

    def p1(self, g: int) -> float:
        h = self.group_z.get(g, ())
        return (1 + sum(h)) / (2 + len(h))

    def guess(self, g: int) -> int:
        return int(self.p1(g) > .5)

    def reliability(self) -> float:
        c = frozen()["retention"]
        n = len(self.cue_counts)
        k = c["cue_prior_strength"]
        p = (sum(self.cue_counts) + k*c["cue_prior_r"])/(3*n+k)
        low, high = c["cue_clamp"]
        return max(low, min(high, p))

    def accept(self, e: E0, action_bit: int, sign: str) -> str:
        if e.session in self.seen_sessions:
            raise ValueError("C14_DUPLICATED_RETAINED_SOURCE")
        if sign not in ("REACHED", "NOT_REACHED") or action_bit not in (0, 1):
            raise ValueError("C14_UNIDENTIFIED_GOAL_CANNOT_LEARN")
        executed_z = (e.prefix.bit_count() & 1) ^ action_bit
        qualified_z = executed_z if sign == "REACHED" else 1-executed_z
        self.seen_sessions.add(e.session)
        self.group_z.setdefault(
            e.group, deque(maxlen=frozen()["retention"]["per_group_z_labels_window"])
        ).append(qualified_z)
        self.cue_counts.append(sum(b == qualified_z for b in e.cues))
        return "POSITIVE" if sign == "REACHED" else "NEGATIVE"

    def signature(self) -> tuple:
        return (
            tuple(tuple(self.group_z.get(g, ())) for g in (0, 1)),
            tuple(self.cue_counts),
        )


class World:
    def __init__(self, case: Case):
        self._case = case
        self._first: FirstReceipt | None = None
        self._first_consumed = False
        self._verify: VerifyReceipt | None = None
        self._verify_consumed = False
        self._retained = False

    def e0(self) -> E0:
        c = self._case
        return E0(c.session, 0, c.group, c.prefix, c.cues,
                  c.health, c.deadline, c.hunger, c.threat)

    def issue_first(self, e: E0, guess_z: int) -> FirstReceipt:
        if self._first is not None:
            raise ValueError("C14_DUPLICATE_FIRST")
        if e != self.e0() or not first_viable(e) or guess_z not in (0, 1):
            raise ValueError("C14_UNAUTHORIZED_FIRST")
        action_bit = (e.prefix.bit_count() & 1) ^ guess_z
        moved = not self._case.obstructed
        goal = moved and guess_z == self._case.z
        status = "UNKNOWN"
        if moved and self._case.first_sensor_visible:
            status = "REACHED" if goal else "NOT_REACHED"
        self._first = FirstReceipt(
            e.session, digest(asdict(e)), action_bit, moved, status, 1,
        )
        return self._first

    def consume_first(self, e: E0, r: FirstReceipt) -> FirstReceipt:
        if (self._first_consumed or self._first is not r or e != self.e0()
                or r.session != e.session or r.evidence_hash != digest(asdict(e))
                or r.revision != 1):
            raise ValueError("C14_FORGED_OR_REPLAYED_FIRST")
        self._first_consumed = True
        return r

    def issue_verify(self, e: E0, first: FirstReceipt) -> VerifyReceipt:
        if (self._verify is not None or self._first is not first
                or not self._first_consumed or not first.moved
                or first.goal_status != "UNKNOWN" or e != self.e0()
                or not verify_viable(e)):
            raise ValueError("C14_VERIFY_NOT_ADMITTED")
        guess_z = (e.prefix.bit_count() & 1) ^ first.action_bit
        status = "VERIFIED_UNKNOWN"
        if self._case.verify_sensor_visible:
            status = (
                "VERIFIED_REACHED" if guess_z == self._case.z
                else "VERIFIED_NOT_REACHED"
            )
        self._verify = VerifyReceipt(
            e.session, digest(asdict(first)), first.action_bit, status, 2,
        )
        return self._verify

    def consume_verify(self, e: E0, first: FirstReceipt,
                       proof: VerifyReceipt) -> VerifyReceipt:
        if (self._verify_consumed or proof is not self._verify
                or self._first is not first or not self._first_consumed
                or e != self.e0() or proof.session != e.session
                or proof.first_hash != digest(asdict(first))
                or proof.action_bit != first.action_bit or proof.revision != 2):
            raise ValueError("C14_FORGED_OR_REPLAYED_VERIFY")
        self._verify_consumed = True
        return proof

    def retain(self, e: E0, first: FirstReceipt,
               verify: VerifyReceipt | None, state: Memory,
               *, enabled: bool, positive_only: bool,
               allow_verify: bool) -> str:
        if (self._retained or not self._first_consumed or first is not self._first
                or e != self.e0() or verify is not self._verify
                or (verify is not None and not self._verify_consumed)):
            raise ValueError("C14_UNCONSUMED_OR_REPLAYED_RETENTION")
        self._retained = True
        if not enabled:
            return "DISABLED"
        status = first.goal_status
        if status == "UNKNOWN" and allow_verify and verify is not None:
            status = {
                "VERIFIED_REACHED": "REACHED",
                "VERIFIED_NOT_REACHED": "NOT_REACHED",
                "VERIFIED_UNKNOWN": "UNKNOWN",
            }[verify.verified_goal_status]
        if not first.moved or status == "UNKNOWN":
            return "UNIDENTIFIED"
        if positive_only and status == "NOT_REACHED":
            return "UNIDENTIFIED"
        return state.accept(e, first.action_bit, status)

    def evaluator(self) -> dict:
        if not self._first_consumed or not self._retained:
            raise ValueError("C14_UNCOMPLETED_EVALUATOR")
        c, first = self._case, self._first
        guessed = (c.prefix.bit_count() & 1) ^ first.action_bit
        return {
            "selected_correct": guessed == c.z,
            "physical_goal": first.moved and guessed == c.z,
            "physical_moved_but_wrong": first.moved and guessed != c.z,
            "hidden_obstructed": c.obstructed,
        }


def majority(e: E0) -> int:
    return int(sum(e.cues) >= 2)


def decide(e: E0, state: Memory, arm: str, warmup: bool) -> tuple[str, int]:
    if arm not in ARMS:
        raise ValueError("C14_UNKNOWN_ARM")
    if not first_viable(e):
        return "ABSTAIN", 0
    z_group = state.guess(e.group)
    if warmup or arm in (
        "FROZEN_GROUP", "NO_FEEDBACK_GROUP", "POS_ONLY_GROUP", "SIGNED_GROUP",
    ):
        return "GROUP", z_group
    if arm in ("FROZEN_MAJORITY", "SIGNED_MAJORITY"):
        return "MAJORITY", majority(e)
    if arm == "EVALUATOR_ORACLE":
        raise ValueError("C14_ORACLE_FORBIDDEN_FROM_SOURCE_DECIDER")
    p_group = max(state.p1(e.group), 1-state.p1(e.group))
    r = state.reliability()
    p_majority = 3*r*r-2*r*r*r
    # Preregistered criterion: +20 for accuracy difference vs extra mode work .5
    if 20*(p_majority-p_group) > .5:
        return "MAJORITY", majority(e)
    return "GROUP", z_group


def trajectory(seed: int, arm: str) -> dict:
    m = frozen()
    if seed not in m["seeds"]["calibration"]+m["seeds"]["heldout"]:
        raise ValueError("C14_UNREGISTERED_SEED")
    if arm not in ARMS:
        raise ValueError("C14_UNREGISTERED_ARM")
    memory = Memory()
    warmup_sig = None
    rows = []
    for case in cases(seed):
        warmup = case.epoch == "warmup"
        if not warmup and warmup_sig is None:
            warmup_sig = memory.signature()
        w = World(case)
        e = w.e0()
        before_r = memory.reliability()
        before_conf = max(memory.p1(e.group), 1-memory.p1(e.group))
        before_group = memory.guess(e.group)
        receipt = None
        verify = None
        label_kind = "NO_FIRST"
        mode, z = ("ABSTAIN", 0)
        first_status = "NO_FIRST"
        if first_viable(e):
            if arm == "EVALUATOR_ORACLE" and not warmup:
                mode, z = "ORACLE", case.z
            else:
                mode, z = decide(e, memory, arm, warmup)
            receipt = w.consume_first(e, w.issue_first(e, z))
            first_status = receipt.goal_status
            has_verify = (
                not warmup and arm in VERIFYING and receipt.moved
                and receipt.goal_status == "UNKNOWN" and verify_viable(e)
            )
            do_verify = has_verify and (
                arm != "SIGNED_VERIFY_SELECTIVE"
                or majority(e) != z or before_r < m["policy"]["selective_r_threshold"]
            )
            if do_verify:
                verify = w.consume_verify(e, receipt, w.issue_verify(e, receipt))
            enabled = warmup or arm not in FROZEN|{"EVALUATOR_ORACLE"}
            label_kind = w.retain(
                e, receipt, verify, memory,
                enabled=enabled,
                positive_only=warmup or arm in POS_ONLY,
                allow_verify=arm != "SIGNED_VERIFY_NO_RETENTION",
            )
            actual = w.evaluator()  # never passed to source policy/retention
            if label_kind in ("POSITIVE", "NEGATIVE"):
                assert actual["selected_correct"] == (label_kind == "POSITIVE")
                assert receipt.moved
        else:
            actual = None

        first_work = (0 if receipt is None else
                      m["policy"]["modes"]["MAJORITY"]["work"]
                      if mode == "MAJORITY" else 1)
        sel_work = (
            0 if warmup or receipt is None else
            m["selector_work_first"][arm]
        )
        learn_work = int(label_kind in ("POSITIVE", "NEGATIVE"))
        paid_work = m["world"]["verify_work"] if verify is not None else 0
        work = first_work+sel_work+learn_work+paid_work
        ticks = (1 if receipt is not None else 0) + (
            m["world"]["verify_ticks"] if verify is not None else 0
        )
        goal = actual["physical_goal"] if actual is not None else False
        correctness = actual["selected_correct"] if actual is not None else None
        score = (m["score"]["initial_abstain"] if receipt is None
                 else m["score"]["goal"] if goal
                 else m["score"]["admitted_failure"])
        score += m["score"]["per_all_work"]*work+m["score"]["per_world_tick"]*ticks
        rows.append({
            "session":e.session,"epoch":case.epoch,"mode":mode,
            "zguess":z if receipt is not None else None,
            "correct":correctness,"physical_goal":goal,
            "moved_wrong":(actual["physical_moved_but_wrong"] if actual is not None else False),
            "moved":receipt.moved if receipt is not None else False,
            "first_status":first_status,
            "verified":verify is not None,
            "verified_status":verify.verified_goal_status if verify else "NO_VERIFY",
            "label_kind":label_kind,"prior_r":before_r,
            "prior_conf":before_conf,"prior_group":before_group,
            "posterior_r":memory.reliability(),
            "memory_sig":memory.signature(),
            "work":work,"ticks":ticks,"score_tenths":round(score*10),
        })
    if warmup_sig is None:
        raise AssertionError("C14_WARMUP_MISSING")
    phases = {}
    for epoch in m["epochs"]:
        chunk = [r for r in rows if r["epoch"] == epoch]
        assert len(chunk) == m["n_per_epoch"]
        phases[epoch] = {
            "correct":sum(r["correct"] is True for r in chunk),
            "wrong":sum(r["correct"] is False for r in chunk),
            "abstain":sum(r["correct"] is None for r in chunk),
            "physical_goals":sum(r["physical_goal"] for r in chunk),
            "moved_wrong":sum(r["moved_wrong"] for r in chunk),
            "blocked_movement":sum(
                r["correct"] is not None and not r["moved"] for r in chunk
            ),
            "first_positive":sum(r["first_status"] == "REACHED" for r in chunk),
            "first_negative":sum(r["first_status"] == "NOT_REACHED" for r in chunk),
            "first_unknown":sum(r["first_status"] == "UNKNOWN" for r in chunk),
            "verified":sum(r["verified"] for r in chunk),
            "verified_resolved":sum(
                r["verified_status"] in ("VERIFIED_REACHED","VERIFIED_NOT_REACHED")
                for r in chunk
            ),
            "positive_cert":sum(r["label_kind"] == "POSITIVE" for r in chunk),
            "negative_cert":sum(r["label_kind"] == "NEGATIVE" for r in chunk),
            "group_choice":sum(r["mode"] == "GROUP" for r in chunk),
            "majority_choice":sum(r["mode"] == "MAJORITY" for r in chunk),
            "work":sum(r["work"] for r in chunk),
            "ticks":sum(r["ticks"] for r in chunk),
            "score_tenths":sum(r["score_tenths"] for r in chunk),
            "last_r":chunk[-1]["posterior_r"],
            "mode_counts":dict(sorted(Counter(r["mode"] for r in chunk).items())),
        }
    return {
        "arm":arm,"seed":seed,"warmup_sig":warmup_sig,
        "phases":phases,"trace":tuple(rows),
    }


def report() -> dict:
    m = frozen()
    res = [
        trajectory(seed, arm)
        for seed in m["seeds"]["calibration"]+m["seeds"]["heldout"]
        for arm in ARMS
    ]
    metrics = (
        "correct","wrong","abstain","physical_goals","moved_wrong",
        "blocked_movement","first_positive","first_negative",
        "first_unknown","verified","verified_resolved","positive_cert",
        "negative_cert","group_choice","majority_choice","work",
        "ticks","score_tenths",
    )
    by_split = {}
    for name,seeds in m["seeds"].items():
        by_split[name] = {}
        for arm in ARMS:
            rr=[row for row in res if row["seed"] in seeds and row["arm"]==arm]
            summary={
                key:sum(r["phases"][ep][key] for r in rr for ep in m["epochs"][1:])
                for key in metrics
            }
            summary["per_epoch_goals"]={
                ep:sum(r["phases"][ep]["physical_goals"] for r in rr)
                for ep in m["epochs"]
            }
            summary["per_epoch_r_estimate"]={
                ep:round(sum(r["phases"][ep]["last_r"] for r in rr)/len(rr),4)
                for ep in m["epochs"]
            }
            summary["per_epoch_r_abs_error"]={
                ep:round(
                    sum(abs(r["phases"][ep]["last_r"]-m["cue_reliability"][ep])
                        for r in rr)/len(rr),4
                ) for ep in m["epochs"]
            }
            by_split[name][arm]=summary
    paired={}
    for seed in m["seeds"]["heldout"]:
        rr={arm:next(x for x in res if x["seed"]==seed and x["arm"]==arm)
            for arm in ARMS}
        assert len({tuple(r["session"] for r in x["trace"]) for x in rr.values()})==1
        assert len({x["warmup_sig"] for x in rr.values()})==1
        paired[str(seed)]={
            "signed_minus_positive_gate":sum(
                rr["SIGNED_GATE"]["phases"][ep]["physical_goals"]-
                rr["POS_ONLY_GATE"]["phases"][ep]["physical_goals"]
                for ep in m["epochs"][1:]
            ),
            "signed_minus_majority":sum(
                rr["SIGNED_GATE"]["phases"][ep]["physical_goals"]-
                rr["FROZEN_MAJORITY"]["phases"][ep]["physical_goals"]
                for ep in m["epochs"][1:]
            ),
            "verify_selective_minus_signed":sum(
                rr["SIGNED_VERIFY_SELECTIVE"]["phases"][ep]["physical_goals"]-
                rr["SIGNED_GATE"]["phases"][ep]["physical_goals"]
                for ep in m["epochs"][1:]
            ),
        }
    answer={"manifest_sha256":MANIFEST_SHA,"summary":by_split,"paired":paired}
    answer["result_sha256"]=digest(answer)
    return answer


if __name__=="__main__":
    print(json.dumps(report(),sort_keys=True,ensure_ascii=False))
