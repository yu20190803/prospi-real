"""等級（S, A〜G）の定義。詳細は docs/grades.md を参照。"""
from __future__ import annotations

# 等級 → 色。S から G へ「薄ピンク → 赤 → 橙 → 緑 → 青 → 灰」と推移する
COLORS = {
    "S": "#f7dbe6",  # 白に近い薄ピンク
    "A": "#f0a0c0",  # S より濃い薄ピンク
    "B": "#e03c3c",  # 赤
    "C": "#e07b1e",  # 濃いオレンジ
    "D": "#f2ac52",  # 薄いオレンジ
    "E": "#4cb050",  # 緑
    "F": "#5b8fd6",  # 青（少し薄め）
    "G": "#9aa0aa",  # 灰
}

# 等級 → 能力値の下限。書き起こしの検算に使う
THRESHOLDS = [("S", 90), ("A", 80), ("B", 70), ("C", 60), ("D", 50), ("E", 40), ("F", 20), ("G", 0)]

# 特殊能力のうち、名前とアルファベットを薄く表示する等級
DIMMED = {"C", "D", "E", "F", "G"}


def color(grade: str | None) -> str:
    return COLORS.get((grade or "").upper(), "#ffffff")


def from_value(value: int) -> str:
    """能力値から等級を求める。"""
    for grade, low in THRESHOLDS:
        if value >= low:
            return grade
    return "G"


def check(label: str, grade: str | None, value) -> str | None:
    """等級と能力値の矛盾を検出する。戻り値は警告文（矛盾なしなら None）。"""
    if not grade or not isinstance(value, int):
        return None
    expected = from_value(value)
    if expected != grade.upper():
        return f"{label}: 能力値 {value} なら等級は {expected} のはずですが {grade} と書かれています"
    return None
