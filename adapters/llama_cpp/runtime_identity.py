"""Model-only runtime identity checks extracted unchanged from the cognition transaction."""
from __future__ import annotations

import hashlib
from pathlib import Path

DEFAULT_CONTEXT = 8192
DEFAULT_SLOTS = 1
EXPECTED_TARGET_QUANTIZATION = "Q4_K_M"
_MODEL_FTYPE_TARGET_QUANTIZATION_EQUIVALENCE = {"Q4_K - Medium": "Q4_K_M"}


class PhysicalTransactionError(RuntimeError):
    """The bounded llama.cpp cognition transaction cannot proceed truthfully."""



def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _model_ids(payload: object) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise PhysicalTransactionError("llama-server /v1/models response is invalid")
    result: list[str] = []
    for item in payload["data"]:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]:
            result.append(item["id"])
    return result


def _model_ftype_matches_target_quantization(
    *, model_ftype: object, target_quantization: str
) -> bool:
    if model_ftype == target_quantization:
        return True
    if not isinstance(model_ftype, str):
        return False
    return (
        _MODEL_FTYPE_TARGET_QUANTIZATION_EQUIVALENCE.get(model_ftype)
        == target_quantization
    )


def attest_runtime(
    *,
    health: object,
    models: object,
    props: object,
    slots: object,
    artifact_path: Path,
    artifact_sha256: str,
    llama_identity: dict[str, object],
) -> dict[str, object]:
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise PhysicalTransactionError("llama-server /health is not ready")
    model_ids = _model_ids(models)
    if len(model_ids) != 1:
        raise PhysicalTransactionError("single-model transaction requires exactly one /v1/models id")
    if not isinstance(props, dict):
        raise PhysicalTransactionError("llama-server /props must return an object")
    if not isinstance(slots, list) or len(slots) != DEFAULT_SLOTS:
        raise PhysicalTransactionError("llama-server must expose exactly one /slots entry")

    build_number = llama_identity.get("buildNumber")
    revision = llama_identity.get("revision")
    build_info = props.get("build_info")
    if not isinstance(build_info, str):
        raise PhysicalTransactionError("props.build_info must be a string")
    if str(build_number) not in build_info:
        raise PhysicalTransactionError("llama-server --version build does not match /props build_info")
    if not isinstance(revision, str) or (
        revision not in build_info and revision[:7] not in build_info
    ):
        raise PhysicalTransactionError("llama.cpp git revision does not match /props build_info")

    model_alias = props.get("model_alias")
    if model_alias != model_ids[0]:
        raise PhysicalTransactionError("/props model_alias does not match /v1/models id")
    model_path = props.get("model_path")
    if not isinstance(model_path, str) or Path(model_path).resolve() != artifact_path:
        raise PhysicalTransactionError("/props model_path does not match the pinned GGUF")
    settings = props.get("default_generation_settings")
    if not isinstance(settings, dict) or settings.get("n_ctx") != DEFAULT_CONTEXT:
        raise PhysicalTransactionError("/props context does not equal 8192")
    if props.get("total_slots") != DEFAULT_SLOTS:
        raise PhysicalTransactionError("/props total_slots does not equal 1")
    slot = slots[0]
    if not isinstance(slot, dict) or slot.get("n_ctx") != DEFAULT_CONTEXT:
        raise PhysicalTransactionError("/slots context does not equal 8192")
    if slot.get("id") != 0:
        raise PhysicalTransactionError("single /slots entry must have id 0")
    model_ftype = props.get("model_ftype")
    if not _model_ftype_matches_target_quantization(
        model_ftype=model_ftype,
        target_quantization=EXPECTED_TARGET_QUANTIZATION,
    ):
        raise PhysicalTransactionError(
            "props.model_ftype does not match target quantization Q4_K_M"
        )
    chat_template = props.get("chat_template")
    if not isinstance(chat_template, str) or not chat_template:
        raise PhysicalTransactionError("props.chat_template must be a non-empty string")

    return {
        "requestModel": model_ids[0],
        "buildInfo": build_info,
        "modelAlias": model_alias,
        "modelPath": str(artifact_path),
        "modelFtype": model_ftype,
        "targetQuantization": EXPECTED_TARGET_QUANTIZATION,
        "artifactSha256": artifact_sha256,
        "chatTemplateSha256": _sha256_bytes(chat_template.encode("utf-8")),
        "context": DEFAULT_CONTEXT,
        "slots": DEFAULT_SLOTS,
        "contextShiftEnabled": False,
        "reasoningEffort": "none",
        "cachePrompt": False,
    }

