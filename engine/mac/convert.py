"""engine/mac/convert.py — ① HWP → HWPX  ⑥ HWPX(또는 HWP) → PDF.

① python-hwpx 가 HWP 5.0 바이너리를 HWPX 문서 모델로 읽어 HWPX 로 저장한다(한컴 없이). 옮기지 못한 요소가 있으면
   warnings 에 싣는다.
⑥ 한컴 렌더러가 없다. 본문·표를 HTML 로 내보내 LibreOffice(무료)로 A4 PDF 를 만든다 — **내용 확인용 근사본**이며
   쪽 배치·글꼴·표 모양은 한컴과 다르다. 그래서 결과에 approximate=True 와 안내를 싣는다(제출용은 한컴에서).
"""
from __future__ import annotations

import html as _html
import os
import shutil
import tempfile
from typing import Any, Dict

from . import _doc

PDF_NOTE = ("macOS 에는 한컴 렌더러가 없어 본문·표만 담은 근사 PDF 입니다(쪽 배치·글꼴·표 모양이 한컴과 다름). "
            "제출용 PDF 는 Windows 의 한컴오피스에서 만드세요.")

_CSS = """<style>
@page { size: A4; margin: 20mm 18mm; }
body { font-family: 'Apple SD Gothic Neo', 'AppleGothic', sans-serif; font-size: 11pt; line-height: 1.6; }
p { margin: 0 0 4pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
td, th { border: 0.75pt solid #444; padding: 3pt 5pt; vertical-align: top; }
</style>"""


def hwp_to_hwpx(hwp, src_path: str, out_path: str) -> str:
    if not out_path.lower().endswith(".hwpx"):
        raise ValueError("out_path 확장자는 .hwpx 여야 합니다.")
    doc = _doc.open_doc(src_path)
    return _doc.save_doc(doc, out_path)


def hwpx_to_pdf(hwp, src_path: str, out_path: str) -> Dict[str, Any]:
    if not out_path.lower().endswith(".pdf"):
        raise ValueError("out_path 확장자는 .pdf 여야 합니다.")
    doc = _doc.open_doc(src_path)
    title = os.path.splitext(os.path.basename(src_path))[0]
    body = doc.export_html(title=title)
    body = body.replace("</head>", _CSS + "\n</head>", 1) if "</head>" in body else (
        f"<!DOCTYPE html><html lang=\"ko\"><head><meta charset=\"utf-8\"><title>{_html.escape(title)}</title>{_CSS}</head><body>{body}</body></html>")
    from engine.lo_bridge import LoBridge
    work = tempfile.mkdtemp(prefix="iris-hwpx-pdf-")
    try:
        page = os.path.join(work, "document.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write(body)
        out = _doc.abspath(out_path)
        LoBridge().run("writer_convert", src=page, out=out, import_filter="HTML (StarWriter)")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"out_path": out, "approximate": True, "note": PDF_NOTE}
