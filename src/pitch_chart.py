"""変化球チャートのSVG幾何を組み立てるモジュール。詳細は docs/grades.md 参照。

## レイアウト

放射状ではなく、3列×2行の固定グリッド。座標系は参考実装（ぷれすぴ）の
寸法をそのまま採用しているため、viewBox は 195x130 固定で、
表示サイズは CSS 側で拡大する。

    列幅:      77   |  41  |  77
    ┌─────────────────────────┐
    │      ストレート系ラベル      │
    │  スライダー系  │  シュート系  │   ← 横方向のラベルは図の上
    │ ◀━━[箱]  [箱]  [箱]━━▶ │   ← 横方向の段（高さ20）
    │  [箱]   [箱]   [箱]      │   ← 斜め・縦方向の箱（高さ20）
    │   ↙     ↓     ↘        │   ← 斜め・縦のラダー（高さ42）
    │   カーブ系   │  シンカー系   │   ← 斜め方向のラベルは図の下
    │       フォーク系ラベル       │
    └─────────────────────────┘

## 1セルの構成

球威の等級色で塗ったラダーが変化方向へ伸び、中心側の端に等級ボックスが付く。
ボックスは塗りが球威の等級色、左が球威（黒文字）、右が制球（制球の等級色）。
ラダーは7段で、変化量ぶんだけ球威色に点灯し、残りは暗いまま。
ストレート系だけは変化量の概念がないためラダーを描かない。
"""
from __future__ import annotations

import math

import grades

VIEW_W, VIEW_H = 195.0, 130.0

BOX_W, BOX_H = 35.0, 20.0
MAX_BREAK = 7          # 変化量の最大段階
RUNG_RATIO = 0.72      # 1段あたりの塗り比率（残りが段間の隙間）
W_IN, W_OUT = 8.0, 2.5  # ラダーの半幅。外側ほど細くなる楔形

TRACK_EMPTY = "#26292f"  # 未到達の段 / 球種を持たない方向

# 大分類ごとの固定配置。box=箱の中心, track=(内側→外側), label=(x, y)
# ストレート系は track を持たない（変化量の概念がないため）
LAYOUT = {
    "straight": {"box": (98.0, 34.0),  "track": None,
                 "label": (98.0, 8.0),   "anchor": "middle", "name": "ストレート系"},
    "slider":   {"box": (59.5, 34.0),  "track": ((42.0, 34.0), (2.0, 34.0)),
                 "label": (49.0, 20.0),  "anchor": "middle", "name": "スライダー系"},
    "shoot":    {"box": (135.5, 34.0), "track": ((153.0, 34.0), (193.0, 34.0)),
                 "label": (146.0, 20.0), "anchor": "middle", "name": "シュート系"},
    "curve":    {"box": (59.5, 54.0),  "track": ((72.0, 66.0), (6.0, 104.0)),
                 "label": (49.0, 117.0), "anchor": "middle", "name": "カーブ系"},
    "fork":     {"box": (98.0, 54.0),  "track": ((98.0, 66.0), (98.0, 104.0)),
                 "label": (98.0, 128.0), "anchor": "middle", "name": "フォーク系"},
    "sinker":   {"box": (135.5, 54.0), "track": ((123.0, 66.0), (189.0, 104.0)),
                 "label": (146.0, 117.0), "anchor": "middle", "name": "シンカー系"},
}


def _rungs(track, break_amount: int, fill: str) -> list[dict]:
    """内側→外側へ伸びる楔形のラダー。break_amount 段まで fill 色で点灯する。"""
    (x0, y0), (x1, y1) = track
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux  # 進行方向に対する垂線

    out = []
    for i in range(MAX_BREAK):
        t0 = i / MAX_BREAK
        t1 = (i + RUNG_RATIO) / MAX_BREAK
        w0 = W_IN + (W_OUT - W_IN) * t0
        w1 = W_IN + (W_OUT - W_IN) * t1
        corners = [(t0, -w0), (t0, w0), (t1, w1), (t1, -w1)]
        out.append({
            "points": " ".join(
                f"{x0 + dx * t + px * w:.1f},{y0 + dy * t + py * w:.1f}"
                for t, w in corners
            ),
            "color": fill if i < break_amount else TRACK_EMPTY,
        })
    return out


def _box(cx: float, cy: float, power: str, control: str) -> dict:
    """球威（塗り色＋黒文字）と制球（カラー文字）を1つの四角にまとめる。"""
    return {
        "x": round(cx - BOX_W / 2, 1),
        "y": round(cy - BOX_H / 2, 1),
        "w": BOX_W,
        "h": BOX_H,
        "fill": grades.color(power),
        "power": power,
        "power_x": round(cx - BOX_W / 4, 1),
        "control": control,
        "control_x": round(cx + BOX_W / 4, 1),
        "control_color": grades.color(control),
        "text_y": round(cy + 5.2, 1),
    }


def build_panels(pitches: list[dict]) -> list[dict]:
    """球種リストを第一球種／第二球種の2パネルに振り分けて描画データを作る。"""
    panels = []
    for order in (1, 2):
        entries = [p for p in pitches if p.get("order", 1) == order]
        if not entries:
            continue

        drawn = []
        for p in entries:
            spec = LAYOUT[p["category"]]
            fill = grades.color(p["power"])
            drawn.append({
                "rungs": _rungs(spec["track"], p.get("break") or 0, fill) if spec["track"] else [],
                "box": _box(*spec["box"], p["power"], p["control"]),
                "label": {"x": spec["label"][0], "y": spec["label"][1],
                          "anchor": spec["anchor"], "text": p["name"]},
            })

        # 球種を持たない大分類は暗いラダーだけ描く
        used = {p["category"] for p in entries}
        empty = [
            {"rungs": _rungs(spec["track"], 0, TRACK_EMPTY)}
            for name, spec in LAYOUT.items()
            if name not in used and spec["track"]
        ]

        panels.append({
            "order": order,
            "pitches": drawn,
            "empty": empty,
            "width": VIEW_W,
            "height": VIEW_H,
        })
    return panels
