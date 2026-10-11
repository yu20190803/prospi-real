"""投手の起用適性（先発・中継・抑え）の記号 ◎ ○ △ ー を元キャプチャの画素で照合する。

使い方:
    python src/check_aptitude.py              # 全投手
    python src/check_aptitude.py skubal_27    # 指定した選手だけ

背景（2026-10-11 追加）:
    書き起こしで ◎ を ○ と読む誤りが続いた（Brazil は ◎ が1つも無く、全部 ○ になっていた）。
    記号は形がはっきり違うので、画像を保存せずに数値の特徴だけで判定できる。

判定（標準レイアウト 865x605 で、記号の中心付近 38x36px を切り出す）:
    - 明るい画素（>110）の縦幅が 8px 以下         → ー
    - 上 1/3 の最大幅 ÷ 下 1/3 の最大幅 < 0.6      → △（上がとがっている）
    - 中心から半径 3.5〜6.5px の平均の明るさ ≥ 100 → ◎（内側にもう1つ輪がある）
    - それ以外                                      → ○
    USA・Australia の投手30人（90個）で全件一致。各特徴は境界から十分離れている
    （縦幅: ー 2〜4 / 他 16〜20、上下比: △ 0.33 / 他 0.79以上、内輪: ◎ 146〜159 / ○ 44〜46）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from capture_paths import resolve
from layout import open_std

ROOT = Path(__file__).resolve().parent.parent
ROWS = {"先発適性": 211, "中継適性": 245, "抑え適性": 280}  # 記号の中心の y（x は 463 付近）
X0, X1, HALF_H = 444, 482, 18
SAME = {"－": "ー", "-": "ー", "―": "ー", "◯": "○"}


def classify(tile: np.ndarray) -> str | None:
    m = tile > 110
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return None
    h = ys.max() - ys.min() + 1
    if h <= 8:
        return "ー"
    k = max(1, h // 3)
    top = m[ys.min():ys.min() + k].sum(1).max()
    bot = m[ys.max() - k + 1:ys.max() + 1].sum(1).max()
    if top / bot < 0.6:
        return "△"
    cy, cx = (ys.max() + ys.min()) / 2, (xs.max() + xs.min()) / 2
    yy, xx = np.mgrid[:tile.shape[0], :tile.shape[1]]
    r = np.hypot(yy - cy, xx - cx)
    return "◎" if tile[(r >= 3.5) & (r <= 6.5)].mean() >= 100 else "○"


def detect(capture: Path) -> dict[str, str | None]:
    g = np.asarray(open_std(capture).convert("L"), dtype=float)
    return {label: classify(g[y - HALF_H:y + HALF_H, X0:X1]) for label, y in ROWS.items()}


def check(d: dict) -> list[str]:
    if d.get("kind") != "pitcher":
        return []
    cap = resolve(d["source_capture"])
    if cap is None:
        return [f"元キャプチャがありません: {d['source_capture']}"]
    img = detect(cap)
    dat = {s["label"]: SAME.get(str(s.get("value")), str(s.get("value"))) for s in d.get("stats", [])}
    return [f"{label}: 画像 {img[label]} / データ {dat.get(label)}"
            for label in ROWS if img[label] != dat.get(label)]


def main(argv: list[str]) -> int:
    files = sorted(p for p in (ROOT / "data").rglob("[!_]*.json"))
    if argv:
        files = [p for p in files if p.stem in argv]
    bad = 0
    for p in files:
        errs = check(json.loads(p.read_text(encoding="utf-8")))
        if errs:
            bad += 1
            print(f"[NG] {p.stem}")
            for e in errs:
                print(f"    {e}")
    print(f"\n起用適性の不一致: {bad}人")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
