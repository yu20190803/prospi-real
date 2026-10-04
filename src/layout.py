"""キャプチャを「標準レイアウト（865x605 の選手詳細パネル）」にそろえて開く。

画面座標を前提にするスクリプト（check_pitch_slots.py / read_break.py / prep_team.py）は、
画像を直接 Image.open せず、必ず open_std() を通す。

既知のレイアウト:
- 865x605  … 標準（WBC各国、2026-08 撮影分）。そのまま使う。
- 1150x695 … 左に選手一覧のサイドバーが付いた画面（Japan_2006/2009/2023/2026、2026-09 撮影分）。
             選手詳細パネルは等倍で (279, 8) から 865x605 の位置にある（全4チームで実測一致）。
上記以外のサイズは従来どおり 865x605 に縮尺を合わせる（レイアウトが違えば座標はずれるので要確認）。
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

STD_W, STD_H = 865, 605
CROPS = {
    (1150, 695): (279, 8),
}


def open_std(path: str | Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if im.size == (STD_W, STD_H):
        return im
    if im.size in CROPS:
        x, y = CROPS[im.size]
        return im.crop((x, y, x + STD_W, y + STD_H))
    return im.resize((STD_W, STD_H))
