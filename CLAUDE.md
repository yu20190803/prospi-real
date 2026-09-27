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
- 同じ検証目的で `src/build_site_work.py` が `site/index_work.html`（一覧を右サイドバー、
  詳細を上部に配置し、詳細の下に対応する `captures/` 画像を表示するレイアウト）を生成する。
  元画像をJPEGのdata URIとしてHTMLに直接埋め込むため `.gitignore` 対象・非公開。公開用は必ず
  `src/build_site.py` の `site/index.html` を使う。

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

**画像を受け取ってからの書き起こし作業は `docs/runbook_transcribe.md` の手順に従う**
（別モデル・別セッションでも同じ品質で進められるよう、判断基準をすべてそこに書いている）。

1. ユーザーがPCの `captures/<npb|wbc>/<team>/` に選手詳細画面のスクリーンショットを置き、
   非公開リポジトリ prospi-captures に push する（ファイル名は自由、投手・野手・メニュー画面混在可）。
   書き起こしはクラウドの定期実行が1回1チームずつ行う（手順は runbook の 0.〜5.）。
   `<ローマ字姓>_<背番号>.png` の命名になっていない画像を未処理とみなす。
2. Claude が画像を読み取り、選手名・背番号から `<player_id>.png` に改名したうえで、
   `docs/data_schema.md` のスキーマに従って `data/<npb|wbc>/<team>/<player_id>.json` を書き起こす。
   既存の player_id と同じ選手なら、画像・JSONとも上書き更新する。
3. `python src/generate.py <data/.../player_id.json>` で
   `src/templates/player_card.html.jinja` + `src/templates/style.css` から
   `output/<npb|wbc>/<team>/<player_id>.html` を生成する。
4. 生成結果と元スクリーンショットを見比べ、ズレがあれば
   テンプレート/CSSを直す（データではなくレイアウト側を直す）。
5. 全選手を再生成する場合は `python src/generate.py --all` を使う想定。
6. `python src/validate.py` で全JSONを機械チェック（等級と能力値の整合、値域、推定値の一覧）。
   エラー0件にしてから次へ進む。あわせて `python src/check_pitch_slots.py` で投手の変化球の
   位置（category）と書き漏れを元画像と照合し、不一致0人にする。そのあと
   `python src/read_break.py --write` で変化量を画像から読み取って反映する。
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
src/check_pitch_slots.py                       投手の変化球の位置・書き漏れを元画像と機械照合
src/read_break.py                              投手の変化量を元画像の画素から読み取り・照合（--write で反映）
src/build_site.py                              全JSON → site/index.html（公開用ページ）
src/site/index.template.html                   公開用ページのテンプレート（__DATA__ にJSONを埋め込む）
site/index.html                                生成された公開用ページ
src/build_site_work.py                         全JSON → site/index_work.html（検証用・非公開）
src/site/index_work.template.html              検証用ページのテンプレート（一覧が右サイド／詳細下に元画像）
site/index_work.html                           生成された検証用ページ（.gitignore対象・コミットしない）
docs/data_schema.md                            選手データのJSONスキーマ定義（投手/野手それぞれ記載）
docs/runbook_transcribe.md                     書き起こし手順書（画像受け取り〜PC書き戻し〜報告）
docs/templates/pitcher.json, batter.json       書き起こし用の雛形（実データと同じ形式）
src/pending.py                                 未処理画像の一覧（--next-team で次に処理するチーム）
src/capture_paths.py                           captures/ のパスを大文字・小文字を無視して解決
data/<npb|wbc>/<team>/_skipped.json            書き起こし対象外の画像（メニュー画面・重複など）の記録
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
- `captures/` の画像はゲームの著作物なので、**公開リポジトリ（prospi-real）には絶対にコミットしない**
  （`captures` を丸ごと .gitignore 済み）。公開ページにも埋め込まない。
  画像は**非公開リポジトリ `yu20190803/prospi-captures`** でのみ管理する（2026-09-28〜。PCの
  `captures/` フォルダ自体がこのリポジトリ）。定期実行はクラウドでこれを clone して
  `prospi-real/captures` にシンボリックリンクして使う。prospi-captures を公開に変えない。
- チームのフォルダ名は大文字を含むことがある（`captures/wbc/USA`）。データ側の `team`・
  `data/` のフォルダ・`source_capture` は常に英小文字。画像を読むコードは必ず
  `src/capture_paths.py` の `resolve()` を通す（Linux は大文字・小文字を区別する）。
- 左投手は画面上の変化方向が左右反転する。`pitches[].category` は右投手基準の大分類
  （スライダー系=左方向 など）で記録する。**category は画面上の箱の位置で決め、球種名からは
  決めない**（チェンジアップが sinker の位置にあることは普通にある）。
  `src/check_pitch_slots.py` で画像と機械照合できる。
- 変化量（`pitches[].break`）は7段階。**目で数えず `src/read_break.py` で画素から読む**
  （2026-09-27 見直し）。目視では箱と同色の1段目を落とすなどして段数がぶれ、品質が安定しなかった。
  - read_break.py は柄7段の中心の画素で点灯/未点灯を判定し、第一・第二パネルの2か所で読んで
    一致したものだけ `--write` で書き込む。柄の座標は全キャプチャ共通（865x605で実測）。
  - category（箱の位置）が違うと別の柄を読むので、先に check_pitch_slots.py を通す。
  - 機械照合済みの変化量には `unverified` を付けない。読み取りに問題が残った球種だけ付ける。
  - ゲーム画面の解像度・レイアウトが変わった場合は、柄の座標（read_break.py の STEMS）と
    箱の座標（check_pitch_slots.py の SLOTS）を測り直す必要がある。
- `captures/` の画像はスクリーンショット原本。生成スクリプトから読むだけで、
  加工・上書きしない。
