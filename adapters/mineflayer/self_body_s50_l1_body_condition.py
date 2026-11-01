"""MP6: source-authenticated experimenter physical body intervention.

This is a genuine Paper-world physical change, not a read-only annotation and
not an additional Self/S49 Action. It must be applied after frozen MP5 model
arm and before the sole original S49 native Action. No learning or retuning.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from adapters.mineflayer.self_body_s50_l1_paper_dispatch import ForecastDispatchRejected
from adapters.mineflayer.self_body_s50_l1_paper_local import check_local_paper_config

_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_MODE = "SLOWNESS_II"


def verify_condition_config(config: Path, config_sha: str) -> None:
    check_local_paper_config(config, config_sha)
    if not config.is_absolute() or config.is_symlink():
        raise ForecastDispatchRejected("MP6 pinned physical config path required")
    data = config.read_bytes()
    if hashlib.sha256(data).hexdigest() != config_sha:
        raise ForecastDispatchRejected("MP6 config bytes changed")
    lines = re.findall(
        r"^s50-changed-body-condition-dev:\s*([^#\r\n]+)", data.decode(), re.M,
    )
    if lines != ["true"]:
        raise ForecastDispatchRejected("MP6 real body intervention must be uniquely opted in")


def condition_command(marker: str, mode: str) -> str:
    if (
        type(marker) is not str or _TOKEN.fullmatch(marker) is None
        or mode != _MODE
    ):
        raise ForecastDispatchRejected("unknown or foreign MP6 condition")
    return f"relaydevcondition {marker} {_MODE}"


def attest_condition_original(
    original: bytes, *, marker: str, paper_world_uuid: str, subject_uuid: str,
) -> dict[str, str]:
    if type(original) is not bytes or len(original) > 8_000_000:
        raise ForecastDispatchRejected("MP6 original bounded Paper stdout required")
    if any(type(v) is not str or _TOKEN.fullmatch(v) is None
           for v in (marker, paper_world_uuid, subject_uuid)):
        raise ForecastDispatchRejected("foreign MP6 identity")
    matched = []
    for source in original.splitlines():
        if b"S50_DEV_BODY_CONDITION_APPLIED marker_id=" not in source:
            continue
        fields = dict(p.split("=", 1) for p in source.decode("utf-8").split()
                      if p.count("=") == 1)
        if fields.get("marker_id") == marker:
            matched.append(fields)
    if len(matched) != 1:
        raise ForecastDispatchRejected("MP6 missing or duplicate Paper-applied effect")
    row = matched[0]
    if any(row.get(k) != v for k, v in (
        ("world", paper_world_uuid), ("subject_uuid", subject_uuid),
        ("condition", _MODE), ("paper_effect", "SLOWNESS"),
        ("amplifier", "1"),
        ("status", "EXPERIMENTER_PHYSICAL_INTERVENTION_PRE_S49_ACTION"),
    )):
        raise ForecastDispatchRejected("MP6 wrong physical environment receipt")
    try:
        if int(row["effect_ticks"]) < 350 or int(row["before_action_world_tick"]) < 0:
            raise ValueError("insufficient physical effect")
    except (KeyError, ValueError) as exc:
        raise ForecastDispatchRejected("MP6 invalid physical receipt fields") from exc
    return row
