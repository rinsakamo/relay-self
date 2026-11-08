# D12 R2 — Long-run Self Experience bridge (DEV)

## Verified original World evidence

Parent: https://github.com/rinsakamo/relay-self/pull/803, exact source HEAD f81b6bdb5ee5494061173b1c7a8277efd4386455. This child integration branch starts at that verified source, NOT the consumed one-use R2 trigger HEAD ea288c43bfe031a9bf07a92a1d3fe0dd9e4d1934.

R2 real World run: https://github.com/rinsakamo/relay-self/actions/runs/42471117373
Original artifact: https://github.com/rinsakamo/relay-self/actions/runs/42471117373/artifacts/13613512334
Paper World UUID: d9176e84-afd4-412b-ae65-514d64803393; native session: 16baeebb-9260-4b2f-9f75-6946bb6331ff.

- Generation 1 vanilla rotten flesh: 2; original S51 Food 11→15.
- Generation 2 vanilla rotten flesh: 1; original S51 Food 11→15. D8 independent audit verified TWO distinct real food cycles. One original S49 ActionSupervisor retained ATTACK2 / MOVE3 / EAT2 = 7 total original S16 outcomes.
- Generation 2 Paper death at tick1201; generation 3 Paper spawn tick1801 = 600 World ticks, fresh native zombie ID35 and original Intent advanced to epoch3 with one-use second-EAT receipt consumed. Rearm issues zero new Action.
- Generation 3 ATTACK, pickup and EAT were NOT performed. No new model calls, retained Learning/Habit change, long-duration self-directed survival or Qualification/Science is claimed.

## Implementation boundary

The new tools/bug0_d12_experience_bridge.py calls the unchanged independent D12 auditor, which itself invokes the D8 original Paper/S50/native motion/nonmotion audit. When and only when it returns PASS_DEV, the bridge projects three source-bound event records:

1. OBSERVED_FOOD_CYCLE, generation1, actual zombie UUID, action IDs, native food/inventory before and after.
2. OBSERVED_FOOD_CYCLE, generation2, a new zombie UUID with its own Action IDs and native food/inventory.
3. OBSERVED_WORLD_RESPAWN_AND_INTENT_REARM, generation3; 600 World ticks, new Intent, no new physical action or meal.

Each event stores source World/session and does not contain a fabricated prediction, learned rule or causal generalization. All source file SHA256 are retained in a derivative projection manifest. If the parent auditor returns NOT_EXERCISED (e.g., genuine natural zero drop), the result has events=[] and is not falsely labeled two meals.

The bridge has NO S49 or World issuer, NO model call, NO Memory writer, NO LearningFeedback authority and NO L0/Habit installation. It is read-only historical evidence for a later cognition/retention path, NOT yet that actual path. Preserve original evidence and prior CI provenance.

## Local execution against the true R2 artifact

Download the original R2 GitHub Actions artifact and verify its SHA256SUMS.txt. Unpack into a fresh read-only directory R2/ with its actual five source files, then invoke:

    python -m tools.bug0_d12_experience_bridge \
      --report R2/report.json \
      --server-log R2/paper_original.log \
      --nonmotion-fence R2/original_nonmotion_fence.json \
      --motion-fence R2/original_motion_fence.json \
      --s50-sidecar R2/s50_native_direct_controls_original.jsonl \
      --out R2-derivatives/d12_experience_view_read_only.json

Replace R2/ with the actual selected artifact directory. The output uses exclusive file creation and checks original bytes for mutation during audit. Never add the derivative to the original frozen 8-file R2 manifest. Original R2 evidence may be downloaded/extracted in a separate directory if the original directory is read-only.

## Offline checks

    python -m pytest -q tests/test_d12_experience_bridge.py tests/test_d12_third_intent_rearm.py tests/test_d8_two_natural_food_post.py
    python -m ruff check tools/bug0_d12_experience_bridge.py tests/test_d12_experience_bridge.py
    python tools/check_repository.py

Bridge unit tests use explicitly synthetic values and a mocked D12 audit PASS to isolate the projection logic. This is NOT a substitute for the real D12 independent physical audit. Run the original D8 and D12 tests and real R2 artifact audit in addition.

## Subsequent development gates (not proven)

- D13: perform third genuine S49 ATTACK, natural item pickup if any, live STOP, actual S51 EAT within the SAME original World/owner, retaining all seven earlier physical Actions, their S16 terminals, and normal vanilla random drops. Do not tune for a chosen success/failure.
- Continuous experience capture: source-bound event stream across epochs with durable episodic readback and checkpoints, rather than always waiting until World shutdown.
- L2 integration: let L2 decide if and when to deliberate, from real source-qualified SelfWorld/SelfBody/Memory; do not force hypotheses, PROBE or new Skill. Learning changes require a separate owner and authority.
- Observe long-running disposable Worlds over meaningful bounded wall-clock time and real survival resource limits; neither one additional meal nor K3-H mock validates long-term adaptive learning.

Classification: DEV_ONLY / R2_HISTORICAL_PASS_DEV / LONG_RUN_LEARNING_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
