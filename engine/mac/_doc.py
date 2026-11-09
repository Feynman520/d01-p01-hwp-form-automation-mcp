"""engine/mac/_doc.py — python-hwpx 공용 도우미: 열기·저장·문단 순회(표 칸 안까지)."""
from __future__ import annotations

import os
import warnings
from typing import Iterator


def abspath(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def open_doc(path: str):
    src = abspath(path)
    if not os.path.exists(src):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {src}")
    from hwpx import HwpxDocument
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return HwpxDocument.open(src)


def save_doc(doc, out_path: str) -> str:
    out = abspath(out_path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc.save_to_path(out)
    if not os.path.exists(out):
        raise RuntimeError(f"저장 실패: {out}")
    return out


def iter_paragraphs(paragraphs) -> Iterator:
    """본문 문단과 표 칸 안 문단(중첩 표 포함)을 문서 순서대로."""
    for p in paragraphs:
        yield p
        for table in p.tables:
            for cell in iter_cells(table):
                yield from iter_paragraphs(cell.paragraphs)


def iter_cells(table) -> Iterator:
    """병합된 칸은 한 번만(기준 칸)."""
    for pos in table.iter_grid():
        if pos.is_anchor:
            yield pos.cell


def all_paragraphs(doc) -> Iterator:
    for section in doc.sections:
        yield from iter_paragraphs(section.paragraphs)


def all_tables(doc) -> Iterator:
    def walk(paragraphs):
        for p in paragraphs:
            for table in p.tables:
                yield table
                for cell in iter_cells(table):
                    yield from walk(cell.paragraphs)
    for section in doc.sections:
        yield from walk(section.paragraphs)
