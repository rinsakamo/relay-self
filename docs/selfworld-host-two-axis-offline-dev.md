# W4 SelfWorld host two-axis offline DEV

`W4_SELF_WORLD_HOST_TWO_AXIS_OFFLINE_DEV_RESULT`

`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`

事前登録: https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6365223951
監査基点: `09b35e49f6319ff64e4ed0f4e6e9e925dea1291b`（親 `3e2b04ef0877a1b272a7ee60a43e7e76c80b66bb`）。監査branchは175 focused、Ruff/contracts、原証拠照合後に非force pushし、remote exact SHAと3変更パスを再取得確認した。

## 読み取り契約

`experiments/self_world_host_two_axis.py` はDEV専用pure reader。`read_epoch` はcase/epochと期待receipt digestを受け、既存 `probe.load_sources` から毎回strict saved replayと元の4合成factoryを取得する。任意のreplayや未検証sourceを受理する入口はない。元のATT/PRD検証を再利用し、期待receipt不一致、foreign case/epoch、改変・stale・異Self・forged ATT/reviewはfail-closed。digestはhost記録の結合であり、外部attestation・World資格を意味しない。

Observationはsource verification status、positive_selected_count、肯定観測、provenance、原observation、ATT、coverage_truncated、source-bound digestを保持する。観測数0はWorld不存在・安全性を証明しない。Predictionはforecast_present_in_viewとprior_forecast_presentを独立に保持し、NO_REVIEW/MATCH/MISMATCH/UNDETERMINED、predicted/observed値、比較属性、完全review、prior forecast/source、source-bound review digestを保持する。

両digestは共通binding（receipt SHA、case/source class、epoch、Self/session/epoch identity）と当該軸の全内容をcanonical hashする。opaque identity/provenanceはhost custody専用。model向けprojectionは作らない。呼出側が結果を変更すればdigest再計算照合で不一致となる。readerは出力先・provider・engineを受け取らない。

## 10 epoch

| case | epoch | 肯定数 / label | review | view内forecast | prior forecast |
|---|---|---|---|---|---|
| w4-original-empty | prior | 0 | NO_REVIEW | false | false |
| w4-original-empty | following | 0 | NO_REVIEW | false | false |
| match | prior | 1 / zombie | NO_REVIEW | true | true |
| match | following | 1 / zombie | MATCH | false | true |
| mismatch | prior | 1 / zombie | NO_REVIEW | true | true |
| mismatch | following | 1 / skeleton | MISMATCH | false | true |
| unknown | prior | 1 / zombie | NO_REVIEW | true | true |
| unknown | following | 0 | UNDETERMINED | false | true |
| synthetic-empty | prior | 0 | NO_REVIEW | false | false |
| synthetic-empty | following | 0 | NO_REVIEW | false | false |

MISMATCH followingはskeletonの肯定的source evidenceを残し、別軸にentity_labelのzombie→skeleton不一致を残す。旧zombie予測への依存はこの比較から支持されないが、現在skeletonの検査可能性は消えない。単一INSPECT/DEFER判断は出力しない。
MATCHの支持は比較対象のentity_label属性に限定。UNDETERMINEDは対象/属性未観測による判定不能で、予測偽ではない。NO_REVIEWは当該epochにレビューがないことを表し、prior予測の存在と両立する。action_success/rewardは常にNoneでAction成否へ変換しない。

## 原結果と検証

保存100呼出・402 journal events・frozen request・reportを元監査器で読み取り照合し、先行audit.jsonの完全再現も確認した。元rubric **RAW 20/40 → SEM 36/40** は不変。二軸表は事後のLLM正答率・再採点ではない。

RSEE共有Python3.12.3で既存175件と新規11件をfocused検証。Ruffとrepository contractsを検証する。新規負対照はdigest、foreign identity、forged review/ATT、異Self、stale、forecast-as-observedの拒否、10 epoch、MISMATCH両立、両軸digestを検証する。既存focused群がstrict replay原本改変等の負対照を含む。

派生証拠は `/home/rinsa/work/w4-host-two-axis-offline-evidence-20261023` にexclusive-new保存。82保護対象・770歴史索引と索引自体、元SEM60ファイル・A/B・factorial・neutral・model-onlyを前後照合。監査worktreeと新規worktree双方で保護pathを確認する。初回archive再照合はtestsのPYTHONPATH不足で停止し、原本変更なく正しいpathで再実行した。新規テスト初回通過後Ruffのfixture名前衝突を修正した。失敗・検証ログは派生証拠へ保持する。

既存SelfWorld/RelayEngine/ATT/PRD/renderer/provider/model ownerは不変。CI/FULL/LLM/GPU/Minecraft/Action/OUTCOME/S10/Memory/SCIENCEは実施0。main、0.x、PR #634を更新しない。PR #634はDraft/open/unmerged、HEAD不変を読み戻す。

次にLLMへ委ね得る候補は、現在観測から何を検査するか、比較で支持されない旧仮説に依存せずどう説明するか、限定的支持と未観測をどう説明に反映するか。host事実の再判定は不要。新しい二問実験の設計・実行はここでは行わない。
