"""Goal-independent Skill definitions and source-bound typed invocation arguments.

Cognitive v0.1 / #843. This is a pure CPU contract: parameterized or learned
Skills cannot obtain an Action/World grant by binding arguments. An Invocation
is a selected *claim* until checked by the existing Intent/Skill/Action owners.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.python_protocol import MineflayerPosition
from relay_self.common_io import ScopeRef
from relay_self.provenance import Provenance
from relay_self.target_contract import TargetContract


class SkillInvocationRefusal(ValueError):
    """Unbound, ambiguous, unbounded, or unregistered Skill arguments."""


class ArgumentKind(str, Enum):
    TARGET = "TARGET"
    CONSTRAINTS = "CONSTRAINTS"
    BUDGET = "BUDGET"
    NUMBER = "NUMBER"
    FLAG = "FLAG"
    SYMBOL = "SYMBOL"
    REFERENCE = "REFERENCE"
    POSITION = "POSITION"


def _name(label: str, value: object) -> None:
    if type(value) is not str or re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_]{0,63}", value,
    ) is None:
        raise SkillInvocationRefusal(f"invalid {label}")


def _ref(label: str, value: object) -> None:
    if (type(value) is not str or not 1 <= len(value) <= 256
            or not value.isprintable() or not value.strip()):
        raise SkillInvocationRefusal(f"invalid {label}")


def _number(label: str, value: object, *, maximum: float = 1e6) -> None:
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not -maximum <= value <= maximum):
        raise SkillInvocationRefusal(f"invalid {label}")


@dataclass(frozen=True, slots=True)
class SkillTarget:
    """Generic target, not a Minecraft destination or a physical grant."""

    ref: str
    kind: str
    contract: TargetContract | None = None

    def __post_init__(self) -> None:
        _ref("target ref", self.ref)
        _name("target kind", self.kind)
        if self.contract is not None and (
            not isinstance(self.contract, TargetContract)
            or self.contract.target_ref != self.ref
        ):
            raise SkillInvocationRefusal("target condition differs from target identity")


@dataclass(frozen=True, slots=True)
class SkillArgument:
    """One additional typed value; no JSON/executable expressions or implicit lookup."""

    name: str
    kind: ArgumentKind
    value: SkillTarget | MineflayerPosition | str | int | float | bool

    def __post_init__(self) -> None:
        _name("argument name", self.name)
        if not isinstance(self.kind, ArgumentKind):
            raise SkillInvocationRefusal("invalid argument kind")
        value = self.value
        if self.kind is ArgumentKind.TARGET:
            if not isinstance(value, SkillTarget):
                raise SkillInvocationRefusal("TARGET requires typed SkillTarget")
        elif self.kind is ArgumentKind.NUMBER:
            _number(self.name, value)
        elif self.kind is ArgumentKind.FLAG:
            if type(value) is not bool:
                raise SkillInvocationRefusal("FLAG requires boolean")
        elif self.kind is ArgumentKind.POSITION:
            if not isinstance(value, MineflayerPosition):
                raise SkillInvocationRefusal("POSITION requires finite position")
        elif self.kind in (ArgumentKind.REFERENCE, ArgumentKind.SYMBOL):
            if self.kind is ArgumentKind.SYMBOL:
                _name(self.name, value)
            else:
                _ref(self.name, value)
        else:
            raise SkillInvocationRefusal("core arguments must use typed fields")


@dataclass(frozen=True, slots=True)
class SkillConstraints:
    """Requirements from Goal/Target. Not proof that WorldBody enforces them."""

    requirements: tuple[SkillArgument, ...] = ()

    def __post_init__(self) -> None:
        if (type(self.requirements) is not tuple
                or len(self.requirements) > 12
                or any(not isinstance(a, SkillArgument) for a in self.requirements)
                or len({a.name for a in self.requirements}) != len(self.requirements)
                or any(a.kind is ArgumentKind.TARGET for a in self.requirements)):
            raise SkillInvocationRefusal("invalid bounded constraint requirements")


@dataclass(frozen=True, slots=True)
class SkillBudget:
    """Caller-desired upper bound, not increased Action authority or time grants."""

    max_actions: int
    max_duration_ms: int
    max_distance_m: float | None = None
    max_observations: int = 32

    def __post_init__(self) -> None:
        if (type(self.max_actions) is not int or not 1 <= self.max_actions <= 64
                or type(self.max_duration_ms) is not int
                or not 1 <= self.max_duration_ms <= 3600000
                or type(self.max_observations) is not int
                or not 1 <= self.max_observations <= 4096):
            raise SkillInvocationRefusal("bounded positive Skill resource budget required")
        if self.max_distance_m is not None:
            _number("travel budget", self.max_distance_m, maximum=100000)
            if self.max_distance_m <= 0:
                raise SkillInvocationRefusal("travel budget must be positive")


@dataclass(frozen=True, slots=True)
class SkillCostEstimate:
    """Self's fallible cost expectation; NOT an ActionPort admission limit."""

    actions: int
    duration_ms: int
    distance_m: float | None = None

    def __post_init__(self) -> None:
        if (type(self.actions) is not int or not 0 <= self.actions <= 64
                or type(self.duration_ms) is not int
                or not 0 <= self.duration_ms <= 3600000):
            raise SkillInvocationRefusal("invalid bounded expected cost")
        if self.distance_m is not None:
            _number("expected distance", self.distance_m, maximum=100000)
            if self.distance_m < 0:
                raise SkillInvocationRefusal("expected distance must be nonnegative")


