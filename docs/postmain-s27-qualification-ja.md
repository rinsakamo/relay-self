# RelaySelf S27 — Mineflayer source-native World evidence の bounded projection

## Authority / base
- S26 Draft PR #362 exact HEAD `33690ff475f4a040bd5b0d4821e3f0175d823bda`
- S18–S26 の frozen artifact と RelayTheory R6、Paper2 MAIN40 は変更しない。
- S15 Mineflayer bridge/protocol は既に `nearby_entities` と
  `nearby_entities_coverage`（registry / 16m / 最大16体）を提供している。
  Source API を新設せず既存事実を利用する。

## 問い
S24–S26 は「脅威との距離」を caller が構造化入力として与えた。
S27 では、既存 Mineflayer JSONL protocol の `observation(kind=probe)`
から **特定の entity ID / name に対応する snapshot 上の距離**を導出し、
その typed provenance を S24 の `PostFailureWorldEvidence` に直接渡す。

```text
MineflayerObservation != authenticated real Minecraft state
adapter-reported entity registry != complete World threat inventory
source-native typed fact != independently verified physical event
World evidence != cognition request != Action authority
```

## 既存 protocol に基づく入力境界
`src/relay_self/source_native_world.py` は新しい World/Action owner でなく、
1回限りの read-only projection `project_source_native_threat` を提供する。

- Action3 は現行 `ActionSupervisor` の terminal OUTCOME。
- 親 `WorldConsequence` は EXECUTED、
  `after_observation.kind == probe`、同じ session・既存 terminal provenance。
- 新 `MineflayerObservation` は `kind=probe`、親と同じ session、
  `seq > parent.after_observation.seq`。
- 既存 `MineflayerNearbyEntitiesCoverage` は source scope が registry、
  max distance 16m、max 16、truncated=false、
  candidate_count=実際のエンティティ件数を要求する。
- caller が特定した entity ID に **ちょうど1体**が対応し、
  name が `zombie` でなければ拒否する。
  対象が registry 内にいない場合は「遠い」「安全」と推定せず拒否。
- bot snapshot.position と entity.position の 3D Euclidean 距離を再計算。
  protocol の entity.distance と絶対誤差 1e-6 以内で一致し、
  距離は観測範囲内であることを要求。
- `observed_at_ns` は Action terminal より後、
  `inspected_at_ns` は観測以後かつ `max_age_ns` 以内。
  ※双方の時刻は caller が与えるため、source-native timestamp の
  真正性を証明するものではない。

出力は S24 の型 `PostFailureWorldEvidence` と監査用
`SourceNativeThreatReceipt`。距離は `floor(m*100+0.5)` で整数cm。
source provenance は `MineflayerObservation.provenance`
（`mineflayer:<session>:<seq>`）をそのまま保持し、親 Action3
consequence との lineage を維持する。

## 正例と反事実
既存 S23 Action3 → WorldConsequence3 → OUTCOME を2つの独立 fixture で実行。
新 `MineflayerObservation` に構造化 entity registry data を埋め、
親より大きい seq の別 probe で同一 entity ID `42` / `zombie` を観測。

- 0.20m / 20cm → S24 固定比較 WAIT8 vs MOVE_AWAY7 →
  **MOVE_AWAY / ADMITTED**
- 1.80m / 180cm → WAIT4 vs MOVE_AWAY7 →
  **WAIT / ADMITTED**

2ケースとも RetainedPreference rev1/v4、Current Intent、Skill3、
演算子、比較規則は不変。新しい Action は発行しない。
さらに JSONL 形の adapter_started(seq0) → before probe(seq1) →
dispatch(seq2) → cleanup(seq3) → after probe(seq4) →
新 probe(seq5) を既存 `MineflayerStreamDecoder` で復号し、
session/seq の連続性と重複拒否をテストする。

## Negative tests
- 古い/重複した observation.seq、別 session、probe 以外の kind
- 違う Action / WorldConsequence / missing terminal
- 不正な target ID、target absent、同じ ID が複数、name 変更
- nearby registry coverage が truncated または count 不一致
- 16m を越える観測、reported distance と position 距離の不一致
- 観測時刻の逆転・future・期限切れ
- JSONL decoder で重複 seq

## 非主張と未実装
今回の protocol message は **決定的 adapter fixture** であり、
実 Minecraft endpoint から採集した証拠ではない。
typed Python object は caller が合成できるし、
JSONL decoder の session/seq は物理的真正性も証明しない。
source-native という言葉は既存 bridge payload の shape/field の意味で
あり、Mineflayer bridge process の attestation でもない。

対象の `zombie` は caller が指定した既知 entity ID に限定する。
位置と距離の整合は対象への距離の正当性を保証する範囲内でのみ検査し、
他の脅威、名前不明、registry 収録外の threat を推論しない。
World の安全性や「敵がいない」は一切資格化しない。

新しい sensor listener、scheduler、エポック再入場、Action 発行、
LRN commit、グローバル replay ledger、永続 state はなし。
S26 までの Action1–4 の independent outcome closure は不変。

## Acceptance
`SOURCE_NATIVE_BOUNDED_MINEFLAYER_WORLD_EVIDENCE_PROJECTION_QUALIFIED`
は exact final HEAD の repo contracts、pytest、Ruff、
Mineflayer adapter CI が成功した場合に限る。PR は Draft / 未マージ。

S28 の候補は **新しい probe request と受信 sequencing を
実 adapter session の API に接続する**（物理真正性は別途）
または **source-native entity identity の寿命・respawn と stale 対応**
を独立した bounded gate として進める。
