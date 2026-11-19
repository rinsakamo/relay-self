"""D8 source-pinned Paper assets: unchanged strict Stage24g hash policy.

Standalone import surface avoids importing the old B-only real L1/MOVE
launcher, which is not authorized for D's observation-only Source run.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from experiments.p0d_real_paper_smoke_dev import (
    PAPER_1218_60_SHA256,
    file_sha256,
    prepare_assets,
)

PINNED_STAGE24G_PLUGIN_SHA256 = (
    "0b20dd042231618fc301bbe26ee48c5808c09dafddc946c49f4393ca48386fb5"
)


class D8PinnedAssetHold(RuntimeError):
    """Paper / plugin identity is not the original permitted binary."""


@dataclass(frozen=True, slots=True)
class D8PinnedAssets:
    paper_jar: Path
    plugin_jar: Path
    scratch_parent: Path
    paper_sha256: str
    plugin_sha256: str
    world_created: bool = False
    gpu_used: bool = False
    physical_action_issued: bool = False


def check_d8_pinned_assets(
    *, paper_jar: Path, plugin_jar: Path,
    scratch_parent: Path, accepted_eula: bool,
) -> D8PinnedAssets:
    if accepted_eula is not True:
        raise D8PinnedAssetHold("Minecraft EULA consent required")
    for p in (paper_jar, plugin_jar):
        if (
            not isinstance(p, Path) or p.is_symlink()
            or not p.is_file() or p.suffix != ".jar"
        ):
            raise D8PinnedAssetHold("original pinned jar required")
    expected = (PAPER_1218_60_SHA256, PINNED_STAGE24G_PLUGIN_SHA256)
    if any(re.fullmatch(r"[0-9a-f]{64}", x) is None for x in expected):
        raise D8PinnedAssetHold("bad immutable pinned source")
    digests = (file_sha256(paper_jar), file_sha256(plugin_jar))
    if digests != expected:
        raise D8PinnedAssetHold("unattested Paper/plugin jar SHA256")
    paper, plugin, scratch = prepare_assets(
        paper_jar=paper_jar, paper_sha256=digests[0],
        plugin_jar=plugin_jar, plugin_sha256=digests[1],
        scratch_parent=scratch_parent, accepted_eula=True,
    )
    return D8PinnedAssets(paper, plugin, scratch, *digests)