@dataclass(frozen=True, slots=True)
class SkillParameterPreset:
    """Registered immutable parameters, already chosen before SystemOne SELECT.

    The caller must supply a Self-accepted registry snapshot. This data type
    itself is not registration, Self approval, or physical authorization.
    """

    pattern_id: str
    preset_id: str
    version: int
    definition_ref: str
    constraints: SkillConstraints
    budget: SkillBudget
    provenance: Provenance
    arguments: tuple[SkillArgument, ...] = ()
    expected_cost: SkillCostEstimate | None = None

    def __post_init__(self) -> None:
        _ref("pattern id", self.pattern_id)
        _name("preset id", self.preset_id)
        _ref("preset definition ref", self.definition_ref)
        if type(self.version) is not int or self.version < 1:
            raise SkillInvocationRefusal("invalid preset version")
        if (not isinstance(self.constraints, SkillConstraints)
                or not isinstance(self.budget, SkillBudget)
                or not isinstance(self.provenance, Provenance)
                or type(self.arguments) is not tuple
                or len(self.arguments) > 9
                or any(not isinstance(a, SkillArgument) for a in self.arguments)
                or len({a.name for a in self.arguments}) != len(self.arguments)
                or any(a.name in {"target", "constraints", "budget"}
                       for a in self.arguments)
                or (self.expected_cost is not None
                    and not isinstance(self.expected_cost, SkillCostEstimate))):
            raise SkillInvocationRefusal("invalid complete parameter preset")

    @property
    def preset_ref(self) -> str:
        payload = (
            self.pattern_id, self.preset_id, self.version, self.definition_ref,
            _constraints(self.constraints),
            (self.budget.max_actions, self.budget.max_duration_ms,
             _hex(self.budget.max_distance_m), self.budget.max_observations),
            self.provenance.source, self.provenance.reference,
            tuple((a.name, a.kind.value, _arg_value(a)) for a in self.arguments),
            None if self.expected_cost is None else (
                self.expected_cost.actions, self.expected_cost.duration_ms,
                _hex(self.expected_cost.distance_m)),
        )
        return "skill-preset:v1@" + _digest(payload)


@dataclass(frozen=True, slots=True)
class SkillParameter:
    name: str
    kind: ArgumentKind
    required: bool = True

    def __post_init__(self) -> None:
        _name("parameter name", self.name)
        if not isinstance(self.kind, ArgumentKind) or type(self.required) is not bool:
            raise SkillInvocationRefusal("typed required parameter definition needed")


