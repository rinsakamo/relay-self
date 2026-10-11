# RSEE 1.0 — Golden Run exact-world admission (offline qualification)

Base: [Draft #583](https://github.com/rinsakamo/relay-self/pull/583)
HEAD `ca4afee5c78102ed3f917ea6011b6bef124d98e3`.
Primary owner #537; standard env #575. No previous Draft/owner modified.

## Fixed native source

Only the snapshot independently audited on 2026-10-11 is admissible
for the first RSEE Golden Run. The #583 original authorized *bootstrap*
finished and its one-time World/EULA grant **was consumed**.

- Minecraft: 1.21.8, exact jar SHA256
  `2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7`
- Seed: 575, original stopped World `s31a-ephemeral`
- Native readback: spawn seq1 → probe seq2, original initial player
  position `(-6.5,-60,10.5)`, health=20, food=20; stopped player yaw/pitch 0/0
- Snapshot: 26 regular files, same SHA256 as original stopped World
- Snapshot manifest SHA256:
  `5b1876db6a97fc8b9c4331938ca47727037c5626a241213d871b2073665996f8`
- Initial native observation SHA256:
  `7c974390d1879967ef5b5ce3b37d59a9628974c5f3e2a2dfefcf5e1e7701648b`

#583 recorded independent prismarine-nbt readback; raw bridge shutdown ACK
was not retained. Do **not** claim GPU STOP ACK, Model Thinking OFF
semantics, later Minecraft action/outcome success, or snapshot identical
dynamic behavior from this historical qualification.

## Offline deterministic verification

Run inside exact child HEAD after dependencies and source identity are checked:

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
"$BASE/venv/bin/python" -m experiments.standard_env.golden_admission \
  --jar "$BASE/minecraft-1.21.8.jar" \
  --snapshot "$BASE/bootstrap-approved-20261011-once/snapshot" \
  --manifest "$BASE/bootstrap-approved-20261011-once/snapshot_manifest.json" \
  --initial-evidence "$BASE/bootstrap-approved-20261011-once/initial_native_observation.json"
```

This inspects existing files ONLY; **no Java/Node/llama/GPU/process** is started.
Read the `classification` field, not just exit 0. Even
`GOLDEN_WORLD_BYTES_PINNED_OFFLINE` means only byte admission, not
authorization to execute Golden Run.

## New Golden Run authorization is independent

The RSEE owned product CLI now requires a new **`--rsee-golden-run-once`**
flag in addition to exact world files, `--rsee-eula-accepted`,
original `--confirm` and RSEE constraints. Without it the request
is **BLOCKED before llama-server/GGUF/Java/Node**, even with a valid
snapshot and earlier World-bootstrap permission. Non-RSEE behavior is
unchanged. The direct `self_demo --rsee-standard` entry point also requires it.

**Do not supply that flag until the operator explicitly grants an
independent, one-shot model/GPU+L2 and disposable World/S49 Action run.**
This Draft and this runbook do not grant permission.

Other remaining *physical qualification* limits:
- Owned llama.cpp `/props` and `/slots` are checked AFTER model start;
  exact compiled binary schema/alias/slot metadata remain unproven on host.
- RSEE request includes `reasoning_effort=none` and `cache_prompt=false`.
  Actual Thinking OFF handling and returned non-empty `content` remain
  subject to an independently authorized runtime observation.
- Current live L2 is one short **read-only commentary** (`max_tokens=96`),
  not a proven strict JSON-schema generation path. Do not claim a
  full structured Self-output qualification based on this mechanism.
- Initial snapshot qualification does not prove the future World action/
  outcome closure, cleanup/VRAM release, or model response acceptance.

On future explicit grant, use exactly one fresh output folder and one
run. Do not auto-restart, retry LLM POST, switch World snapshot, or
carry forward the previous bootstrap permission. Preserve the first
terminal and owned cleanup receipts on error. No changes to frozen
S49 Action authority or Lane A/B/C.
