"""選手データ(JSON) から選手カードHTMLを生成するスクリプト。

使い方:
    python src/generate.py data/wbc/usa/web_62.json
    python src/generate.py --all

生成先: output/<category>/<team>/<player_id>.html
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import grades
from pitch_chart import build_panels

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
TEMPLATE_DIR = ROOT / "src" / "templates"


def load_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


KIND_TEMPLATES = {
    "pitcher": "player_card_pitcher.html.jinja",
    "batter": "player_card_batter.html.jinja",
}


def check_grades(data: dict) -> list[str]:
    """等級と能力値の矛盾を洗い出す（書き起こしミスの検出用）。"""
    warnings = []
    for s in data.get("stats", []):
        for part in s.get("splits", [{"vs": "", **s}]):
            w = grades.check(f'{s["label"]}{part.get("vs", "")}',
                             part.get("grade"), part.get("value"))
            if w:
                warnings.append(w)
    return warnings


def render_one(env: Environment, data_path: Path) -> Path:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    kind = data.get("kind")
    if kind not in KIND_TEMPLATES:
        raise ValueError(
            f"{data_path}: 'kind' は {list(KIND_TEMPLATES)} のいずれかにしてください（現在: {kind!r}）"
        )
    for warning in check_grades(data):
        print(f"  [警告] {data_path.name}: {warning}")

    # 変化球チャートは座標計算が必要なのでPython側で組み立ててから渡す
    panels = build_panels(data.get("pitches", []))

    template = env.get_template(KIND_TEMPLATES[kind])
    html = template.render(player=data, pitch_panels=panels, grade_color=grades.color,
                           dimmed_grades=grades.DIMMED)

    out_path = OUTPUT_DIR / data["category"] / data["team"] / f"{data['player_id']}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_files", nargs="*", type=Path, help="選手データJSONのパス")
    parser.add_argument("--all", action="store_true", help="data/ 配下の全JSONを生成する")
    args = parser.parse_args()

    env = load_env()

    targets = list(args.data_files)
    if args.all:
        targets += sorted(DATA_DIR.rglob("*.json"))

    if not targets:
        parser.error("データファイルを指定するか --all を使ってください")

    for data_path in targets:
        out_path = render_one(env, data_path)
        print(f"生成しました: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
