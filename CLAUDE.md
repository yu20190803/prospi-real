# CLAUDE.md — prospi-real

野球ゲームの選手詳細画面（スクリーンショット）を、**レイアウト忠実にHTMLで再現する**プロジェクト。
対象は NPB12球団の選手と、WBC代表チームの選手。実際のゲームアセット（フォント・アイコン画像）は
再配布せず、色・形・配置を自作CSS/SVGで再現する。

## 分類

- **npb** … 日本プロ野球12球団（例: giants, tigers, carp, dragons, swallows,
  baystars, hawks, buffaloes, lions, marines, eagles, fighters）
- **wbc** … WBC代表チーム（例: japan, usa, dominican, korea, mexico, venezuela, ...）

チームディレクトリは必要になった時点で作成する。存在しない国・球団のフォルダを
先回りして大量に空生成しない（管理コストが増えるだけなので）。

選手データはさらに **投手 (`kind: "pitcher"`) / 野手 (`kind: "batter"`)** に分かれる。
画面レイアウトが別物（野手は対右/対左の分割ステータス・得意苦手コース・守備
ダイアグラムを持つ）ため、テンプレートも `player_card_pitcher.html.jinja` /
`player_card_batter.html.jinja` に分けている。ヘッダー部分（背番号・年度・
選手名・守備位置・投打・★とOVR）だけは共通で `_header.html.jinja` を共有する。
`kind` に応じてどちらのテンプレートを使うかは `src/generate.py` が自動判定する。

## ワークフロー

1. ユーザーが選手詳細画面のスクリーンショットを渡す。
2. Claude が画像を読み取り、`docs/data_schema.md` のスキーマに従って
   `data/<npb|wbc>/<team>/<player_id>.json` を書き起こす。
   元画像は `captures/<npb|wbc>/<team>/<player_id>.png` に保存する（差分検証用）。
3. `python src/generate.py <data/.../player_id.json>` で
   `src/templates/player_card.html.jinja` + `src/templates/style.css` から
   `output/<npb|wbc>/<team>/<player_id>.html` を生成する。
4. 生成結果と元スクリーンショットを見比べ、ズレがあれば
   テンプレート/CSSを直す（データではなくレイアウト側を直す）。
5. 全選手を再生成する場合は `python src/generate.py --all` を使う想定。

## ディレクトリ

```
data/<npb|wbc>/<team>/<player_id>.json         選手データ（書き起こし結果。kind: pitcher|batter）
captures/<npb|wbc>/<team>/<player_id>.png      元スクリーンショット（読み取り専用）
src/generate.py                                JSON → HTML 生成スクリプト（kindでテンプレート自動選択）
src/templates/_header.html.jinja               投手/野手共通のヘッダー部分
src/templates/player_card_pitcher.html.jinja   投手カードのテンプレート
src/templates/player_card_batter.html.jinja    野手カードのテンプレート
src/templates/style.css                        カード共通スタイル
output/<npb|wbc>/<team>/<player_id>.html       生成されたHTML（コミット対象外でよい）
docs/data_schema.md                            選手データのJSONスキーマ定義（投手/野手それぞれ記載）
```

## player_id の命名規則

`<ローマ字姓>_<背番号>` 形式（例: `web_62`）。同姓同背番号の衝突が起きたら
`_2` を付ける。ファイル名はASCII小文字・アンダースコアのみ。

## データの出典と検証

- 数値・能力・球種はすべて元スクリーンショットからの書き起こし。ゲーム側の
  更新（能力変更・年度更新）があれば `captures/` に新しい画像を追加し、
  同じ `player_id` の JSON を上書きする。JSON側に `"source_capture"` として
  対応する `captures/` パスを必ず記録する。
- OCRやClaudeの読み取りmiss はあり得るので、数値系（球速・スタミナ値・OVR）は
  書き起こし後に元画像と目視で一致確認する。

## レイアウト再現の方針

- ヘッダー（背番号バッジ／年度バッジ／選手名／守備位置／投打／★とOVR）と
  ステータス表（球速・スタミナ・疲労回復・先発/中継/抑え適性）、特殊能力リストは
  CSS Grid/Flexboxで再現する（Phase 1）。
- 球種セクション（軌道図＋方向ごとのグレードバッジ）は座標指定が必要な
  カスタムSVGになる。共通レイアウトが固まってから個別に調整する（Phase 2）。
- 色は元画像からの近似値。ゲームの正式カラーコードではないため、
  再現しつつも「近似」であることを前提とする。

## フェーズ

| フェーズ | 内容 |
|---|---|
| Phase 0 | ディレクトリ・スキーマ・テンプレート骨格（このコミット） |
| Phase 1 | サンプル1枚（ウェブ / WBC USA / 62）でヘッダー・ステータス・能力リストを再現 |
| Phase 2 | 球種セクション（軌道図）の再現 |
| Phase 3 | 複数選手・複数チームでテンプレートの汎用性を検証 |
| Phase 4 | NPB12球団・WBC各国のデータ投入を進める |

## 禁止・注意事項

- ゲーム公式のフォント・アイコン画像ファイルそのものはリポジトリに含めない
  （自作CSS/SVGで見た目を再現する）。
- `captures/` の画像はスクリーンショット原本。生成スクリプトから読むだけで、
  加工・上書きしない。
