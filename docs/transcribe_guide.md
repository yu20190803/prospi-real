# 書き起こしガイド（1枚の画像 → 1つのJSON）

選手詳細画面の画像（`work/<cat>/<team>/sheets/*.png`、標準レイアウトに正規化・拡大済み）を読み、
JSON を1つ書く。**このガイドだけで作業が完結するように書いている。** 細かい定義は
`docs/data_schema.md`、等級表は下記。迷ったら推測で埋めず、いちばん近い読み値を入れて
`notes` に書く（後で人が確認する）。

## 出力

- 置き場所: 指示された `out` のパス（例: `work/wbc/australia/json/Screen_20260811_180119_611.png.json`）
- 1画像につき1ファイル。**`data/` には書かない**（`src/merge_team.py` が重複をまとめてから移す）。
- 形式は下の雛形どおり（キーの順番もこのまま）。`source_original` は指示された元画像のパス、
  `source_capture` は `captures/<cat>/<team>/<player_id>.png`（team は英小文字）。

### 投手
```json
{"category": "wbc", "team": "australia", "kind": "pitcher", "player_id": "skenes_30",
 "source_capture": "captures/wbc/australia/skenes_30.png",
 "source_original": "captures/wbc/Australia/Screen_....png",
 "year": 2026, "uniform_number": "30", "name": "スキーンズ", "position": "投手", "throws_bats": "右投右打",
 "photo": null, "rarity": {"star": true, "overall": 605},
 "stats": [
  {"label": "球速", "value": "161km/h", "grade": null},
  {"label": "スタミナ", "value": 70, "grade": "B"},
  {"label": "疲労回復", "value": 77, "grade": "B"},
  {"label": "先発適性", "value": "◎", "grade": null},
  {"label": "中継適性", "value": "ー", "grade": null},
  {"label": "抑え適性", "value": "ー", "grade": null}],
 "pitches": [
  {"category": "straight", "order": 1, "name": "ナチュラル", "power": "B", "control": "A", "break": null},
  {"category": "slider", "order": 1, "name": "スライダー", "power": "A", "control": "D", "break": 4}],
 "abilities": [
  {"name": "ケガしにくさ", "grade": "D", "highlighted": true, "type": "plus"},
  {"name": "援護▼", "grade": null, "highlighted": false, "type": "minus"}]}
```

### 野手
```json
{"category": "wbc", "team": "usa", "kind": "batter", "player_id": "judge_99",
 "source_capture": "captures/wbc/usa/judge_99.png", "source_original": "captures/wbc/USA/Screen_....png",
 "year": 2026, "uniform_number": "99", "name": "ジャッジ", "position": "右翼手", "throws_bats": "右投右打",
 "photo": null, "rarity": {"star": true, "overall": 514},
 "stats": [
  {"label": "ミート", "splits": [{"vs": "対右", "grade": "B", "value": 73}, {"vs": "対左", "grade": "B", "value": 73}]},
  {"label": "パワー", "grade": "S", "value": 97},
  {"label": "走力", "grade": "C", "value": 61},
  {"label": "捕球", "grade": "C", "value": 68},
  {"label": "スローイング", "grade": "C", "value": 61},
  {"label": "肩力", "grade": "A", "value": 85},
  {"label": "疲労回復", "grade": "B", "value": 71}],
 "fielding_aptitude": [],
 "zone_grid": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
 "fielding_diagram": {"primary_position": "RF", "primary_grade": 52, "catcher_lead_grade": null,
  "positions": [{"position": "RF", "grade": "D", "value": 52}, {"position": "CF", "grade": "E", "value": 41},
                {"position": "LF", "grade": "F", "value": 35}]},
 "abilities": [{"name": "アーチスト", "grade": null, "highlighted": true, "type": "plus"}]}
```
読めない値・自信のない値があれば `"notes": ["肩力の数値 85 か 86 か判別しにくい"]` を足す（なければ書かない）。

## 読み方

**ヘッダー**: 左上の大きい数字＝`uniform_number`（文字列）、その下の小さい数字＝`year`。
選手名・守備位置・投打は表記どおり。★の右の数値＝`rarity.overall`。守備位置が「投手」なら
`kind: "pitcher"`、それ以外は `"batter"`。

