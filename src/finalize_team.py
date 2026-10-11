"""書き起こし後の仕上げ（変化量の画素読み取り＋全チェック＋サイト生成）を1コマンドで行う。

使い方:
    python3 src/finalize_team.py wbc/brazil     # 1チーム（merge_team.py のあとに実行）
    python3 src/finalize_team.py --all          # 全チーム（コミット前の最終確認）

なぜ1つにまとめたか（2026-10-11）:
    Brazil・Canada の書き起こしでは、手順書にあるチェックと read_break.py --write を
    「画像がない」という誤った判断で丸ごと飛ばし、変化量が仮置きの 4 のまま・箱の位置の誤り・
    特殊能力の誤り・◎を○と読む誤りが残ったままコミットされた。チェックを個別に実行させると
    飛ばされうるので、ここで全部を順に実行し、1件でも NG があれば終了コード 1 で止める。

処理:
    1. 投手の変化球の箱の位置（check_pitch_slots）を照合
    2. 箱の位置が正しい投手だけ、変化量を画素から読んで書き込む（read_break と同じ基準:
       第一・第二パネルで一致し、点灯段が途切れていないものだけ）
    3. 全チェック: validate / 箱の位置 / 変化量 / 特殊能力 / 守備図 / 起用適性 / 元画像の有無
    4. NG 0 のときだけ build_site.py を実行し「完了条件を満たしました」と出す

NG が出たら、その選手の work/<cat>/<team>/sheets/<元ファイル名>.png を見て data/ の JSON を直し、
もう一度このスクリプトを実行する。数値を都合よく変えてエラーを消してはいけない。
このスクリプトが終了コード 0 で終わるまで、そのチームの data/ をコミットしない。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from capture_paths import ROOT, resolve
import check_abilities
import check_aptitude
import check_fielding
import check_pitch_slots
import read_break
import validate


def _players(target: str) -> list[Path]:
    base = ROOT / "data" if target == "--all" else ROOT / "data" / target.strip("/").lower()
    return sorted(base.rglob("[!_]*.json"))


def _write_breaks(path: Path, d: dict) -> int:
    changed = 0
    for r in read_break.read_player(d):
        n1 = r["p1"][0]
        if not r["problems"] and r["pitch"]["break"] != n1:
            r["pitch"]["break"] = n1
            changed += 1
    if changed:
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def finalize(target: str) -> int:
    files = _players(target)
    if not files:
        print(f"データがありません: data/{target}")
        return 1
    ng: dict[str, list[str]] = {}
    written = 0
    for path in files:
        d = json.loads(path.read_text(encoding="utf-8"))
        pid, errs = d.get("player_id", path.stem), []
        if not d.get("source_capture") or resolve(d["source_capture"]) is None:
            ng[pid] = [f"元画像が見つかりません: {d.get('source_capture')}（画像を取り込んでから実行する）"]
            continue
        errs += [f"検証: {e}" for e in validate.validate(path)[0]]
        if d.get("kind") == "pitcher":
            slot_errs = check_pitch_slots.check(d)
            errs += [f"変化球の箱: {e}" for e in slot_errs]
            if not slot_errs:
                written += _write_breaks(path, d)
                d = json.loads(path.read_text(encoding="utf-8"))
                for r in read_break.read_player(d):
                    p = r["pitch"]
                    if r["problems"]:
                        errs.append(f"変化量: {p['name']} {'、'.join(r['problems'])}")
                    elif p["break"] != r["p1"][0]:
                        errs.append(f"変化量: {p['name']} 画像 {r['p1'][0]} / データ {p['break']}")
            errs += [f"起用適性: {e}" for e in check_aptitude.check(d)]
        else:
            errs += [f"守備図: {e}" for e in check_fielding.check(d)]
        errs += [f"特殊能力: {e}" for e in check_abilities.check(d)]
        if d.get("unverified"):
            errs.append(f"推定値が残っている: {d['unverified']}")
        if errs:
            ng[pid] = errs

    print(f"対象 {len(files)}人（data/{'' if target == '--all' else target}）/ 変化量を画素から書き込み {written}球種")
    for pid, errs in ng.items():
        print(f"[NG] {pid}")
        for e in errs:
            print(f"    {e}")
    if ng:
        print(f"\n未完了: NG {len(ng)}人。直してからもう一度実行する（このチームはまだコミットしない）")
        return 1
    subprocess.run([sys.executable, str(ROOT / "src" / "build_site.py")], check=True)
    print("\n完了条件を満たしました（全チェック NG 0）")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(finalize(sys.argv[1]))
