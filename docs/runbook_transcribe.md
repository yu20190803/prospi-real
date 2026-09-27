# 書き起こし手順書（別モデル・別セッション向け）

ユーザーが `captures/<npb|wbc>/<team>/` に選手詳細画面のスクリーンショットを置き、
「入れました」と報告したあとに行う作業の手順。**この手順書の通りに進めれば、どのモデルでも
同じ品質になるように書いている。判断に迷う点は「迷ったとき」の節に従い、勝手に仕様を変えない。**

関連ドキュメント: `CLAUDE.md`（方針）、`docs/data_schema.md`（JSONの形式）、
`docs/templates/pitcher.json` / `batter.json`（雛形）、`docs/grades.md`（等級の定義）。

---

## 0. 作業環境の準備（クラウド。PCの電源状態に関係なく動く）

リポジトリは2つ。**画像は非公開リポジトリにだけ置く。公開リポジトリには絶対に入れない。**

| リポジトリ | 公開 | 中身 | クラウドでの場所 |
|---|---|---|---|
| `yu20190803/prospi-real` | 公開 | コード・データ・公開ページ | `/home/claude/prospi-real` |
| `yu20190803/prospi-captures` | **非公開** | ゲーム画面キャプチャ（`wbc/<Team>/...png`） | `/home/claude/prospi-captures` |

1. 両方を `add_repo`（access: push）でセッションに追加し、それぞれ `git clone --depth 1` する
   （captures は約350MBあるので clone のタイムアウトは10分にする）。
2. 画像を作業コピーから見えるようにリンクする:
   `ln -s /home/claude/prospi-captures /home/claude/prospi-real/captures`
   （`prospi-real/.gitignore` で `captures` を丸ごと除外済みなので、公開リポジトリには入らない）
3. Python 依存: `pip install -r requirements.txt --break-system-packages`
4. チームのフォルダ名は `USA`・`Australia` のように大文字を含むことがある。
   **データ側（`team`・`data/` のフォルダ・`source_capture`）は常に英小文字**（`usa`, `australia`, `japan_2026`）。
   画像を読むスクリプトは `src/capture_paths.py` で大文字・小文字を無視して解決するので、
   フォルダ名を変える必要はない（PCのWindowsで大文字小文字だけの改名は事故のもと）。

## 1. 未処理の画像を特定する

1. `python src/pending.py` で未処理の画像をチームごとに一覧する。
   `python src/pending.py --next-team` は未処理が残っている最初のチーム（例: `wbc/Australia`）を返す。
2. 未処理の判定: JSON の `source_original` / `source_capture` に記録された画像と、
   `data/<cat>/<team>/_skipped.json` に記録された画像は処理済み。それ以外が未処理。
3. **1回の作業では1チームだけ処理する**（1チーム40枚前後。途中で打ち切られないように）。
4. 未処理の画像には選手詳細画面以外も混ざっている。1枚ずつ見て分類する:
   - 選手詳細画面 → 2. の手順で書き起こす
   - 選手一覧のメニュー画面・画面切り替え途中のフレーム（2画面が半透明に重なったもの）・
     同じ選手の2枚目 → `_skipped.json` に `{"file": "captures/wbc/<Team>/<元ファイル名>", "reason": "…"}` で記録
   - 迷ったら選手画面として書き起こし、報告で触れる
5. メニュー画面の選手一覧に載っているのに詳細画面がない選手がいれば、報告に書く
   （例: USA のバクストン、クロウ=アームストロング）。

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
- 画像を**実際のフォルダ**（例: `captures/wbc/Australia/`）に `<player_id>.png` という名前でコピーする
  （元ファイルは消さない・上書きしない）。
- JSON には `"team": "<英小文字>"`、`"source_capture": "captures/<cat>/<英小文字team>/<player_id>.png"`、
  `"source_original": "captures/<cat>/<実際のフォルダ名>/<元のファイル名>"` を書く。
  JSON の置き場所は `data/<cat>/<英小文字team>/<player_id>.json`。
- 読み取りは、画像全体ではなく**上半分・下半分を切り出して3倍に拡大したもの**を Read で見る
  （PIL で crop → resize）。細かい等級・記号の読み違いが減る。

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
python3 src/pending.py       # 処理したチームの未処理が0件になっていること
python3 src/build_site.py    # site/index.html を再生成
```
4つのチェックがすべて通るまで次へ進まない。

validate.py のエラーは読み違いのサイン。**エラーを消すために数値を都合よく変えない。**
画像を拡大して読み直し、それでも決められない場合は「迷ったとき」に従う。

## 4. GitHubへ反映する（2つのリポジトリ）

1. **prospi-captures（非公開）**: 改名コピーした `<player_id>.png` を追加してコミット・push。
   元ファイルは消さない。
   ```bash
   cd /home/claude/prospi-captures && git add wbc/<Team>/ && git commit -m "<Team>: add renamed captures" && git push
   ```
2. **prospi-real（公開）**: `data/<cat>/<team>/`（JSONと `_skipped.json`）と `site/index.html` をコミット・push。
   **push 前に `git status` で `captures` 配下や画像ファイルが含まれていないことを必ず確認する。**
   ```bash
   cd /home/claude/prospi-real && git add data/ site/index.html && git status --short && git commit -m "<Team>: add N players" && git push
   ```
   push が拒否されたら（PC側で先に push された等）、`git pull --rebase` してから push し直す。
   強制 push はしない。
3. `site/index_work.html`（検証用）は .gitignore 対象なので push しない。

ユーザーはPCで両方のリポジトリを `git pull` して結果を受け取る。

## 5. ユーザーへの報告（短く）

- 処理したチームと、追加した選手の人数（投手・野手の内訳）
- スキップした画像の枚数と理由の内訳
- 一覧画面にいるのに詳細画面がない選手
- **読み取りに自信がない箇所の一覧**（選手・項目・読んだ値・迷った理由）
- read_break.py / check_pitch_slots.py で問題が残った球種があればその一覧
- 残りのチーム数

## 迷ったとき

- 読めない・判別できない値は推測で埋めず、JSON にはいちばん近い読み値を入れたうえで
  報告の「自信がない箇所」に必ず載せる。
- スキーマにない情報（新しい表示要素など）が出てきたら、JSON に勝手なキーを足さずに報告する。
- テンプレート・CSS・スクリプトは変更しない（この手順の範囲外）。レイアウトの崩れに
  気づいたら報告だけする。
