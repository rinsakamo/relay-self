# RelaySelf L-EU — Experience–Understanding Pair v0 (2026-11-03)

Status: **DEV_ONLY / ARCHIVED_SOURCE_REPLAY / NO_LEARNING_ADMISSION / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Rationale

A physical outcome and how Self interpreted it are different facts.

- **Experience (E)**: immutable reference to original World/Paper or original model-review bytes plus SHA256. The model did not create or certify this source. Factual summaries are not inferred causes.
- **Understanding (U)**: the model's actual historical claim, *including inaccurate or contradictory statements*. Preserve its original decision, rule, nullable speed, applicability, reason, and falsification text; cite one or more E and older U. Never overwrite a previous U.
- **PairLink (E↔U)**: source-bound assessment of an interpretation against an observation, with its own SHA256 and explicit provenance, not automatic truth.
- **EULedger**: immutable, bounded, content-addressed many-to-many graph. The same experience can have multiple competing understandings; an interpretation can cite multiple experiences; a new revision can branch from an old one.

This is a **shadow-only intermediate schema**. It does not replace S16/S17 source events, the existing PersistentCognition Memory owner, or S10 LearningPreferenceState and its explicit learning authority. Serialization to JSON does not imply the Self has learned or committed a memory.

## Actual archived Z2b→Z2c case

The source data comes from [real Z2b H1/Paper World PR #703](https://github.com/rinsakamo/relay-self/pull/703) and [real Z2c H2 attempt PR #714](https://github.com/rinsakamo/relay-self/pull/714). This branch starts no new World or model request.

| Record | Source and meaning | Status |
| --- | --- | --- |
| E_Z2B_PAPER_T37_T57 | Original Paper stdout SHA 1c20c9e7aa456cdf163edf56a3caab3eead2431febb3f40743896054730e4815; exact tick37→57, 1.4837801948120548m error | archived physical source replay |
| E_Z2C_REAL_H2_RESPONSE | H2 original HTTP SHA 66e47bcf99f72fea9e32ca49ad3dc806cd5794f56d6fbdb050a6c97b7ee51a78 | archived reply, NOT successful cognition |
| U_H1_GEMMA_STATIONARY | Original model selected STATIONARY, but original falsification text named CONSTANT_VELOCITY | unadmitted original model claim |
| U_H2_GEMMA_RAW_REINTERPRETATION | Original H2 decision ABSTAIN_PENDING_MORE_EVIDENCE + proposed TARGET_APPROACH + speed null | rejected semantic contract, unadmitted |

Three recorded source-linked relationships:

1. E1→U1: TESTED_BY / ORIGINAL_PREDICTION_MISMATCH, evaluated against original Paper outcome.
2. E1→U2: REVISES_ABOUT / PROPOSAL_NOT_ADMITTED, based on independent H2 original-contract readback.
3. E2→U2: CONTRADICTED_BY / NUMERIC_LIMITED_SEMANTIC_FAIL, based on **host semantic review** (explicitly NOT a second independent human or model reviewer).

In particular, the H2 contradiction is recorded **without correcting the model's original words**. Later U3/U4 can be added as new hypotheses, with their own sources and a parent reference to old U, without deleting failure history.

## Reproducible archived original export

From a clean checkout of this branch using Python3.12 and the existing test environment:

~~~bash
export PYTHONPATH=src:tests:.
python -m pytest -p no:cacheprovider -o addopts='' -q \
  tests/test_experience_understanding.py \
  tests/test_experience_bridge.py \
  tests/test_learning_qualification.py

python -m tools.l_eu_pair_z2c_original_replay \
  --repo "$PWD" \
  --output "/tmp/l-eu-pair-z2b-z2c-NEW-UNUSED.json"
~~~

The output path must not exist. Replay checks the archived Z2b 68-file original chain, its H1 response/model policy SHA and real Paper outcome; also Z2c original HTTP and the independent H2 raw readback. Only after all checks does it export **2 Experience / 2 Understanding / 3 PairLinks** in canonical, content-SHA-verified JSON. The separate CI produces a downloadable artifact of the generated ledger. It is a source-replayed index, NOT new physical evidence.

Negative tests reject duplicate/cyclic or forward revision lineage, missing/unattested source pointers, source SHA mismatch, corrupted/noncanonical durable bytes, incorrect link identity and attempted automatic Memory/S10/Habit/S49/SCIENCE authority. Read-only retrieval never turns rejected U2 into a learned L1 habit.

## Actual learning in later steps

The v0 ledger stores the *pairing needed for learning*, **not** a trained model or a demonstrated adaptive L1.

- **EU next epoch:** serve source-linked records as read-only context to real L2 and let the model author a new U3 candidate without copying a host-prewritten answer. Preserve that new original request/response and source SHA. Evaluate the new understanding against U1/U2.
- **Condition validation:** compare competing interpretations under independent situations, including an unknown placement and properly preregistered exact +20 tick World prediction. No need for one-shot superiority to cheap baselines.
- **Governed retention:** only after source owner qualification and explicit existing Memory/S10 authority should a learned candidate be retained or distilled to L1. Never infer L0 promotion from simply saving these records.

In this step: **new Gemma HTTP 0, new Minecraft World 0, new Action 0, learning commits 0, no L0 promotion**. Source replay is not contemporaneous JVM/GGUF identity attestation. Host semantic review is not independent semantic proof; the H2 numeric match alone also does not prove 2-axis Euclidean calculation. Maintain CLIENT_TICK_JOIN_UNATTESTED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
