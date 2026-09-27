# 選手データ JSON スキーマ

`data/<npb|wbc>/<team>/<player_id>.json` の形式。**実データ（`data/wbc/usa/*.json`）と
`src/validate.py` / `src/build_site.py` が前提にしている形式**をここに定義する。
書き起こしの雛形は `docs/templates/pitcher.json` / `docs/templates/batter.json`。
手順は `docs/runbook_transcribe.md` を参照。

## 共通フィールド（投手・野手）

| キー | 型 | 内容 |
|---|---|---|
| `category` | `"npb"` \| `"wbc"` | フォルダ名と一致 |
| `team` | string | チームフォルダ名（英小文字）と一致 |
| `kind` | `"pitcher"` \| `"batter"` | 守備位置が「投手」なら pitcher、それ以外は batter |
| `player_id` | string | ファイル名（拡張子なし）と一致。命名規則は runbook 参照 |
| `source_capture` | string | `captures/<category>/<team>/<player_id>.png` |
| `source_original` | string（任意） | 改名前の元ファイルのパス（例: `captures/npb/giants/IMG_0012.png`）。pending.py が処理済み判定に使う |
| `year` | int | 左上の小さい年度バッジ（例: 2026） |
| `uniform_number` | string | 背番号。**文字列**で持つ（"7", "99"） |
| `name` | string | 画面の選手名をそのまま（例: "ウィットJr."） |
| `position` | string | 画面右上の守備位置（例: "投手", "遊撃手", "右翼手"） |
| `throws_bats` | string | 画面右上の投打（例: "右投右打", "左投右打"） |
| `photo` | null | 常に null（顔写真は扱わない） |
| `rarity` | object | `{"star": true, "overall": <★の右の数値 int>}` |
| `stats` | array | 下記。画面の表示順のまま |
| `abilities` | array | 下記。画面の表示順のまま |
| `unverified` | array（任意） | 推定値を含む項目名。投手は通常 `["pitches[].break"]`。ユーザー確認済みなら削除 |

## `stats`

各要素は次のどちらか。

- 単一値: `{"label": "パワー", "grade": "S", "value": 97}`
  - `grade` は等級バッジ（S, A〜G）。等級がない行は `null`。
  - `value` は数値（int）または画面表示どおりの文字列。
- 対右/対左の分割（野手のミートのみ）:
  `{"label": "ミート", "splits": [{"vs": "対右", "grade": "B", "value": 74}, {"vs": "対左", "grade": "B", "value": 72}]}`

### 投手の stats（この順・このラベル）
```json
[
  {"label": "球速",     "value": "161km/h", "grade": null},
  {"label": "スタミナ", "value": 70,  "grade": "B"},
  {"label": "疲労回復", "value": 77,  "grade": "B"},
  {"label": "先発適性", "value": "◎", "grade": null},
  {"label": "中継適性", "value": "ー", "grade": null},
  {"label": "抑え適性", "value": "ー", "grade": null}
]
```
適性の記号は `◎` `○` `△` `ー` のいずれか（横棒は全角長音「ー」で統一）。

### 野手の stats（この順・このラベル）
`ミート`（splits）, `パワー`, `走力`, `捕球`, `スローイング`, `肩力`, `疲労回復`。
「守備適性」行は stats に含めず、`fielding_diagram` に入れる。

## `abilities`（特殊能力。右側のリスト、上から順に）

```json
{"name": "ケガしにくさ", "grade": "D", "highlighted": false, "type": "plus"}
```
- `name`: 画面の表記どおり。「○」「▼」などの記号も含める（例: "打球反応○", "援護▼"）。
- `grade`: 右端に等級バッジがあれば S/A〜G、なければ `null`。
- `highlighted`: リストの**一番上の行だけ `true`**、他は `false`（画面の選択枠の名残。表示には使わない）。
- `type`: 行頭の小さい四角アイコンの色で決める。
  - ピンク一色 → `"plus"`
  - 紫（濃い藤色）一色 → `"minus"`
  - 斜めにピンクと紫の2色 → `"both"`

## 投手のみ: `pitches`（変化球）

```json
{"category": "slider", "order": 1, "name": "スライダー", "power": "A", "control": "D", "break": 5}
```
- `order`: 画面下部の「1」パネル＝第一球種は `1`、「2」パネルで**新たに現れた**球種は `2`。
  「2」パネルで薄く（暗く）表示されているだけの球種は第一球種の残像なので記録しない。
- `category`: 変化の方向による大分類。**右投手基準**で記録する。

  | 画面上の位置（右投手） | category |
  |---|---|
  | 最上段の単独の箱（柄なし） | `straight` |
  | 2段目・左の箱（柄が左へ） | `slider` |
  | 2段目・右の箱（柄が右へ） | `shoot` |
  | 3段目・左の箱（柄が左下へ） | `curve` |
  | 3段目・中央の箱（柄が真下へ） | `fork` |
  | 3段目・右の箱（柄が右下へ） | `sinker` |

  **左投手（`throws_bats` が「左投」で始まる）は画面が左右反転している**ので、
  左右を入れ替えて記録する（画面で右の箱 → `slider`、左下 → `sinker` など）。
- `power` / `control`: 箱の中の左の文字＝球威、右の黒い四角の中の文字＝制球。
- `break`: 変化量（1〜7）。`straight` は常に `null`。目で数えず `src/read_break.py --write` で画像から読む（runbook 参照）。

## 野手のみ

```json
"fielding_aptitude": [],
"zone_grid": [[0,0,0],[0,0,0],[0,0,0]],
"fielding_diagram": {
  "primary_position": "RF",
  "primary_grade": 52,
  "catcher_lead_grade": null,
  "positions": [
    {"position": "RF", "grade": "D", "value": 52},
    {"position": "CF", "grade": "E", "value": 41}
  ]
}
```
- `fielding_aptitude`: 常に `[]`。
- `zone_grid`: 得意・苦手コースの3×3の数字を上の行から。
- `fielding_diagram.positions`: 守備図に出ている「等級＋数値」をすべて。**先頭は画面右上の守備位置**。
  位置コードは `C`(捕) `1B` `2B` `3B` `SS` `LF` `CF` `RF`。図上の位置で判断する
  （左奥=LF、中央奥=CF、右奥=RF、内野左寄り=SS/3B、右寄り=2B/1B、手前=C）。
- `primary_position` / `primary_grade`: positions 先頭の position と value。
- `catcher_lead_grade`: 捕手で「捕手リード」の等級が出ていればその等級、それ以外は `null`。
