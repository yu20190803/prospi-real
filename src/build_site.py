"""data/ 配下の全選手JSONを1枚のデータベースページ(site/index.html)にまとめる。

使い方:
    python src/build_site.py

選手詳細はゲームの選手詳細画面の見た目に寄せた自作CSS/SVGで描く。
画像（captures/・顔写真・ロゴ）は一切埋め込まない。
変化球チャートの座標は src/pitch_chart.py で計算し、描画データとしてページに埋め込む。
"""
from __future__ import annotations

import json
from pathlib import Path

from pitch_chart import build_panels
import grades

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "src" / "site" / "index.template.html"
OUT = ROOT / "site" / "index.html"

# サイトに出す項目だけに絞る（キャプチャのパスなど内部情報は出さない）
PUBLIC_KEYS = ["player_id", "category", "team", "kind", "year", "uniform_number", "name",
               "position", "throws_bats", "rarity", "stats", "pitches", "fielding_diagram",
               "zone_grid", "abilities"]

# 左投手は画面上の変化方向が左右反転する（データは右投手基準で持っている）
MIRROR = {"slider": "shoot", "shoot": "slider", "curve": "sinker", "sinker": "curve"}


def pitch_panels(d: dict) -> list[dict]:
    """第一・第二球種パネルの描画データ。第二パネルには第一球種を薄く重ねる（画面の表示に合わせる）。"""
    pitches = d.get("pitches", [])
    if d.get("throws_bats", "").startswith("左"):
        pitches = [{**p, "category": MIRROR.get(p["category"], p["category"])} for p in pitches]
    first = [p for p in pitches if p.get("order", 1) == 1]
    second = [p for p in pitches if p.get("order", 1) == 2]

    panels = build_panels(first)
    for pn in panels:
        for x in pn["pitches"]:
            x["ghost"] = False
    if second:
        cats = {p["category"] for p in second}
        ghosts = [{**p, "order": 2} for p in first if p["category"] not in cats]
        p2 = build_panels(second + ghosts)[0]
        for i, x in enumerate(p2["pitches"]):
            x["ghost"] = i >= len(second)
        panels.append(p2)
    return panels


def main() -> None:
    players = []
    for path in sorted((ROOT / "data").rglob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        pub = {k: d[k] for k in PUBLIC_KEYS if k in d}
        players.append(pub)
    data = json.dumps(players, ensure_ascii=False).replace("</", "<\\/")
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__DATA__", data)
            .replace("__GRADE_COLORS__", json.dumps(grades.COLORS)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"{len(players)}選手 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
