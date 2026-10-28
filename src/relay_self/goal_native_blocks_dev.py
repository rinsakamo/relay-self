"""Observer-local DEV SelfWorld present geometry, not long-term memory.

Exactly 6 loaded-client-cache columns (3 per lane), 2 vertical cells each.
Missing chunks are UNKNOWN, never clear; this has neither Action permission
nor general Minecraft terrain inference.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from relay_self.goal_navigation import GoalControlRejected
from relay_self.provenance import Provenance
from relay_self.self_world import WorldOrigin, WorldReading


@dataclass(frozen=True, slots=True)
class NativeLanePresentDev:
    side: str
    states: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            self.side not in ("LEFT", "RIGHT")
            or not isinstance(self.states, tuple)
            or len(self.states)!=3
            or any(v not in ("CLEAR", "BLOCKED", "UNKNOWN") for v in self.states)
        ):
            raise GoalControlRejected("incomplete bounded native lane geometry")

    @property
    def outcome(self) -> str:
        if "BLOCKED" in self.states:
            return "BLOCKED"
        if "UNKNOWN" in self.states:
            return "UNKNOWN"
        return "CLEAR"


@dataclass(frozen=True, slots=True)
class NativeRouteBlockPresentDev:
    """One correlated native cache snapshot for the current SelfWorld epoch."""

    session_id: str
    native_seq: int
    request_id: str
    origin_x: float
    origin_z: float
    player_y: float
    coverage: str
    lanes: tuple[NativeLanePresentDev, ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.session_id,str) or not self.session_id
            or type(self.native_seq) is not int or self.native_seq<1
            or not isinstance(self.request_id,str) or not self.request_id
            or len(self.request_id)>128
            or any(type(v) is not float or not math.isfinite(v)
                   for v in (self.origin_x,self.origin_z,self.player_y))
            or self.coverage!="loaded_client_cache_only"
            or not isinstance(self.lanes,tuple)
            or len(self.lanes)!=2
            or tuple(l.side for l in self.lanes)!=("LEFT","RIGHT")
            or self.provenance!=Provenance(
                "mineflayer",f"{self.session_id}:{self.native_seq}",
            )
        ):
            raise GoalControlRejected("foreign or unbounded native block Present")

    def observed_lane(self, side:str) -> WorldReading:
        if side not in ("LEFT","RIGHT"):
            raise GoalControlRejected("unknown source lane")
        lane=next(l for l in self.lanes if l.side==side)
        # The WorldReading is observer-local. SelfWorld's ordinary entity
        # schema is unchanged; this typed DEV extension cannot act on World.
        return WorldReading(
            origin=WorldOrigin.OBSERVED,value=lane.outcome,
            source_refs=(
                f"present:{self.session_id}:{self.native_seq}:{self.request_id}"
                f":route-blocks:{side}",
            ),
            source_provenance=(self.provenance,),
        )
