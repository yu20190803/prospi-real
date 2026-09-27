"""選手データ(JSON)の書き起こしミスを機械的に洗い出す検証スクリプト。

使い方:
    python src/validate.py            # data/ 配下の全JSONを検証
    python src/validate.py data/wbc/usa/judge_99.json

チェック内容（エラー＝ほぼ確実に誤読、警告＝要目視確認）:
- 必須フィールドの有無、player_id とファイル名・source_capture の一致
- 能力値と等級の整合（docs/grades.md の閾値）
- 値域（能力値 1〜100、球速 100〜170km/h、変化量 1〜7、OVR 1〜999）
- 等級・適性記号が定義済みの文字か
- unverified に記録された「推定値」の一覧
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import grades

ROOT = Path(__file__).resolve().parent.parent
GRADE_SET = set(grades.COLORS)
APTITUDE = {"◎", "○", "△", "ー", "－"}
PITCH_CATEGORIES = {"straight", "slider", "shoot", "curve", "fork", "sinker"}
REQUIRED = ["category", "team", "kind", "player_id", "source_capture", "year",
            "uniform_number", "name", "position", "throws_bats", "rarity", "stats", "abilities"]


def validate(path: Path) -> tuple[list[str], list[str]]:
    errors, warns = [], []
    d = json.loads(path.read_text(encoding="utf-8"))

    for k in REQUIRED:
        if k not in d:
            errors.append(f"必須フィールド {k} がありません")
    if d.get("player_id") != path.stem:
        errors.append(f"player_id({d.get('player_id')}) とファイル名({path.stem}) が不一致")
    if not re.fullmatch(r"[a-z0-9_]+", path.stem):
        errors.append("ファイル名はASCII小文字・数字・_ のみ")
    cap = d.get("source_capture", "")
    if not (ROOT / cap).exists():
        warns.append(f"元画像 {cap} が見つかりません")

    ovr = d.get("rarity", {}).get("overall")
    if not isinstance(ovr, int) or not 1 <= ovr <= 999:
        errors.append(f"OVR が範囲外: {ovr}")

    for s in d.get("stats", []):
        for part in s.get("splits", [s]):
            label = s["label"] + part.get("vs", "")
            g, v = part.get("grade"), part.get("value")
            if g is not None:
                if g not in GRADE_SET:
                    errors.append(f"{label}: 未定義の等級 {g}")
                if not isinstance(v, int) or not 1 <= v <= 100:
                    errors.append(f"{label}: 能力値が範囲外 {v}")
                msg = grades.check(label, g, v)
                if msg:
                    errors.append(msg)
            elif s["label"] == "球速":
                m = re.fullmatch(r"(\d+)km/h", str(v))
                if not m or not 100 <= int(m.group(1)) <= 170:
                    errors.append(f"球速の表記/値が不正: {v}")
            elif s["label"].endswith("適性") and v not in APTITUDE:
                errors.append(f"{label}: 適性記号が不正 {v}")

    for p in d.get("pitches", []):
        if p["category"] not in PITCH_CATEGORIES:
            errors.append(f"球種 {p['name']}: 未定義の大分類 {p['category']}")
        for key in ("power", "control"):
            if p.get(key) not in GRADE_SET:
                errors.append(f"球種 {p['name']}: {key} の等級が不正 {p.get(key)}")
        b = p.get("break")
        if p["category"] == "straight":
            if b is not None:
                warns.append(f"球種 {p['name']}: ストレート系に変化量 {b} が入っています")
        elif not isinstance(b, int) or not 1 <= b <= 7:
            errors.append(f"球種 {p['name']}: 変化量が範囲外 {b}")
    if d.get("kind") == "pitcher":
        keys = [(p["category"], p["order"]) for p in d.get("pitches", [])]
        if len(keys) != len(set(keys)):
            errors.append("同じパネル・同じ方向に球種が重複しています")

    fd = d.get("fielding_diagram") or {}
    for pos in fd.get("positions", []):
        msg = grades.check(f"守備 {pos['position']}", pos.get("grade"), pos.get("value"))
        if msg:
            errors.append(msg)

    for a in d.get("abilities", []):
        if a.get("grade") and a["grade"] not in GRADE_SET:
            errors.append(f"特殊能力 {a['name']}: 等級が不正 {a['grade']}")
        if a.get("type") not in {"plus", "minus", "both"}:
            errors.append(f"特殊能力 {a['name']}: type が不正 {a.get('type')}")

    for u in d.get("unverified", []):
        warns.append(f"推定値あり（要目視）: {u}")
    return errors, warns


def main() -> int:
    targets = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "data").rglob("*.json"))
    n_err = 0
    for t in targets:
        errors, warns = validate(t)
        status = "NG" if errors else "OK"
        print(f"[{status}] {t.relative_to(ROOT) if t.is_absolute() else t}")
        for e in errors:
            print(f"    エラー: {e}")
        for w in warns:
            print(f"    警告  : {w}")
        n_err += len(errors)
    print(f"\n{len(targets)}件 / エラー {n_err}件")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
