"""engine/mac/extract.py — ② 본문 텍스트·필드(누름틀·셀 필드)·표 추출(Windows 판과 같은 반환)."""
from __future__ import annotations

from typing import Any, Dict, List

from . import _doc


def _table_grid(table) -> List[List[str]]:
    rows = table.row_count
    cols = table.column_count
    grid = [["" for _ in range(cols)] for _ in range(rows)]
    for pos in table.iter_grid():
        if pos.is_anchor and pos.row < rows and pos.column < cols:
            grid[pos.row][pos.column] = (pos.cell.text or "").strip()
    return grid


def extract(hwp, path: str) -> Dict[str, Any]:
    doc = _doc.open_doc(path)
    text = doc.export_text()
    fields: Dict[str, Any] = {}
    names: List[str] = []

    def put(name, value):
        if not name:
            return
        if name not in names:
            names.append(name)
            fields[name] = value
        elif fields[name] != value:  # 같은 이름에 다른 값이 있으면 목록으로
            prev = fields[name]
            fields[name] = (prev if isinstance(prev, list) else [prev]) + [value]

    for f in doc.list_form_fields():
        put(f.name, "" if f.is_placeholder else (f.value or ""))
    for table in _doc.all_tables(doc):
        for cell in _doc.iter_cells(table):
            if cell.field_name:
                put(cell.field_name, (cell.text or "").strip())
    tables = [_table_grid(t) for t in _doc.all_tables(doc)][:200]
    return {"text": text, "fields": fields, "field_names": names, "tables": tables, "table_count": len(tables)}
