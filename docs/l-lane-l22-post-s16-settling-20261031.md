# L22 — Post-S16 Settling & Goal Stability (independent DEV)

2026-10-31. Base: L21 real-run HEAD `477e045984e6eda3e91a33a8befe6443d988c8a3`.
This milestone adds an **offline source reviewer**, not a new executor or a physical claim.

## Boundary

`S16 OUTCOME` means the previously issued Action finished. It does **not**
prove that the Minecraft avatar, velocity, pending protocol updates or other
physics have settled. L21 Run2 demonstrates S7 move events at seq32 and seq34
after the original after-probe seq31, with Goal probes seq33/35. The two Goal
probe positions differ by ~0.032m, below the old 0.05m delta, *but move
events occurred inside that interval*. The L21 observer twice returned the
same quantized position; those samples were not synchronous with S7.

`inspect_l22_settling` checks the original S7 received/sent stream, source
receipt and saved L18 S16 row; requires a single session, action, set-control,
S15 clear ACK and two correlated Goal probes. Unknown post-S16 events, foreign
probes, unexpected effects, corrupted source bytes, and mismatched S16 fail
closed. An unsolicited `move` is retained as explicit settling evidence,
rather than silently ignored or promoted to stability.

State/labels:

- `SETTLING_OBSERVED`: native post-S16 move event or significant displacement.
- `STABILITY_UNPROVEN`: no qualifying move seen, but the stream has no
  independently attested continuous idle tick window.
- `geometric_goal_candidate` is the two-point spatial calculation, useful
  for diagnosis only.
- `accepted_goal_status=UNDETERMINED` in **all** L22 v1 cases.
  No L10 pairs, S10 updates, S11 grants, L0 promotions or claimed physical
  absence of intervention.

There is intentionally **no shortcut from two equal locations to physical
stability**. An event gap or an S7 time_of_day delta is not a tick-contiguous
idle attestation. This branch does not modify the L16 admission contract,
the L21 second-client source, the existing S49 executor, or any archived
L21 originals. Existing L16 may still reject a run that L22 can describe as
settling. These are distinct outcomes, not a bypass.

## Run2 expected offline result

- after seq31; Goal probes seq33/35; native moves seq32/34.
- state `SETTLING_OBSERVED`, reason `POST_S16_MOVE_EVENT`.
- geometric candidate `NOT_REACHED`, accepted Goal `UNDETERMINED`.
- independent L21 formal admission still fails because the original lacks
  the clean `closed` line. No retroactive seal or report repair.

## Next integration boundary (requires separate work)

1. Run an opt-in post-S16 **bounded settling observation window** in the
   original executor without issuing another movement Action. Observe actual
   move events and separately source-owned continuous World ticks including
   physical input idle / position. Any move resets the candidate stability
   window; unknown tick, disconnect, source mismatch or deadline yields
   `UNDETERMINED`.
2. Independently close/verify the L21 observer source before goal admission.
   Do not infer simultaneous S7/observer sampling from request ordering.
3. Only after an offline-owned stability contract is tested, wire an explicit
   DEV Goal readback. The independent learning authority/provenance gates
   of L13/L14/L20 remain separate.
4. A **new user grant** is required before any real Minecraft trial.

## Reproduction

```bash
PYTHONPATH=src:tests:. python3 -m pytest -o addopts='' -q \
  tests/test_l22_post_s16_settling.py \
  tests/test_l16_s49_first_action_original_capture.py
```

Classification: `DEV_ONLY / OFFLINE_SOURCE_REVIEW / REAL_WORLD_NEW_0 /
PHYSICAL_STABILITY_UNPROVEN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
