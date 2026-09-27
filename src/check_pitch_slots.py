"""投手の変化球の「位置（category）」を元キャプチャと機械的に照合する。

使い方:
    python src/check_pitch_slots.py            # 全投手
    python src/check_pitch_slots.py skubal_27  # 指定した選手だけ

背景:
    category は球種名ではなく「画面上のどの枠にあるか」で決まる（docs/data_schema.md）。
    例: チェンジアップでも、右下の枠にあれば sinker、真下なら fork。
    名前から推測すると間違えるので、キャプチャの各枠が埋まっているかを色で判定し、
    データの category と一致するかを確かめる。

判定内容:
    - 第一球種パネル: 色のついた枠の集合 == order=1 の変化球の category の集合
    - 第二球種パネル: 明るく表示された枠（第二球種で新しく現れた球種）の集合
      == order=2 の変化球の category の集合（暗い枠は第一球種の残像なので対象外）
    - 直球（最上段）: 第二パネルの最上段が明るい == order=2 の straight がある

枠の座標は 865x605 のキャプチャで実測した値。解像度が違う画像は縮尺を合わせる。
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BASE_W, BASE_H = 865, 605

# 第一球種パネルの枠の中心（左寄りの球威の文字付近）。第二パネルは x+291
SLOTS = {"top": (142, 374), "r2L": (112, 420), "r2R": (182, 420),
         "r3L": (67, 467), "r3C": (140, 467), "r3R": (227, 467)}
PANEL2_DX = 291

# 画面上の枠 → category（右投手基準）。左投手は画面が左右反転している
RIGHT = {"r2L": "slider", "r2R": "shoot", "r3L": "curve", "r3C": "fork", "r3R": "sinker"}
LEFT = {"r2L": "shoot", "r2R": "slider", "r3L": "sinker", "r3C": "fork", "r3R": "curve"}

LIT = 95      # これより明るい画素を「色のついた枠」の画素とみなす
BRIGHT = 140  # 第二パネルで新しい球種とみなす明るさ（実測: 残像は最大127、新球種は最低156）


def _patch(im: Image.Image, cx: int, cy: int):
    sx, sy = im.width / BASE_W, im.height / BASE_H
    px = [im.getpixel((int(x * sx), int(y * sy)))
          for x in range(cx - 26, cx - 12) for y in range(cy - 6, cy + 7)]
    lit = [p for p in px if max(p) > LIT]
    if len(lit) < len(px) * 0.35:
        return None  # 空の枠（暗い灰色）
    return tuple(int(statistics.median(c)) for c in zip(*lit))


def detect(capture: Path) -> dict:
    """{'p1': {枠: 色}, 'p2': {枠: 色}} を返す（空の枠は含めない）"""
    im = Image.open(capture).convert("RGB")
    out = {}
    for name, dx in (("p1", 0), ("p2", PANEL2_DX)):
        out[name] = {k: c for k, (x, y) in SLOTS.items() if (c := _patch(im, x + dx, y))}
    return out


def check(d: dict) -> list[str]:
    cap = ROOT / d["source_capture"]
    if not cap.exists():
        return [f"元キャプチャがありません: {d['source_capture']}"]
    slots = detect(cap)
    table = LEFT if d.get("throws_bats", "").startswith("左") else RIGHT
    pitches = d.get("pitches", [])
    errs = []

    img1 = {table[k] for k in slots["p1"] if k != "top"}
    dat1 = {p["category"] for p in pitches if p.get("order", 1) == 1 and p["category"] != "straight"}
    img2 = {table[k] for k, c in slots["p2"].items() if k != "top" and max(c) > BRIGHT}
    dat2 = {p["category"] for p in pitches if p.get("order") == 2 and p["category"] != "straight"}
    new_straight = "top" in slots["p2"] and max(slots["p2"]["top"]) > BRIGHT
    has_straight2 = any(p.get("order") == 2 and p["category"] == "straight" for p in pitches)

    def diff(label, img, dat):
        if img != dat:
            errs.append(f"{label}: 画像={sorted(img)} データ={sorted(dat)}"
                        + (f"  画像にあってデータにない={sorted(img - dat)}" if img - dat else "")
                        + (f"  データにあって画像にない={sorted(dat - img)}" if dat - img else ""))
    diff("第一球種の変化球の位置", img1, dat1)
    diff("第二球種で新しく出た変化球の位置", img2, dat2)
    if new_straight != has_straight2:
        errs.append(f"第二球種の直球: 画像={'あり' if new_straight else 'なし'} データ={'あり' if has_straight2 else 'なし'}")
    return errs


def main(argv: list[str]) -> int:
    files = sorted((ROOT / "data").rglob("*.json"))
    if argv:
        files = [f for f in files if f.stem in argv]
    n_err = 0
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("kind") != "pitcher":
            continue
        errs = check(d)
        print(f"[{'NG' if errs else 'OK'}] {d['player_id']}（{d['throws_bats'][:2]}）")
        for e in errs:
            print("    " + e)
        n_err += bool(errs)
    print(f"\n位置の不一致: {n_err}人")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
