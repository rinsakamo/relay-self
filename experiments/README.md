# Experiments

This directory is an experimental simulation surface, not a supported `relay_self` package API or semantic authority.

## Evolved-value experiments

The evolved-value experiments preserve the causal separation relevant to RelaySelf:

```text
physical viability consequence
  != inherited intrinsic reward signal
  != evolutionary selection result
```

### Food / motor baseline

`evolved_values.py` is inspired by Yuji Kanagawa and Kenji Doya, *Evolution of Rewards for Food and Motor Action by Simulating Birth and Death* (ALIFE 2024, arXiv:2406.15016), and its Apache-2.0 reference implementation in `oist/emevo`.

Agents consume physical energy through basal metabolism and movement, gain physical energy from food, reproduce by transferring energy to offspring, inherit mutated food/movement reward coefficients, and learn an action policy during their lifetime using only those inherited intrinsic reward coefficients.

The model is deliberately smaller than the paper: it uses a one-dimensional toroidal world, nearest-food direction as the observation, tabular Q-learning, and standard-library Python rather than the paper's continuous 2D JAX/physics setup. A mismatch with the paper's qualitative evolved rewards is therefore evidence about this reduction, not a result to tune away silently.

Run:

```bash
python experiments/evolved_values.py --seed 1 --steps 5000
```

### Predator / sensor follow-up

`predator_values.py` is inspired by Kanagawa and Doya, *Evolution of Fear and Social Rewards in Prey-Predator Relationship* (arXiv:2507.09992), and the upstream `oist/emevo` predator experiment.

The reduced simulation adds active chasing predators plus inherited linear reward weights for food, movement, conspecific proximity, and predator proximity. Physical predation remains a World/body consequence; the predator-sensor coefficient is only an intrinsic learning signal whose evolutionary distribution can be measured later.

The reduced predator implementation intentionally does **not** claim full prey-predator co-evolution, fear semantics, social-emotion semantics, or reproduction of the paper's reported distributions. It uses fixed predator controllers, one-dimensional local sensing, and tabular learning so that the causal mechanism remains easy to inspect.

Run the default active-predator condition:

```bash
python experiments/predator_values.py --seed 1 --steps 5000
```

Run the no-predator control:

```bash
python experiments/predator_values.py --seed 1 --steps 5000 --predators 0
```

A stationary-predator ablation is also available:

```bash
python experiments/predator_values.py --seed 1 --steps 5000 --stationary-predators
```

Both evolved-value experiments support `--json` for machine-readable output.

## Adaptive mechanism-selection probe

`adaptive_mechanisms.py` is a synthetic, non-biological probe for Issue #60. It compares four paired conditions over the exact same seeded task sequence:

```text
cheap_only
expensive_only
fixed_switch
adaptive
```

The task has repeated contexts, observable uncertainty, explicit synthetic computation cost, deadlines, and a hidden regime shift. Three experiment-local mechanisms have deliberately different latency / information / cost profiles:

```text
FAST    cheap reuse or a brittle default
MEDIUM  moderate-cost use of a noisy regime signal
SLOW    expensive direct inspection of the correct action
```

A successful `SLOW` solve can populate a transparent per-context cache later reused by `FAST`. A failed cached response invalidates that entry, allowing the adaptive condition to re-escalate after distribution shift. The cache is only an experiment-local stand-in for amortization; it is not a RelaySelf Skill registry, Cognitive Frontier, Thinking Level, or supported runtime API.

Run the default 20-seed paired comparison:

```bash
python experiments/adaptive_mechanisms.py --seeds 20
```

Increase selector overhead as a metacontrol-cost ablation:

```bash
python experiments/adaptive_mechanisms.py --seeds 20 --selector-cost 10
```

Machine-readable output is available with `--json`; add `--trace` to include per-episode decision records.

Simulation results from this harness are evidence only for the recorded configuration and seeds. Do not promote a favorable comparison into RelaySelf semantic authority without the normal evaluation and Grand Null process.

## Mineflayer viability-relay fixture

`mineflayer_viability_relay.py` is a deterministic, simulation-only fixture for #46. It is grounded in `PrismarineJS/mineflayer` revision `91204b2a034f0663b39814771e236bcb7c8f26c8` but does not import Mineflayer or require a Minecraft server.

