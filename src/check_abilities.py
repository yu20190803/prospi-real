"""特殊能力の「行数」と「行頭アイコンの色（type）」を元キャプチャと機械的に照合する。

使い方:
    python3 src/check_abilities.py            # 全選手
    python3 src/check_abilities.py judge_99   # 指定した選手だけ

判定内容（標準レイアウト 865x605 で実測した座標。layout.open_std で正規化してから読む）:
    - 右の能力リストの各行の行頭アイコン（x 596〜610）が色付きかどうか → 能力の行数
    - アイコンの左上と右下の色: 両方ピンク=plus、両方紫=minus、ピンクと紫の2色=both
    データの abilities の件数・type と一致しなければ報告する（書き漏れ・余分な行・色の読み違い）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from capture_paths import resolve
from layout import open_std

ROOT = Path(__file__).resolve().parent.parent
ROW0, ROW_H, MAX_ROWS = 104.5, 34.55, 14


def _color(px: np.ndarray) -> str | None:
    r, g, b = (float(v) for v in px.reshape(-1, 3).mean(0))
    if r > 200 and b > 200 and r - g > 35:
        return "pink"
    if r < 200 and b > 160 and b - r > 12 and b - g > 15:
        return "purple"
    return None


def detect(capture: Path) -> list[str]:
    """画像の能力リストの type を上から順に返す（空の行で終わり）"""
    a = np.asarray(open_std(capture)).astype(int)
    out = []
    for i in range(MAX_ROWS):
        c = round(ROW0 + ROW_H * i)
        tl, br = _color(a[c - 7:c - 3, 597:602]), _color(a[c + 3:c + 7, 605:610])
        if tl is None and br is None:
            break
        if tl == br:
            out.append("plus" if tl == "pink" else "minus")
        elif tl and br:
            out.append("both")
        else:
            out.append("?")
    return out


def check(d: dict) -> list[str]:
    cap = resolve(d["source_capture"])
    if cap is None:
        return [f"元キャプチャがありません: {d['source_capture']}"]
    img = detect(cap)
    dat = [a.get("type") for a in d.get("abilities", [])]
    errs = []
    if len(img) != len(dat):
        errs.append(f"行数: 画像 {len(img)}行 / データ {len(dat)}件")
    for i, (x, y) in enumerate(zip(img, dat)):
        if x != y:
            name = d["abilities"][i]["name"]
            errs.append(f"{i + 1}行目 {name}: 画像 {x} / データ {y}")
    return errs


def main(argv: list[str]) -> int:
    files = sorted(p for p in (ROOT / "data").rglob("*.json") if not p.name.startswith("_"))
    if argv:
        files = [p for p in files if p.stem in argv]
    bad = 0
    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        errs = check(d)
        if errs:
            bad += 1
            print(f"[NG] {p.stem}")
            for e in errs:
                print(f"    {e}")
    print(f"\n特殊能力の不一致: {bad}人")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
