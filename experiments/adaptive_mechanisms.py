from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
from statistics import fmean, median
from typing import Iterable

FAST = "fast"
MEDIUM = "medium"
SLOW = "slow"
CONDITIONS = ("cheap_only", "expensive_only", "fixed_switch", "adaptive")
MECHANISMS = (FAST, MEDIUM, SLOW)


@dataclass(frozen=True)
class SimulationConfig:
    episodes: int = 240
    context_count: int = 8
    learning_end: int = 80
    regime_shift_at: int = 160
    high_uncertainty_probability: float = 0.50
    low_uncertainty: float = 0.05
    high_uncertainty: float = 0.45
    uncertainty_threshold: float = 0.25
    tight_deadline_probability: float = 0.15
    medium_deadline_probability: float = 0.20
    tight_deadline: int = 2
    medium_deadline: int = 4
    relaxed_deadline: int = 10
    fast_latency: int = 1
    medium_latency: int = 3
    slow_latency: int = 8
    fast_cost: float = 1.0
    medium_cost: float = 3.0
    slow_cost: float = 10.0
    selector_cost: float = 0.25

    def __post_init__(self) -> None:
        if self.episodes < 3:
            raise ValueError("episodes must be at least 3")
        if self.context_count < 1:
            raise ValueError("context_count must be positive")
        if not 0 < self.learning_end < self.regime_shift_at < self.episodes:
            raise ValueError(
                "phase boundaries must satisfy 0 < learning_end < regime_shift_at < episodes"
            )
        for name, value in (
            ("high_uncertainty_probability", self.high_uncertainty_probability),
            ("tight_deadline_probability", self.tight_deadline_probability),
            ("medium_deadline_probability", self.medium_deadline_probability),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if self.tight_deadline_probability + self.medium_deadline_probability > 1.0:
            raise ValueError("deadline probabilities must sum to at most 1")
        if not 0.0 <= self.low_uncertainty <= self.high_uncertainty <= 1.0:
            raise ValueError("uncertainty values must satisfy 0 <= low <= high <= 1")
        if not self.low_uncertainty <= self.uncertainty_threshold <= self.high_uncertainty:
            raise ValueError("uncertainty_threshold must lie between low and high uncertainty")
        if not 0 < self.tight_deadline < self.medium_deadline < self.relaxed_deadline:
            raise ValueError("deadlines must be strictly increasing and positive")
        if not 0 < self.fast_latency < self.medium_latency < self.slow_latency:
            raise ValueError("mechanism latencies must be strictly increasing and positive")
        if min(self.fast_cost, self.medium_cost, self.slow_cost) < 0.0:
            raise ValueError("mechanism costs must be non-negative")
        if self.selector_cost < 0.0:
            raise ValueError("selector_cost must be non-negative")


@dataclass(frozen=True)
class Task:
    episode: int
    phase: str
    context: int
    base_action: int
    hidden_regime: int
    regime_signal: int
    uncertainty: float
    deadline: int
    target_action: int


@dataclass(frozen=True)
class CacheEntry:
    action: int
    learned_at_episode: int


@dataclass(frozen=True)
class DecisionRecord:
    episode: int
    phase: str
    context: int
    mechanism: str
    action: int
    target_action: int
    success: bool
    deadline_miss: bool
    latency: int
    cost: float
    cache_hit: bool


@dataclass(frozen=True)
class ConditionResult:
    seed: int
    condition: str
    episodes: int
    successes: int
    failures: int
    success_rate: float
    deadline_misses: int
    total_cost: float
    total_latency: int
    mean_latency: float
    selector_overhead: float
    mechanism_counts: dict[str, int]
    phase_mechanism_counts: dict[str, dict[str, int]]
    slow_solves_cached: int
    cheap_reuses: int
    cache_invalidations: int
    escalation_episodes: tuple[int, ...]
    re_escalation_episodes: tuple[int, ...]
    shifted_failures_before_re_escalation: int
    shift_recovery_episode: int | None
    trace: tuple[DecisionRecord, ...] = field(repr=False)

    def as_dict(self, *, include_trace: bool = False) -> dict[str, object]:
        data = asdict(self)
        if not include_trace:
            data.pop("trace")
        return data


@dataclass(frozen=True)
class BenchmarkSummary:
    condition: str
    seeds: int
    mean_success_rate: float
    median_success_rate: float
    min_success_rate: float
    max_success_rate: float
    mean_deadline_misses: float
    mean_total_cost: float
    mean_total_latency: float
    mean_selector_overhead: float
    mean_mechanism_counts: dict[str, float]
    mean_shifted_failures_before_re_escalation: float


@dataclass(frozen=True)
class BenchmarkResult:
    config: SimulationConfig
    seed_count: int
    summaries: dict[str, BenchmarkSummary]
    runs: dict[str, tuple[ConditionResult, ...]]

    def as_json(self, *, include_trace: bool = False) -> str:
        payload = {
            "config": asdict(self.config),
            "seed_count": self.seed_count,
            "summaries": {
                condition: asdict(summary) for condition, summary in self.summaries.items()
            },
            "runs": {
                condition: [run.as_dict(include_trace=include_trace) for run in runs]
                for condition, runs in self.runs.items()
            },
        }
        return json.dumps(payload, indent=2, sort_keys=True)


def generate_tasks(*, seed: int, config: SimulationConfig | None = None) -> tuple[Task, ...]:
    config = config or SimulationConfig()
    rng = random.Random(seed)
    base_actions = [rng.randrange(2) for _ in range(config.context_count)]
    tasks: list[Task] = []

    for episode in range(config.episodes):
        context = episode % config.context_count
        hidden_regime = int(episode >= config.regime_shift_at)
        if episode < config.learning_end:
            phase = "learning"
        elif episode < config.regime_shift_at:
            phase = "stable"
        else:
            phase = "shifted"

        uncertainty = (
            config.high_uncertainty
            if rng.random() < config.high_uncertainty_probability
            else config.low_uncertainty
        )
        regime_signal = hidden_regime
        if rng.random() < uncertainty:
            regime_signal = 1 - regime_signal

        deadline_draw = rng.random()
        if deadline_draw < config.tight_deadline_probability:
            deadline = config.tight_deadline
        elif deadline_draw < (
            config.tight_deadline_probability + config.medium_deadline_probability
        ):
            deadline = config.medium_deadline
        else:
            deadline = config.relaxed_deadline

        base_action = base_actions[context]
        tasks.append(
            Task(
                episode=episode,
                phase=phase,
                context=context,
                base_action=base_action,
                hidden_regime=hidden_regime,
                regime_signal=regime_signal,
                uncertainty=uncertainty,
                deadline=deadline,
                target_action=base_action ^ hidden_regime,
            )
        )

    return tuple(tasks)


def choose_mechanism(
    *,
    condition: str,
    task: Task,
    cache: dict[int, CacheEntry],
    config: SimulationConfig,
) -> str:
    if condition == "cheap_only":
        return FAST
    if condition == "expensive_only":
        return SLOW
    if condition == "fixed_switch":
        if (
            task.uncertainty >= config.uncertainty_threshold
            and config.slow_latency <= task.deadline
        ):
            return SLOW
        if config.medium_latency <= task.deadline:
            return MEDIUM
        return FAST
    if condition == "adaptive":
        if task.context in cache:
            return FAST
        if (
            task.uncertainty >= config.uncertainty_threshold
            and config.slow_latency <= task.deadline
        ):
            return SLOW
        if config.medium_latency <= task.deadline:
            return MEDIUM
        return FAST
    raise ValueError(f"unknown condition: {condition}")


def mechanism_action(
    mechanism: str,
    task: Task,
    cache: dict[int, CacheEntry],
) -> tuple[int, bool]:
    if mechanism == FAST:
        entry = cache.get(task.context)
        return (entry.action if entry is not None else task.base_action, entry is not None)
    if mechanism == MEDIUM:
        return task.base_action ^ task.regime_signal, False
    if mechanism == SLOW:
        return task.target_action, False
    raise ValueError(f"unknown mechanism: {mechanism}")


def mechanism_latency(mechanism: str, config: SimulationConfig) -> int:
    return {
        FAST: config.fast_latency,
        MEDIUM: config.medium_latency,
        SLOW: config.slow_latency,
    }[mechanism]


def mechanism_cost(mechanism: str, config: SimulationConfig) -> float:
    return {
        FAST: config.fast_cost,
        MEDIUM: config.medium_cost,
        SLOW: config.slow_cost,
    }[mechanism]


def run_condition(
    *,
    seed: int,
    condition: str,
    tasks: Iterable[Task] | None = None,
    config: SimulationConfig | None = None,
) -> ConditionResult:
    config = config or SimulationConfig()
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}")
    task_sequence = tuple(tasks) if tasks is not None else generate_tasks(seed=seed, config=config)
    if len(task_sequence) != config.episodes:
        raise ValueError("task sequence length must match config.episodes")

    cache: dict[int, CacheEntry] = {}
    trace: list[DecisionRecord] = []
    mechanism_counts: Counter[str] = Counter()
    phase_counts: dict[str, Counter[str]] = defaultdict(Counter)
    successes = 0
    deadline_misses = 0
    total_cost = 0.0
    total_latency = 0
    slow_solves_cached = 0
    cheap_reuses = 0
    cache_invalidations = 0
    escalation_episodes: list[int] = []
    re_escalation_episodes: list[int] = []
    awaiting_re_escalation: set[int] = set()
    shifted_failures_before_re_escalation = 0
    stale_at_shift: set[int] | None = None
    pending_shift_recovery: set[int] = set()
    shift_recovery_episode: int | None = None

    for task in task_sequence:
        if task.episode == config.regime_shift_at:
            stale_at_shift = set(cache)
            pending_shift_recovery = set(stale_at_shift)
            if not pending_shift_recovery:
                shift_recovery_episode = task.episode

        mechanism = choose_mechanism(
            condition=condition,
            task=task,
            cache=cache,
            config=config,
        )
        if condition == "adaptive" and mechanism == SLOW and task.context in awaiting_re_escalation:
            re_escalation_episodes.append(task.episode)
            awaiting_re_escalation.remove(task.context)

        latency = mechanism_latency(mechanism, config)
        decision_cost = mechanism_cost(mechanism, config)
        if condition == "adaptive":
            decision_cost += config.selector_cost
        action, cache_hit = mechanism_action(mechanism, task, cache)
        deadline_miss = latency > task.deadline
        success = not deadline_miss and action == task.target_action

        if success:
            successes += 1
        if deadline_miss:
            deadline_misses += 1
        mechanism_counts[mechanism] += 1
        phase_counts[task.phase][mechanism] += 1
        total_cost += decision_cost
        total_latency += latency

        if mechanism == FAST and cache_hit and success:
            cheap_reuses += 1

        if mechanism == FAST and cache_hit and not success:
            del cache[task.context]
            cache_invalidations += 1
            if condition == "adaptive":
                escalation_episodes.append(task.episode)
                awaiting_re_escalation.add(task.context)
                if task.phase == "shifted":
                    shifted_failures_before_re_escalation += 1

        elif (
            condition == "adaptive"
            and task.phase == "shifted"
            and task.context in awaiting_re_escalation
            and not success
        ):
            shifted_failures_before_re_escalation += 1

        if mechanism == SLOW and success:
            previous = cache.get(task.context)
            if previous is None or previous.action != action:
                cache[task.context] = CacheEntry(action=action, learned_at_episode=task.episode)
                slow_solves_cached += 1
            if task.phase == "shifted" and task.context in pending_shift_recovery:
                pending_shift_recovery.remove(task.context)
                if not pending_shift_recovery and shift_recovery_episode is None:
                    shift_recovery_episode = task.episode

        trace.append(
            DecisionRecord(
                episode=task.episode,
                phase=task.phase,
                context=task.context,
                mechanism=mechanism,
                action=action,
                target_action=task.target_action,
                success=success,
                deadline_miss=deadline_miss,
                latency=latency,
                cost=decision_cost,
                cache_hit=cache_hit,
            )
        )

    failures = config.episodes - successes
    selector_overhead = config.selector_cost * config.episodes if condition == "adaptive" else 0.0
    return ConditionResult(
        seed=seed,
        condition=condition,
        episodes=config.episodes,
        successes=successes,
        failures=failures,
        success_rate=successes / config.episodes,
        deadline_misses=deadline_misses,
        total_cost=total_cost,
        total_latency=total_latency,
        mean_latency=total_latency / config.episodes,
        selector_overhead=selector_overhead,
        mechanism_counts={mechanism: mechanism_counts[mechanism] for mechanism in MECHANISMS},
        phase_mechanism_counts={
            phase: {mechanism: counts[mechanism] for mechanism in MECHANISMS}
            for phase, counts in phase_counts.items()
        },
        slow_solves_cached=slow_solves_cached,
        cheap_reuses=cheap_reuses,
        cache_invalidations=cache_invalidations,
        escalation_episodes=tuple(escalation_episodes),
        re_escalation_episodes=tuple(re_escalation_episodes),
        shifted_failures_before_re_escalation=shifted_failures_before_re_escalation,
        shift_recovery_episode=shift_recovery_episode,
        trace=tuple(trace),
    )


