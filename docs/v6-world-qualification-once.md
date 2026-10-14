# S/R — V6 1回限り実World環境資格確認（2026-10-14）

**目的：** 認知性能を評価する48本のV6試験ではなく、RSEE Golden #588から作る**使い捨てMinecraft 1.21.8 Worldを1回だけ実行**し、2つの計時Datapackの実パーサ・ロード、初回ネイティブ観測、サーバー原記録、STOP・後片付けを工学的に検証する。

許可：この会話でユーザーが明示的に**資格確認用の実World 1回**を許可。実行先はユーザー自身のWindows 11/WSL2ホスト。ChatGPTのGitHub/API環境は当該ローカルホストとGolden原バイトを操作できないため、**このドキュメントの作成は許可の消費ではない**。実行できるのはホストのLocalCodex等の明示的な操作者だけ。再試行、再起動、fallback、新しいWorldの勝手な代用、V6の本試験への転用は不可。

## 不変Authority

- R: Issue #575 / 既存Draft PR #610（R元HEAD `7b7da8b2bcbb082083ddb47744a345329475ad34`、CI #38561126541 4/4 success）。Rは別worktreeの独立読取り・資格判定者。
- S: Issue #537 / 既存Draft PR #545。開始Datapack V1の不変S producer HEAD `2aaff0b921bcbd47a61d563b52d502596f896924`、blob `d1510006dc370d217afe6d4988662ca0f36c5522`。食料召喚Datapack V2の不変producer HEAD `37f9365d3d16c9bda440ca9a9c8a10be6a32f1fc`、blob `ea4f4123e9d43a774f736b519743616115b78ea2`。新しいS実行器は**別コミット／別ソース**として審査し、以前の固定Datapackバイトを変更しない。
- Golden RSEE：#588 HEAD `34820f6bf391c77f325d7c29d3b779a33e3ca835`。固定JAR SHA256 `2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7`、固定World manifest SHA256 `5b1876db6a97fc8b9c4331938ca47727037c5626a241213d871b2073665996f8`。
- V: Issue #619 / 既存Draft #625。V6の2代謝条件・6arm×4開始条件＝48試験は**0実施**。今回のqualification一回を48試験に算入しない。Vの科学的NO-GOを保持する。

## 正しい実行準備（実Worldを起動する前）

1. 過去のB0 58ファイルや既存Golden、main、S/R/V siblingを変更しない。各Git worktreeにブランチ・フルHEAD・clean、CI終端、R5 ancestryを記録。ユーザーの一回許可はこの特定の環境資格確認だけに適用。
2. **既存S51 `--food-source groundv6` はJava起動前に意図的にBLOCKED**。現行のフラグを強引に解除したり、古い `groundv2` 経路で代用したりしない。S #545の所有領域に**資格確認専用**（V実験とは別）のone-shotランナーを実装し、オフラインテスト・負対照・R/V出典レビューを終える。ユーザーから新しい科学実験許可は得ていない。
3. 固定RSEEのJAR/26ファイルWorld/manifest/initial evidence/外部Node22+Mineflayer4.39.0を既存の `verify_b0_rsee` で原始バイト再照合。Worldの複製は所有PIDと専用使い捨てディレクトリに一度だけ作り、**Goldenは不変**。最初に何も上書きしない一意の証拠保存先を確保する。
4. 固定food V2 `relayself_v6_atomic` 3ファイル＋固定start V1 `relayself_v6_start_v1` 3ファイルの**計6ファイルのみ**を複製Worldに加える。固定 `WORLD_START_A..D` と当該セッション固有の正規32小文字hex nonceを用いる（nonceは相関ラベル、真正認証ではない）。R #610の `python -m experiments.standard_env.v6_start_admission` を別clean checkoutから呼び、固定した各S checkoutと現物の停止World clone・Golden・JARを**Java起動前**に独立チェックする。3ファイル版を6ファイル版として通さない。
5. 起動前にS実行器が、サーバー原出力・issuer生コマンド記録・Mineflayer未改変JSONLの保存、完全な命令/Score readback、実起動・停止・owner PID/port/STOP領域を保証できることをソースとfocused/offlineテストで確認する。実際の `server_stdout_original.log`, `issuer_commands_original.jsonl`, `native_bridge_original.jsonl` は**現状のS51からは出てこない**。R #610の新しい原証拠envelopeは**将来のフォーマット仕様**であり、現物の代用品ではない。
6. どれか1つでも欠ければ、`PREWORLD_BLOCKED`として**Java/Node/Minecraft起動ゼロ**で停止し、事実をIssue #537/#575に記録して本許可は未消費のままとする。

## 唯一の実行（前段がPASSした場合だけ）

同じ実行器からR認定した複製WorldでMojang 1.21.8 JARを起動し、S専用の生Mineflayerで一つのsessionを形成する。計時パケットは1.21.8クライアントの `update_time` を生で記録し、**疎なpacket ageやhost nsを正確なcommand effect時刻と混同しない**。

予定の一セッション：
- 両packの正しいinstall順とMinecraft実parser/loadを**サーバー原ログ**で確認。
- 最初のitem-freeネイティブL0 probe（session/seq/request id）を読んでから、start packの初回 `start_trial` を1回のみ実行。原stdoutと `#start_attempt=1`, `#start_gametime` を記録。L0 probeと関数実行は同じgametimeであるとは仮定しない。
- food packの初回 `atomic_food` を**固定した許容機会**で1回のみ実行。 `#attempt=1`, `#before=#after`, `#ok=1` と原ログ中のsource markerを記録。サーバーの食料Item出現を別のネイティブ観測で確認。これは外生食料fixtureでありSelfの自発的採食や進化・学習の成果とはしない。
- `T_food - T_start` を、真正原ログと整合する符号付き32bitのserver gametime**候補**として報告。Vの腕間同一経過tickはこの1回では検証不能。M0の11decision tickと別扱い。
- **試験でないので**余分なWorld Action、MOVE/EAT/M-credit、48-armループ、負対照世界2回目、再試行、fallbackを実施しない。固定V6の「11M0 tick食料出現」を無断で再現したと主張しない。
- 最終的に元のNode/Java所有PIDとSTOP ACK、退出コード、ポート再bind、VRAM（関係する時だけ）を確認。どこかで異常があれば、その一回の実起動で終了。**Javaが一度でも実際に起動したら本許可は消費**。STOP失敗や未完はPASSにしない。

## 原証拠／独立評価

original log・native JSONL・issuer stdin command bytes・source version・元Worldバイトindex・6追加Datapack SHA・原Score readback・報告書を保存し、Rが別プロセス/別checkoutで前後SHA256・session/seq/STOP・元World不変・source-to-effect readbackを監査する。証拠ファイルにmissing/duplicate/alias/自称原証拠しか無い場合は `UNDETERMINED`/ `BLOCKED` とし、改竄や再実行で補完しない。

この1回は**Engineering World load/clock-source qualification**であり、科学的学習や予測の効果、V6 48試験の入場・同一世界経過tick、G3/production GOではない。結果はS #537、R #575、必要に応じV #619へ原証拠SHAを添えて報告する。未実施段階の分類は `S_V6_PHYSICAL_QUALIFICATION_PREPARED_NOT_RUN / ONE_SHOT_GRANT_UNCONSUMED / WORLD_V6_STUDY_0 / G3_NO_GO`。
