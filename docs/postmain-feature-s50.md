# S50 SEEK physical step interface

An explicit ActionSupervisor-owned ISSUED Action and S45 fresh SeekStep may execute one bounded native yaw/forward/clear step; receipt chronology, before/after native geometry and progress classified PROGRESSED/ARRIVED/BLOCKED. It has no independent grant issuer, no pathfinding and does not itself close Action. If any effect or cleanup is ambiguous, caller must preserve UNKNOWN rather than replay. Real Minecraft path traversal has NOT been qualified. Refs #393.
