# R2-3i Original World reJOIN DEV

R2-3i stacks on [R2-3h #1147](https://github.com/rinsakamo/relay-self/pull/1147) at
`194df9c64a6fd543993fc35a9d24566d4bb33583`. The
[Q #1146](https://github.com/rinsakamo/relay-self/pull/1146) CPU audit
covers the inherited Question-only GPU ticket. Its branch is outside this stack.

## Execution

Use the owned `experiments.p0d_real_resident_presence_dev` runner with
`--original-rejoin-dev --exploration-schema-dev --eula-accepted --real-world-dev-grant`,
explicit Java 21 and Node 22, expected Paper and recorder hashes, and an
existing scratch parent. It creates a fresh disposable server directory and
World using the B-NP1b launcher. For the optional Question, pass
`--grant-real-question-post --question-gguf --question-llama-pid
--question-model-alias --question-endpoint` with the verified local model pins.

The run starts with Original Physical in observation-only mode and retains
one Original Resident across A retirement, A reconnect, and B continuity.
The runner polls the owned Paper JOIN, QUIT and PRESENT stream, adopts the
correlated Native probes through the Original Bridge, and uses the
existing CPU Present and Inquiry path. The R2-3h seam freezes the
Question sourced from that CURRENT and uses the existing Question-only
inference lane for at most one raw HTTP POST. POST, source result, and
retirement are independently qualified. A terminal ADOPT remains a diagnostic
result. A source change after POST preserves the raw exchange and fences the
attempting Self.

Run the separate read-only auditor with
`python -m experiments.r2_3i_independent_audit_dev <owned-world>/evidence`.
It joins the frozen Native transcript, complete Paper log, tick ACKs,
Original source references, WAL and model records. The SHA-256 manifest
detects evidence changes relative to the captured inventory.

## First real trial

Trial HEAD `cc3596502a744990b3bcd4078244ba8d3afc0b56`. One disposable
Paper 1.21.8 build 60 World was attempted. The resident Paper PID was
`312396`, World UUID `ddcc63a2-9a48-41d1-a205-dd0c50295e03`, presence boot
`016270e3-7299-4009-8a51-f2840e2b8d4f`. Paper JOIN/PRESENT was observed for
both players. Initial Native evidence records A PID `312492` and
session `e22ae56f-6724-404a-8df0-394ae0b98315`, and B PID `312510` and
session `0114fb4b-4899-4dc5-8b6d-fc5b89b56d46`. Native A supplied two
correlated probes and B supplied one. Historical Original A Composite
qualification failed before the planned A-only logout.

The Paper stdout snapshots show JLine appending `> ` after a newline and
extending that same tail with carriage returns before the next record.
This can place the captured SHA-256 outside the full-line boundaries used by
B-NP1b history verification. The failed run recorded the outer refusal
without its inner cause. The follow-up uses headless Paper logging and
preserves exception chains. It also runs Original Bridge logout before
poisoning the shared Physical issuer on failure. The live effects of these
fixes require a separately authorized trial.

Both owned Native children exited, both Physical WALs were independently
verified empty, and Paper reported a successful save/stop with the main-thread
ACK at Paper tick 163. Original Owner retirement remained uncertain in this
trial because the shared issuer closed before Bridge logout.

Gemma preflight passed with llama-server PID `311791`, RTX 3060 and one idle
slot. The GGUF digest was
`c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`.
Gemma POST attempts were zero. The owned llama-server was stopped.
The independent partial audit verified the raw manifest, initial Paper and
Native streams, WAL and Paper stop. ReJOIN, B continuity through reJOIN,
Question result eligibility and full independent Source qualification are HOLD.

`R2_3_PRODUCT_L1_SWITCH_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`
