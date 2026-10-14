from __future__ import annotations

from dataclasses import dataclass, replace


class CapabilityCompositionError(ValueError):
    """Base error for declarative capability composition."""


class InvalidCapabilityData(CapabilityCompositionError):
    """Raised when a capability specification or plan is malformed."""


class UnknownCapability(CapabilityCompositionError):
    """Raised when a plan references a capability that is not declared."""


class UnsatisfiedCapabilityDependency(CapabilityCompositionError):
    """Raised when an enabled capability has a disabled dependency."""


class CapabilityDependencyCycle(CapabilityCompositionError):
    """Raised when declared capability dependencies contain a cycle."""


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    """Pure metadata describing one composable capability.

    A CapabilitySpec owns no cognitive state and executes no behavior. The
    identifiers name already-owned state scopes and already-admitted runtime
    seams that a future integration layer may bind explicitly.
    """

    capability_id: str
    state_scopes: tuple[str, ...] = ()
    operator_ids: tuple[str, ...] = ()
    criterion_ids: tuple[str, ...] = ()
    port_ids: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text("capability_id", self.capability_id)
        _validate_text_tuple("state_scopes", self.state_scopes)
        _validate_text_tuple("operator_ids", self.operator_ids)
        _validate_text_tuple("criterion_ids", self.criterion_ids)
        _validate_text_tuple("port_ids", self.port_ids)
        _validate_text_tuple("dependencies", self.dependencies)

        if self.capability_id in self.dependencies:
            raise InvalidCapabilityData(
                "a capability cannot depend on itself"
            )


@dataclass(frozen=True, slots=True)
class CapabilityPlan:
    """Immutable ON/OFF selection over declarative capability metadata.

    The plan does not own state, schedule work, call cognition, or mutate any
    runtime owner. Enabling only means that a later explicitly admitted
    integration may use the declared routes.
    """

    specs: tuple[CapabilitySpec, ...]
    enabled_ids: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.specs, tuple):
            raise InvalidCapabilityData("specs must be a tuple")
        if not all(isinstance(spec, CapabilitySpec) for spec in self.specs):
            raise InvalidCapabilityData(
                "specs must contain only CapabilitySpec values"
            )
        if not isinstance(self.enabled_ids, frozenset):
            raise InvalidCapabilityData("enabled_ids must be a frozenset")
        if not all(isinstance(value, str) and value.strip() for value in self.enabled_ids):
            raise InvalidCapabilityData(
                "enabled_ids must contain only non-empty strings"
            )

        by_id = self._spec_index()
        unknown_enabled = self.enabled_ids.difference(by_id)
        if unknown_enabled:
            raise UnknownCapability(
                "enabled capability is not declared: "
                + ", ".join(sorted(unknown_enabled))
            )

        for spec in self.specs:
            unknown_dependencies = set(spec.dependencies).difference(by_id)
            if unknown_dependencies:
                raise UnknownCapability(
                    f"{spec.capability_id} depends on undeclared capability: "
                    + ", ".join(sorted(unknown_dependencies))
                )

        self._validate_acyclic(by_id)

        for capability_id in self.enabled_ids:
            spec = by_id[capability_id]
            missing = set(spec.dependencies).difference(self.enabled_ids)
            if missing:
                raise UnsatisfiedCapabilityDependency(
                    f"{capability_id} has disabled dependency: "
                    + ", ".join(sorted(missing))
                )

    @property
    def enabled_specs(self) -> tuple[CapabilitySpec, ...]:
        """Return enabled specs in declaration order without executing them."""

        return tuple(
            spec
            for spec in self.specs
            if spec.capability_id in self.enabled_ids
        )

    def spec(self, capability_id: str) -> CapabilitySpec:
        _require_text("capability_id", capability_id)
        by_id = self._spec_index()
        try:
            return by_id[capability_id]
        except KeyError as exc:
            raise UnknownCapability(
                f"capability is not declared: {capability_id}"
            ) from exc

    def is_enabled(self, capability_id: str) -> bool:
        self.spec(capability_id)
        return capability_id in self.enabled_ids

    def with_enabled(
        self,
        capability_id: str,
        *,
        enabled: bool = True,
    ) -> CapabilityPlan:
        """Return a new validated plan with one selection changed.

        Disabling a dependency of another enabled capability fails closed
        through normal plan validation. No retained cognition is modified.
        """

        self.spec(capability_id)
        if not isinstance(enabled, bool):
            raise InvalidCapabilityData("enabled must be bool")

        selected = set(self.enabled_ids)
        if enabled:
            selected.add(capability_id)
        else:
            selected.discard(capability_id)

        return replace(self, enabled_ids=frozenset(selected))

    def _spec_index(self) -> dict[str, CapabilitySpec]:
        by_id: dict[str, CapabilitySpec] = {}
        for spec in self.specs:
            if spec.capability_id in by_id:
                raise InvalidCapabilityData(
                    f"duplicate capability_id: {spec.capability_id}"
                )
            by_id[spec.capability_id] = spec
        return by_id

    @staticmethod
    def _validate_acyclic(by_id: dict[str, CapabilitySpec]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(capability_id: str) -> None:
            if capability_id in visited:
                return
            if capability_id in visiting:
                raise CapabilityDependencyCycle(
                    f"capability dependency cycle includes: {capability_id}"
                )

            visiting.add(capability_id)
            for dependency_id in by_id[capability_id].dependencies:
                visit(dependency_id)
            visiting.remove(capability_id)
            visited.add(capability_id)

        for capability_id in by_id:
            visit(capability_id)


def _validate_text_tuple(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise InvalidCapabilityData(f"{name} must be a tuple")

    seen: set[str] = set()
    for index, value in enumerate(values):
        _require_text(f"{name}[{index}]", value)
        if value in seen:
            raise InvalidCapabilityData(
                f"{name} must not contain duplicates: {value}"
            )
        seen.add(value)


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidCapabilityData(f"{name} must be a non-empty string")
