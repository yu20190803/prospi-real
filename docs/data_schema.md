# 選手データ JSON スキーマ

`data/<npb|wbc>/<team>/<player_id>.json` の形式。**投手 (`kind: "pitcher"`) と
野手 (`kind: "batter"`) でフィールド構成が大きく異なる**ため、それぞれ別セクションで示す。
`kind` によって `src/generate.py` が使うテンプレートを切り替える
（`player_card_pitcher.html.jinja` / `player_card_batter.html.jinja`）。
ヘッダー部分（背番号・年度・選手名・守備位置・投打・★とOVR）は両者共通で、
`src/templates/_header.html.jinja` を共有する。

## 投手データ

添付サンプル画像（WBC USA #62 ウェブ）を例に、画面上のどの要素がどのフィールドに
対応するかを示す。

```jsonc
{
  "category": "wbc",              // "npb" | "wbc"
  "team": "usa",                  // チームディレクトリ名と一致させる
  "kind": "pitcher",              // "pitcher" | "batter"
  "player_id": "web_62",          // ファイル名（拡張子抜き）と一致させる
  "source_capture": "captures/wbc/usa/web_62.png",

  "year": 2026,                   // 左上の小さい年度バッジ
  "uniform_number": "62",         // 左上の大きい背番号バッジ
  "name": "ウェブ",                // 選手名
  "position": "投手",              // 右上の守備位置
  "throws_bats": "右投右打",        // 右上の投打
  "photo": null,                  // 顔写真のパス（未着手ならnull。著作物なので扱いは要相談）

  "rarity": {
    "star": true,                 // 星アイコンの有無
    "overall": 483                // 星の右のオレンジ数値（OVR）
  },

  "stats": [
    // 表示順のまま配列で保持する。grade は A〜E などの等級、value は数値/記号。
    { "label": "球速",     "value": "153km/h", "grade": null },
    { "label": "スタミナ",  "value": 84,        "grade": "A" },
    { "label": "疲労回復",  "value": 88,        "grade": "A" },
    { "label": "先発適性",  "value": "◎",       "grade": null },
    { "label": "中継適性",  "value": "ー",       "grade": null },
    { "label": "抑え適性",  "value": "ー",       "grade": null }
  ],

  "pitch_groups": [
    // 画面下部の「1」「2」パネル。各パネルは中心から変化方向へ
    // ゲージが伸びる放射状レイアウトなので、slot に position を持たせる。
    {
      "group_number": 1,
      "slots": [
        // position: top | left | right | bottom
        // amount:   変化量（ラダーゲージの segments 数。1〜5想定）
        { "position": "top",    "name": "ツーシーム",   "grades": ["B", "B"], "amount": 3 },
        { "position": "left",   "name": "スライダー",   "grades": ["B", "B"], "amount": 3 },
        { "position": "bottom", "name": "チェンジアップ", "grades": ["B", "B"], "amount": 3 }
      ]
    },
    {
      "group_number": 2,
      "slots": [
        { "position": "top",    "name": "ストレート",  "grades": ["E", "B"], "amount": 4 },
        { "position": "left",   "name": "カットボール", "grades": ["E", "C"], "amount": 3 },
        { "position": "bottom", "name": "",           "grades": ["B", "B"], "amount": 3 }
      ]
    }
  ],

  "abilities": [
    // 右側の特殊能力リスト。表示順のまま。
    // active: アイコンが色付き（習得済み）か灰色（未習得）か
    // highlighted: 現在選択中を示す青枠があるか（画面キャプチャ時点の状態。基本false）
    { "name": "ケガしにくさ", "grade": "B", "active": true,  "highlighted": true },
    { "name": "対ピンチ",     "grade": "D", "active": false, "highlighted": false },
    { "name": "クイック",     "grade": "B", "active": true,  "highlighted": false },
    { "name": "打たれ強さ",   "grade": "D", "active": false, "highlighted": false },
    { "name": "対左打者",     "grade": "D", "active": false, "highlighted": false },
    { "name": "奪三振",       "grade": null, "active": false, "highlighted": false },
    { "name": "逃げ球",       "grade": null, "active": false, "highlighted": false },
    { "name": "リリース",     "grade": null, "active": false, "highlighted": false },
    { "name": "球持ち",       "grade": null, "active": false, "highlighted": false },
    { "name": "打球反応○",    "grade": null, "active": false, "highlighted": false },
    { "name": "ゴロピッチャー", "grade": null, "active": true,  "highlighted": false, "icon": "flag" }
  ]
}
```

## 投手データのフィールド補足

