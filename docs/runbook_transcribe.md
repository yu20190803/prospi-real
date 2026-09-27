# 書き起こし手順書（別モデル・別セッション向け）

ユーザーが `captures/<npb|wbc>/<team>/` に選手詳細画面のスクリーンショットを置き、
「入れました」と報告したあとに行う作業の手順。**この手順書の通りに進めれば、どのモデルでも
同じ品質になるように書いている。判断に迷う点は「迷ったとき」の節に従い、勝手に仕様を変えない。**

関連ドキュメント: `CLAUDE.md`（方針）、`docs/data_schema.md`（JSONの形式）、
`docs/templates/pitcher.json` / `batter.json`（雛形）、`docs/grades.md`（等級の定義）。

---

## 0. 作業環境の準備

- ユーザーのPC上の本体: `C:\dev\claude\prospi-real`（GitHub: `yu20190803/prospi-real`）
- クラウド側の作業コピー: `/home/claude/prospi-real`
  - 存在しなければ `git clone --depth 1 https://github.com/yu20190803/prospi-real /home/claude/prospi-real`
  - `captures/` の画像は GitHub に上がっていない（.gitignore）。**画像はPCから取り込む。**
- PCとのやりとりはデバイス連携ツールで行う。
  - 一覧: `device_list_dir`（`C:\dev\claude\prospi-real\captures`, recursive）
  - 取り込み: `device_stage_files` → `/mnt/user-data/uploads/prospi-real/...` に届く
  - 書き戻し: ファイルを `/mnt/user-data/outputs/prospi-real/<同じ相対パス>` に置き、
    `device_commit_files` で `C:\dev\claude\prospi-real\<相対パス>` に書く
  - フォルダへのアクセスがない場合は `device_request_folder_access` で
    `C:\dev\claude\prospi-real` を1回だけ要求する
- Python 依存は `pip install -r requirements.txt --break-system-packages`（jinja2 のみ）

## 1. 未処理の画像を特定する

1. PCの `captures` を `device_list_dir` で再帰的に一覧する。
2. `<ローマ字姓>_<背番号>.png` 形式**でない**画像が未処理。
   すでにその形式で、`data/` に同名JSONがあるものは処理済み。
3. 未処理の画像を `device_stage_files` で取り込み、作業コピーの
   `captures/<npb|wbc>/<team>/<元のファイル名>` にコピーする。
4. `python src/pending.py` で、作業コピー上の未処理一覧を確認する。

## 2. 1枚ずつ書き起こす

画像を Read で開き、次の順に読む。**1枚読むごとにJSONを保存する**（まとめて最後に書かない）。

### 2-1. ヘッダー
- 背番号（左上の大きい数字）→ `uniform_number`（文字列）
- 年度（その下の小さい数字）→ `year`
- 選手名 → `name`（画面表記どおり）
- 守備位置・投打（右上）→ `position` / `throws_bats`
- ★の右の数値 → `rarity.overall`
- `kind` は守備位置が「投手」なら `pitcher`、それ以外は `batter`

### 2-2. player_id を決める
- `<ローマ字姓>_<背番号>`、ASCII小文字・数字・アンダースコアのみ。
- ローマ字は**実在選手の英語表記の姓**を使う（ウィットJr. → `witt`、ジャッジ → `judge`、
  日本人選手はヘボン式: 大谷 → `ohtani`、山本 → `yamamoto`）。
- 同じチームで同じIDがすでにあり**別人**なら末尾に `_2`。**同一人物**なら上書き更新。
- 画像を作業コピー内で `captures/<cat>/<team>/<player_id>.png` にコピーし、
  JSON に `"source_capture": "captures/<cat>/<team>/<player_id>.png"` と
  `"source_original": "captures/<cat>/<team>/<元のファイル名>"` を書く。

### 2-3. ステータス（中央の表）
- 等級の文字（S, A〜G）と数値を読む。等級と数値は `docs/grades.md` の表で必ず対応する
  （S=90以上, A=80〜89, B=70〜79, C=60〜69, D=50〜59, E=40〜49, F=20〜39, G=19以下）。
  **食い違ったらどちらかの読み違い。画像を拡大して読み直す。**
- 投手: 球速（"161km/h" のように単位付き文字列）、スタミナ、疲労回復、先発/中継/抑え適性。
- 野手: ミート（対右・対左の2行）、パワー、走力、捕球、スローイング、肩力、疲労回復。

### 2-4. 特殊能力（右のリスト）
- 上から順に全行。名前は記号（○ ▼）も含めて表記どおり。
- 右端に等級バッジがあれば `grade`、なければ `null`。
- 行頭の四角アイコンの色で `type`: ピンク=`plus`、紫=`minus`、ピンクと紫の斜め2色=`both`。
- 一番上の行だけ `highlighted: true`。

