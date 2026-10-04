"""書き起こし結果（work/<cat>/<team>/json/*.json）を data/ にまとめる（LLM不要）。

使い方:
    python3 src/merge_team.py work/wbc/australia
    python3 src/merge_team.py work/wbc/australia --outputs /mnt/user-data/outputs/prospi-real
        → 改名コピーを outputs にも置き、device_commit_files に渡す一覧を work/.../commit_files.json に書く

やること:
    1. 同じ選手（背番号＋名前が同じ）が複数枚あれば、写り込み（ghost）の少ない1枚を残し、
       残りを _skipped.json に「同じ選手の重複」として記録する
       （{"duplicate_of": ...} だけの結果も同様に記録する）
    2. data/<cat>/<team>/<player_id>.json に書く。同じ player_id が既にあって
       - 同じ選手（背番号＋名前が同じ）なら上書き更新
       - 別人なら player_id の末尾に _2, _3 … を付ける
    3. 改名コピー captures/<cat>/<元のフォルダ>/<player_id>.png を作る（元ファイルはそのまま）
    4. notes（読みにくかった箇所）は data には入れず、最後に一覧表示する
最後に、PCへ書き戻す改名コピーの一覧と、既知の選手一覧（写り込み画像の照合用）を表示する。
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from capture_paths import ROOT, key, resolve

PID = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*_\d+(?:_\d+)?$")
REQUIRED = ["category", "team", "kind", "player_id", "year", "uniform_number", "name",
            "position", "throws_bats", "rarity", "stats", "abilities"]


def _ident(d: dict) -> tuple[str, str]:
    return (str(d.get("uniform_number", "")).strip(), str(d.get("name", "")).strip())


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    outputs = Path(argv[argv.index("--outputs") + 1]) if "--outputs" in argv else None
    work = (ROOT / argv[0]).resolve()
    man = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
    cat, team = man["category"], man["team"]
    ghost = {key(it["file"]): it["ghost"] for it in man["transcribe"]}
    data_dir = ROOT / "data" / cat / team
    data_dir.mkdir(parents=True, exist_ok=True)

    results, dups, problems = [], [], []
    merged_ok = []
    for jp in sorted((work / "json").glob("*.json")):
        try:
            d = json.loads(jp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"{jp.name}: JSONとして読めません（{e}）")
            continue
        if "duplicate_of" in d:
            dups.append(d)
            merged_ok.append(jp)
            continue
        missing = [k for k in REQUIRED if k not in d]
        if missing or not d.get("source_original"):
            problems.append(f"{jp.name}: 必須キーがありません {missing or ['source_original']}")
            continue
        if not PID.match(d["player_id"]):
            problems.append(f"{jp.name}: player_id の形式が不正 {d['player_id']!r}")
            continue
        results.append(d)
        merged_ok.append(jp)

    # 1) 同じ選手をまとめる
    by_id: dict[tuple, list[dict]] = {}
    for d in results:
        by_id.setdefault(_ident(d), []).append(d)
    skipped, keep = [], []
    for ident, ds in by_id.items():
        ds.sort(key=lambda d: ghost.get(key(d["source_original"]), 0.0))
        keep.append(ds[0])
        for d in ds[1:]:
            skipped.append({"file": d["source_original"],
                            "reason": f"同じ選手の重複（{Path(ds[0]['source_original']).name}）"})

    # 写り込みのある画像の結果は、同じ選手のデータが既にあれば上書きしない（きれいな画像を優先）
    existing = {}
    for jp in data_dir.glob("*.json"):
        if not jp.name.startswith("_"):
            existing[_ident(json.loads(jp.read_text(encoding="utf-8")))] = jp.stem
    kept = []
    for d in keep:
        if ghost.get(key(d["source_original"]), 0.0) >= 0.02 and _ident(d) in existing:
            skipped.append({"file": d["source_original"],
                            "reason": f"同じ選手の切り替え途中のフレーム（{existing[_ident(d)]}）"})
        else:
            kept.append(d)
    keep = kept

    # 2) data/ へ書く
    written, copies, notes = [], [], []
    for d in keep:
        pid = d["player_id"]
        n = 1
        while (data_dir / f"{pid}.json").exists():
            old = json.loads((data_dir / f"{pid}.json").read_text(encoding="utf-8"))
            if _ident(old) == _ident(d):
                break  # 同じ選手 → 上書き（ゲーム側の能力更新などで撮り直した場合）
            n += 1
            pid = f"{d['player_id']}_{n}"
        d["player_id"] = pid
        d["category"], d["team"] = cat, team
        d["source_capture"] = f"captures/{cat}/{team}/{pid}.png"
        for x in d.pop("notes", None) or []:
            notes.append(f"{pid}: {x}")
        ordered = {k: d[k] for k in ["category", "team", "kind", "player_id", "source_capture", "source_original"]}
        ordered.update({k: v for k, v in d.items() if k not in ordered})
        (data_dir / f"{pid}.json").write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
        written.append(d)
        # 3) 改名コピー（元のフォルダに置く。大文字小文字はPC側のフォルダ名に合わせる）
        src = resolve(d["source_original"])
        if src is None:
            problems.append(f"{pid}: 元画像が見つかりません {d['source_original']}")
            continue
        dst = src.parent / f"{pid}.png"
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            shutil.copyfile(src, dst)
            copies.append(str(dst.relative_to(ROOT)))  # PC にまだ無い（取り込んだ画像に無かった）改名コピー

    known = {d["player_id"] for d in written}
    for d in dups:
        skipped.append({"file": d["source_original"],
                        "reason": f"同じ選手の切り替え途中のフレーム（{d['duplicate_of']}）"})
        if d["duplicate_of"] not in known and not (data_dir / f"{d['duplicate_of']}.json").exists():
            problems.append(f"duplicate_of の選手がデータにありません: {d['duplicate_of']}（{d['source_original']}）")

    sp = data_dir / "_skipped.json"
    cur = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else []
    have = {key(e["file"]) for e in cur}
    add = [e for e in skipped if key(e["file"]) not in have]
    if add:
        sp.write_text(json.dumps(cur + add, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 取り込んだ結果は json_merged/ へ移す（もう一度 merge しても二重に取り込まない）
    done_dir = work / "json_merged"
    done_dir.mkdir(exist_ok=True)
    for jp in merged_ok:
        shutil.move(str(jp), str(done_dir / jp.name))

    n_p = sum(1 for d in written if d["kind"] == "pitcher")
    print(f"{cat}/{team}: {len(written)}人をdataに書き込み（投手 {n_p} / 野手 {len(written) - n_p}）、"
          f"重複 {len(skipped)}枚を _skipped.json に記録")
    if problems:
        print("\n■ 問題（要対応）")
        for p in problems:
            print(f"  {p}")
    if notes:
        print("\n■ 読み取りに自信がない箇所（notes）")
        for x in notes:
            print(f"  {x}")
    # 今回の作業で新しく作った改名コピーを累積して記録（pass1/pass2 の merge をまたいで書き戻すため）
    nc = work / "new_copies.txt"
    prev = nc.read_text(encoding="utf-8").split() if nc.exists() else []
    copies = list(dict.fromkeys(prev + copies))
    nc.write_text("\n".join(copies) + ("\n" if copies else ""), encoding="utf-8")
    print("\n■ PCへ書き戻す改名コピー（PCにまだ無いもの）")
    for c in copies:
        print(f"  {c}")
    if outputs is not None:
        pc_root = "C:\\dev\\claude\\prospi-real"
        commit = []
        for c in copies:
            src = ROOT / c
            rel = Path(c)  # captures/<cat>/<PC側のフォルダ名>/<player_id>.png
            staged = outputs / rel
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, staged)
            commit.append({"stagedPath": str(staged), "devicePath": pc_root + "\\" + str(rel).replace("/", "\\")})
        (work / "commit_files.json").write_text(json.dumps(commit, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"device_commit_files 用の一覧: {(work / 'commit_files.json').relative_to(ROOT)}（{len(commit)}件）")
    all_players = []
    for jp in sorted(data_dir.glob("*.json")):
        if jp.name.startswith("_"):
            continue
        d = json.loads(jp.read_text(encoding="utf-8"))
        first = d["abilities"][0]["name"] if d.get("abilities") else ""
        all_players.append(f"{d['player_id']} #{d['uniform_number']} {d['name']} {d['position']} "
                           f"OVR{d['rarity']['overall']} 先頭能力:{first}")
    (work / "known_players.txt").write_text("\n".join(all_players) + "\n", encoding="utf-8")
    print(f"\n既知の選手一覧: {(work / 'known_players.txt').relative_to(ROOT)}（{len(all_players)}人）")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