- `stats[].grade` … `A`〜`E` の等級バッジがある行のみ設定。ない行（球速・適性など）は `null`。
- `pitch_groups[].slots[]` … 球種は「変化方向」ごとのスロットとして持つ。
  **`position` の割り当てと `amount` の値はキャプチャからの推定であり、未確定。**
  ゲーム内の実際の方向定義（8方向あるのか4方向なのか、ラダーの段数が何を
  表すのか）が判明したら、ここを直してから全選手のデータを入れ直すこと。
- 球種の等級は**等級色の塗り箱に白文字**で表示される（ステータス欄の等級は
  背景なしの色付き文字）。同じ等級でも表現が違う点に注意。
- `abilities[].icon` … 通常のグレードバッジ以外の特殊表示（チェックマーク的な
  アイコンなど）がある場合のみ設定。
- 数値・文字列とも「画面に表示されている通り」を書き起こす。単位や記号
  （`km/h`, `◎`, `ー`）も削らない。

## 野手データ

添付サンプル画像（WBC USA #29 ローリー・捕手）を例にする。ヘッダー
（`year`〜`rarity`）は投手と共通なので省略し、野手固有の部分だけ示す。

```jsonc
{
  "category": "wbc",
  "team": "usa",
  "kind": "batter",
  "player_id": "raleigh_29",
  "source_capture": "captures/wbc/usa/raleigh_29.png",

  "year": 2026,
  "uniform_number": "29",
  "name": "ローリー",
  "position": "捕手",
  "throws_bats": "右投両打",
  "photo": null,
  "rarity": { "star": true, "overall": 458 },

  "stats": [
    // ミートのみ対右/対左でsplitsを持つ。他は投手と同様にgrade+valueの単一行。
    {
      "label": "ミート",
      "splits": [
        { "vs": "対右", "grade": "E", "value": 49 },
        { "vs": "対左", "grade": "D", "value": 53 }
      ]
    },
    { "label": "パワー",     "grade": "S", "value": 91 },
    { "label": "走力",       "grade": "D", "value": 53 },
    { "label": "捕球",       "grade": "E", "value": 46 },
    { "label": "スローイング", "grade": "C", "value": 66 },
    { "label": "肩力",       "grade": "A", "value": 82 },
    { "label": "疲労回復",   "grade": "B", "value": 73 }
  ],

  // 守備適性: ポジションごとのアイコン行。サンプル画像では空欄表示だったため
  // 現状は未着手。中身が判明したら { "position": "一塁", "grade": "B" } 等の配列にする。
  "fielding_aptitude": [],

  // 得意・苦手コース: 3x3のストライクゾーングリッド（上から見た並び順）。
  "zone_grid": [
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0]
  ],

  // 画面下部のダイヤモンド図。捕手以外は catcher_lead_grade を null にする。
  "fielding_diagram": {
    "primary_position": "C",
    "primary_grade": 67,
    "catcher_lead_grade": "C"
  },

  "abilities": [
    { "name": "アーチスト",   "grade": null, "active": true,  "highlighted": true },
    { "name": "ケガしにくさ", "grade": "C",  "active": false, "highlighted": false },
    { "name": "バント",      "grade": "D",  "active": false, "highlighted": false },
    { "name": "チャンス",    "grade": "D",  "active": false, "highlighted": false },
    { "name": "走塁",       "grade": "E",  "active": false, "highlighted": false },
    { "name": "盗塁",       "grade": "D",  "active": false, "highlighted": false },
    { "name": "存在感",     "grade": null, "active": false, "highlighted": false },
    { "name": "満塁男",     "grade": null, "active": false, "highlighted": false },
    { "name": "連発",       "grade": null, "active": false, "highlighted": false },
    { "name": "初球",       "grade": null, "active": false, "highlighted": false },
    { "name": "逆境",       "grade": null, "active": false, "highlighted": false },
    { "name": "悪球打ち",   "grade": null, "active": false, "highlighted": false },
    { "name": "プルヒッター", "grade": null, "active": true, "highlighted": false, "icon": "flag" },
    { "name": "死球",       "grade": null, "active": true,  "highlighted": false, "icon": "flag" }
  ]
}
```

## 野手データのフィールド補足

- `stats[]` は要素ごとに **単一値（`grade`+`value`）** か **`splits`（対右/対左などの
  複数行）** のどちらかを持つ。両方同時には持たせない。
- `zone_grid` は行×列 = 3×3固定。値の意味（本数なのか評価なのか）は現時点では
  不明なため、画面表示の数値をそのまま書き起こす。
- `fielding_diagram.catcher_lead_grade` は捕手（`position == "捕手"`）のときだけ
  値を持つ。捕手以外は `null` にしてテンプレート側で行ごと非表示にする。
- `abilities` の構造・`icon` フィールドの意味は投手データと共通。