CORE_PARAMETERS = (
    SkillParameter("target", ArgumentKind.TARGET),
    SkillParameter("constraints", ArgumentKind.CONSTRAINTS),
    SkillParameter("budget", ArgumentKind.BUDGET),
)


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Skill ability and parameter schema; deliberately no Goal/Target instance."""

    skill_id: str
    version: int
    origin: str
    provenance: Provenance
    parameters: tuple[SkillParameter, ...] = CORE_PARAMETERS
    capability_ref: str | None = None
    capability_version: int | None = None

    def __post_init__(self) -> None:
        _name("Skill ID", self.skill_id)
        if (type(self.version) is not int or self.version < 1
                or self.origin not in ("INNATE", "LEARNED")
                or not isinstance(self.provenance, Provenance)):
            raise SkillInvocationRefusal("invalid Skill definition identity/origin")
        if (type(self.parameters) is not tuple
                or not 3 <= len(self.parameters) <= 12
                or any(not isinstance(p, SkillParameter) for p in self.parameters)
                or self.parameters[:3] != CORE_PARAMETERS
                or len({p.name for p in self.parameters}) != len(self.parameters)):
            raise SkillInvocationRefusal("core target/constraints/budget parameters required")
        if self.capability_ref is None:
            if self.capability_version is not None:
                raise SkillInvocationRefusal("no version without physical capability")
        else:
            _name("capability ref", self.capability_ref)
            if type(self.capability_version) is not int or self.capability_version < 1:
                raise SkillInvocationRefusal("versioned physical capability required")

    @property
    def definition_ref(self) -> str:
        payload = (
            self.skill_id, self.version, self.origin,
            self.provenance.source, self.provenance.reference,
            tuple((p.name, p.kind.value, p.required) for p in self.parameters),
            self.capability_ref, self.capability_version,
        )
        return "skill-definition:v1@" + _digest(payload)


@dataclass(frozen=True, slots=True)
class SkillInvocation:
    """A single Goal-bound invocation of a reusable ability definition."""

    scope: ScopeRef
    skill_id: str
    skill_version: int
    definition_ref: str
    goal_id: str
    target: SkillTarget
    constraints: SkillConstraints
    budget: SkillBudget
    provenance: Provenance
    arguments: tuple[SkillArgument, ...] = ()
    parameter_preset_ref: str | None = None
    expected_cost: SkillCostEstimate | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not self.scope.world_session_id:
            raise SkillInvocationRefusal("Self and World session required")
        _name("Skill ID", self.skill_id)
        _name("Goal ID", self.goal_id)
        if type(self.skill_version) is not int or self.skill_version < 1:
            raise SkillInvocationRefusal("invalid Skill version")
        _ref("definition ref", self.definition_ref)
        if self.parameter_preset_ref is not None:
            _ref("parameter preset ref", self.parameter_preset_ref)
        if self.expected_cost is not None and not isinstance(
            self.expected_cost, SkillCostEstimate
        ):
            raise SkillInvocationRefusal("invalid Self expected cost")
        if (not isinstance(self.target, SkillTarget)
                or not isinstance(self.constraints, SkillConstraints)
                or not isinstance(self.budget, SkillBudget)
                or not isinstance(self.provenance, Provenance)):
            raise SkillInvocationRefusal("typed target, constraints, budget and source required")
        if self.target.contract is not None and (
            self.target.contract.scope != self.scope
            or self.target.contract.goal_id != self.goal_id
        ):
            raise SkillInvocationRefusal("target condition has wrong Self/World/Goal")
        if (type(self.arguments) is not tuple or len(self.arguments) > 9
                or any(not isinstance(x, SkillArgument) for x in self.arguments)
                or len({x.name for x in self.arguments}) != len(self.arguments)
                or any(x.name in {"target", "constraints", "budget"}
                       for x in self.arguments)):
            raise SkillInvocationRefusal("invalid bounded named invocation arguments")
        if any(
            x.kind is ArgumentKind.TARGET
            and x.value.contract is not None
            and (
                x.value.contract.scope != self.scope
                or x.value.contract.goal_id != self.goal_id
            )
            for x in self.arguments
        ):
            raise SkillInvocationRefusal("foreign extra target contract")

    @property
    def invocation_ref(self) -> str:
        payload = (
            self.scope.self_id, self.scope.world_session_id,
            self.skill_id, self.skill_version, self.definition_ref, self.goal_id,
            _target(self.target), _constraints(self.constraints),
            (self.budget.max_actions, self.budget.max_duration_ms,
             _hex(self.budget.max_distance_m), self.budget.max_observations),
            self.provenance.source, self.provenance.reference,
            tuple((a.name, a.kind.value, _arg_value(a)) for a in self.arguments),
        )
        if self.parameter_preset_ref is not None or self.expected_cost is not None:
            payload += (
                self.parameter_preset_ref,
                None if self.expected_cost is None else (
                    self.expected_cost.actions, self.expected_cost.duration_ms,
                    _hex(self.expected_cost.distance_m)),
            )
        return "skill-invocation:v1@" + _digest(payload)


def bind_skill_invocation(
    definition: SkillDefinition, invocation: SkillInvocation,
) -> SkillInvocation:
    """Validate a Self-proposed call against the registered definition's ABI."""
    if not isinstance(definition, SkillDefinition) or not isinstance(
        invocation, SkillInvocation
    ):
        raise SkillInvocationRefusal("typed Skill definition/invocation required")
    if (invocation.skill_id != definition.skill_id
            or invocation.skill_version != definition.version
            or invocation.definition_ref != definition.definition_ref):
        raise SkillInvocationRefusal("stale/foreign Skill version or parameter ABI")
    validate_preset_arguments(definition, invocation.arguments)
    return invocation


