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

画素読み取りの構造的不一致（2026-10-12 追加。docs/runbook_transcribe.md「4. チェック」参照）:
    第一パネルと第二パネルで変化量の段数が食い違うが、データ側ではなく画像側の問題であるもの。
    G 等級などの灰色に近い柄が、第二パネルで暗く表示されると点灯判定のしきい値に届かなくなる
    （Brazil の aparecido_23 シンキング・monteiro_59 チェンジアップで実測）。次をすべて満たすときだけ該当とし、
    第一パネルの値を採用して unverified と break_panel_mismatch（画素値と判断根拠）を記録する。
    完了判定はブロックしない（報告で「要目視確認」として一覧にする）。
      1. 問題が「第一パネルX段と第二パネルY段が不一致」だけで、X > Y（第二パネルが少なく読んでいる）
      2. 第一パネルの点灯段が根元から連続し、各段が明るさ 90 以上または彩度 20 以上（背景は 48〜52 / 0〜2）
      3. 第二パネルで読めなかった段が、同じ柄の確実に未点灯の段（X+2段目〜6段目）より
         彩度 +4 以上かつ明るさ +3 以上高い（背景に完全に同化していない）
    固定のしきい値で「背景より高い」を判定しないのは、正常な画像でも点灯段のすぐ次の段に色のにじみがあり、
    明るさ 61・彩度 16 まで上がるため（USA・Australia の全投手で実測）。同じ柄の中で比べる。
    「点灯段が途中で途切れている」「点灯段が0」、箱の位置・特殊能力・守備図・起用適性・validate の NG は
    従来どおりブロックする。

NG が出たら、その選手の work/<cat>/<team>/sheets/<元ファイル名>.png を見て data/ の JSON を直し、
もう一度このスクリプトを実行する。数値を都合よく変えてエラーを消してはいけない。
このスクリプトが終了コード 0 で終わるまで、そのチームの data/ をコミットしない。
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
from pathlib import Path

import numpy as np

from capture_paths import ROOT, resolve
from layout import open_std
import check_abilities
import check_aptitude
import check_fielding
import check_pitch_slots
import read_break
import validate


def _players(target: str) -> list[Path]:
    base = ROOT / "data" if target == "--all" else ROOT / "data" / target.strip("/").lower()
    return sorted(base.rglob("[!_]*.json"))


LIT1_BRIGHT, LIT1_SAT = 90, 20      # 条件2: 第一パネルの点灯段
DIFF_SAT, DIFF_BRIGHT = 4, 3         # 条件3: 同じ柄の未点灯段との差


def structural_mismatch(im: np.ndarray, r: dict) -> dict | None:
    """read_break の1球種の結果 r が「画素読み取りの構造的不一致」なら、記録用の dict を返す。違えば None"""
    (n1, pat1), (n2, _) = r["p1"], r["p2"]
    if n2 is None or not (n1 > n2 > -1) or "□■" in pat1:
        return None
    if [p for p in r["problems"] if "パネル" not in p or "不一致" not in p]:
        return None  # 途切れ・0段など、ほかの問題が混ざっている
    order = r["pitch"].get("order", 1)
    v1 = read_break.stem_values(im, r["slot"], order, 1)
    v2 = read_break.stem_values(im, r["slot"], order, 2)
    if not all(b >= LIT1_BRIGHT or s >= LIT1_SAT for b, s in v1[:n1]):
        return None
    ref = v2[n1 + 1:6]  # 点灯段のすぐ次（にじみ）と先端（暗い）を除いた未点灯段
    if not ref:
        return None
    ref_sat, ref_bright = max(s for _, s in ref), statistics.median(b for b, _ in ref)
    if not all(s >= ref_sat + DIFF_SAT and b >= ref_bright + DIFF_BRIGHT for b, s in v2[n2:n1]):
        return None
    fmt = lambda vs: [f"{b:.0f}/{s:.0f}" for b, s in vs]
    return {"pitch": r["pitch"]["name"], "category": r["pitch"]["category"], "order": order,
            "panel1": n1, "panel2": n2, "adopted": n1,
            "panel1_pixels": fmt(v1), "panel2_pixels": fmt(v2),
            "reason": (f"第一パネルの点灯{n1}段は明確（明るさ/彩度 {', '.join(fmt(v1[:n1]))}）。"
                       f"第二パネルの{n2 + 1}〜{n1}段目はしきい値（明るさ75・彩度20）未満だが、同じ柄の未点灯段"
                       f"（彩度最大{ref_sat:.0f}・明るさ中央値{ref_bright:.0f}）より高い（{', '.join(fmt(v2[n2:n1]))}）。"
                       f"暗い色の柄が第二パネルで背景に近くなる画像側の問題と判断し、第一パネルの値を採用")}


