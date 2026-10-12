"""data/ 配下の全選手JSONを検証用ページ(site/index_work.html)にまとめる。

使い方:
    python src/build_site_work.py

build_site.py（公開用 site/index.html）との違い:
    - 選手詳細を上部、選手一覧を右サイドバーに配置
    - 選手詳細の下に元キャプチャ（captures/配下のPNG）を表示する
    - そのため source_capture をページに埋め込む（公開版には含めない）

元キャプチャは JPEG にして site/work_img/<cat>/<team>/<player_id>.jpg に書き出し、ページからは
相対パスで参照する（2026-10-12 変更。data URI 埋め込みでは248人で22MBになり、Artifact の
1ページ16MB上限を超えたため）。Artifact へは画像を `files` として一緒に公開する。
前回から内容が変わった画像の一覧を site/work_img_changed.json に書くので、2回目以降はそれだけを
`files` に渡せばよい（渡さなかったファイルは Artifact 側に残る）。
`--inline` を付けると従来どおり data URI で1ファイルに埋め込む（ローカルで1枚だけ持ち運ぶ用）。
ゲーム画面そのものを含むので site/index_work.html・site/work_img/ は .gitignore 対象。内部検証専用で、公開しない。
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


IMG_DIR = ROOT / "site" / "work_img"
CHANGED = ROOT / "site" / "work_img_changed.json"


def capture_jpeg(rel: str) -> bytes | None:
    path = resolve(rel)
    if path is None:
        return None
    from PIL import Image
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def main() -> None:
    import sys
    inline = "--inline" in sys.argv[1:]
    players, captures, missing, changed = [], {}, [], []
    for path in sorted((ROOT / "data").rglob("[!_]*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        pub = {k: d[k] for k in PUBLIC_KEYS if k in d}
        players.append(pub)
        if inline:
            uri = capture_data_uri(d["source_capture"]) if d.get("source_capture") else None
        else:
            jpg = capture_jpeg(d["source_capture"]) if d.get("source_capture") else None
            uri = None
            if jpg:
                rel = f"work_img/{d['category']}/{d['team']}/{d['player_id']}.jpg"
                dst = OUT.parent / rel
                if not dst.exists() or dst.read_bytes() != jpg:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(jpg)
                    changed.append(rel)
                uri = rel
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
    if not inline:
        CHANGED.write_text(json.dumps(changed, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"画像 {len(captures)}枚（今回新しく書き出し・変更 {len(changed)}枚 → {CHANGED.relative_to(ROOT)}）")
    print(f"{len(players)}選手 → {OUT.relative_to(ROOT)}（検証用・非公開）")


if __name__ == "__main__":
    main()
