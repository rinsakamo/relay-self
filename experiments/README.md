# Evolved-value experiments

This directory is an experimental simulation surface, not a supported `relay_self` package API or semantic authority.

All experiments preserve the causal separation relevant to RelaySelf:

```text
physical viability consequence
  != inherited intrinsic reward signal
  != evolutionary selection result
```

## Food / motor baseline

`evolved_values.py` is inspired by Yuji Kanagawa and Kenji Doya, *Evolution of Rewards for Food and Motor Action by Simulating Birth and Death* (ALIFE 2024, arXiv:2406.15016), and its Apache-2.0 reference implementation in `oist/emevo`.

Agents consume physical energy through basal metabolism and movement, gain physical energy from food, reproduce by transferring energy to offspring, inherit mutated food/movement reward coefficients, and learn an action policy during their lifetime using only those inherited intrinsic reward coefficients.

The model is deliberately smaller than the paper: it uses a one-dimensional toroidal world, nearest-food direction as the observation, tabular Q-learning, and standard-library Python rather than the paper's continuous 2D JAX/physics setup. A mismatch with the paper's qualitative evolved rewards is therefore evidence about this reduction, not a result to tune away silently.

Run:

```bash
python experiments/evolved_values.py --seed 1 --steps 5000
```

## Predator / sensor follow-up

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

Both experiments support `--json` for machine-readable output.
