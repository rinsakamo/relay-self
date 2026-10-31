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
4. The user supplied `L_LANE_REAL_WORLD_DEV_GRANT=APPROVED_STANDING` on
   2026-10-31, valid until revoked for disposable L Lane DEV Worlds.
   Per-World reapproval is not required. Models and other lanes are excluded.

## Reproduction

```bash
PYTHONPATH=src:tests:. python3 -m pytest -o addopts='' -q \
  tests/test_l22_post_s16_settling.py \
  tests/test_l16_s49_first_action_original_capture.py
```

Classification: `DEV_ONLY / OFFLINE_SOURCE_REVIEW / REAL_WORLD_NEW_0 /
PHYSICAL_STABILITY_UNPROVEN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## L22 opt-in runtime wiring (offline implementation only)

S49 now accepts `--l22-settling-probes N` (integer 3..8). It is valid
**only** with an explicit fresh L16 original capture root and fixed Goal plan.
The preflight rejects invalid combinations before Java starts. With the flag
absent, the previous L16/L21 control flow remains unchanged.

After genuine first S16 OUTCOME and S15 clear, the **same original
MineflayerProcessSession** (single S7 raw recorder/decoder) sends
`l22:<session>:<action>:settle-N` correlated observe requests, with a
0.1-second host delay per request and an absolute 5-second request deadline.
A transient `move` event or spatial delta over the predeclared 0.05m
resets the quiet-probe streak. The sampler exits after three consecutive
quiet probes or the specified maximum. This is **not a Minecraft tick
counter**, input-idle attestation, stop proof, or second Action issuer.

S49 next obtains its two ordinary L16 Goal probes for diagnostics, closes
the L21 observer before auditing, seals the native S7 original, and runs the
L22 source audit. The L22 audit permits exactly 0..8 bound settling
requests followed by exactly two native Goal requests, rejects extraneous
probe/motor/unknown events, and checks runtime sample seq against the sealed
original. Its status is `SETTLING_OBSERVED` or `STABILITY_UNPROVEN`;
its accepted Goal remains `UNDETERMINED` even if both clients'
geometric candidates agree.

When this additional bounded pre-Goal probe prefix is enabled, strict L16
two-Goal-only formal admission is **not invoked**: the report explicitly
records `L16_NOT_RUN_L22_EXTRA_PROBES`. L16's verifier and all historical
admission decisions remain unchanged. The L21 reviewer can still verify a
fresh complete second-client original, with native comparison status
`UNDETERMINED` and no reward authority. S49 may independently verify its
preexisting movement Action sequence; this is not an L22/Goal qualification.

Command extension on a disposable L Lane DEV World under the standing grant:

```text
# Add to the previously preregistered L21 disposable S49 command:
--l22-settling-probes 6
```

The new pure Python fake-stream tests exercise quiet streak, repeated move
reset, drift, invalid requests and pre-Java blocking; the sealed L21 Run2
remains unchanged and is still a negative control. An artificial S7 prefix
with additional probe frames tests L22 ordering and hash-based source
checks. Live World tick/Paper-owned input idle is not supplied by this
Minecraft vanilla S7 extension. **Physical stability/learning qualification
requires a different, source-owned tick-contiguous boundary** in later work.


## Fresh physical integration preparation (2026-10-31)

The S16 writer and auditor share `S16_FILE`; the actual original path is
`<capture_root>/l18_s16_terminal_original.jsonl`. L22 keeps the legacy L16
strict branch separate. Observer close precedes source audit; failure enters
owned-process cleanup and seals the incomplete S7 source in `finally`.
The runtime now compares the first sample against the actual S16 after-probe,
records each quiet streak and displacement, and records budget exhaustion.
The opt-in L22 flow ends after WAIT + one MOVE rather than staging a second
MOVE. The non-opt-in S49 two-MOVE contract stays unchanged.

The L20 geometry is operator-authored and precommitted before the World; it
is not an authenticated independent Goal owner. Continuous physical idle,
Goal admission, L10, S10 and S11 remain outside these diagnostic samples.
