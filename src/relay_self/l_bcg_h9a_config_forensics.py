"""Posthoc H9a configuration forensics; NEVER substitutes for raw-SHA pair admission.

The ORIGINAL H9a pair's preregistered raw-SHA equality failed and remains
REJECTED, even if a narrowly scoped generated timestamp is the sole cause.
Only preserved source bytes, original manifests and exact unchanged-property
bytes are examined. This is an observational posthoc diagnostic, not a new
World, a pair-pass gate, Goal, physical clear, or formal L1 training.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

_TIMESTAMP_LINE = re.compile(
    rb"\#[A-Z][a-z]{2} [A-Z][a-z]{2} [ 0-9][0-9] "
    rb"[0-2][0-9]:[0-5][0-9]:[0-5][0-9] "
    rb"[A-Z]{2,5} 20[0-9][0-9]\n\Z"
)
_HEADER = b"#Minecraft server properties\n"
_CRITICAL = (
    "/minecraft.jar",
    "/server.properties",
    "/plugins/relay-metabolism-paper-dev.jar",
    "/plugins/RelayMetabolismDev/config.yml",
)


class ConfigForensicsRejected(ValueError):
    """Original digest absent, manipulated content, or wider config drift."""


@dataclass(frozen=True, slots=True)
class H9aTimestampForensic:
    raw_sha_a: str
    raw_sha_b: str
    raw_sha_different: bool
    byte_diff_line_numbers: tuple[int, ...]
    only_generated_timestamp_line_differs: bool
    other_critical_asset_sha_equal: bool
    independent_original_manifest_per_arm_checked: bool
    original_pair_raw_sha_gate: str = "REJECTED_AS_PREDECLARED"
    changes_original_pair_decision: bool = False
    supplementary_classification: str = (
        "POSTHOC_CONFIG_TIMESTAMP_ONLY_DIAGNOSTIC_NOT_PAIR_PASS"
    )
    extra_worlds: int = 0
    additional_actions: int = 0
    qualified_training_worlds: int = 0
    qualification: str = "NO_GO"
    science: str = "NOT_RUN"


def _check(ok: bool, reason: str) -> None:
    if not ok:
        raise ConfigForensicsRejected(reason)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _manifest(raw: bytes, name: str) -> dict:
    _check(type(raw) is bytes and 0 < len(raw) <= 2_000_000, name + " bounds")
    try:
        obj = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise ConfigForensicsRejected(name + " invalid JSON") from exc
    _check(type(obj) is dict, name + " object needed")
    return obj


def _asset_sha(manifest: dict, suffix: str) -> str:
    matches = [
        v.get("sha256") for k, v in manifest.items()
        if type(k) is str and k.endswith(suffix) and type(v) is dict
    ]
    _check(len(matches) == 1, "missing or multiple asset " + suffix)
    value = matches[0]
    _check(
        type(value) is str and len(value) == 64
        and all(x in "0123456789abcdef" for x in value),
        "invalid asset digest " + suffix,
    )
    return value


def _check_arm(
    config_original: bytes, raw_asset_manifest: bytes,
    raw_original_manifest: bytes,
) -> tuple[str, tuple[str, ...]]:
    _check(
        type(config_original) is bytes
        and 0 < len(config_original) <= 65_536,
        "invalid original server.properties bounds",
    )
    assets = _manifest(raw_asset_manifest, "runtime-assets-sha256.json")
    originals = _manifest(raw_original_manifest, "original-sha256.json")
    digest = _sha(config_original)
    _check(
        originals.get("runtime-config/server.properties") == digest,
        "archived server.properties does not match original-sha256.json",
    )
    _check(
        originals.get("runtime-assets-sha256.json") == _sha(raw_asset_manifest),
        "archived runtime assets manifest does not match original digest",
    )
    values = tuple(_asset_sha(assets, suffix) for suffix in _CRITICAL)
    _check(values[1] == digest, "runtime asset manifest server.properties mismatch")
    return digest, values


def compare_h9a_archived_generated_timestamp(
    *, a_config_original: bytes, a_runtime_assets_original: bytes,
    a_original_sha256_manifest: bytes, b_config_original: bytes,
    b_runtime_assets_original: bytes, b_original_sha256_manifest: bytes,
) -> H9aTimestampForensic:
    """STRICT forensic: exact bytes of every other line must agree.

    No generic comment deletion, reordering, normalization of escapes,
    whitespace, duplicate keys, line ending changes, or ignoring properties.
    """
    sha_a, assets_a = _check_arm(
        a_config_original, a_runtime_assets_original, a_original_sha256_manifest
    )
    sha_b, assets_b = _check_arm(
        b_config_original, b_runtime_assets_original, b_original_sha256_manifest
    )
    _check(sha_a != sha_b, "H9a observed raw-SHA mismatch absent")
    _check(
        all(assets_a[i] == assets_b[i] for i in (0, 2, 3)),
        "other critical Paper/plugin/config assets not identical",
    )
    a = a_config_original.splitlines(keepends=True)
    b = b_config_original.splitlines(keepends=True)
    _check(
        len(a) == len(b) and len(a) >= 3
        and a[0] == b[0] == _HEADER,
        "server.properties structure changed",
    )
    _check(
        _TIMESTAMP_LINE.fullmatch(a[1]) is not None
        and _TIMESTAMP_LINE.fullmatch(b[1]) is not None
        and a[1] != b[1],
        "second line is not only the changed generated timestamp",
    )
    diff = tuple(i for i, (left, right) in enumerate(zip(a, b), start=1) if left != right)
    _check(diff == (2,), "non-timestamp byte differences remain")
    _check(
        all(
            line.endswith(b"\n") and not line.startswith(b"#")
            for line in a[2:]
        ),
        "unexpected additional comments or newline variation",
    )
    return H9aTimestampForensic(
        raw_sha_a=sha_a, raw_sha_b=sha_b,
        raw_sha_different=True,
        byte_diff_line_numbers=diff,
        only_generated_timestamp_line_differs=True,
        other_critical_asset_sha_equal=True,
        independent_original_manifest_per_arm_checked=True,
    )
