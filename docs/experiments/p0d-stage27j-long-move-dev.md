# Stage27j — original L1 MOVE, long-range 5m WALK→SNEAK (DEV ONLY)

Parent [Issue #951](https://github.com/rinsakamo/relay-self/issues/951);
stacked on [Stage27i Draft PR #990](https://github.com/rinsakamo/relay-self/pull/990).

## Purpose

Extend the **same original Self A MOVE Skill / one L1 numbered selection**
from Stage27i's one-shot 1.5m DEV run to a **5.0m east** operator DEMO target
using the existing source-bound L0 CPU closed-loop executor. This is a new
frozen operator-accepted Preset, **not** Self-learned parameters, autonomous
Skill success, Path Planning, or increased physical authority.

Stage27i demonstrated WALK / WALK / SNEAK and native final horizontal
0.027884m from its 1.5m target in one real World. The last SNEAK did not
have a Paper MOVE event, so its independent Action-level Paper correlation
remains UNATTESTED; QUIT-position equality is not Action causality.
**Do not add fine-grained Paper movement measurement in Stage27j.**

### Stage27j prebound accepted Preset

- ID `OperatorLongWalkSneakAt075`
- Original MOVE Skill, `EXPLORE_WORLD`, TargetContract destination
  **5.0m east from fresh source**; radius **0.15m**
- Each short native ACTION stays fixed **0.15s**; L0 selects **WALK** when
  source-bound horizontal distance >0.75m, **SNEAK** otherwise while outside
  the target radius
- Budget **12 Actions / 45,000ms / 6.0m cumulative displacement /
  1,024 native observations**; previous preissue **60 STOP probes per Action**
  and terminal-only unused-observation refund are unchanged
- The original L1 chooses only prebound MOVE+Target+Preset, ESCALATE_L2 or
  DEFER. Only an authorized *different* Preset may change parameters
- Source owner, ActionPort/PhysicalIssueAdmission, PREPARED-before-effect WAL,
  STOP, independent settled native probe, terminal WAL, B Intent/Skill/Memory/WAL
  before/after content hashes, and original real HTTP pre/post two-request
  census are reused without added observer instruments
- Stage27h authorizes >4 Actions **only when the original Self actually
  accepted the exact Stage27j Preset and all four budget values match**.
  Stage27i's 4-Action constraints remain unchanged
- **One new isolated World maximum** and `--stage27j-long-move` is mutually
  exclusive with `--stage27i-precision-gait`, Stage27h and older modes

## Real-world qualification boundary

Run `experiments/p0d_stage27_real_place_move_dev.py --stage27j-long-move`
with existing authorized EULA/real World DEV grant only **after** independent
LocalCodex preflight confirms CI exact HEAD, owned Paper/plugin/native Java/
Node binaries, real Gemma GGUF/llama.cpp PID/GPU/slot and frozen presets.

Use a **new** World; do not replay either historical Stage27h/Stage27i World.
B identity, memory comparison, HTTP sources, all STOP/ACK/WAL and final native
Target assessment remain mandatory. Paper independent event-based motion
correlation is retained as a coarse observation; it can be UNATTESTED without
being silently rewritten to success, and does not establish causal Action ID.

The committed checkpoint is prephysical until independently established
otherwise. If a child Action or STOP becomes unresolved, HOLD and never
automatically reissue. Final `L0_TARGET_REACHED_YIELD_EVALUATION` means
native Target **condition observed**, not a terminal Skill or Goal success.

## DEV test qualifications

- Source-shaped synthetic: single original Skill makes multiple short MOVE
  Actions and walks the last 0.75m in SNEAK, with unique Action IDs and
  fully settled original terminal WAL; no additional synthetic model calls.
- Adversarial: previous Stage27i policy cannot use Stage27j original Preset,
  stale native source cannot issue, mutually exclusive runtime mode flags,
  original Stage27h/27i budget stays bounded.
- Any real movement, long-range arrival, physically viable total runtime,
  genuine nonempty B retained Memory preservation, QUAL or SCIENCE is
  **NOT ATTESTED** by synthetic tests.
