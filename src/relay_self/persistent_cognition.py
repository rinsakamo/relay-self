import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from relay_self.appraisal import (
    AppraisalAspect,
    AppraisalBias,
    AppraisalDisposition,
    AppraisalTargetKind,
    InvalidAppraisalData,
)
from relay_self.provenance import InvalidProvenanceData, Provenance

CURRENT_SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1


class PersistentCognitionError(ValueError):
    """Base error for the minimum durable Persistent Cognition slice."""


class InvalidPersistentCognitionData(PersistentCognitionError):
    """Raised when persistent cognition data is malformed."""


class DuplicateMemoryIdentity(PersistentCognitionError):
    """Raised when one snapshot would contain two memories with the same identity."""


class DuplicateAppraisalDisposition(PersistentCognitionError):
    """Raised when one snapshot contains duplicate exact-scope appraisal state."""


class UnsupportedPersistentCognitionVersion(PersistentCognitionError):
    """Raised when a durable snapshot uses an unsupported schema version."""


class PersistentCognitionLoadError(PersistentCognitionError):
    """Raised when a durable snapshot cannot be read or decoded."""


class PersistentCognitionWriteError(PersistentCognitionError):
    """Raised when a durable snapshot cannot be committed."""


@dataclass(frozen=True, slots=True)
class IdentitySpecification:
    """Minimum durable identity/SOUL representation for the first MVP."""

    self_id: str
    directives: tuple[str, ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_text("self_id", self.self_id)
        if not isinstance(self.directives, tuple) or not self.directives:
            raise InvalidPersistentCognitionData(
                "identity directives must be a non-empty tuple"
            )
        for index, directive in enumerate(self.directives):
            _require_text(f"identity directive {index}", directive)
        _require_provenance("identity provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class Memory:
    """One governed durable memory, distinct from current World attestation."""

    memory_id: str
    content: str
    source_provenance: Provenance
    integration_provenance: Provenance

    def __post_init__(self) -> None:
        _require_text("memory_id", self.memory_id)
        _require_text("memory content", self.content)
        _require_provenance("memory source provenance", self.source_provenance)
        _require_provenance(
            "memory integration provenance",
            self.integration_provenance,
        )


@dataclass(frozen=True, slots=True)
class PersistentCognition:
    """Immutable MVP snapshot of the durable cognition actually implemented now."""

    identity: IdentitySpecification
    memories: tuple[Memory, ...] = ()
    appraisal_dispositions: tuple[AppraisalDisposition, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.identity, IdentitySpecification):
            raise InvalidPersistentCognitionData(
                "identity must be an IdentitySpecification"
            )
        if not isinstance(self.memories, tuple):
            raise InvalidPersistentCognitionData("memories must be a tuple")

        seen: set[str] = set()
        for memory in self.memories:
            if not isinstance(memory, Memory):
                raise InvalidPersistentCognitionData(
                    "every memories entry must be a Memory"
                )
            if memory.memory_id in seen:
                raise DuplicateMemoryIdentity(
                    f"duplicate memory identity: {memory.memory_id}"
                )
            seen.add(memory.memory_id)

        if not isinstance(self.appraisal_dispositions, tuple):
            raise InvalidPersistentCognitionData(
                "appraisal_dispositions must be a tuple"
            )
        appraisal_seen: set[
            tuple[AppraisalTargetKind, str, AppraisalAspect]
        ] = set()
        for disposition in self.appraisal_dispositions:
            if not isinstance(disposition, AppraisalDisposition):
                raise InvalidPersistentCognitionData(
                    "every appraisal_dispositions entry must be "
                    "an AppraisalDisposition"
                )
            if disposition.key in appraisal_seen:
                raise DuplicateAppraisalDisposition(
                    "duplicate appraisal disposition key: "
                    f"{disposition.key}"
                )
            appraisal_seen.add(disposition.key)

    def retain_memory(self, memory: Memory) -> "PersistentCognition":
        """Return a new snapshot after an already-governed Memory is accepted."""

        if not isinstance(memory, Memory):
            raise InvalidPersistentCognitionData("retained value must be a Memory")
        if any(existing.memory_id == memory.memory_id for existing in self.memories):
            raise DuplicateMemoryIdentity(
                f"duplicate memory identity: {memory.memory_id}"
            )
        return replace(self, memories=(*self.memories, memory))

    def seed_appraisal_disposition(
        self,
        disposition: AppraisalDisposition,
    ) -> "PersistentCognition":
        """Add one initial tendency grounded in this Identity Specification."""

        if not isinstance(disposition, AppraisalDisposition):
            raise InvalidPersistentCognitionData(
                "seeded appraisal value must be an AppraisalDisposition"
            )
        if disposition.source_provenance != self.identity.provenance:
            raise InvalidPersistentCognitionData(
                "seeded appraisal source provenance must match identity provenance"
            )
        if any(
            existing.key == disposition.key
            for existing in self.appraisal_dispositions
        ):
            raise DuplicateAppraisalDisposition(
                f"duplicate appraisal disposition key: {disposition.key}"
            )
        return replace(
            self,
            appraisal_dispositions=(
                *self.appraisal_dispositions,
                disposition,
            ),
        )

    def integrate_appraisal_disposition(
        self,
        disposition: AppraisalDisposition,
    ) -> "PersistentCognition":
        """Upsert one exact-scope tendency after governed experience integration.

        This operation never generalizes an entity-instance disposition into an
        entity-class disposition. The caller must explicitly choose the scope
        justified by its evidence.
        """

        if not isinstance(disposition, AppraisalDisposition):
            raise InvalidPersistentCognitionData(
                "integrated appraisal value must be an AppraisalDisposition"
            )

        updated = list(self.appraisal_dispositions)
        for index, existing in enumerate(updated):
            if existing.key == disposition.key:
                updated[index] = disposition
                break
        else:
            updated.append(disposition)

        return replace(self, appraisal_dispositions=tuple(updated))


def save_persistent_cognition(
    path: str | os.PathLike[str],
    cognition: PersistentCognition,
) -> None:
    """Atomically replace one local JSON snapshot on the same filesystem."""

    if not isinstance(cognition, PersistentCognition):
        raise InvalidPersistentCognitionData(
            "cognition must be a PersistentCognition snapshot"
        )

    target = Path(path)
    temporary = target.with_name(f".{target.name}.tmp")
    rendered = json.dumps(
        _encode_persistent_cognition(cognition),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise PersistentCognitionWriteError(
            f"could not commit persistent cognition snapshot: {exc}"
        ) from exc


def load_persistent_cognition(
    path: str | os.PathLike[str],
) -> PersistentCognition:
    """Load one supported local snapshot and fail closed on malformed data."""

    target = Path(path)
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise PersistentCognitionLoadError(
            f"could not read persistent cognition snapshot: {exc}"
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PersistentCognitionLoadError(
            f"persistent cognition snapshot is not valid JSON: {exc}"
        ) from exc

    return _decode_persistent_cognition(payload)


def _encode_persistent_cognition(cognition: PersistentCognition) -> dict[str, Any]:
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "identity": {
            "self_id": cognition.identity.self_id,
            "directives": list(cognition.identity.directives),
            "provenance": _encode_provenance(cognition.identity.provenance),
        },
        "memories": [
            {
                "memory_id": memory.memory_id,
                "content": memory.content,
                "source_provenance": _encode_provenance(memory.source_provenance),
                "integration_provenance": _encode_provenance(
                    memory.integration_provenance
                ),
            }
            for memory in cognition.memories
        ],
        "appraisal_dispositions": [
            _encode_appraisal_disposition(disposition)
            for disposition in cognition.appraisal_dispositions
        ],
    }


def _decode_persistent_cognition(value: object) -> PersistentCognition:
    payload = _require_mapping("persistent cognition snapshot", value)

    version = payload.get("schema_version")
    if type(version) is not int:
        raise InvalidPersistentCognitionData("schema_version must be an integer")
    if version not in {LEGACY_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION}:
        raise UnsupportedPersistentCognitionVersion(
            f"unsupported persistent cognition schema version: {version}"
        )

    expected_keys = {"schema_version", "identity", "memories"}
    if version == CURRENT_SCHEMA_VERSION:
        expected_keys.add("appraisal_dispositions")
    _require_exact_keys(
        "persistent cognition snapshot",
        payload,
        expected_keys,
    )

    identity = _decode_identity(payload["identity"])
    memories_value = payload["memories"]
    if not isinstance(memories_value, list):
        raise InvalidPersistentCognitionData("memories must be a JSON array")

    memories = tuple(
        _decode_memory(memory, index)
        for index, memory in enumerate(memories_value)
    )

    if version == LEGACY_SCHEMA_VERSION:
        appraisal_dispositions: tuple[AppraisalDisposition, ...] = ()
    else:
        dispositions_value = payload["appraisal_dispositions"]
        if not isinstance(dispositions_value, list):
            raise InvalidPersistentCognitionData(
                "appraisal_dispositions must be a JSON array"
            )
        appraisal_dispositions = tuple(
            _decode_appraisal_disposition(disposition, index)
            for index, disposition in enumerate(dispositions_value)
        )

    return PersistentCognition(
        identity=identity,
        memories=memories,
        appraisal_dispositions=appraisal_dispositions,
    )

def _decode_identity(value: object) -> IdentitySpecification:
    payload = _require_mapping("identity", value)
    _require_exact_keys(
        "identity",
        payload,
        {"self_id", "directives", "provenance"},
    )

    directives = payload["directives"]
    if not isinstance(directives, list):
        raise InvalidPersistentCognitionData(
            "identity directives must be a JSON array"
        )

    return IdentitySpecification(
        self_id=_decoded_text("identity self_id", payload["self_id"]),
        directives=tuple(
            _decoded_text(f"identity directive {index}", directive)
            for index, directive in enumerate(directives)
        ),
        provenance=_decode_provenance("identity provenance", payload["provenance"]),
    )


def _decode_memory(value: object, index: int) -> Memory:
    name = f"memory {index}"
    payload = _require_mapping(name, value)
    _require_exact_keys(
        name,
        payload,
        {
            "memory_id",
            "content",
            "source_provenance",
            "integration_provenance",
        },
    )

    return Memory(
        memory_id=_decoded_text(f"{name} memory_id", payload["memory_id"]),
        content=_decoded_text(f"{name} content", payload["content"]),
        source_provenance=_decode_provenance(
            f"{name} source provenance",
            payload["source_provenance"],
        ),
        integration_provenance=_decode_provenance(
            f"{name} integration provenance",
            payload["integration_provenance"],
        ),
    )


def _encode_appraisal_disposition(
    disposition: AppraisalDisposition,
) -> dict[str, Any]:
    return {
        "target_kind": disposition.target_kind.value,
        "target_key": disposition.target_key,
        "aspect": disposition.aspect.value,
        "bias": disposition.bias.value,
        "source_provenance": _encode_provenance(
            disposition.source_provenance
        ),
        "integration_provenance": _encode_provenance(
            disposition.integration_provenance
        ),
    }


def _decode_appraisal_disposition(
    value: object,
    index: int,
) -> AppraisalDisposition:
    name = f"appraisal disposition {index}"
    payload = _require_mapping(name, value)
    _require_exact_keys(
        name,
        payload,
        {
            "target_kind",
            "target_key",
            "aspect",
            "bias",
            "source_provenance",
            "integration_provenance",
        },
    )

    try:
        target_kind = AppraisalTargetKind(
            _decoded_text(f"{name} target_kind", payload["target_kind"])
        )
        aspect = AppraisalAspect(
            _decoded_text(f"{name} aspect", payload["aspect"])
        )
        bias = AppraisalBias(
            _decoded_text(f"{name} bias", payload["bias"])
        )
        return AppraisalDisposition(
            target_kind=target_kind,
            target_key=_decoded_text(
                f"{name} target_key",
                payload["target_key"],
            ),
            aspect=aspect,
            bias=bias,
            source_provenance=_decode_provenance(
                f"{name} source provenance",
                payload["source_provenance"],
            ),
            integration_provenance=_decode_provenance(
                f"{name} integration provenance",
                payload["integration_provenance"],
            ),
        )
    except (InvalidAppraisalData, ValueError) as exc:
        raise InvalidPersistentCognitionData(
            f"{name} is invalid: {exc}"
        ) from exc


def _encode_provenance(provenance: Provenance) -> dict[str, str]:
    return {
        "source": provenance.source,
        "reference": provenance.reference,
    }


def _decode_provenance(name: str, value: object) -> Provenance:
    payload = _require_mapping(name, value)
    _require_exact_keys(name, payload, {"source", "reference"})

    try:
        return Provenance(
            source=_decoded_text(f"{name} source", payload["source"]),
            reference=_decoded_text(f"{name} reference", payload["reference"]),
        )
    except InvalidProvenanceData as exc:
        raise InvalidPersistentCognitionData(f"{name} is invalid: {exc}") from exc


def _require_mapping(name: str, value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidPersistentCognitionData(f"{name} must be a JSON object")
    return value


def _require_exact_keys(
    name: str,
    value: dict[str, Any],
    expected: set[str],
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise InvalidPersistentCognitionData(
            f"{name} fields are invalid; missing={missing}, unexpected={unexpected}"
        )


def _decoded_text(name: str, value: object) -> str:
    _require_text(name, value)
    return value


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidPersistentCognitionData(f"{name} must be a non-empty string")


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidPersistentCognitionData(f"{name} must be Provenance")
