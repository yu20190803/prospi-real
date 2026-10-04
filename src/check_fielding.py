"""野手の守備図の「どの守備位置に数値が出ているか」を元キャプチャと機械的に照合する。

使い方:
    python3 src/check_fielding.py            # 全野手
    python3 src/check_fielding.py anthony_3  # 指定した選手だけ

守備図の数値は守備位置ごとに決まった場所に表示される（標準レイアウト 865x605 で実測。
USA・Australia の野手25人で、出ている位置は白い数字の画素が119以上、出ていない位置は0と完全に分かれる）。
データの fielding_diagram.positions の位置の集合が、画像で数値が出ている位置の集合と一致するかを確かめる。
位置の取り違え（外野の右を 2B にする等）は目視では起きやすいので、prep_team.py もこの検出結果を
書き起こしの指示に含める。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from capture_paths import resolve
from layout import open_std

ROOT = Path(__file__).resolve().parent.parent
# 数値（白い数字）の中心
ANCHORS = {"LF": (321, 456), "CF": (414, 427), "RF": (517, 456), "3B": (325, 533),
           "SS": (350, 493), "2B": (486, 493), "1B": (513, 533), "C": (418, 577)}
MIN_WHITE = 50


def detect(capture: Path) -> list[str]:
    a = np.asarray(open_std(capture)).astype(int)
    out = []
    for k, (x, y) in ANCHORS.items():
        w = a[y - 12:y + 12, x - 30:x + 30]
        if int((w.min(2) > 200).sum()) >= MIN_WHITE:
            out.append(k)
    return out


def check(d: dict) -> list[str]:
    cap = resolve(d["source_capture"])
    if cap is None:
        return [f"元キャプチャがありません: {d['source_capture']}"]
    img = set(detect(cap))
    dat = {p["position"] for p in d.get("fielding_diagram", {}).get("positions", [])}
    if img == dat:
        return []
    return [f"守備位置: 画像={sorted(img)} データ={sorted(dat)}"
            f"  データにあって画像にない={sorted(dat - img)} 画像にあってデータにない={sorted(img - dat)}"]


def main(argv: list[str]) -> int:
    files = sorted(p for p in (ROOT / "data").rglob("*.json") if not p.name.startswith("_"))
    if argv:
        files = [p for p in files if p.stem in argv]
    bad = 0
    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("kind") != "batter":
            continue
        errs = check(d)
        if errs:
            bad += 1
            print(f"[NG] {p.stem}")
            for e in errs:
                print(f"    {e}")
    print(f"\n守備位置の不一致: {bad}人")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
