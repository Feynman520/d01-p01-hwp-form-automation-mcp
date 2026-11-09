"""engine/mac/save.py — ⑤ 표준 HWPX 로 저장/정규화(python-hwpx 로 열고 다시 쓴다)."""
from __future__ import annotations

from . import _doc


def save_hwpx(hwp, src_path: str, out_path: str) -> str:
    if not out_path.lower().endswith(".hwpx"):
        raise ValueError("out_path 확장자는 .hwpx 여야 합니다.")
    return _doc.save_doc(_doc.open_doc(src_path), out_path)
