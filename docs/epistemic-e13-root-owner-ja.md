# Lane A E13 後継 — root→S23 オフライン実行器

Authority: #568 comment 6109417356。凍結E12
`e0cfa142612bae14d5db9435dbad5a31feb3a1fb` からの単一stacked後継。
RSEE #575 / #586 exact `cbf8c40d83e149ec438a9af024c5416cff4df0dc`
の明示的外部createRequire方式だけを参照し、全体cherry-pickは行わない。

## 実行器の契約

`experiments.epistemic_e13_root_owner.run_root_to_episode` は本番ライブラリ関数。
fixture、模擬OUTCOME、既成last_updateを読み込まない。

1. callerの現在Intent、初期risk_weight rev0/value3、S13 admission/bindingから
   S14 Skill1とAction1を提案し、独立authorize callbackと同一Supervisorで発行。
2. 注入sessionのS15通信→S16解釈／OUTCOME→LearningFeedback→
   明示LearningUpdateAuthorityによるgoverned retained rev1/value4。
3. 正確なcommit.new_stateを第二PLAN callbackへ渡し、同一オブジェクトであることと
   PRD／PLANの学習feedback、rule、authority、revision provenanceをS19/S20で検証。
   S14 Action2を提案・認可・発行し、独立sessionのS15/S16でOUTCOMEを取得。
4. 独立SkillGoalEvidenceとSkillTerminalAuthorityによるS21評価・FAILED。
   OUTCOME単独ではFAILEDもGoal成功も認定しない。
5. 独立SkillExitEvidence／AuthorityのS22評価・STARTED recovery Skill、
   新規S13 admission、S23 propose→独立authorize→Supervisor issue。
6. E12 run_issued_parent_action3によるS15/S16 Action3終端、その正確な所有権を
   E11 run_episode→S29 correlated probe→S24→Action4/WAITへ引き渡す。

`AdmissionInputs` はcallerが本番S12/S13/PRD/PLAN APIで構成する。
第二／回復callbackは新たな学習snapshotを作成できない。E11 callbackは観測認可、
cursor、Action4 binding／認可、別transportなどを返すが、Supervisor／Action3／
Intent／retained等のroot所有入力を置換できない。

各native frameのsessionと連続seqを入口で検証する。
3つのroot sessionは異なるID・同一declared config・adapter_started seq0を要求。
caller所有`used_root_sessions`は最初のowner遷移前に消費し、失敗後も再利用不可。
独立Action認可callbackの戻り値は元提案と同一Action lineageと完全な履歴prefixを
要求する。別Supervisorや再構築Actionの認可は代替できない。

これはAction所有権の実行器であり、Java、Node、LLMを自動起動するCLIではない。
実transportの寿命、Action1/2→Action3のavatar連続性、server/World原本、
各native sourceの独立認証と停止ACKはcaller／E12 ownerの責任。
注入されたtransportの自己申告をphysical authenticationへ昇格しない。
`RootReceipt.physically_authenticated` は常にfalse。
今後の実機callerは並行botを作らず、Action1/2のsourceを順次停止してから次を開く。
今回のテストはインメモリdoubleのみ。

## 共通環境

既存BASE `/home/rinsa/.local/share/relay-self/rsee-1.0-20261011` の
Python `venv/bin/python` と物理 `npm-mineflayer-4.39.0` を再利用する。
worktree venv/node_modules、pip/npm再インストール、symlink、NODE_PATH、NODE_OPTIONSは使わない。

`epistemic_e13_shared_runtime` は読取専用。共通Python3.12/prefix、pytest9.1.1、
httpx0.28.1の原本パス、interpreter SHA256、package/lockの原本一致、
Mineflayer4.39.0とminecraft-protocolのlocked version、entry/metadata実パス・SHA256、
jar SHA256 `2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7` を検証する。
外部moduleの実importは今回起動しないため、ファイル検証結果はimport実行証明ではない。

E12 OriginalWireSession／OneAvatarOriginalOwnerは新しい明示opt-in
`node_runtime_root=Path(...)` を受け取る。原本manifest検証後、child envの
`RELAYSELF_RSEE_NODE_RUNTIME_ROOT` だけでbridge接続を選択。
bridge自体もhash・realpath・versionを検査し、
`createRequire(NODE_ROOT/package.json)` とMineflayer入口をanchorとするtransitive
minecraft-protocol解決を要求する。未指定時の既存解決は維持。

オフライン検証コマンド（production PYTHONPATHにtestsを含めない）:

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  "$BASE/venv/bin/python" -m experiments.epistemic_e13_shared_runtime
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD:$PWD/tests" \
  "$BASE/venv/bin/python" -m pytest \
    tests/test_epistemic_e13_root_owner.py \
    tests/test_epistemic_e13_shared_runtime.py tests/test_epistemic_e12_native_owner.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD:$PWD/tests" \
  "$BASE/venv/bin/python" -m pytest
```

GitHub hosted CIは独立CPU runnerでoffline Python回帰とNode構文／protocol単体検証を行う。
WSL共通環境は変更しない。CIもJava、Minecraft bridge、LLM/GPUを起動しない。

## 不変な物理境界

`E13_PREWORLD_BLOCKED / PREWORLD_S23_OWNER_UNAVAILABLE` は過去の終端のまま。
この後継の資格化はOFFLINEのみ。実World Action1/2追加取引とAction3/4、
新規server/Node lifetimeには別の新しい実機許可が必要。
Minecraft/Node実機、Java、LLM/GPU、E5の36試行は今回すべて0／NOT_RUN。
旧receipt、RSEE製品・sealed Golden artifact、main、他Laneは変更しない。