def _write_breaks(path: Path, d: dict) -> tuple[int, list[dict]]:
    """変化量を画素から書き込む。構造的不一致の球種は第一パネルの値を採用して記録する"""
    im = np.array(open_std(resolve(d["source_capture"]))).astype(int)
    changed, structural = 0, []
    for r in read_break.read_player(d):
        n1 = r["p1"][0]
        sm = structural_mismatch(im, r) if r["problems"] else None
        if sm:
            structural.append(sm)
        if (not r["problems"] or sm) and r["pitch"]["break"] != n1:
            r["pitch"]["break"] = n1
            changed += 1
    # 構造的不一致の記録は毎回画素から作り直す（古い記録や手書きの記録は信用しない）
    before = (d.get("unverified"), d.get("break_panel_mismatch"))
    unv = [u for u in d.get("unverified", []) if u != "pitches[].break"]
    if structural:
        d["unverified"] = unv + ["pitches[].break"]
        d["break_panel_mismatch"] = structural
    else:
        d.pop("break_panel_mismatch", None)
        if unv:
            d["unverified"] = unv
        else:
            d.pop("unverified", None)
    if changed or before != (d.get("unverified"), d.get("break_panel_mismatch")):
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed, structural


def finalize(target: str) -> int:
    files = _players(target)
    if not files:
        print(f"データがありません: data/{target}")
        return 1
    ng: dict[str, list[str]] = {}
    review: list[str] = []  # 画素読み取りが構造的に不一致だった箇所（ブロックしないが要目視確認）
    written = 0
    for path in files:
        d = json.loads(path.read_text(encoding="utf-8"))
        pid, errs = d.get("player_id", path.stem), []
        if not d.get("source_capture") or resolve(d["source_capture"]) is None:
            ng[pid] = [f"元画像が見つかりません: {d.get('source_capture')}（画像を取り込んでから実行する）"]
            continue
        errs += [f"検証: {e}" for e in validate.validate(path)[0]]
        structural: list[dict] = []
        if d.get("kind") == "pitcher":
            slot_errs = check_pitch_slots.check(d)
            errs += [f"変化球の箱: {e}" for e in slot_errs]
            if not slot_errs:
                n, structural = _write_breaks(path, d)
                written += n
                d = json.loads(path.read_text(encoding="utf-8"))
                exempt = {(s["category"], s["order"]) for s in structural}
                for r in read_break.read_player(d):
                    p = r["pitch"]
                    if (p["category"], p.get("order", 1)) in exempt:
                        continue
                    if r["problems"]:
                        errs.append(f"変化量: {p['name']} {'、'.join(r['problems'])}")
                    elif p["break"] != r["p1"][0]:
                        errs.append(f"変化量: {p['name']} 画像 {r['p1'][0]} / データ {p['break']}")
            errs += [f"起用適性: {e}" for e in check_aptitude.check(d)]
        else:
            errs += [f"守備図: {e}" for e in check_fielding.check(d)]
        errs += [f"特殊能力: {e}" for e in check_abilities.check(d)]
        unv = [u for u in d.get("unverified", []) if not (structural and u == "pitches[].break")]
        if unv:
            errs.append(f"推定値が残っている: {unv}")
        if errs:
            ng[pid] = errs
        for s in structural:
            review.append(f"{pid} {s['pitch']}（order{s['order']}）: 第一パネル{s['panel1']}段 / 第二パネル{s['panel2']}段"
                          f" → {s['adopted']}段を採用。第一パネル {s['panel1_pixels'][:s['panel1']]}、"
                          f"第二パネル {s['panel2_pixels'][s['panel2']:s['panel1']]}（明るさ/彩度）")

    print(f"対象 {len(files)}人（data/{'' if target == '--all' else target}）/ 変化量を画素から書き込み {written}球種")
    for pid, errs in ng.items():
        print(f"[NG] {pid}")
        for e in errs:
            print(f"    {e}")
    if review:
        print(f"\n■ 画素読み取りが構造的に不一致だった箇所（{len(review)}球種・完了判定はブロックしない・要目視確認）")
        for x in review:
            print(f"    {x}")
    if ng:
        print(f"\n未完了: NG {len(ng)}人。直してからもう一度実行する（このチームはまだコミットしない）")
        return 1
    subprocess.run([sys.executable, str(ROOT / "src" / "build_site.py")], check=True)
    print("\n完了条件を満たしました（全チェック NG 0"
          + (f"。構造的不一致 {len(review)}球種は報告に載せて目視確認を依頼する）" if review else "）"))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(finalize(sys.argv[1]))
