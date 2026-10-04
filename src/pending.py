"""未処理のスクリーンショットと、データとの対応漏れを一覧にする。

使い方:
    python src/pending.py              # 一覧を表示
    python src/pending.py --next-team  # 未処理が残っている最初のチームのフォルダ（例: wbc/Australia）だけを出力
                                       # 残りがなければ何も出力しない
    python src/pending.py --done-count # チームごとの「処理済みとして記録された画像の数」を出力
                                       # （PCのフォルダの画像数がこれより多いチームに未処理がある）

判定:
- 処理済みの画像 … 次のどれか
    * どれかの JSON の "source_original" に記録されている元ファイル
    * どれかの JSON の "source_capture" そのもの（改名後の画像）
    * data/<cat>/<team>/_skipped.json に記録された画像（重複・メニュー画面・切り替え途中のフレームなど）
- 未処理の画像 … それ以外の画像（= これから書き起こす対象）
- 画像のないデータ … data/ に JSON があるが、source_capture の画像が見つからない
- 推定値あり … JSON に "unverified" が残っている選手

パスの比較は大文字・小文字を区別しない（captures/wbc/USA と data の "usa" を同一視する）。

_skipped.json の形式:
    [{"file": "captures/wbc/USA/Screen_20260811_175002_988.png", "reason": "選手一覧のメニュー画面"}, ...]
"""
from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

from capture_paths import ROOT, key, resolve

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def load() -> tuple[list[Path], dict[str, Path], set[str]]:
    caps = sorted(p for p in (ROOT / "captures").rglob("*")
                  if p.suffix.lower() in IMG_EXT and ".git" not in p.parts)
    datas = {key(p.relative_to(ROOT)): p for p in (ROOT / "data").rglob("*.json")
             if not p.name.startswith("_")}
    done: set[str] = set()
    for jp in datas.values():
        d = json.loads(jp.read_text(encoding="utf-8"))
        for k in ("source_original", "source_capture"):
            if d.get(k):
                done.add(key(d[k]))
    for sp in (ROOT / "data").rglob("_skipped.json"):
        for e in json.loads(sp.read_text(encoding="utf-8")):
            done.add(key(e["file"]))
    return caps, datas, done


def pending_by_team() -> "OrderedDict[str, list[Path]]":
    caps, _, done = load()
    out: "OrderedDict[str, list[Path]]" = OrderedDict()
    for p in caps:
        rel = p.relative_to(ROOT)
        if key(rel) in done:
            continue
        parts = p.relative_to(ROOT / "captures").parts
        team = "/".join(parts[:2]) if len(parts) == 3 else "(置き場所が不正)"
        out.setdefault(team, []).append(p)
    return out


def done_counts() -> "OrderedDict[str, int]":
    """data/<cat>/<team>/ ごとに、JSON の source_original/source_capture と _skipped.json に記録された画像の数"""
    out: "OrderedDict[str, set]" = OrderedDict()
    for jp in sorted((ROOT / "data").rglob("*.json")):
        team = "/".join(jp.relative_to(ROOT / "data").parts[:2])
        files = out.setdefault(team, set())
        d = json.loads(jp.read_text(encoding="utf-8"))
        if jp.name == "_skipped.json":
            files.update(key(e["file"]) for e in d)
        elif not jp.name.startswith("_"):
            files.update(key(d[k]) for k in ("source_original", "source_capture") if d.get(k))
    return OrderedDict((t, len(v)) for t, v in out.items())


def main(argv: list[str]) -> None:
    if "--done-count" in argv:
        for team, n in done_counts().items():
            print(f"{team}\t{n}")
        return
    by_team = pending_by_team()
    if "--next-team" in argv:
        for team in by_team:
            if team != "(置き場所が不正)":
                print(team)
                return
        return

    _, datas, _ = load()
    total = sum(len(v) for v in by_team.values())
    print(f"■ 未処理の画像 {total}件（{len(by_team)}チーム）")
    for team, ps in by_team.items():
        print(f"  {team}: {len(ps)}枚")
    no_image, unverified = [], []
    for k, p in sorted(datas.items()):
        d = json.loads(p.read_text(encoding="utf-8"))
        if not d.get("source_capture") or resolve(d["source_capture"]) is None:
            no_image.append(k)
        if d.get("unverified"):
            unverified.append(f"{k}  {d['unverified']}")
    print(f"\n■ 画像のないデータ {len(no_image)}件")
    for k in no_image:
        print(f"  {k}")
    print(f"\n■ 推定値あり（要確認） {len(unverified)}件")
    for k in unverified:
        print(f"  {k}")


if __name__ == "__main__":
    main(sys.argv[1:])
