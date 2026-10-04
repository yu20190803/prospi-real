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

1. ユーザーがPCの `captures/<npb|wbc>/<team>/` に選手詳細画面のスクリーンショットを置く
   （ファイル名は自由、投手・野手・メニュー画面混在可）。画像はPCに置いたままでよく、
   どのGitHubリポジトリにも上げない。書き起こしはクラウドの定期実行がPCにリンクして
   1回1チームずつ行う。処理済みかどうかは、JSON の `source_original`/`source_capture` と
   `_skipped.json` に記録されているかで決める（ファイル名では決めない）。
2. `src/prep_team.py` が画素だけでメニュー画面・切り替え途中のフレーム・重複を仕分け、
   選手画面ごとに読み取り用画像とジョブを作る（LLM不要）。
3. 選手画面の書き起こしはサブエージェントが並列で行う（`docs/transcribe_guide.md` に従う）。
   `src/merge_team.py` が同じ選手の重複をまとめて `data/<npb|wbc>/<team>/<player_id>.json` に書き、
   改名コピー `<player_id>.png` を作る。既存の player_id と同じ選手なら上書き更新する。
4. 画素で照合できる項目はすべてスクリプトで照合し、不一致0にする:
   `validate.py`（等級と数値の整合）、`check_pitch_slots.py`（変化球の箱の位置）、
   `check_abilities.py`（特殊能力の行数・アイコン色）、`check_fielding.py`（守備図の位置）、
   `read_break.py --write`（変化量を画素から読んで反映）。
5. `python src/build_site.py` で `site/index.html`（公開用データベースページ）を生成する。
6. （内部検証用）`python src/generate.py` で画面再現カード `output/.../*.html` を作り、元画像と見比べられる。

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
src/pending.py                                 未処理画像の一覧（--done-count でチームごとの処理済み記録数）
src/capture_paths.py                           captures/ のパスを大文字・小文字を無視して解決
src/layout.py                                  キャプチャを標準レイアウト(865x605)に正規化（日本代表の1150x695画面など）
src/prep_team.py                               1チームの画像を画素で仕分け、読み取り用画像・ジョブを作る
src/merge_team.py                              書き起こし結果の重複をまとめて data/ に書く・改名コピー作成
src/check_abilities.py                         特殊能力の行数・アイコン色を元画像と機械照合
src/check_fielding.py                          守備図の守備位置を元画像と機械照合
docs/transcribe_guide.md                       1枚の画像を書き起こすためのガイド（サブエージェント用）
work/<cat>/<team>/                             作業用（読み取り画像・ジョブ・中間JSON）。.gitignore対象・コミットしない
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
- `captures/` の画像はゲームの著作物なので、**いずれのGitHubリポジトリにもコミットしない**
  （`captures` を丸ごと .gitignore 済み・ローカルPCにのみ保存）。公開ページにも埋め込まない。
  クラウドの定期実行はPCにリンクしてデバイス連携ツールで直接画像を読み書きする
  （画像取得のためだけに非公開リポジトリ prospi-captures を経由する運用は廃止、2026-09-28）。
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
  - 座標はすべて標準レイアウト（865x605）基準。別レイアウトの画面は `src/layout.py` で
    標準レイアウトに切り出してから読む（日本代表の1150x695画面は (279, 8) から等倍で切り出し）。
    新しいレイアウトが出てきたら `layout.py` に切り出し位置を足す。
- 特殊能力の type（行頭アイコンの色）と行数、守備図の守備位置も画素で照合する
  （2026-10-04 追加。目視の書き起こしでは USA の8人に type の誤り・行の書き漏れ、3人に守備位置の誤りがあった）。
- `captures/` の画像はスクリーンショット原本。生成スクリプトから読むだけで、
  加工・上書きしない。
