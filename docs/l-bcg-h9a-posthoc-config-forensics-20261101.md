# L-BCG H9a 補助監査：server.properties生成日時のみの差分

2026-11-01。PR #656 / Issue #431 / #537。

## 原本と判定（変更なし）

H9a実Minecraft A/B 2 World（A: native S42=2.0m、B=3.5m）は
それぞれ独立したsession、Paper World UUID、元S49 Action 1、
S16 Outcome 1、retries 0、cleanup PASS。
固定CHEAP（元native S42<3.0m）はA=true、B=false。
Paper reported-input-OFF中変位は A=0.06709170283354737m、
B=0.06424660150896089m（**正式な実効clear後物理移動ではない**）。

事前固定されたH9a pair gateは、重要資材のraw SHA一致を要求した。
`server.properties` raw SHAが次のように異なるため、
`H9A_PAIR_REJECTED_RUNTIME_SHA_MISMATCH` / `exploratory_pair_pass=false`を
**永久保存**する。

- A: `dbcae461ab304682b8d97d7876de46748501ad9fab83300387d4218f5743487c`
- B: `288b1cfb719d2b6d8c964cc37b77fffd5b708e7e9d988445c7e8731898748c36`

原本は
`docs/evidence/l-bcg-h9a-20261101/{a,b}/run1/runtime-config/server.properties`。
旧判定は
`docs/evidence/l-bcg-h9a-20261101/pair/result-rejected.json`。

## 追加した**事後**解析の上限

`src/relay_self/l_bcg_h9a_config_forensics.py`、
`tools/l_bcg_h9a_config_forensics.py`、
`tests/test_l_bcg_h9a_config_forensics.py`を追加。

旧 `l_bcg_h9a_pair_readback.py`の一致条件は変更しない。
本監査は**別の補助diagnostic**として、各原本の
`original-sha256.json`（保存設定・runtime manifestのraw SHA）と
`runtime-assets-sha256.json`（server.properties/Paper/plugin/config SHA）を
照合し、さらに2設定ファイルの**行バイト単位**差分を検査する。

厳格な許容条件：
1. 最初の行 `#Minecraft server properties\n` は完全一致。
2. 第二行だけが、それぞれ形式の合う起動時日時コメントで異なる。
3. 第三行以降はすべて**バイト完全一致**（空白、改行、行順、
   escape、重複キー、コメントを削除・正規化しない）。
4. `minecraft.jar`、Paper plugin jar、
   `RelayMetabolismDev/config.yml` のraw SHA完全一致。
5. それぞれの元 `server.properties` のraw SHA不一致という
   **元reject原因が事実として存続**する。

この条件を満たす場合、唯一許す補助結論は
`POSTHOC_CONFIG_TIMESTAMP_ONLY_DIAGNOSTIC_NOT_PAIR_PASS`。
`original_pair_raw_sha_gate=REJECTED_AS_PREDECLARED`、
`changes_original_pair_decision=false`。
失敗時は補助解析自身を拒否して元判定を保持する。
日時以外のプロパティ・その他コメント・順序・改行・主要jar/configの
改変は（保存SHA manifestを合わせて捏造しても）拒否する。

```bash
PYTHONPATH=src:tests:. python tools/l_bcg_h9a_config_forensics.py \
  docs/evidence/l-bcg-h9a-20261101/a \
  docs/evidence/l-bcg-h9a-20261101/b
```

実行World=0、Action=0、モデル呼出し=0、学習=0。
H9aの探索的pairは依然REJECTED、
QUALIFICATION NO_GO、SCIENCE NOT_RUN、
GOAL UNDETERMINED、EFFECTIVE CLEAR NOT_ATTESTED、
FORMAL TRAINING WORLD 0、L1 `DEFER_UNKNOWN`。

この**事後**仕様をH9a実験の事前宣言に遡って適用しない。
今後の新しい独立World対では、旧原本を一切書き換えず、
例えば「各Worldのraw SHAと生成物1行の厳密限定等価性」の双方を
**World開始前に別基準として宣言**した新試験にする。
World間の遺伝・物理・経験的な一般化の検証はさらに後続。