### 2-5. 野手: 守備図と得意苦手コース
- 守備図の「等級＋数値」をすべて `fielding_diagram.positions` へ。先頭は右上の守備位置。
- 得意・苦手コースの3×3の数字を `zone_grid` へ（上の行から）。

### 2-6. 投手: 変化球（最も間違えやすい。必ずこの通りに）
1. 画面下部の「1」パネルの球種をすべて `order: 1` で記録する。
2. 「2」パネルで**明るく表示されている**球種のうち、「1」と違う箱にあるもの・同じ方向でも
   名前が違うものを `order: 2` で記録する。**暗く表示されているのは第一球種の残像なので記録しない。**
3. 方向 → `category` は `docs/data_schema.md` の表で決める。
   **左投手は画面が左右反転しているので、左右を入れ替えて記録する。**
   **球種名から決めない。** 例: チェンジアップでも右投手の右下の箱なら `sinker`、真下なら `fork`、
   左投手の左下なら `sinker`。名前で決めて全投手の約半数を取り違えた（2026-09-27）。
   記録後は必ず `python3 src/check_pitch_slots.py` で画像の箱の位置と機械照合する。
   このチェックは「画像にある箱がデータにない」＝球種の書き漏れも検出する。
4. 箱の左の文字＝`power`、右の黒い四角の文字＝`control`。
5. **変化量 `break` は目で数えない。`src/read_break.py` で画素から読む（必須）**
   - 目視だと箱と同色の1段目を落とすなどして段数がぶれる（2026-09-27 に全投手で不安定だった）。
   - 書き起こし時は変化球の `break` を仮に `4` で入れておき、category（箱の位置）を確定させてから
     `python3 src/check_pitch_slots.py` → `python3 src/read_break.py --write` の順に実行する。
     category が間違っていると別の柄を読むので、必ず位置照合を先に通すこと。
   - read_break.py は柄7段の中心の画素を見て点灯/未点灯を判定し、第一・第二パネルの2か所で読んで
     一致したものだけ書き込む。「読み取りに問題あり」が出た球種は書き込まれないので、
     拡大画像（柄に判定点を重ねたもの）を見て原因を調べる。数値を手で合わせて消さない。
   - 直球系（最上段の箱）は柄がないので `break: null`。
6. read_break.py で書き込めた変化量には `unverified` を付けない（画像と機械照合済み）。
   読み取りに問題が残った球種だけ `"unverified": ["pitches[].break"]` を付けて報告する。

## 3. チェック

```bash
cd /home/claude/prospi-real
python3 src/validate.py      # エラー0件になるまで直す（警告は可）
python3 src/check_pitch_slots.py  # 投手の変化球の位置・書き漏れを画像と照合。不一致0人になるまで直す
python3 src/read_break.py    # 変化量を画像と照合。「不一致0球種 / 問題あり0球種」になっていること
python3 src/pending.py       # 未処理が0件になっていること
python3 src/build_site.py    # site/index.html を再生成
```

validate.py のエラーは読み違いのサイン。**エラーを消すために数値を都合よく変えない。**
画像を拡大して読み直し、それでも決められない場合は「迷ったとき」に従う。

## 4. PCへ書き戻す

次のファイルを `/mnt/user-data/outputs/prospi-real/` 以下に同じ相対パスで置き、
`device_commit_files` で `C:\dev\claude\prospi-real\` 以下に書き戻す（1回50件まで）。
- `data/<cat>/<team>/<player_id>.json`（新規・更新したもの全部）
- `captures/<cat>/<team>/<player_id>.png`（改名したコピー）
- `site/index.html`

PC上の元のファイル（改名前の名前のもの）は消さない。JSONの `source_original` に記録済みなので
未処理とはみなされない。不要ならユーザーが消す。

公開ページ（Artifact）を更新する場合は、`site/index.html` をこれまでと同じ Artifact に再公開する。

## 5. ユーザーへの報告（短く）

- 追加・更新した選手の人数（チーム別）
- **読み取りに自信がない箇所の一覧**（選手・項目・読んだ値・迷った理由）
- 変化量は画素から機械読み取りしている旨（read_break.py で問題が残った球種があればその一覧）
- GitHubへはPCからコミット・pushしてもらう（このセッションからはpushできない）

## 迷ったとき

- 読めない・判別できない値は推測で埋めず、JSON にはいちばん近い読み値を入れたうえで
  報告の「自信がない箇所」に必ず載せる。
- スキーマにない情報（新しい表示要素など）が出てきたら、JSON に勝手なキーを足さずに報告する。
- テンプレート・CSS・スクリプトは変更しない（この手順の範囲外）。レイアウトの崩れに
  気づいたら報告だけする。
