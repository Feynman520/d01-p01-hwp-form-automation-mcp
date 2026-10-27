"""engine/mac/fields.py — ③ `{{이름}}`→누름틀 · `[[이름]]`→셀 필드  ④ 필드 채우기(Windows 판과 같은 반환).

누름틀은 python-hwpx 가 만드는 실제 한컴 모양(fieldBegin 의 Clickhere 매개변수 + fieldEnd)을 그대로 쓰고, 자리만
옮긴다: 자리표시자가 든 글자 묶음(run)을 앞·뒤로 나누고 그 사이에 누름틀 묶음을 끼운다. 바뀐 문단의 줄 배치
캐시(linesegarray)는 지워 한컴이 열 때 다시 계산하게 한다.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from . import _doc

HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
BRACE = re.compile(r"\{\{\s*([^{}\[\]]+?)\s*\}\}")
CELL = re.compile(r"\[\[\s*([^\[\]{}]+?)\s*\]\]")


def _runs(p_el):
    return [c for c in p_el if c.tag == f"{HP}run"]


def _plain_t(t) -> bool:
    return len(t) == 0  # 탭·줄바꿈 같은 자식이 없는 글자 노드만 나눈다


def _drop_layout_cache(p_el) -> None:
    for c in list(p_el):
        if c.tag == f"{HP}linesegarray":
            p_el.remove(c)


def _merge_span(p_el, token: str) -> bool:
    """자리표시자가 여러 글자 묶음에 걸쳐 있으면 그 구간의 글자를 첫 묶음 하나로 모은다(그 구간의 서식 차이만 잃는다)."""
    ts = [(r, t) for r in _runs(p_el) for t in r if t.tag == f"{HP}t" and _plain_t(t)]
    text = "".join(t.text or "" for _, t in ts)
    at = text.find(token)
    if at < 0:
        return False
    pos, first = 0, None
    end = at + len(token)
    for r, t in ts:
        s = t.text or ""
        seg_start, seg_end = pos, pos + len(s)
        pos = seg_end
        if seg_end <= at or seg_start >= end:
            continue
        if first is None:
            first = t
            first.text = s
        else:
            first.text = (first.text or "") + s
            t.text = ""
    return first is not None


def _convert_one(paragraph, token: str, name: str) -> bool:
    p_el = paragraph.element
    for attempt in (0, 1):
        for run in _runs(p_el):
            for t in list(run):
                if t.tag != f"{HP}t" or not _plain_t(t) or token not in (t.text or ""):
                    continue
                before, after = (t.text or "").split(token, 1)
                t.text = before
                # 뒤쪽 글자: 같은 서식의 새 묶음으로(원래 묶음에서 이 글자 노드 뒤의 것도 함께 옮긴다)
                tail_run = run.makeelement(f"{HP}run", dict(run.attrib))
                new_t = tail_run.makeelement(f"{HP}t", {})
                new_t.text = after
                tail_run.append(new_t)
                for sib in list(t.itersiblings()):
                    tail_run.append(sib)
                # 누름틀 묶음: python-hwpx 가 문단 끝에 만든 것을 이 자리로 옮긴다
                before_runs = _runs(p_el)
                paragraph.add_form_field(name, char_pr_id_ref=run.get("charPrIDRef"))
                new_runs = [r for r in _runs(p_el) if r not in before_runs]
                anchor = run
                for r in new_runs + [tail_run]:
                    anchor.addnext(r)
                    anchor = r
                _drop_layout_cache(p_el)
                paragraph.section.mark_dirty()
                return True
        if attempt == 0 and not _merge_span(p_el, token):
            return False
    return False


def insert_fields_by_bracket(hwp, path: str, out_path: str) -> Tuple[str, List[str]]:
    doc = _doc.open_doc(path)
    names: List[str] = []
    # [[이름]] → 그 표 칸을 셀 필드로(칸 이름 = 필드 이름), 자리표시자 글자는 지운다
    for table in list(_doc.all_tables(doc)):
        for cell in _doc.iter_cells(table):
            m = CELL.search(cell.text or "")
            if not m:
                continue
            name = m.group(1).strip()
            cell.field_name = name
            for p in cell.paragraphs:
                for run in _runs(p.element):
                    for t in run:
                        if t.tag == f"{HP}t" and t.text and CELL.search(t.text):
                            t.text = CELL.sub("", t.text)
                _drop_layout_cache(p.element)
            if name not in names:
                names.append(name)
    # {{이름}} → 그 자리에 누름틀
    for p in list(_doc.all_paragraphs(doc)):
        for _ in range(200):
            m = BRACE.search(p.text or "")
            if not m:
                break
            name = m.group(1).strip()
            if not _convert_one(p, m.group(0), name):
                break
            if name not in names:
                names.append(name)
    if not names:
        raise ValueError("{{필드명}} 또는 [[필드명]] 자리표시자를 찾지 못했습니다.")
    return _doc.save_doc(doc, out_path), names


def _available(doc) -> Tuple[List[Any], List[str], List[str]]:
    form = list(doc.list_form_fields())
    cells: List[str] = []
    for table in _doc.all_tables(doc):
        for cell in _doc.iter_cells(table):
            if cell.field_name and cell.field_name not in cells:
                cells.append(cell.field_name)
    names: List[str] = []
    for n in [f.name for f in form] + cells:
        if n and n not in names:
            names.append(n)
    return form, cells, names


def fill_fields(hwp, path: str, data: Dict[str, Any], out_path: str) -> Dict[str, Any]:
    doc = _doc.open_doc(path)
    form, cells, available = _available(doc)
    unknown = [k for k in data if k not in available]
    for key, value in data.items():
        text = "" if value is None else str(value)
        idxs = [i for i, f in enumerate(form) if f.name == key]
        for i in idxs:  # 같은 이름의 누름틀은 모두 같은 값
            doc.fields.fill(text, field_index=i)
        if key in cells:
            doc.fields.fill_cell(text, name=key)
    out = _doc.save_doc(doc, out_path)
    check = _doc.open_doc(out)
    form2, _, _ = _available(check)
    filled: Dict[str, Any] = {}
    for key in data:
        if key in unknown:
            continue
        vals = [("" if f.is_placeholder else f.value or "") for f in form2 if f.name == key]
        for table in _doc.all_tables(check):
            for cell in _doc.iter_cells(table):
                if cell.field_name == key:
                    vals.append((cell.text or "").strip())
        filled[key] = vals[0] if len(set(vals)) == 1 else vals
    return {"out_path": out, "filled": filled, "unknown_fields": unknown, "available_fields": available}
