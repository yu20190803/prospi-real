"""captures/ 以下のパスを大文字・小文字を区別せずに解決する。

PC（Windows）は大文字・小文字を区別しないが、定期実行するクラウド（Linux）は区別する。
画像フォルダは `captures/wbc/USA/` のように大文字始まりのことがある一方、
データの `source_capture` は `captures/wbc/usa/...` のように小文字で記録している。
画像を読むスクリプトはすべてこの resolve() を通すこと。

クラウドでは、非公開リポジトリ prospi-captures を `prospi-real/captures` にシンボリックリンクして使う
（docs/runbook_transcribe.md の「定期実行」を参照）。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def resolve(rel: str | Path) -> Path | None:
    """ROOT からの相対パスを、大文字・小文字を無視して実在するパスに解決する。見つからなければ None。"""
    p = ROOT / rel
    if p.exists():
        return p
    cur = ROOT
    for part in Path(rel).parts:
        if not cur.is_dir():
            return None
        hit = next((c for c in cur.iterdir() if c.name.lower() == part.lower()), None)
        if hit is None:
            return None
        cur = hit
    return cur


def key(rel: str | Path) -> str:
    """比較用のキー（小文字・スラッシュ区切り）"""
    return Path(rel).as_posix().lower()
