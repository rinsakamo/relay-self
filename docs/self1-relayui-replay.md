# Self 1.0: observed World replay → RelayUI bridge (read-only)

Authority: [#537](https://github.com/rinsakamo/relay-self/issues/537) and the **third physical Golden Run** documented in [#588](https://github.com/rinsakamo/relay-self/pull/588#issuecomment-6108859052). This is the **first user-visible RelayUI-compatible output** in the Self repository. It is **not** a continuously operating Minecraft agent, an action dispatcher, or a standalone RelayUI product.

## What was physically demonstrated

Exactly one fixed S49 session at source HEAD
\`34820f6bf391c77f325d7c29d3b779a33e3ca835\`: 3 native
observations / L0 decisions, 1 WAIT, 2 MOVE_AWAY actions with physical
OUTCOME and ~0.627 m measured movement each, 2 retained *observed* Memory
episodes, and 1 L2 advisory response with \`EXPIRED_WORLD_ADVANCED\`.
All three HTTP identity endpoints passed; /props 22,858 bytes. The original
first terminal \`SELF_DEMO_RETURNED_SUCCESS_NOT_PHYSICAL_ATTESTATION\` / exit 0
does **not** independently certify all physical claims.

No live S10 preference update, S11 Habit grant, signed goal completion,
L2-generated Action or model STOP ACK was certified. No original HTTP wire
request/response for the L2 transaction was retained. Later offline
viewing cannot create missing evidence. The user reported a verified
69-file final SHA256 index:
\`57f0f55079943f8a9c714f166213917ca625ab5e143c4102a927fa4de7195fb0\`.
That index remains on the user's WSL2 host, **not** inside this GitHub PR.

## Generate a visual replay from already sealed evidence

In a checkout of this child Draft, with existing Python environment:

\`\`\`bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
EVIDENCE="$BASE/golden-third-20261011-authorized-once"

# Read-only qualification; no output file and no process launch.
"$BASE/venv/bin/python" -m adapters.mineflayer.self_replay_ui \
  --evidence-dir "$EVIDENCE" --dry-run

# Write exactly one NEW HTML file OUTSIDE the sealed evidence roots.
mkdir -p /home/rinsa/work/self-ui-replay
"$BASE/venv/bin/python" -m adapters.mineflayer.self_replay_ui \
  --evidence-dir "$EVIDENCE" \
  --output-file /home/rinsa/work/self-ui-replay/self-1-world-replay.html

# Open the generated HTML in a browser on your own host, no server needed.
\`\`\`

The CLI reads exactly the **existing** \`native_report.json\`,
\`self_trace.jsonl\`, \`observed_memory.json\`, and optional
\`live_l2.jsonl\`. Each must be a non-symlink regular source file at most
5 MiB; duplicate JSON keys, inconsistent session/epoch/trace or missing
native Action evidence are rejected before creating the output.

It delegates original source binding to
\`self_demo.project_native_report\` and retained snapshot regeneration to
\`self_demo.retain_native_observations\`. The stored trace must match this
projection exactly; loaded retained Memory must equal the projected native
snapshot. L2 sidecar must match the trace, carry zero Action/LRN/Habit
grants and correctly flag expired stale text. The page contains the
original input SHA256 digests, normalized native event timeline, current
read-only L2 status and explicit *unproven* learning, Habit and goal labels.

The result is a **self-contained, offline HTML** with no backend,
network call, websocket, external CSS/JS dependency, Minecraft or
model process. It cannot pause, resume, command, or change Minecraft.
No source is overwritten; its output destination must be new,
outside the evidence directory and have an existing physical parent.
Browsers render any model/source text with textContent (never innerHTML)
and escape dangerous JSON-script delimiters. Use this viewer as a
presentation/replay bridge, **not** as a new authority to assert genuine
World execution.

## Next integrated runtime increment (NOT implemented or authorized here)

The current S49 backend is a **fixed 3-decision test source** with
operator-staged zombie positions and two independently supervised
Actions. Do not relabel it autonomous open-ended gameplay.

1. In #537's product lane, make an explicitly bounded ongoing
   **one-session supervised gameplay owner** with pause/resume/stop,
   idle intervals, explicit per-session Action count, start/end, and
   local fail-closed recovery (NO automatic restart). Reuse
   \`NormalWorldL0\` and \`NormalSessionActionExecutor\` in place;
   do not reimplement L0 grants or grant L1/L2 Action authority.
2. Emit **append-only, source-tagged** event receipts from the real
   runtime (Present/epoch, L0/L1/L2 status, Action proposal/admission,
   ISSUE, OUTCOME, stale reasons, owner-local Memory revisions).
   Continue to distinguish issued Action from observed physical closure,
   observed Memory from governed learning, and L2 text from accepted
   Action authorization. Real event timestamps are allowed;
   do not fabricate unobserved decisions for a smooth UI animation.
3. RelayUI can consume the read-only event schema and display
   nodes/transitions next to the Minecraft window without controlling
   the actor. A control channel, if ever added, needs **its own**
   explicit Action/World authority and operator safety contract.
4. Keep A/B/C isolated: A owns counterfactuals, B retained graph/
   learning/Habit, C resource allocation. Neither this replay nor
   the continuous host may take those over or promote their
   unqualified scientific results.

No additional physical Golden, Minecraft, GPU, model or World action
has been authorized by the instruction to **continue code development**.
The three prior Golden grants were fully consumed. A new World session
requires its own explicit scoped permission and EULA applicability proof
before starting physical processes.