def run_paired(*, seed: int, config: SimulationConfig | None = None) -> dict[str, ConditionResult]:
    config = config or SimulationConfig()
    tasks = generate_tasks(seed=seed, config=config)
    return {
        condition: run_condition(seed=seed, condition=condition, tasks=tasks, config=config)
        for condition in CONDITIONS
    }


def summarize_runs(condition: str, runs: tuple[ConditionResult, ...]) -> BenchmarkSummary:
    rates = [run.success_rate for run in runs]
    return BenchmarkSummary(
        condition=condition,
        seeds=len(runs),
        mean_success_rate=fmean(rates),
        median_success_rate=median(rates),
        min_success_rate=min(rates),
        max_success_rate=max(rates),
        mean_deadline_misses=fmean(run.deadline_misses for run in runs),
        mean_total_cost=fmean(run.total_cost for run in runs),
        mean_total_latency=fmean(run.total_latency for run in runs),
        mean_selector_overhead=fmean(run.selector_overhead for run in runs),
        mean_mechanism_counts={
            mechanism: fmean(run.mechanism_counts[mechanism] for run in runs)
            for mechanism in MECHANISMS
        },
        mean_shifted_failures_before_re_escalation=fmean(
            run.shifted_failures_before_re_escalation for run in runs
        ),
    )


