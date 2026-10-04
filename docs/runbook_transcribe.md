# 書き起こし手順書（定期実行・別モデル・別セッション向け）

PCの `C:\dev\claude\prospi-real\captures\<npb|wbc>\<Team>\` に置かれたスクリーンショットを、
1回の作業で1チームずつ `data/` に書き起こす手順。**この手順書の通りに進めれば、どのモデルでも
同じ品質になるように書いている。判断に迷う点は「迷ったとき」に従い、勝手に仕様を変えない。**

関連: `CLAUDE.md`（方針）、`docs/transcribe_guide.md`（1枚の読み方。サブエージェントが読む）、
`docs/data_schema.md`（JSONの定義）、`docs/grades.md`（等級）。

## 考え方（2026-10-04 見直し: 1チーム30分 → 数分、品質は同等以上）

- **LLMに画像を読ませるのは「選手画面を1人1回」だけ**。メニュー画面・切り替え途中のフレーム・
  完全に同じ画像は `src/prep_team.py` が画素で仕分ける（USAの正解ラベル103枚で全件一致）。
- **書き起こしはサブエージェントに並列で任せる**（1サブエージェント5枚まで）。メインの会話に
  選手画像を溜めないので、トークンも時間も大きく減る。
- **画素で確かめられるものは全部スクリプトで照合する**: 変化球の箱の位置（check_pitch_slots）、
  変化量（read_break）、特殊能力の行数とアイコンの色（check_abilities）、守備図の位置（check_fielding）、
  等級と数値の整合（validate）。書き起こし側には検出結果をヒントとして渡す。
- 読み取り画像の倍率は 1.5倍（1.0/1.5/2.0倍で同じ8人を書き起こし、精度差がないことを確認済み）。

## 0. 準備

1. `add_repo`（access: push）で `yu20190803/prospi-real` を追加し、`/home/claude/prospi-real` に clone。
2. `cd /home/claude/prospi-real && pip install -r requirements.txt --break-system-packages`
3. PCにリンクされていること（`mcp__remote-devices__*` が使え、`get_device_info` の
   `connectedFolders` に `C:\dev\claude\prospi-real` がある）。なければ
   「PCのcapturesフォルダにアクセスできないため今回は何もしませんでした」と報告して終了
   （`device_request_folder_access` は呼ばない）。
4. この手順書と `CLAUDE.md` を読む。`docs/transcribe_guide.md` はサブエージェントが読むので、
   メインは読まなくてよい（fallback で自分が書き起こすときだけ読む）。

## 1. 対象チームを決めて取り込む

1. `device_list_dir` で `C:\dev\claude\prospi-real\captures\wbc`（と `npb` があればそれも）を
   **再帰なしで**一覧し、チームフォルダ名を得る（再帰一覧は900件超になり重いので使わない）。
2. `python3 src/pending.py --done-count` で、チームごとの「処理済みとして記録された画像の数」を見る。
3. チームフォルダ名の順に、`device_list_dir`（再帰なし）でそのフォルダの画像数を数え、
   記録数より多いチーム（＝未処理がある）を最初に見つけたら、それを今回のチームにする。
   全チームで一致していれば「全チームの書き起こしが完了しました」と報告して終了（何もコミットしない）。
4. そのチームのフォルダの**画像をすべて**（処理済みも含めて。重複判定に使う）`device_stage_files` で
   取り込む（1回50件まで。超えたら分ける）。届き先は `/mnt/user-data/uploads/prospi-real/captures/...`。
5. `ln -sfn /mnt/user-data/uploads/prospi-real/captures /home/claude/prospi-real/captures`
   （`captures` は .gitignore 済み。公開リポジトリには入らない）

チームのフォルダ名は `USA`・`Australia` のように大文字を含むことがある。データ側（`team`・`data/` の
フォルダ・`source_capture`）は常に英小文字。スクリプトは大文字小文字を無視して解決する。

## 2. 仕分け（スクリプト・数秒）

```bash
python3 src/prep_team.py captures/wbc/<Team> --write-skipped
```
- メニュー画面・切り替え途中（写り込み率 w≥0.5）・完全に同じ画像を `_skipped.json` に記録する。
- 書き起こし対象を `work/wbc/<team>/jobs/pass1_NN.json`（きれいな画像）と `pass2_NN.json`
  （写り込みのある画像 0.02≤w<0.5）に5枚ずつ分ける。読み取り画像は `work/.../sheets/`。
- 選手一覧（メニュー画面）は `work/.../roster.png`。
- `work/` は .gitignore 済み（ゲーム画像を含むので絶対にコミットしない）。

## 3. 書き起こし（サブエージェント並列）

**pass1 のジョブファイル1つにつきサブエージェント1つを、1回のメッセージでまとめて起動する**（並列実行）。
モデルは指定しない（このセッションと同じモデル。品質を下げないため軽いモデルにしない）。プロンプト:

```
You are transcribing プロ野球スピリッツ (baseball game) player screenshots into JSON. Work in /home/claude/prospi-real.
1. Read docs/transcribe_guide.md fully and follow it exactly.
2. Read the job file <ジョブファイルのパス> (a JSON list of jobs). For each job: Read its `sheet` image (once; re-read only if genuinely unsure), then write one JSON file to its `out` path with the Write tool, as the guide specifies, using the job's category, team, source_original, pitch_boxes, fielding_positions and renamed_copies.
Do not open anything under data/ or captures/, or other job files. Do not run scripts.
3. Reply with one line per job: "<out> <player_id> #<number> <name>", then any notes. Under 100 words.
```

全員終わったら:
```bash
python3 src/merge_team.py work/wbc/<team>
```
同じ選手（背番号＋名前）の重複をまとめて `data/wbc/<team>/` に書き、改名コピー `<player_id>.png` を作り、
`work/.../known_players.txt`（既知の選手一覧）を出す。「問題」が出たら、そのジョブだけやり直す。

**pass2 のジョブがあれば**、同様にサブエージェントを起動する（プロンプトの 2. の前に
`Read work/wbc/<team>/known_players.txt (players already transcribed). For each job, follow the guide's
last section about ghost images: if the player is in that list, write only the duplicate_of JSON.` を足す）。
終わったら `merge_team.py` をもう一度実行する（取り込み済みの結果は `json_merged/` に移るので二重にならない）。

**Agent ツールが使えない場合**は、メインが `docs/transcribe_guide.md` を読み、ジョブファイルを順に
自分で処理する（手順と品質基準は同じ）。

## 4. チェック（すべて通るまで直す）

```bash
python3 src/validate.py           # エラー0件（等級と数値の整合など）
python3 src/check_pitch_slots.py  # 位置の不一致0人（変化球の箱の位置・書き漏れ）
python3 src/check_abilities.py    # 不一致0人（特殊能力の行数・アイコンの色）
python3 src/check_fielding.py     # 不一致0人（守備図の位置）
python3 src/read_break.py --write && python3 src/read_break.py   # 「不一致0球種 / 問題あり0球種」
python3 src/build_site.py
```
- NG が出た選手だけ、その選手の `work/.../sheets/<元ファイル名>.png` を Read で見て `data/` の JSON を直す。
  **エラーを消すために数値を都合よく変えない。** 画像と食い違うのはデータ側の読み違い。
- `merge_team.py` が出した「読み取りに自信がない箇所（notes）」も、その画像を見て確かめる。
  決められないものは報告に残す。

## 5. 選手一覧との照合

`work/.../roster.png`（1枚）を Read で見て、`known_players.txt` にいない選手を
「一覧にいるのに詳細画面がない選手」として報告する。日本代表のサイドバー画面など roster が
無いチームは「対象外」とする。

## 6. 反映

1. 改名コピーをPCへ: `python3 src/merge_team.py work/wbc/<team> --outputs /mnt/user-data/outputs/prospi-real`
   を実行すると（新しい結果がなくても）`work/.../commit_files.json` に一覧ができる。その中身をそのまま
   `device_commit_files` に渡す（元ファイルは消さない・上書きしない）。
   ※ merge を最後に実行したときの一覧なので、pass2 のあとに `--outputs` 付きで1回実行すればよい。
2. GitHub（prospi-real、公開）: `data/` と `site/index.html` をコミットして push。
   **push 前に `git status --short` で `captures`・`work`・画像ファイルが含まれていないことを確認する。**
   拒否されたら `git pull --rebase` してから push。強制 push はしない。push に失敗しても処理は止めない
   （次回は別の未処理チームに進む設計）。成否は報告に書く。

## 7. 報告（短く、日本語で）

- 処理したチームと追加人数（投手・野手の内訳）、スキップ枚数と理由の内訳
- 一覧にいるのに詳細画面がない選手
- 読み取りに自信がない箇所（選手・項目・読んだ値・理由）、チェックで残った問題
- GitHub への push の成否、残りのチーム数

## 迷ったとき

- 読めない値は推測で埋めず、いちばん近い読み値を入れて報告に載せる。
- スキーマにない情報が出てきたら、JSON に勝手なキーを足さずに報告する。
- テンプレート・CSS・スクリプトは定期実行では変更しない。画面のレイアウトや解像度が変わって
  スクリプトの座標が合わなくなった（チェックが大量にNGになる）場合は、無理に直さず報告する
  （`src/layout.py` に新しいレイアウトの切り出し位置を足す作業が必要）。
