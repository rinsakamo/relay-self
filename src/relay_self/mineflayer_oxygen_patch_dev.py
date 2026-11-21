"""Stage24d backport detector for exact locked Mineflayer 4.39.0.

Only source verification. The version in package.json alone does NOT
attest that upstream PR #4052's self-owner guard is installed.
"""
from __future__ import annotations

from pathlib import Path

OWNERLESS = (
    "// Breathing (formerly in breath.js)\n"
    "      if (metas.air_supply != null) {\n"
    "        bot.oxygenLevel = Math.round(metas.air_supply / 15)\n"
    "        bot.emit('breath')\n"
    "      }"
)
SELF_OWNED = OWNERLESS.replace(
    "metas.air_supply != null) {",
    "metas.air_supply != null && entity.id === bot.entity?.id) {",
)


class MineflayerOxygenPatchRefusal(RuntimeError):
    """Unpatched or unexpected vendor package cannot qualify oxygen source."""


def require_owned_mineflayer_oxygen_patch(bridge: Path) -> str:
    """Validate the exact backport in the same worktree as the Paper runner.

    No auto-patching; an operator must run the narrow reviewed Node patch
    explicitly after npm ci. No unstated trust in external NODE_PATH.
    """
    source = bridge / "node_modules" / "mineflayer" / "lib" / "plugins" / "entities.js"
    if source.is_symlink() or not source.is_file():
        raise MineflayerOxygenPatchRefusal(
            "locked Mineflayer entities.js owner patch missing"
        )
    try:
        content = source.read_text(encoding="utf-8")
    except (UnicodeError, OSError) as exc:
        raise MineflayerOxygenPatchRefusal(
            "Mineflayer entities.js is unreadable"
        ) from exc
    if content.count(SELF_OWNED) != 1 or OWNERLESS in content:
        raise MineflayerOxygenPatchRefusal(
            "Mineflayer 4.39.0 self-owned air_supply backport not verified; "
            "node adapters/mineflayer/oxygen_owner_patch.mjs --apply"
        )
    return "mineflayer-4.39.0+upstream-4052-self-owner-guard"
