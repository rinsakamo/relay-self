# 実Gemma H1→身体経験→H2 新規DEV試行

Base #685 `51ec50537ecaa88f27b98c1199f2c5e1bda88d17`。子branch `dev/l-cognitive-loop-world-20261102`。今回の明示missionと、現行#537の2026-10-14 DEV運用（新しい使い捨てrun）/2026-11-01認知発達方針を確認。旧#679/#684の消費済試行・FAIL原本を流用/変更しない。main/他レーン不変。

新規root `/home/rinsa/evidence/l-cognitive-loop-20261102T034000Z`。修正後clean exact HEADに実プローブとWorldを固定する。実モデル起動前に既存process/portsを確認、既存binary/GGUFだけを使用。実argv、binary/GGUF SHA、mmap、API/slot/template/GPUを保存する。

予算: synthetic Gemma HTTP1/retry0、PASS時だけ新World1/retry0、Mineflayer1、元S49 Action最大3、World Gemma OPEN最大2。L2 Actions/物理条件変更/learning admission/L0昇格0。GRASS/MOVE_BACKWARDを元ownerで実行し、H1受理→Action2→H1予測誤差→H2受理→Action3の順。固定草地のDEVでありB2/C成立は主張しない。

native strict json_schema/strict true/完全10フィールド、reasoning_effort none、enable_thinking false、temperature0、seed1、stream/cache_prompt false、max_tokens512を固定。プローブFAILならWorld起動なし。要求/応答/failed terminalsを原本保存。モデル設定の途中変更なし。

実行前監査でCLIのargparse.REMAINDERがaction以降のオプションを飲み込む不具合を確認。明示`--`より前だけoperator引数として解析し、後ろを原S49 argvとして渡す。プローブにexecution_headを記録しprepare/run双方で一致を要求。CLI prepare/runと別HEAD拒否の負対照を追加。元issuer/Executorは変更しない。

prepareは新規空W3 root作成とREADYのみ、runはSTARTEDをexclusive/fsyncしてから元ownerを1回spawn。実PPID/start_ticks/exe/cwd/argvで帰属し、終了後identityとportを照合する。失敗時もG3/live-prefix/feedback原本監査を独立processで行い、必須FAILを補足照合でPASS化しない。

Aは原本から有効H1/H2を再構成、B1は予測誤差と説明文の意味を個別評価、B2独立holdoutなし、C設計上未実施。DEV/QUALIFICATION/SCIENCEを分離する。
