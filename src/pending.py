"""未処理のスクリーンショットと、データとの対応漏れを一覧にする。

使い方:
    python src/pending.py

出力:
- 未処理の画像  … captures/ にあるが、ファイル名が <player_id>.png 形式でない、
                  または対応する data/ の JSON がない画像（= これから書き起こす対象）。
                  ただし、どれかの JSON の "source_original" に記録済みの元ファイルは処理済みとみなす
- 画像のないデータ … data/ に JSON があるが captures/ に元画像がない
- 推定値あり    … JSON に "unverified" が残っている選手（ユーザー確認待ち）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*_\d+(?:_\d+)?$")
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def main() -> None:
    caps = [p for p in (ROOT / "captures").rglob("*") if p.suffix.lower() in IMG_EXT]
    datas = {p.relative_to(ROOT / "data").with_suffix(""): p for p in (ROOT / "data").rglob("*.json")}

    # 改名前の元ファイル名は JSON の "source_original" に記録される。記録済みなら処理済みとみなす
    originals = set()
    for jp in datas.values():
        o = json.loads(jp.read_text(encoding="utf-8")).get("source_original")
        if o:
            originals.add(o)

    pending = []
    for p in sorted(caps):
        if str(p.relative_to(ROOT).as_posix()) in originals:
            continue
        rel = p.relative_to(ROOT / "captures")
        if len(rel.parts) != 3 or rel.parts[0] not in {"npb", "wbc"}:
            pending.append((p, "置き場所が captures/<npb|wbc>/<team>/ ではない"))
        elif p.suffix.lower() != ".png" or not ID_RE.match(p.stem):
            pending.append((p, "未改名（書き起こし前）"))
        elif rel.with_suffix("") not in datas:
            pending.append((p, "改名済みだが JSON がない"))

    cap_keys = {p.relative_to(ROOT / "captures").with_suffix("") for p in caps}
    no_image = [k for k in sorted(datas) if k not in cap_keys]
    unverified = [k for k, p in sorted(datas.items())
                  if json.loads(p.read_text(encoding="utf-8")).get("unverified")]

    print(f"■ 未処理の画像 {len(pending)}件")
    for p, why in pending:
        print(f"  {p.relative_to(ROOT)}  … {why}")
    print(f"\n■ 画像のないデータ {len(no_image)}件")
    for k in no_image:
        print(f"  data/{k}.json")
    print(f"\n■ 推定値あり（ユーザー確認待ち） {len(unverified)}件")
    for k in unverified:
        print(f"  data/{k}.json")


if __name__ == "__main__":
    main()