def validate_preset_arguments(
    definition: SkillDefinition, arguments: tuple[SkillArgument, ...],
) -> None:
    """Check the declared ABI before admission; does not create any Target."""
    if (not isinstance(definition, SkillDefinition)
            or type(arguments) is not tuple
            or len(arguments) > 9
            or any(not isinstance(a, SkillArgument) for a in arguments)
            or len({a.name for a in arguments}) != len(arguments)):
        raise SkillInvocationRefusal("invalid typed preset arguments")
    declared = {p.name: p for p in definition.parameters[3:]}
    provided = {p.name: p for p in arguments}
    if (set(provided) - set(declared)
            or any(name not in provided and p.required
                   for name, p in declared.items())
            or any(declared[name].kind is not p.kind
                   for name, p in provided.items())):
        raise SkillInvocationRefusal("undeclared, missing or mis-typed Skill argument")


def bind_preset_invocation(
    definition: SkillDefinition, preset: SkillParameterPreset, *,
    scope: ScopeRef, goal_id: str, target: SkillTarget,
    provenance: Provenance,
) -> SkillInvocation:
    """Resolve a registered preset on the CPU BEFORE offering an L1 option.

    No budget/parameter generation occurs at L1 selection or SkillRun start.
    """
    if not isinstance(preset, SkillParameterPreset):
        raise SkillInvocationRefusal("registered parameter preset required")
    if preset.definition_ref != definition.definition_ref:
        raise SkillInvocationRefusal("preset targets stale/foreign Skill ABI")
    return bind_skill_invocation(definition, SkillInvocation(
        scope=scope, skill_id=definition.skill_id, skill_version=definition.version,
        definition_ref=definition.definition_ref, goal_id=goal_id,
        target=target, constraints=preset.constraints, budget=preset.budget,
        provenance=provenance, arguments=preset.arguments,
        parameter_preset_ref=preset.preset_ref,
        expected_cost=preset.expected_cost,
    ))


@dataclass(frozen=True, slots=True)
class SkillCallTemplate:
    """A learned program's finite parameter forwarding, not a native Action."""

    skill_id: str
    skill_version: int
    arguments: tuple[tuple[str, str], ...] = (
        ("target", "target"), ("constraints", "constraints"), ("budget", "budget"),
    )

    def __post_init__(self) -> None:
        _name("child Skill", self.skill_id)
        if type(self.skill_version) is not int or self.skill_version < 1:
            raise SkillInvocationRefusal("child Skill version invalid")
        if (type(self.arguments) is not tuple or not 3 <= len(self.arguments) <= 12
                or any(type(pair) is not tuple or len(pair) != 2 for pair in self.arguments)):
            raise SkillInvocationRefusal("finite typed child argument mappings required")
        for dest, source in self.arguments:
            _name("child parameter", dest)
            _name("parent parameter", source)
        if len({a for a, _ in self.arguments}) != len(self.arguments):
            raise SkillInvocationRefusal("duplicate child parameter")


