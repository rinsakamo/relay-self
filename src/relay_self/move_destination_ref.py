"""Stable configured MOVE target reference; never a physical grant."""
from __future__ import annotations

import hashlib
import json
import re

from adapters.mineflayer.python_protocol import MineflayerPosition
from relay_self.provenance import Provenance


class MoveDestinationRefusal(ValueError):
    """Configured destination ID/coordinates/provenance are not admissible."""


def move_destination_ref(
    destination_id: str, position: MineflayerPosition, provenance: Provenance,
) -> str:
    """Bind ID to *exact* config source and position (no native World claim)."""
    if (
        not isinstance(destination_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,89}", destination_id)
        or not isinstance(position, MineflayerPosition)
        or not isinstance(provenance, Provenance)
        or provenance.source in {"mineflayer", "paper"}
    ):
        raise MoveDestinationRefusal("qualified non-native configured destination required")
    body = (
        destination_id, provenance.source, provenance.reference,
        float(position.x).hex(), float(position.y).hex(),
        float(position.z).hex(),
    )
    digest = hashlib.sha256(
        json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"destination:{destination_id}@{digest}"
