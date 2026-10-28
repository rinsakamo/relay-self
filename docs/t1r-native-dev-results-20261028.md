# T1r 実Minecraft DEV結果（2026-10-28）

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

T1r固有判定 **PASS**。新規World 1実行、1 PASS / 0 FAIL。同一World・Self/sessionの両epochで、自然な0.2秒MOVEによるP1疲労蓄積、SelfBodyの非ゼロ内受容、REST_PREFERRED、WAIT_DEVによる回復、READY_FEELINGの順序を原本で確認した。RESTは受動的な感覚上の選好であり、疲労によってActionを中断・遅延・選択したという証拠ではない。

branch: `self/dev-t1r-fatigue-timecourse-20261028`。開始remote HEAD `331d0acc0c7b2afca7896b941096cd1a773f98b2`、T1q基底 `4c82333e6015db423ce631674dc6907081a2ba30` の祖先関係を確認。隔離worktree `/home/rinsa/work/relay-self-t1r-20261028`。実装commit `bfc2091e3feabad8ab694075dfcc52b90494743b`。実行時は開始HEAD＋保存 `code-diff.patch`、全追跡source hashをlaunch receiptへ記録。報告のみを後続commitに追加する。

## 修正・オフライン検証

- `t1q_interoception_dev.py`: passive投影では未会計anchorを拒否。通常T1qの既存挙動は維持。
- `t1r_fatigue_timecourse_dev.py`: 回復後の最初のREADY tickを保持し、RESTより後のWAIT回復のみを順序判定に採用。import順序を修正。
- `test_t1r_fatigue_timecourse_dev.py`: anchor拒否と最初のREADY保持の負対照を追加。
- 本Markdownと同名JSONを実測報告として追加。既存T1e、S49/S16、ActionSupervisor、T2、M0/P1式、T1q行動選択、センサ量子化は変更していない。

Python 3.12.3 focused **125 PASS**、継承FAST＋T1r **45ファイル738 PASS**、Ruff・486 Pythonファイル構文・repository contracts PASS。system Pythonのpytest欠損、追加テスト初回2 FAIL、初回Ruff FAILをphase1へ保存。既存 `/home/rinsa/relay-self-s60b1-venv/bin/python` 使用。FULL・不要なNode/Java再ビルドなし。

単一T1e readerの `TickAccounting.observe()` 完了後のみpassive callbackを呼ぶ。会計anchorを除外し、observer例外はowner.failedをラッチ、source喪失は既存fail-closed経路で次Actionを拒否する。observerは正常・例外の両方で解除する。Action中はread-only投影だけを許容し、通常T1q投影と元Action発行ガードを維持する。`BodyState`/`FatigueState`は元transitionのafter辞書から復元でき、`rows()`名の遮蔽なし。MAX_PASSIVE_TICKS=240は変更せず、実測61サンプルで上限内。

## 実測

Node22.22.2、Java21.0.12.1、Paper1.21.8-60、Mineflayer4.39.0。元T1q資産のPaper/Plugin hash、bootstrap 121ファイル、136依存manifestを再照合。World本体はコピーせず新規生成。

| 指標 | 実測 |
| --- | --- |
| MOVE / OUTCOME / clear ACK | 2 / 2 / 2 |
| Action/effect重複 / 追加Motor | 0 / 0 |
| source | Paper 80/80 ADMITTED、欠損・順序違反0 |
| 連続会計WorldTick / SelfBodyサンプル | 1033–1093、61 / 61 |
| 最大因果年齢 | 88.224962 ms（Node同一時計上の上限） |
| M0 Energy | 12 → 11.929535788206891 |
| M0消費 | 0.07046421179314717（basal .061、cognition .0061、move .003364211793147172） |
| P1蓄積 / 回復 / 最終疲労 | .06728423586294344 / .06728423586294344 / 0 |
| WAIT_DEV | 40 tick、qualified WAITではない |
| Epoch 0 REST → 回復後READY | 1036 → 1044 |
| Epoch 1 REST → 回復後READY | 1066 → 1074 |
| 最大非ゼロ疲労感覚 | .03 |
| 最大感覚と同時点の最大host疲労（監査専用） | .03428678879345788（例: WorldTick 1070） |
| REST / READYサンプル | 16 / 45 |
| 食料credit / LLM / TPS actuator | 0 / 0 / 0 |
| 同期Node timing trace | OFF、ファイルなし |
| Java / Node | exit 0 / 0、両PID消滅 |
| cleanup | 元transport終端・World保存・独立port再bind PASS |

元S49 OUTCOME移動距離は各約.6269065734、Paper静止後変位は各約.8571697198。Action発行・effect・clear ACK・OUTCOMEと静止観測はそれぞれ別の原本で照合した。native seqは全native messageで単調連続、Paper frameのseqには他messageが挟まるため+1を要求しない。Paper WorldTick/indexは連続。両epochともAction中にRESTが現れたが、clearは元cleanupの各1回のみ。

## 原本と独立read-only監査

原本 `/home/rinsa/work/t1r-evidence-20261028/T1R-001/t1r_body_recovery/` にnative.jsonl、commands.jsonl、paper.log、t2_ticks.json、python_timing.jsonl、report.json、完全なWorld本体を保存。launch argv/environment、Paper/Plugin/runtime hashと実行source hashは同階層のlaunch/assets記録に保存。

独立 `/home/rinsa/work/t1r-evidence-20261028/audit.py` は保存原本のみを読み、全61サンプルのsession/seq/WorldTick/M0 tick、source refs、INTEROCEPTION origin、元P1 advance再実行、M0/P1センサ再投影、Energy収支、WAIT回復の因果clear・idle条件、各epochの順序、各1回のAction/clear、trace OFFとcleanupを照合。全27チェックPASS。正確なhost値は `host-audit.json`、認知へ渡った感覚は `selfbody-timecourse.json` に分離し、元認知traceにhost値の混入なし。未来台帳値を用いた認知入力なし。

原本manifest: `/home/rinsa/work/t1r-evidence-20261028/originals-manifest.json`。**206ファイル全SHA256読み戻し一致**。manifest SHA256: `09c6de37c6ca16b629ea04a8d0a29e6d094c2167e9ced74fc09b7c07e1a908bc`。

GitHub報告先: [#537](https://github.com/rinsakamo/relay-self/issues/537)、[#627](https://github.com/rinsakamo/relay-self/issues/627)、[#632](https://github.com/rinsakamo/relay-self/issues/632)、[#616](https://github.com/rinsakamo/relay-self/issues/616)。投稿URL・本文読み戻しと最終remote HEADは外部 `delivery.json` に保存する。

未成立: 身体感覚により実際に休息Actionを選んだこと、P1-qualified WAIT、独立R資格、科学効果は未証明。次候補は、別段階で既存L0の次epoch判断へ休息選好を接続して行動差を検証すること。今回の物理式・許可・Action経路は維持する。
