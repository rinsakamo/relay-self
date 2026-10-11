# RSEE 1.0 — Worktree-independent shared runtime (Node/Python) layout

Authority #537 / #575; stacked on #585 `c553ebb3e824dd9cbe61a470fe97408fdf4ebaf8`.
This is environment installation and **read-only host verification ONLY**,
not consent for Minecraft, llama-server, GPU, LLM POST or Golden Run.
Retain the failed #585 first terminal and audit SHA unchanged.

## Recommended WSL2 filesystem

```text
/home/rinsa/.local/share/relay-self/rsee-1.0-20261011/
├── venv/                    # existing shared Python 3.12 virtualenv, pytest/httpx
├── npm-mineflayer-4.39.0/   # new physical *directory*, outside ALL Git worktrees
│   ├── package.json         # byte-identical copy of current source adapter
│   ├── package-lock.json    # byte-identical copy of current source adapter
│   └── node_modules/        # genuine npm ci installation, no symlinks
├── minecraft-1.21.8.jar    # existing verified physical Mojang jar
└── bootstrap-approved-20261011-once/
    ├── snapshot/            # #583 stopped initial world, 26 bytes-sealed files
    ├── snapshot_manifest.json
    └── initial_native_observation.json

/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf
/home/rinsa/src/llama.cpp/build/bin/llama-server
/home/rinsa/work/<independent-Git-worktrees>
```

**Python:** Use the already installed dedicated venv at
`.../rsee-1.0-20261011/venv/bin/python`; interpreter and runtime prefix
are now included in preflight reports. Do not copy the venv into worktrees.
Install only from existing `requirements-host.lock.txt` if a genuinely
new interpreter environment is required. An existing working venv
and `pytest`/`httpx` imports need no repair.

**Node:** Physically install the pinned dependency tree **once** in
`npm-mineflayer-4.39.0`. Do not use `node_modules` symlinks,
`NODE_PATH`, `NODE_OPTIONS` shims, or implicit resolution from another
checkout. `bridge.mjs`, `protocol.mjs`, `bridge_hooks.mjs` remain
code owned by the exact Git worktree. During **RSEE-only** runs,
`RELAYSELF_RSEE_NODE_RUNTIME_ROOT` is supplied by the validated launcher,
and the bridge uses
`createRequire(<external-root>/package.json)`. Legacy sessions
without explicit RSEE runtime root keep their original worktree resolution.

**Model & llama-server:** Never copy the 7.38GB GGUF. Use the same
verified absolute path and recheck its exact SHA256
`c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`.
Keep the already built exact llama-server binary as-is (expected SHA256
`ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`).
Do not download a new Minecraft jar.

## One-time dependency provisioning, separate from #585 failed audit

Only in an isolated checkout of this child Draft after reading the exact
branch HEAD and verifying it has the same pinned
`adapters/mineflayer/package.json` and `package-lock.json`:

```bash
export PATH=/home/rinsa/.nvm/versions/node/v22.22.2/bin:$PATH
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
NODE_ROOT="$BASE/npm-mineflayer-4.39.0"

# Stop if NODE_ROOT already exists; never overwrite someone else's installation.
test ! -e "$NODE_ROOT" && test ! -L "$NODE_ROOT" || exit 2
mkdir -- "$NODE_ROOT" || exit 2
cp -- adapters/mineflayer/package.json "$NODE_ROOT/package.json"
cp -- adapters/mineflayer/package-lock.json "$NODE_ROOT/package-lock.json"
npm ci --prefix "$NODE_ROOT" --ignore-scripts --omit=dev \
  --no-audit --no-fund --fetch-retries=0
```

A failing installation stays an incomplete and unqualified directory;
do not delete/recreate, retry, or silently switch versions. The repository
does not install anything by itself. Do **not** install into #585's
stopped audit worktree or modify its terminal evidence.

## New host read-only validation from the child HEAD

Only when central npm installation is physically complete, use the *new*
child Draft, a new independent worktree and a new audit receipt ID:

```bash
export PATH=/home/rinsa/.nvm/versions/node/v22.22.2/bin:$PATH
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
NODE_ROOT="$BASE/npm-mineflayer-4.39.0"
"$BASE/venv/bin/python" -m experiments.standard_env.golden_host_gate \
  --expected-head <EXACT_CHILD_HEAD_FROM_GITHUB> \
  --node-runtime-root "$NODE_ROOT" \
  --new-output-dir "$BASE/golden-run-first-once" \
  --jar "$BASE/minecraft-1.21.8.jar" \
  --snapshot "$BASE/bootstrap-approved-20261011-once/snapshot" \
  --manifest "$BASE/bootstrap-approved-20261011-once/snapshot_manifest.json" \
  --initial-evidence "$BASE/bootstrap-approved-20261011-once/initial_native_observation.json" \
  --gguf /home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf \
  --llama-server /home/rinsa/src/llama.cpp/build/bin/llama-server
```

Checks: exact source adapter lock/package SHA match central npm copies,
Mineflayer version 4.39.0, real module paths inside central root and
transitive minecraft-protocol real import via original bridge-context probe;
Python's actual S49 closure (with pytest) and interpreter/venv identity;
#583 immutable native snapshot; model/binary/jar hashes and other
#585 read-only constraints.

Even `RSEE_GOLDEN_HOST_FILES_READY_NOT_AUTHORIZED` is **not** a
Golden Run permit. The product `--rsee-required`/direct
`--rsee-standard` now also requires
`--rsee-node-runtime-root <absolute-physical-npm-root>`.
Independently granted `--rsee-golden-run-once` remains mandatory
before any model/GPU/Minecraft physical process is started.

**Never promote a successful offline import into claims of live
/props/slots, Thinking OFF, GPU release or successful S49 Action.**