def run_benchmark(
    *,
    seed_count: int,
    config: SimulationConfig | None = None,
) -> BenchmarkResult:
    if seed_count < 1:
        raise ValueError("seed_count must be positive")
    config = config or SimulationConfig()
    collected: dict[str, list[ConditionResult]] = {condition: [] for condition in CONDITIONS}
    for seed in range(seed_count):
        paired = run_paired(seed=seed, config=config)
        for condition, result in paired.items():
            collected[condition].append(result)

    runs = {condition: tuple(values) for condition, values in collected.items()}
    summaries = {
        condition: summarize_runs(condition, condition_runs)
        for condition, condition_runs in runs.items()
    }
    return BenchmarkResult(
        config=config,
        seed_count=seed_count,
        summaries=summaries,
        runs=runs,
    )


def _format_summary(result: BenchmarkResult) -> str:
    lines = [
        "condition        success   cost      deadline_miss  fast   medium  slow",
        "---------------  --------  --------  -------------  -----  ------  -----",
    ]
    for condition in CONDITIONS:
        summary = result.summaries[condition]
        counts = summary.mean_mechanism_counts
        lines.append(
            f"{condition:<15}  {summary.mean_success_rate:>7.3f}  "
            f"{summary.mean_total_cost:>8.1f}  {summary.mean_deadline_misses:>13.1f}  "
            f"{counts[FAST]:>5.1f}  {counts[MEDIUM]:>6.1f}  {counts[SLOW]:>5.1f}"
        )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bounded adaptive mechanism-selection probe")
    parser.add_argument("--seeds", type=int, default=20, help="number of paired seeds")
    parser.add_argument("--episodes", type=int, default=SimulationConfig.episodes)
    parser.add_argument("--selector-cost", type=float, default=SimulationConfig.selector_cost)
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable benchmark output"
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="include per-episode traces in JSON output",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.episodes != SimulationConfig.episodes:
        learning_end = max(1, args.episodes // 3)
        regime_shift_at = max(learning_end + 1, (2 * args.episodes) // 3)
        if regime_shift_at >= args.episodes:
            regime_shift_at = args.episodes - 1
        config = replace(
            SimulationConfig(),
            episodes=args.episodes,
            learning_end=learning_end,
            regime_shift_at=regime_shift_at,
            selector_cost=args.selector_cost,
        )
    else:
        config = replace(SimulationConfig(), selector_cost=args.selector_cost)

    result = run_benchmark(seed_count=args.seeds, config=config)
    if args.json:
        print(result.as_json(include_trace=args.trace))
    else:
        print(_format_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