**player_id**: `<実在選手の英語表記の姓>_<背番号>`（ASCII小文字・数字・_）。ウィットJr.→`witt`、
日本人はヘボン式（大谷→`ohtani`）。カタカナから機械的に起こさず、実在の選手の綴りにする
（例: サーポルト→`saupold`、ウィングローブ→`wingrove`）。ジョブの `renamed_copies` は過去の実行で
付けた名前で、**誤っていることがある**ので参考程度にし、正しい綴りを優先する。

**ステータス**: 等級の文字と数値を両方読み、必ず下の表で突き合わせる。食い違ったら読み違いなので
画像を見直す（数値を等級に合わせて書き換えるのではなく、両方を見直す）。

| 等級 | S | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|---|
| 数値 | 90以上 | 80〜89 | 70〜79 | 60〜69 | 50〜59 | 40〜49 | 20〜39 | 19以下 |

投手の球速は `"154km/h"` の文字列。適性の記号は `◎ ○ △ ー`（横棒は全角長音「ー」）。
野手は「守備適性」行を stats に入れない。

**特殊能力**（右のリスト、上から全行）: 名前は記号（○ ▼ など）も含め表記どおり。右端に等級
バッジがあれば `grade`、なければ `null`。行頭の小さい四角の色で `type`: ピンク＝`plus`、
紫（藤色）＝`minus`、斜めにピンクと紫の2色＝`both`。一番上の行だけ `highlighted: true`。
空の行（暗い行）は書かない。

**投手の変化球**（間違えやすい）:
1. 「1」パネルの球種をすべて `order: 1`。「2」パネルで**明るく**表示されている球種のうち、
   「1」に無いもの（違う箱、または同じ箱でも名前が違うもの）を `order: 2`。**暗い箱は第一球種の
   残像なので書かない。**
2. 箱の左の文字＝`power`、右の黒い四角の文字＝`control`。球種名は表記どおり。画面の端で名前が
   切れているとき（例「シンキング⁝」）は**見えている文字だけ**を書き、補完しない（`notes` に書く）。
3. `category` は**箱の位置**で決める（球種名からは決めない。チェンジアップが右下の箱なら sinker）。
   指示の `pitch_boxes` に、画素で検出した箱の一覧と、右投（`if_right`）・左投（`if_left`）それぞれの
   category が書いてある。**投打を読んでから、各球種がどの箱にあるかを見て、その箱の
   `if_right` か `if_left` をそのまま使う**（左右反転を頭の中でやらない）。検出された箱の数と
   自分が読んだ球種の数が合わなければ、画像を見直す。参考までに対応表:

   | 画面上の箱 | 右投手 | 左投手（画面が左右反転） |
   |---|---|---|
   | 最上段（柄なし） | straight | straight |
   | 2段目・左 | slider | shoot |
   | 2段目・右 | shoot | slider |
   | 3段目・左 | curve | sinker |
   | 3段目・中央 | fork | fork |
   | 3段目・右 | sinker | curve |
4. `break` は目で数えない。straight は `null`、それ以外は仮に `4`（後で `read_break.py` が画素から読む）。

**野手の守備図・コース**: 守備図の「等級＋数値」をすべて `positions` へ。先頭は画面右上の守備位置。
ジョブの `fielding_positions` に、**数値が出ている守備位置（画素で検出）**が書いてある。各数値を
図の上の場所で見て、その一覧の位置コードに割り当てる（一覧にない位置コードは使わない。数値の個数と
一覧の個数が合わなければ画像を見直す）。位置コードと場所: LF=外野・左、CF=外野・中央、RF=外野・右、
3B=内野・左の手前、SS=内野・左の奥、2B=内野・右の奥、1B=内野・右の手前、C=本塁の手前。
2番目以降は順不同。`primary_position`/`primary_grade` は先頭の position と value。
捕手で「捕手リード」の等級があれば `catcher_lead_grade` に、なければ `null`。
得意・苦手コースの3×3の数字を上の行から `zone_grid` へ。`fielding_aptitude` は常に `[]`。

## 写り込みのある画像（指示で ghost が 0.02 以上と書かれたもの）

メニュー画面が薄く重なった、切り替え途中のフレーム。同じ選手のきれいな画像が別にあることが多い。
指示に「既知の選手一覧」があれば、まず背番号・名前（隠れていればOVRや能力）で照合し、
一覧にいる選手なら `{"duplicate_of": "<player_id>", "source_original": "<元画像>"}` だけを書いて終える。
一覧にいなければ通常どおり書き起こし、重なりで読みにくい値は `notes` に書く。
