# R #610 — B0 DEV originals / prospective Golden qualification (2026-10-15)

Authority: R #575 / Draft #610; S #537 / Draft #545; M #616/#617; V #619/#625. **No new World authorization.**

## Exact source identities

- S physical DEV HEAD: 291417539497f42269af9a15512cea320f375310
- S completed code HEAD: ec02b414d09fb0885eb481b1488f1a861ed73edb (post-run receipt correction; no rerun)
- R starting HEAD: 49592916c141bdcc58b373efeb7f3130351ed641
- RSEE Golden #588 HEAD: 34820f6bf391c77f325d7c29d3b779a33e3ca835
- DEV run ID: ed76bb71518a4bebbe5639e768c74a79; session: 0e177abe-88e3-498e-afc5-d850e789dc60
- DEV original root: /home/rinsa/work/relay-self-b0-development-20261015/attempt-01
- External readback: /home/rinsa/work/relay-self-b0-development-20261015/attempt-01-readback.json

The S owner reports 148 native frames (seq0–147), 17 L0 choices, 2 issued MOVE outcomes, rotten flesh inventory 0→1, one parent EAT with distinct equip/consume child IDs and source-side applied receipts, food13→17, parent-ID M0 single credit (E5→8.5), next native WAIT, shutdown_ack seq146 and connection_end seq147, Java/Node exit0 and cleanup. **These are not R-attested host original bytes until independently read.** This is a disposable DEV World, NOT an RSEE Golden clone. The old DEV receipt 0/0 S49 counters are deliberately not repaired: their external correction must remain separately traceable. An ACK original frame is not independently qualified shutdown or cleanup. Simulated M0 Energy is not Minecraft food.

## Host read-only audit

Run inside a clean detached checkout of the exact current R #610 HEAD, using the existing shared Python environment (PYTHONPATH=src:tests:.), with separate audit output storage. The default command reads no files.

    python -m experiments.standard_env.b0_dev_original_audit
    python -m experiments.standard_env.b0_dev_original_audit \
      --root /home/rinsa/work/relay-self-b0-development-20261015/attempt-01 \
      --readback /home/rinsa/work/relay-self-b0-development-20261015/attempt-01-readback.json

Expected original SHA256SUMS hash: d5446025952d9f4b34619a11a43c2d34cfb1cf5ce87b5e5ae40b262df88b30df. External readback expected SHA256: fd53e8fbe0bd372be9bec68269fd20d23b92f94fecb32c4e82632f0d81c9843e.

The source reader checks all 7 indexed file hashes, mandatory externally pinned originals, original-session native seq continuity, outbound STOP, inbound ACK/end, distinct equipped/consumed child effect receipts, two MOVE source probes, observed pickup and EAT inventory/food deltas, matching M0 parent Action ID and exactly one credited meal, next native WAIT, and DEV non-promotion. Positive status is RSEE_B0_DEV_ORIGINAL_BYTES_AND_SOURCE_SHAPED_EFFECTS_REVIEW_ONLY; never Golden engineering qualification. The legacy B0 ground2/two-meal reviewer and the V6 three-stream envelope are NOT substitutes. Do not write audit data inside the original root; independently capture pre/post file size/SHA/PID identity and output the R reviewer report/exit/checksums to a new R-owned evidence root. STOP original frame presence and process/PID/port cleanup must be qualified independently.

## Existing Golden RSEE preflight — without World launch

Reuse the existing RSEE original validators, including:

    BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
    python -m experiments.standard_env.golden_admission \
      --jar "$BASE/minecraft-1.21.8.jar" \
      --snapshot "$BASE/bootstrap-approved-20261011-once/snapshot" \
      --manifest "$BASE/bootstrap-approved-20261011-once/snapshot_manifest.json" \
      --initial-evidence "$BASE/bootstrap-approved-20261011-once/initial_native_observation.json"

Confirm 26 original Golden files, SHA256 JAR 2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7, manifest SHA256 5b1876db6a97fc8b9c4331938ca47727037c5626a241213d871b2073665996f8, initial native SHA256 7c974390d1879967ef5b5ce3b37d59a9628974c5f3e2a2dfefcf5e1e7701648b, Java21 / Node22+ / Mineflayer4.39.0 runtime imports and bridge hash, PID ownership, unused 25565 and protected existing Worlds. Verify original/clone physical separation; read Golden hashes before and after. A self-consistent new manifest is NOT an independent Golden qualification. Existing S49/S51 launcher/issuer MUST NOT be replicated inside R.

## Entry gate for a new QUALIFICATION run

A prospective run needs fresh and exclusively owned ID/root, exact S/R/Golden HEADs and latest push+PR CI, fixed JAR and Node/minecraft dependencies and Golden original/clone identity, owner-approved actions and server console operations, independently captured original native/commands/server streams, STOP/cleanup procedure, hard-fail terminal and failure preservation, and independent R assessment. S must demonstrate the existing NON-DEV S51 Golden route with correct World clone and source capture; R must pass specific missing connections to S owner rather than create a second launcher. DEV-only S51 cannot be relabeled to qualify. The earlier spent V6 grant must never be reused or the originals appended.

Synthetic negatives must reject false Golden/clone/JAR/manifest/dependency SHA, foreign/gapped native session, pickup-only credit, UNKNOWN EAT, double/foreign M0 Action, forged food and inventory, ACK omission, DEV→QUALIFIED and R→SCIENCE promotions, exhausted V6 grant and overwritten original evidence. Synthetic CI is not an R-host physical admission.

**PREWORLD_READY_NOT_AUTHORIZED** can be assigned only after independent host DEV readback and Golden/environment preflight and exact-head CI succeed. Otherwise retain PREWORLD_BLOCKED and list missing gates. This message does not permit World startup. V6 science 48 trials=0, G3/production NO_GO and historical consumed grants remain unchanged.

## 2026-10-15 fresh R qualification transaction

The user has separately authorized one new B0 engineering qualification World.
The authorization is consumed at the first Java Minecraft start, regardless of
result; preworld rejection leaves it unconsumed. No replay, DEV promotion, V6
grant reuse, science trial, or B1 inclusion is permitted. Source is frozen S B0
completion HEAD ec02b414d09fb0885eb481b1488f1a861ed73edb, despite subsequent S
branch development. Original Golden #588 remains unchanged.

R CI now executes full-regression and sibling-readonly on both push and Draft
PR events. Their existing test bodies and exact source pins remain unchanged.
A SKIPPED check is not a passed admission gate. Recheck remote R HEAD before
push and before any physical boundary; results belong only to their exact head.

The pinned original DEV receipt uses the historical STOP label
NOT_SEPARATELY_ATTESTED_BY_S49_REPORT. The reviewer accepts this only as an
unattested label, with a regression test preserving independent normal shutdown
qualification=false. It also accepts the corrected UNATTESTED spelling for
synthetic records; original hash anchors remain mandatory. The original receipt
and its zero counters are never rewritten.

Host evidence is stored outside all source/evidence roots at
/home/rinsa/work/relay-self-r-b0-qualification-evidence-20261015.
The first rejected review is retained alongside the corrected offline review.
Current PID absence and a successful bind establish current host state only;
they cannot retroactively attest the historical DEV shutdown.
