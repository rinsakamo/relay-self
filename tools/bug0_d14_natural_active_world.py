"""One-use natural Survival World with original S49 bounded action reactions.

No staging, health/hunger injection, teleport, L2, or world retry. Requires
the inherited R3 grant set PLUS a distinct physical R4 DEV grant.
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from tools.bug0_d14_natural_life import R4_GRANT, NaturalLifeLoop
from tools.bug0_d14_natural_world import R3_ENV, run


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("report", "server-log", "event-journal"):
        parser.add_argument("--" + name, required=True, type=Path)
    a = parser.parse_args()
    if os.environ.get(R4_GRANT) != "1" or any(
        os.environ.get(name) != "1" for name in R3_ENV
    ):
        raise SystemExit("distinct R4 + R3 one-World DEV grants required")
    raise SystemExit(asyncio.run(
        run(a.report, a.server_log, a.event_journal, life_factory=NaturalLifeLoop),
    ))


if __name__ == "__main__":
    main()
