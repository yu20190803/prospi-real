"""1チーム分のキャプチャを画素だけで仕分けし、書き起こし用の画像を用意する（LLM不要・数秒）。

使い方:
    python3 src/prep_team.py captures/wbc/Australia                 # 仕分け結果を表示するだけ
    python3 src/prep_team.py captures/wbc/Australia --write-skipped # メニュー等を _skipped.json に記録

出力（work/ は .gitignore 済み。ゲーム画像を含むので絶対にコミットしない）:
    work/<cat>/<team>/manifest.json   書き起こす画像の一覧と、スキップした画像の一覧
    work/<cat>/<team>/sheets/*.png    書き起こし用の画像（1枚＝1選手。標準レイアウトに正規化して拡大）
    work/<cat>/<team>/roster.png      選手一覧（メニュー画面）の画像。詳細画面がない選手の確認用

仕分けの考え方（USA 103枚の正解ラベルで全件一致を確認済み）:
    - 処理済み（JSON の source_original/source_capture、_skipped.json にある画像）は対象外
    - 画素が完全に同じ画像は1枚にまとめる。片方が <player_id>.png（過去に改名だけされたコピー）なら
      そのファイル名を player_id の候補として manifest に残す
    - 選手一覧のメニュー画面 … 画面の明るさの特徴で判定
    - 切り替え途中のフレーム … メニュー画面の写り込み率 w（0=選手画面, 1=メニュー）を
      「選手画面の共通部分」と「メニュー画面」の重ね合わせとして最小二乗で求め、w>=0.5 をスキップ
      （選手情報が半分以上消えていて読めない）。w<0.5 は書き起こし対象（同じ選手が複数枚あれば
      merge_team.py が背番号＋名前で重複をまとめ、w の小さい方を残す）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from capture_paths import ROOT, key
from layout import open_std
from pending import load as load_done
from check_pitch_slots import detect as detect_slots, BRIGHT
from check_fielding import detect as detect_fielding

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
RENAMED = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*_\d+(?:_\d+)?\.png$")
ZOOM = 1.5          # 書き起こし用画像の倍率（1.0/1.5/2.0倍で精度差なしを確認。余裕をみて1.5倍）
W_TRANSITION = 0.5  # これ以上メニューが写り込んでいたら「切り替え途中」としてスキップ
W_GHOST = 0.02      # これ以上なら「写り込みあり（要注意）」として manifest に印を付ける

R_MENU = "選手一覧のメニュー画面"
R_TRANS = "選手画面への切り替え途中のフレーム"
FIELD_JA = {"LF": "外野・左", "CF": "外野・中央", "RF": "外野・右", "3B": "内野・左の手前",
            "SS": "内野・左の奥", "2B": "内野・右の奥", "1B": "内野・右の手前", "C": "本塁の手前"}
SLOT_JA = {"top": "最上段", "r2L": "2段目・左", "r2R": "2段目・右",
           "r3L": "3段目・左", "r3C": "3段目・中央", "r3R": "3段目・右"}


def _slots(path: Path) -> dict:
    """投手の変化球の箱（画素で検出）と、右投/左投それぞれの場合の category。野手では無視してよい"""
    from check_pitch_slots import RIGHT, LEFT
    d = detect_slots(path)

    def desc(k):
        if k == "top":
            return {"box": SLOT_JA[k], "if_right": "straight", "if_left": "straight"}
        return {"box": SLOT_JA[k], "if_right": RIGHT[k], "if_left": LEFT[k]}
    order = list(SLOT_JA)
    return {"panel1": [desc(k) for k in order if k in d["p1"]],
            "panel2_bright": [desc(k) for k in order if k in d["p2"] and max(d["p2"][k]) > BRIGHT]}


def _feats(g: np.ndarray) -> tuple[float, float, float]:
    """1/2縮小グレースケール (302x432) から (ヘッダー, 能力リスト下部, ステータス表) の平均輝度"""
    return (float(g[5:25, 150:280].mean()), float(g[150:250, 300:420].mean()),
            float(g[47:150, 107:277].mean()))


def _is_menu(f) -> bool:
    h, ab, st = f
    return st > 120 and ab < 50 and h < 200


def _is_clean_player(f) -> bool:
    h, ab, st = f
    return st < 70 and h > 215


def _menu_weight(g, P, Ps, M) -> float:
    mask = (Ps < 12) & (np.abs(P - M) > 40)
    A = np.stack([P[mask], M[mask], np.ones(int(mask.sum()))], 1)
    c, *_ = np.linalg.lstsq(A, g[mask], rcond=None)
    s = c[0] + c[1]
    return float(c[1] / s) if s > 1e-6 else 1.0


def analyze(team_dir: Path) -> dict:
    rel_dir = team_dir.relative_to(ROOT)
    cat, team = rel_dir.parts[1], rel_dir.parts[2].lower()
    _, _, done = load_done()
    all_files = sorted(p for p in team_dir.iterdir() if p.suffix.lower() in IMG_EXT)
    is_done = {p: key(p.relative_to(ROOT)) in done for p in all_files}

    # 1) 完全一致の重複をまとめる（処理済みの画像とも照合する）
    groups: dict[str, list[Path]] = {}
    std: dict[str, Image.Image] = {}
    for p in all_files:
        im = open_std(p)
        h = hashlib.md5(im.tobytes()).hexdigest()
        groups.setdefault(h, []).append(p)
        std.setdefault(h, im)  # 処理済みの画像も、選手画面・メニュー画面の基準づくりに使う

    skipped, items = [], []
    reps: dict[str, Path] = {}
    hints: dict[str, list[str]] = {}
    for h, ps in groups.items():
        todo = [p for p in ps if not is_done[p]]
        if not todo:
            continue
        done_ps = [p for p in ps if is_done[p]]
        if done_ps:  # 処理済みの画像と同じ（過去の改名コピーなど）
            for p in todo:
                skipped.append({"file": str(p.relative_to(ROOT)),
                                "reason": f"完全に同じ画像の重複（{done_ps[0].name}）"})
            continue
        originals = [p for p in todo if not RENAMED.match(p.name)]
        renamed = [p for p in todo if RENAMED.match(p.name)]
        rep = originals[0] if originals else renamed[0]
        reps[h] = rep
        hints[h] = [p.name for p in renamed if p != rep]
        for p in originals[1:]:
            skipped.append({"file": str(p.relative_to(ROOT)), "reason": f"完全に同じ画像の重複（{rep.name}）"})
        # 改名コピーは merge_team.py で source_capture になるか、別名ならここで重複として記録される

    # 2) メニュー／切り替え途中／選手画面
    gray = {h: np.asarray(im.convert("L").resize((432, 302)), dtype=np.float32) for h, im in std.items()}
    feats = {h: _feats(g) for h, g in gray.items()}
    menus = [h for h in gray if _is_menu(feats[h])]
    cleans = [h for h in gray if _is_clean_player(feats[h])]
    M = np.median(np.stack([gray[h] for h in menus]), 0) if len(menus) >= 3 else None
    if len(cleans) >= 3:
        stack = np.stack([gray[h] for h in cleans])
        P, Ps = np.median(stack, 0), np.std(stack, 0)
    else:
        P = Ps = None

    for h, rep in reps.items():
        relp = str(rep.relative_to(ROOT))
        if h in menus:
            skipped.append({"file": relp, "reason": R_MENU})
            continue
        w = _menu_weight(gray[h], P, Ps, M) if (M is not None and P is not None) else 0.0
        if w >= W_TRANSITION:
            skipped.append({"file": relp, "reason": R_TRANS})
            continue
        items.append({"file": relp, "ghost": round(w, 3), "renamed_copies": hints[h],
                      "pitch_boxes": _slots(rep),
                      "fielding_positions": [f"{k}（{FIELD_JA[k]}）" for k in detect_fielding(rep)],
                      "_h": h})

    out = {"category": cat, "team": team, "team_dir": str(rel_dir), "transcribe": items,
           "skipped": skipped, "roster": None}
    out["_std"], out["_menus"], out["_gray"], out["_M"] = std, menus, gray, M
    return out


def write_outputs(res: dict, work: Path, zoom: float, batch: int = 5) -> None:
    sheets = work / "sheets"
    sheets.mkdir(parents=True, exist_ok=True)
    for it in res["transcribe"]:
        im = res["_std"][it["_h"]]
        sp = sheets / (Path(it["file"]).stem + ".png")
        im.resize((round(im.width * zoom), round(im.height * zoom)), Image.LANCZOS).save(sp)
        it["sheet"] = str(sp.relative_to(ROOT))
    if res["_menus"]:
        M = res["_M"]
        best = min(res["_menus"], key=lambda h: float(np.abs(res["_gray"][h] - M).mean()))
        im = res["_std"][best].crop((0, 0, 865, 330))
        rp = work / "roster.png"
        im.resize((round(865 * 1.6), round(330 * 1.6)), Image.LANCZOS).save(rp)
        res["roster"] = str(rp.relative_to(ROOT))
    # サブエージェントに渡すジョブ（1ファイル＝1サブエージェント分）
    jobs = work / "jobs"
    if jobs.exists():
        shutil.rmtree(jobs)
    jobs.mkdir()
    (work / "json").mkdir(exist_ok=True)
    for pas, sel in (("pass1", [it for it in res["transcribe"] if it["ghost"] < W_GHOST]),
                     ("pass2", [it for it in res["transcribe"] if it["ghost"] >= W_GHOST])):
        for b in range(0, len(sel), batch):
            js = [{"sheet": it["sheet"], "out": str((work / "json" / (Path(it["file"]).name + ".json")).relative_to(ROOT)),
                   "source_original": it["file"], "category": res["category"], "team": res["team"],
                   "ghost": it["ghost"], "renamed_copies": it["renamed_copies"], "pitch_boxes": it["pitch_boxes"],
                   "fielding_positions": it["fielding_positions"]}
                  for it in sel[b:b + batch]]
            (jobs / f"{pas}_{b // batch + 1:02d}.json").write_text(json.dumps(js, ensure_ascii=False, indent=1),
                                                                 encoding="utf-8")
    clean = {k: v for k, v in res.items() if not k.startswith("_")}
    clean["transcribe"] = [{k: v for k, v in it.items() if not k.startswith("_")} for it in res["transcribe"]]
    (work / "manifest.json").write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")


def write_skipped(res: dict) -> int:
    path = ROOT / "data" / res["category"] / res["team"] / "_skipped.json"
    cur = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    have = {key(e["file"]) for e in cur}
    add = [e for e in res["skipped"] if key(e["file"]) not in have]
    if add:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cur + add, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(add)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("team_dir")
    ap.add_argument("--write-skipped", action="store_true")
    ap.add_argument("--zoom", type=float, default=ZOOM)
    ap.add_argument("--batch", type=int, default=5, help="1サブエージェントあたりの画像枚数")
    a = ap.parse_args(argv)
    from capture_paths import resolve
    td = resolve(a.team_dir)
    if td is None or not td.is_dir():
        print(f"フォルダがありません: {a.team_dir}")
        return 1
    res = analyze(td)
    work = ROOT / "work" / res["category"] / res["team"]
    write_outputs(res, work, a.zoom, a.batch)
    n_ghost = sum(1 for it in res["transcribe"] if it["ghost"] >= W_GHOST)
    reasons: dict[str, int] = {}
    for e in res["skipped"]:
        r = "完全に同じ画像の重複" if e["reason"].startswith("完全に同じ") else e["reason"]
        reasons[r] = reasons.get(r, 0) + 1
    print(f"{res['team_dir']}: 書き起こし対象 {len(res['transcribe'])}枚（うち写り込みあり {n_ghost}枚）"
          f" / スキップ {len(res['skipped'])}枚 {reasons}")
    print(f"manifest: {(work / 'manifest.json').relative_to(ROOT)}  roster: {res['roster']}")
    print("jobs: " + " ".join(sorted(p.name for p in (work / "jobs").glob("*.json"))))
    if a.write_skipped:
        print(f"_skipped.json に {write_skipped(res)}件 追記")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
