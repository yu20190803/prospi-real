"""data/ 配下の全選手JSONを検証用ページ(site/index_work.html)にまとめる。

使い方:
    python src/build_site_work.py

build_site.py（公開用 site/index.html）との違い:
    - 選手詳細を上部、選手一覧を右サイドバーに配置
    - 選手詳細の下に元キャプチャ（captures/配下のPNG）を表示する
    - そのため source_capture をページに埋め込む（公開版には含めない）

元キャプチャは JPEG の data URI としてHTMLに直接埋め込む（相対パス参照だと
開く場所によって画像が表示されないため）。ゲーム画面そのものを含むので
site/index_work.html は .gitignore 対象。内部検証専用で、公開しない。
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from build_site import PUBLIC_KEYS as _BASE_KEYS
import grades
from capture_paths import resolve

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "src" / "site" / "index_work.template.html"
OUT = ROOT / "site" / "index_work.html"

PUBLIC_KEYS = _BASE_KEYS + ["source_capture"]


def capture_data_uri(rel: str) -> str | None:
    """captures/ の画像をJPEGに変換して data URI にする（HTMLをどこで開いても表示できるように）。"""
    path = resolve(rel)
    if path is None:
        return None
    from PIL import Image  # 検証ページ生成時だけ必要
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> None:
    players, captures, missing = [], {}, []
    for path in sorted((ROOT / "data").rglob("[!_]*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        pub = {k: d[k] for k in PUBLIC_KEYS if k in d}
        players.append(pub)
        uri = capture_data_uri(d["source_capture"]) if d.get("source_capture") else None
        if uri:
            captures[d["player_id"]] = uri
        else:
            missing.append(d["player_id"])
    data = json.dumps(players, ensure_ascii=False).replace("</", "<\\/")
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__DATA__", data)
            .replace("__GRADE_COLORS__", json.dumps(grades.COLORS))
            .replace("__CAPTURES__", json.dumps(captures)))
    if missing:
        print("元キャプチャなし:", ", ".join(missing))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"{len(players)}選手 → {OUT.relative_to(ROOT)}（検証用・非公開）")


if __name__ == "__main__":
    main()
