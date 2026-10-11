"""captures/ 以下のパスを大文字・小文字を区別せずに解決する。

PC（Windows）は大文字・小文字を区別しないが、定期実行するクラウド（Linux）は区別する。
画像フォルダは `captures/wbc/USA/` のように大文字を含むことがある。`source_capture` のチーム部分は
英小文字（`captures/wbc/brazil/...`）が原則で、USA だけは大文字 `USA` で書く（2026-10-11 決定）。
この表記は capture_folder() で決める。画像を読むスクリプトはすべてこの resolve() を通すこと。

大文字・小文字だけが違うフォルダが2つある場合（クラウドに古い `usa` と `USA` が並んでいた、2026-10-11）、
表記が完全に一致するものを優先し、次にファイルが実際に見つかるほうを選ぶ。

クラウドでは、非公開リポジトリ prospi-captures を `prospi-real/captures` にシンボリックリンクして使う
（docs/runbook_transcribe.md の「定期実行」を参照）。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# source_capture に書くチームフォルダ名の例外（原則は team と同じ英小文字）
FOLDER_NAME = {"usa": "USA"}


def capture_folder(team: str) -> str:
    """source_capture に書くチームフォルダ名（usa → USA、それ以外は英小文字のまま）"""
    return FOLDER_NAME.get(team.lower(), team.lower())


def resolve(rel: str | Path) -> Path | None:
    """ROOT からの相対パスを、大文字・小文字を無視して実在するパスに解決する。見つからなければ None。"""
    p = ROOT / rel
    if p.exists():
        return p

    def walk(cur: Path, parts: tuple[str, ...]) -> Path | None:
        if not parts:
            return cur
        if not cur.is_dir():
            return None
        hits = sorted((c for c in cur.iterdir() if c.name.lower() == parts[0].lower()),
                      key=lambda c: c.name != parts[0])  # 表記が完全一致するものを先に試す
        for c in hits:
            found = walk(c, parts[1:])
            if found is not None:
                return found
        return None

    return walk(ROOT, Path(rel).parts)


def key(rel: str | Path) -> str:
    """比較用のキー（小文字・スラッシュ区切り）"""
    return Path(rel).as_posix().lower()
