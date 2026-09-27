# CLAUDE.md — prospi-real

野球ゲーム「プロ野球スピリッツ」最新作の実在選手データを、**数値＋グラフで一覧・比較できる
オリジナルデザインのデータベースサイト**として公開するプロジェクト（収益化目的）。
対象は NPB12球団の選手と、WBC代表チームの選手。

**方針転換（2026-09-27）**: 当初は選手詳細画面をレイアウト忠実にHTML再現していたが、
ゲーム画面デザインの模倣は収益サイトとして権利リスクが高く、閲覧者の価値（検索・並べ替え・比較）
にもつながらないため、数値データベース型に切り替えた。
- 公開物は `site/`（`src/build_site.py` で生成）。ゲーム画面の再現・画像・アイコンは載せない。
- `src/generate.py` + `player_card_*.jinja` の画面再現カードは、書き起こし結果を元画像と
  見比べる**内部の検証用**としてのみ残す（公開しない）。

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
6. `python src/validate.py` で全JSONを機械チェック（等級と能力値の整合、値域、推定値の一覧）。
   エラー0件にしてから次へ進む。
7. `python src/build_site.py` で `site/index.html`（公開用データベースページ）を生成する。

## ディレクトリ

```
data/<npb|wbc>/<team>/<player_id>.json         選手データ（書き起こし結果。kind: pitcher|batter）
captures/<npb|wbc>/<team>/<player_id>.png      元スクリーンショット（読み取り専用）
src/generate.py                                JSON → HTML 生成スクリプト（kindでテンプレート自動選択）
src/templates/_header.html.jinja               投手/野手共通のヘッダー部分
src/templates/player_card_pitcher.html.jinja   投手カードのテンプレート
src/templates/player_card_batter.html.jinja    野手カードのテンプレート
src/templates/style.css                        カード共通スタイル
output/<npb|wbc>/<team>/<player_id>.html       検証用の画面再現HTML（公開しない・コミット対象外）
src/validate.py                                書き起こしデータの検証スクリプト
src/build_site.py                              全JSON → site/index.html（公開用ページ）
src/site/index.template.html                   公開用ページのテンプレート（__DATA__ にJSONを埋め込む）
site/index.html                                生成された公開用ページ
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

| フェーズ | 内容 | 状態 |
|---|---|---|
| Phase 0 | ディレクトリ・スキーマ・テンプレート骨格 | 済 |
| Phase 1 | 書き起こし手順の確立（WBC USA 8選手、検証スクリプト） | 済 |
| Phase 2 | データベースページ試作（一覧・並べ替え・比較・選手詳細） | 試作済 |
| Phase 3 | 選手ごとの個別ページ・球団別/ポジション別ページ（SEO用URL構造） | 未 |
| Phase 4 | NPB12球団・WBC各国のデータ投入、公開（静的ホスティング）と広告導入 | 未 |

## 禁止・注意事項

- ゲーム公式のフォント・アイコン画像ファイルそのものはリポジトリに含めない
  （自作CSS/SVGで見た目を再現する）。
- `captures/` の画像はゲームの著作物なので **GitHubにはコミットしない**（.gitignore 済み、
  ローカルPCにのみ保存）。公開ページにも埋め込まない。
- 左投手は画面上の変化方向が左右反転する。`pitches[].category` は右投手基準の大分類
  （スライダー系=左方向 など）で記録する。
- 変化量（`pitches[].break`）は7段階。柄の読み取りは次の手順で行う（2026-09-27 見直し）。
  - 箱のすぐ外側の1段目は箱と同じ色で区切り線がなく、箱の一部に見える。**点灯段を数えると
    この1段を落としやすい**（スクーバルで全球種1段少なく誤読した）。
  - そのため **点灯段ではなく未点灯段（暗い段。先端の山形も1段）を数え、7から引く**。
    未点灯段は区切りがはっきりしているので数え違えにくい。
  - 斜め方向は根元が箱の下に隠れるため、見えている段の合計が6になることがある。この場合も
    「7−未点灯段」で求める。
  - ユーザーがゲームで確認した選手は `"unverified"` を外す。未確認の選手は推定値として残し、
    validate.py が警告として一覧化する。
- `captures/` の画像はスクリーンショット原本。生成スクリプトから読むだけで、
  加工・上書きしない。