@dataclass(frozen=True, slots=True)
class LearnedSkillProgram:
    """Finite L2 Skill composition candidate. Validation DOES NOT register/run it."""

    definition: SkillDefinition
    calls: tuple[SkillCallTemplate, ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        if (not isinstance(self.definition, SkillDefinition)
                or self.definition.origin != "LEARNED"
                or not isinstance(self.provenance, Provenance)
                or type(self.calls) is not tuple
                or not 1 <= len(self.calls) <= 4
                or any(not isinstance(c, SkillCallTemplate) for c in self.calls)):
            raise SkillInvocationRefusal("bounded learned Skill hypothesis required")

    def validate_calls(
        self, registry: tuple[SkillDefinition, ...], *,
        learned_programs: tuple[LearnedSkillProgram, ...] = (),
    ) -> None:
        """Validate a finite acyclic learned-call DAG, not its execution.

        Registered learned callees need an explicit separate program. Missing
        definitions/programs, recursive expansion and resource explosions
        fail closed. This does not register the root or provide Action grants.
        """
        if (type(registry) is not tuple or len(registry) > 64
                or any(not isinstance(d, SkillDefinition) for d in registry)
                or len({(d.skill_id, d.version) for d in registry}) != len(registry)
                or type(learned_programs) is not tuple
                or len(learned_programs) > 16
                or any(not isinstance(p, LearnedSkillProgram)
                       for p in learned_programs)):
            raise SkillInvocationRefusal("unique bounded Skill registry required")
        definitions = {(d.skill_id, d.version): d for d in registry}
        root_key = (self.definition.skill_id, self.definition.version)
        if (root_key in definitions
                and definitions[root_key] != self.definition):
            raise SkillInvocationRefusal("learned root definition revision mismatch")
        programs = {root_key: self}
        for program in learned_programs:
            key = (program.definition.skill_id, program.definition.version)
            if (key in programs or definitions.get(key) != program.definition
                    or program.definition.origin != "LEARNED"):
                raise SkillInvocationRefusal("unregistered/duplicate learned program")
            programs[key] = program

        leaves = 0

        def check(program: LearnedSkillProgram, stack: tuple[tuple[str, int], ...]) -> None:
            nonlocal leaves
            if len(stack) > 8:
                raise SkillInvocationRefusal("learned Skill call depth exceeded")
            parent = {p.name: p.kind for p in program.definition.parameters}
            for call in program.calls:
                key = (call.skill_id, call.skill_version)
                if key in stack:
                    raise SkillInvocationRefusal("recursive learned Skill cycle")
                child = definitions.get(key)
                if child is None:
                    raise SkillInvocationRefusal("unregistered child Skill")
                provided = dict(call.arguments)
                declared = {p.name: p for p in child.parameters}
                if (set(provided) - set(declared)
                        or any(p.required and p.name not in provided
                               for p in child.parameters)
                        or any(parent.get(source) is not declared[dest].kind
                               for dest, source in call.arguments)):
                    raise SkillInvocationRefusal("invalid child typed argument forwarding")
                if child.origin == "LEARNED":
                    nested = programs.get(key)
                    if nested is None or nested.definition != child:
                        raise SkillInvocationRefusal("learned child program not registered")
                    check(nested, stack + (key,))
                else:
                    leaves += 1
                    if leaves > 32:
                        raise SkillInvocationRefusal("learned Skill call expansion too large")

        check(self, (root_key,))


def _hex(value: float | None) -> str | None:
    return None if value is None else float(value).hex()


def _target(target: SkillTarget) -> tuple[object, ...]:
    return (target.ref, target.kind, None if target.contract is None
            else target.contract.contract_ref)


def _arg_value(value: SkillArgument) -> object:
    if value.kind is ArgumentKind.TARGET:
        assert isinstance(value.value, SkillTarget)
        return _target(value.value)
    if value.kind is ArgumentKind.POSITION:
        assert isinstance(value.value, MineflayerPosition)
        p = value.value
        return (float(p.x).hex(), float(p.y).hex(), float(p.z).hex())
    if value.kind is ArgumentKind.NUMBER:
        assert isinstance(value.value, (float, int))
        return float(value.value).hex()
    return value.value


def _constraints(c: SkillConstraints) -> tuple[object, ...]:
    return tuple((a.name, a.kind.value, _arg_value(a)) for a in c.requirements)


def _digest(value: tuple[object, ...]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode(),
    ).hexdigest()