The fixture preserves Mineflayer-like body facts and events separately from a minimal signed health gradient:

```text
Mineflayer observation / event
  != health-gradient sample
  != belief / appraisal
  != action
```

The first gradient is intentionally only:

```text
current bot.health - previous bot.health
```

No extra penalty is attached to `death`, and `respawn` remains an independent observation event. As a result, the built-in death/respawn trace deliberately produces a positive health delta after respawn, which keeps Minecraft recovery semantics available for later cognition experiments instead of hard-coding human death aversion.

Emit both A/B payloads:

```bash
python experiments/mineflayer_viability_relay.py --condition both
```

Or emit one condition:

```bash
python experiments/mineflayer_viability_relay.py --condition observations
python experiments/mineflayer_viability_relay.py --condition gradient
```

This fixture does not demonstrate useful Minecraft cognition by itself. Its output is a bounded input surface for a later controlled cognitive-consumer comparison.

## Mineflayer cognition A/B probe

`mineflayer_cognition_ab.py` turns the merged viability fixture into four matched cognition conditions. The original semantic A/B pair preserves Mineflayer field/event names; a second A/B pair deterministically aliases those names so the value signal can be tested with less pretrained Minecraft/human semantic leakage.

```text
observationsOnly
withHealthGradient
neutralObservationsOnly
neutralWithGradient
```

All four conditions use the same task, candidate plans, observation values, model id, temperature, output instruction, and generic signed-signal semantics. Within each semantic-label pair, the model-visible treatment difference is only whether the history rows contain the derived gradient/signal values.

The task asks the model to reach one target efficiently and choose one of three geometry-only plan ids:

```text
direct
detour
observe
```

The candidate descriptions contain coordinates only; they are not labeled with affective or safety semantics. The primary output is therefore a behavior choice (`plan_id`), not an emotion word.

The neutral history uses fixed experiment-local aliases such as `resource_0`, `event_1`, and `signal_0`. It removes Mineflayer/Minecraft and health/death/hurt labels from the history while preserving values, event/source association, and timing. This is an evaluation control only; it is not an adapter or runtime schema proposal.

Render deterministic requests without network access:

```bash
python experiments/mineflayer_cognition_ab.py --model MODEL_ID
```

Run repeated calls against an OpenAI-compatible endpoint:

```bash
python experiments/mineflayer_cognition_ab.py \
  --model MODEL_ID \
  --endpoint http://127.0.0.1:1234/v1/chat/completions \
  --repeats 10 \
  --run
```

If the endpoint requires a key, the script reads `OPENAI_API_KEY` by default; `--api-key-env` can name another environment variable. Condition order reverses across trials, request hashes are recorded, malformed or out-of-set model outputs are preserved as failures rather than silently repaired, and run output reports per-condition plan counts plus separate semantic-gradient, neutral-gradient, and semantic-prior detour-rate differences.

The gradient remains mathematically derivable from the original health observations. A measured effect therefore demonstrates representational/evaluative salience, not additional World information. Model-run results are model/system-quality evidence only; they do not establish a Value/Emotion/Fear owner, and a null result does not justify strengthening the gradient merely to force an effect.


## Mineflayer cognition physical qualification

The canonical local physical entrypoint for the pinned #46 llama.cpp qualification is the no-bytecode launcher:

```bash
EVIDENCE=/tmp/relay-self-mineflayer-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_mineflayer_cognition_llama_cpp_transaction.sh \
  --evidence-root "$EVIDENCE"
```

The launcher executes the existing transaction as:

```text
python3 -B -m experiments.mineflayer_cognition_llama_cpp_transaction
```

The `-B` flag is part of the physical launcher contract. It prevents Python import bytecode from creating checkout-local `__pycache__` / `.pyc` files before the transaction's clean-check precondition runs. The clean-check itself is intentionally not weakened, generated files are not hidden through `.gitignore`, and the launcher does not delete or reset operator files.

For physical qualification, direct `python -m experiments.mineflayer_cognition_llama_cpp_transaction` invocation is non-canonical because ordinary Python bytecode caching can dirty a fresh checkout before preflight. The launcher changes no llama.cpp, GGUF, attestation, request, condition, repeat, retry, or evidence semantics; it only supplies the import environment required by the existing clean-check contract.
