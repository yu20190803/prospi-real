"""投手の変化量（pitches[].break）を元キャプチャの画素から読み取る。

使い方:
    python src/read_break.py              # 全投手: 画像から読んだ値とデータの値を並べて表示
    python src/read_break.py skubal_27    # 指定した選手だけ
    python src/read_break.py --write      # 読み取り値をデータに書き込む（両パネルで一致したものだけ）

なぜ目視をやめたか:
    柄の1段目は箱と同じ色で区切り線がなく、目で数えると段数がぶれる（1段少なく数える等）。
    ここでは柄の7段それぞれの中心の画素を見て、点灯（色つき）か未点灯（暗い灰色）かを判定する。

仕組み:
    - 柄の位置は全キャプチャ共通（865x605）。空の柄の区切り線から7段の中心位置を実測して固定値にした。
      方向ごとに「手前の柄（第一球種 order=1）」と「奥の柄（第二球種 order=2）」の2本がある。
    - 第一パネルと第二パネル（x+291）の両方で読み、一致を確かめる。
      第二パネルでは第一球種が暗く表示されるが、暗い色でも灰色より明るい/彩度が高いので点灯と判定できる。
    - 点灯段は根元から連続しているはず。途中で途切れる読み取りは異常として報告する。

箱の位置（category）が正しいことが前提。先に check_pitch_slots.py を通すこと。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from capture_paths import resolve

ROOT = Path(__file__).resolve().parent.parent
BASE_W, BASE_H = 865, 605
PANEL2_DX = 291
R = 0.7071

# 柄ごとの基準点・向き・7段の中心（基準点からの距離px）。空の柄の区切り線から実測（2026-09-27）
STEMS = {
    ("r2L", 1): ((85, 421), (-1, 0), [7.3, 15.1, 22.9, 30.8, 38.8, 46.8, 53.4]),
    ("r2L", 2): ((85, 431), (-1, 0), [11.3, 19.2, 27.2, 35.2, 43.2, 51.1, 57.5]),
    ("r2R", 1): ((212, 421), (1, 0), [7.9, 15.4, 22.6, 30.2, 38.2, 46.2, 52.9]),
    ("r2R", 2): ((212, 431), (1, 0), [11.8, 19.8, 27.8, 35.8, 43.8, 51.8, 57.6]),
    ("r3C", 1): ((139, 480), (0, 1), [6.3, 14.2, 22.2, 30.2, 38.2, 46.1, 52.8]),
    ("r3C", 2): ((150, 480), (0, 1), [14.3, 22.2, 30.2, 38.2, 46.2, 54.1, 60.5]),
    ("r3L", 1): ((70, 470), (-R, R), [20.3, 29.1, 38.1, 47.1, 55.8, 64.8, 71.8]),
    ("r3L", 2): ((88, 470), (-R, R), [31.5, 40.6, 49.8, 58.6, 67.4, 76.4, 83.5]),
    ("r3R", 1): ((222, 470), (R, R), [23.8, 32.9, 41.8, 50.5, 59.5, 68.5, 75.8]),
    ("r3R", 2): ((208, 470), (R, R), [32.8, 41.6, 50.2, 59.0, 68.2, 77.2, 84.2]),
}
# category → 画面上の枠（右投手）。左投手は左右反転
SLOT_RIGHT = {"slider": "r2L", "shoot": "r2R", "curve": "r3L", "fork": "r3C", "sinker": "r3R"}
SLOT_LEFT = {"slider": "r2R", "shoot": "r2L", "curve": "r3R", "fork": "r3C", "sinker": "r3L"}


def _is_lit(im: np.ndarray, x: float, y: float, d, sx: float, sy: float) -> bool:
    n = (-d[1], d[0])
    vals = []
    for a in (-1.5, 0, 1.5):          # 段の長さ方向
        for b in (-1, 0, 1):          # 幅方向
            px = (x + d[0] * a + n[0] * b) * sx
            py = (y + d[1] * a + n[1] * b) * sy
            vals.append(im[int(round(py)), int(round(px))])
    c = np.mean(vals, axis=0)
    bright, sat = c.max(), c.max() - c.min()
    # 未点灯の段は明るさ45〜60・彩度ほぼ0の灰色(50,50,50)。点灯段は第二パネルで暗く表示されていても
    # 色味が残る（例: 暗い青 (45,57,81) は彩度36）。灰色系の等級(G)や薄い色(S)は明るさで拾う
    return bright > 75 or sat > 20


def read_stem(im: np.ndarray, slot: str, order: int, panel: int) -> tuple[int, str]:
    """(点灯段数, 7段の点灯パターン '■■■□□□□') を返す"""
    (x0, y0), d, centers = STEMS[(slot, order)]
    sx, sy = im.shape[1] / BASE_W, im.shape[0] / BASE_H
    dx = PANEL2_DX if panel == 2 else 0
    lit = [_is_lit(im, x0 + dx + d[0] * t, y0 + d[1] * t, d, sx, sy) for t in centers]
    return int(sum(lit)), "".join("■" if v else "□" for v in lit)


def read_player(d: dict) -> list[dict]:
    im = np.array(Image.open(resolve(d["source_capture"])).convert("RGB")).astype(int)
    table = SLOT_LEFT if d.get("throws_bats", "").startswith("左") else SLOT_RIGHT
    rows = []
    for p in d.get("pitches", []):
        if p["category"] == "straight":
            continue
        slot, order = table[p["category"]], p.get("order", 1)
        n1, pat1 = read_stem(im, slot, order, 1)
        n2, pat2 = read_stem(im, slot, order, 2)
        # 同じ枠に第二球種がある場合、第二パネルでは第二球種の箱が手前に重なり、
        # 第一球種の柄の根元が隠れるので照合に使えない
        shared = order == 1 and any(q.get("order") == 2 and q["category"] == p["category"]
                                    for q in d["pitches"])
        if shared:
            n2, pat2 = None, "（第二球種と重なるため照合対象外）"
        problems = []
        for pat in (pat1, pat2):
            if "□■" in pat:
                problems.append(f"点灯段が途中で途切れている({pat})")
        if n2 is not None and n1 != n2:
            problems.append(f"第一パネル{n1}段と第二パネル{n2}段が不一致")
        if n1 == 0:
            problems.append("点灯段が0（箱の位置か order が違う可能性）")
        rows.append({"pitch": p, "slot": slot, "p1": (n1, pat1), "p2": (n2, pat2), "problems": problems})
    return rows


def main(argv: list[str]) -> int:
    write = "--write" in argv
    ids = [a for a in argv if not a.startswith("--")]
    n_diff = n_prob = 0
    for f in sorted((ROOT / "data").rglob("[!_]*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("kind") != "pitcher" or (ids and d["player_id"] not in ids):
            continue
        rows = read_player(d)
        print(f"{d['player_id']}（{d['throws_bats'][:2]}）")
        changed = False
        for r in rows:
            p, (n1, pat1), (n2, pat2) = r["pitch"], r["p1"], r["p2"]
            mark = "  " if p["break"] == n1 else "≠ "
            print(f"  {mark}{p['name']:<10} order{p.get('order', 1)} {p['category']:<7}"
                  f" 画像 {n1} {pat1} / 第二パネル {'' if n2 is None else n2} {pat2}   データ {p['break']}"
                  + ("   ※" + "、".join(r["problems"]) if r["problems"] else ""))
            n_diff += p["break"] != n1
            n_prob += bool(r["problems"])
            if write and not r["problems"] and p["break"] != n1:
                p["break"] = n1
                changed = True
        if changed:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nデータと画像の不一致: {n_diff}球種 / 読み取りに問題あり: {n_prob}球種"
          + ("（--write で問題のない球種を書き込み済み）" if write else ""))
    return 1 if n_prob else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
