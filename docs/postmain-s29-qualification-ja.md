# RelaySelf S29 — request ID 付き明示観測の protocol correlation

## Authority / scope
- S28 Draft PR #364, exact frozen base `1485917e1ecef309c5d33bd50843baee19f7cfb2`.
- S18–S28 の frozen receipts / tests / MAIN40、RelayTheory R6 は改変しない。
- S29 では既存 Node bridge, Node protocol, Python protocol と
  `MineflayerProcessSession` に後方互換の **optional request_id** を追加する。

## Problem
S28 は one-shot cursor + session/seq により serialized observe/receive を
検証したが、既存 `observe` コマンド・`probe` 応答の双方に request ID がない。
よって「このプローブが今回の要求に返された」と protocol level で確定できなかった。

## Wire contract（S29）
旧：
```json
{"type":"observe"}
```
→ 従来の `observation(kind="probe")` は request_id を持たない。
新：
```json
{"type":"observe","request_id":"s29-probe:one.1"}
```
→ Node bridge は `observation(kind="probe", request_id="s29-probe:one.1")` を返す。

- 同一 ID を一つの Node bridge session で再使用すると command_error、
  観測 probe は生成しない。使用済み集合は in-memory。
- ID は ASCII 1〜128字、先頭英数字、残り `A-Z/a-z/0-9/._:-` のみ。
- request ID を受け付けるのは observe command と probe response のみ。
  別 event に request_id を持たせた payload は Python decoder で拒否。
- 古いコマンド/返信の exact shape は変更しない。
- Python `encode_observe(request_id=None)`、既存 `MineflayerObservation` の
  optional field、`MineflayerProcessSession.send_observe(request_id=None)` も
  旧呼び出し互換である。

## Correlated receiver
S29 `CorrelatedProbeGrant` が既存 S28 の scope authority と request ID を束ねる。
`request_correlated_post_action_probe` は：
- S23 Action3 exact supervised OUTCOME、WorldConsequence3 EXECUTED、
  after-probe seq4、同じ adapter_started session を検査。
- S28 と同様に1回だけ使える caller cursor を送信前に消費する。
- request ID とともに `send_observe(request_id)` を1回呼ぶ。
- `receive` した全 frame の session/seq を検査し、観測以外は fail-closed。
- 非probe観測 event の挿入は連続 seq なら認め、`probe` の
  `request_id == grant.request_id` を必須とする。
  request_id欠落、違うID、旧返信の再利用は拒否する。
- S27 source-native projection に渡し、typed S24 evidence を生成する。
- 別の caller が同セッションに対し2つ目の要求を行う場合、
  直前の exact receipt（seq/ID）から新 cursor を取得し、別 request ID を要求する。
- タイムアウト・send error・correlation mismatch は再試行しない。

## Deterministic tests
- JS `protocol.test.mjs`：旧/新 command parse、ID文法、reply payload、
  Node session 内 duplicate ID を検証。
- Python codec/process session：旧/新 observe の stdout/encode、legacy probe
  decoding、correlated request ID の保存、明示 null/invalid を拒否。
- S29 adapter double：`req1`（seq5; zombie 20cm → S24 MOVE_AWAY）、
  `req2`（seq6; zombie 180cm → S24 WAIT）を同一 session で区別。
- Seq が進んでも ID が違えば拒否する。旧 probe に ID がなければ拒否。
- Action/Skill/Intent/retained authority は変わらず、Action発行なし。

## Strongly bounded conclusions
```text
exact protocol request_id echo != independent physical sensor attestation
request_id correlation != cryptographic World truth or bridge process trust
in-memory used ID set != persistent distributed exactly-once
explicit observation != autonomous scheduler / cognition / Action
```

Node bridge が request ID を返すという **アプリケーション protocol 上の対応**
のみ資格化する。悪意ある/改ざんされた bridge は任意の ID と観測値を返せる。
実 Minecraft endpoint の genuine response、独立時計、World truth は対象外。
真正性を「暗号的」「物理的」とは呼ばない。

## Acceptance
`PROTOCOL_CORRELATED_MINEFLAYER_PROBE_ROUNDTRIP_QUALIFIED`
は exact S29 HEAD の repo contracts / pytest / Ruff /
Node Mineflayer adapter 全ジョブ成功の場合のみ採用。
Draft / unmerged 維持。

次の S30 候補は live bridge を *安全に短時間だけ* 起動した試験で
correlated request/response を独立に検証すること。
実 Minecraft サーバーのアクセス可能性、観測のソース真正性と
Skill 行動の資格化はそれぞれ分離して扱う。
