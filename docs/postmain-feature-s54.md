# S54 — real Minecraft L0 Action while an L2 HTTP call is blocked

Authority: frozen S53 Draft PR #401 exact HEAD `a3eb88579d8bda89dcf8ae0e339934b3df1e50ff`. S54 is stacked Draft, no prior milestone changed.

**New physical experiment**: download official Minecraft Java 1.21.8, launch unmodified Mineflayer 4.39.0 and a localhost OpenAI-compatible **fake** responder that intentionally refuses to send an answer until L0 has completed a source-authorized physical MOVE_BACKWARD. The exact native session must observe far zombie → WAIT, then two distinct near zombies → two distinct Action OUTCOME. The first near action *must complete in the physical Minecraft World before the HTTP fake response is released*. Then a perfectly admissible late `MOVE_AWAY` model-like answer must be rejected by S48/S53 as stale. Native transport has a single foreground reader; issue and proposal rights remain independent explicit supervisor decisions, never inferred from fake model text. No restart/replay or unknown-state optimistic handling.

**Required real CI outputs**:
- `l0_completed_before_fake_http_response=true`
- `stale_l2_result_discarded=true`
- exactly one blocked **fake** localhost HTTP call, zero real model inference calls
- far WAIT with 0 Action; two source-identified near zombies; two separately terminal Action OUTCOME with real physical movement
- `backend_stop_ack=false` and `gpu_release_measured=false` (no actual model/GPU backend)
- log and JSON artifact, standalone exact-HEAD physical CI both push and PR if possible

Physical local GPU cancellation and genuine model inference are **not** qualified here. These remain owned by Issues #395/#396. The local actual-model gate must supply independently verifiable GGUF hash/model ID, caller authority, session lineage, World action outcome, L0 latency, model tokens, backend stop ACK (if claiming stop) and measured resource release (if claiming VRAM release). An asynchronous Thread/HTTP socket is not GPU preemption. Do not close #395/#396 or claim Self general agency.

Execute CI with `S54_REAL_SERVER_CI=1` and GitHub job `Post-MAIN S54 genuine one-session reactive L0 during blocked fake L2 HTTP`.