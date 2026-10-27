"""
macOS 엔진 검증(한컴 없음) — engine/mac 의 여섯 작업을 python-hwpx 로 돌린다.

시험 문서는 python-hwpx 로 새로 만든다: `{{대표자}}`(두 번)·`{{주소}}` 문단과 `[[금액]]` 표 칸.
누름틀이 자리표시자 **그 자리**에 생기는지(앞뒤 글자 유지), 같은 이름은 모두 채워지는지, 결과가 OWPML 스키마
검사(`HwpxDocument.validate`)를 통과하는지, HWP 5.0 왕복이 되는지 본다. PDF 는 LibreOffice 가 있을 때만.

실행: python tests/mac_engine.py
"""
import os
import shutil
import sys
import tempfile
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.simplefilter("ignore")

from hwpx import HwpxDocument  # noqa: E402
from engine.mac import convert, extract, fields, save  # noqa: E402
from engine.mac.session import HwpSession  # noqa: E402
from engine.lo_bridge import find_soffice  # noqa: E402


def make_template(path):
    doc = HwpxDocument.new()
    sec = doc.sections[0]
    sec.add_paragraph("신청서")
    sec.add_paragraph("대표자: {{대표자}} (인)")
    sec.add_paragraph("주소는 {{주소}} 입니다. 확인자 {{대표자}}")
    holder = sec.add_paragraph("")
    table = holder.add_table(2, 2)
    table.cell(0, 0).set_text("항목")
    table.cell(0, 1).set_text("값")
    table.cell(1, 0).set_text("금액")
    table.cell(1, 1).set_text("[[금액]]")
    doc.save_to_path(path)


def schema_errors(path):
    rep = HwpxDocument.open(path).validate()
    issues = getattr(rep, "issues", None) or getattr(rep, "errors", None) or []
    errors = [i for i in issues if str(getattr(i, "level", getattr(i, "severity", "error"))).lower().endswith("error")]
    ok = getattr(rep, "ok", None)
    return errors if ok is None else ([] if ok else (errors or ["validation failed"]))


def main():
    tmp = tempfile.mkdtemp(prefix="iris-hwpx-test-")
    fails = 0

    def check(cond, name):
        nonlocal fails
        print(("PASS" if cond else "FAIL"), name, flush=True)
        if not cond:
            fails += 1

    try:
        s = HwpSession()
        s.start()
        h = s.handle
        check(h.Version[0] == "python-hwpx", f"hwp_health 판 정보 {h.Version}")
        src = os.path.join(tmp, "form.hwpx")
        make_template(src)

        tpl = os.path.join(tmp, "out", "template.hwpx")
        out, names = fields.insert_fields_by_bracket(h, src, tpl)
        check(sorted(names) == ["금액", "대표자", "주소"], f"insert_fields_by_bracket → {names}")
        check(not schema_errors(tpl), f"필드화된 문서가 OWPML 스키마 검사 통과 {schema_errors(tpl)[:2]}")
        info = extract.extract(h, tpl)
        check("{{" not in info["text"] and "[[" not in info["text"], "자리표시자 글자는 사라졌다")
        check(sorted(info["field_names"]) == ["금액", "대표자", "주소"] and info["table_count"] == 1, f"extract_hwpx 필드 {info['field_names']} 표 {info['table_count']}")
        check(info["tables"][0][1][0] == "금액", f"표 내용 {info['tables'][0]}")
        n_rep = sum(1 for f in HwpxDocument.open(tpl).list_form_fields() if f.name == "대표자")
        check(n_rep == 2, f"같은 이름 자리표시자 두 곳 모두 누름틀({n_rep})")

        filled_path = os.path.join(tmp, "out", "filled.hwpx")
        r = fields.fill_fields(h, tpl, {"대표자": "홍길동", "주소": "서울시 종로구", "금액": "1,000,000원", "없는칸": "x"}, filled_path)
        check(r["filled"] == {"대표자": "홍길동", "주소": "서울시 종로구", "금액": "1,000,000원"}, f"fill_fields 검증값 {r['filled']}")
        check(r["unknown_fields"] == ["없는칸"] and sorted(r["available_fields"]) == ["금액", "대표자", "주소"], "모르는 키·쓸 수 있는 필드 목록")
        text = extract.extract(h, filled_path)["text"]
        check("대표자: 홍길동 (인)" in text and "주소는 서울시 종로구 입니다. 확인자 홍길동" in text,
              "누름틀이 자리표시자 그 자리에(앞뒤 글자 그대로) 채워졌다")
        check(not schema_errors(filled_path), "채운 문서도 스키마 검사 통과")

        norm = save.save_hwpx(h, filled_path, os.path.join(tmp, "out", "norm.hwpx"))
        check(extract.extract(h, norm)["text"] == text, "save_hwpx → 내용 그대로")

        legacy = os.path.join(tmp, "legacy.hwp")
        HwpxDocument.open(filled_path).save_to_path(legacy)
        back = convert.hwp_to_hwpx(h, legacy, os.path.join(tmp, "out", "back.hwpx"))
        check(extract.extract(h, back)["text"] == text, "convert_hwp_to_hwpx(HWP 5.0) → 같은 내용")
        try:
            convert.hwp_to_hwpx(h, legacy, os.path.join(tmp, "x.docx"))
            check(False, "출력 확장자 검사")
        except ValueError:
            check(True, "출력 확장자 검사")

        if find_soffice():
            r = convert.hwpx_to_pdf(h, filled_path, os.path.join(tmp, "out", "filled.pdf"))
            with open(r["out_path"], "rb") as f:
                data = f.read()
            check(data[:5] == b"%PDF-" and r["approximate"] is True and "한컴" in r["note"], "convert_hwpx_to_pdf → 근사 PDF(approximate·안내)")
            check(any(k in data for k in (b"AppleSDGothic", b"AppleGothic", b"Nanum")), "근사 PDF 에 한글 글꼴")
        else:
            print("SKIP: LibreOffice 없음 — 근사 PDF 시험 건너뜀")
        try:
            fields.insert_fields_by_bracket(h, filled_path, os.path.join(tmp, "none.hwpx"))
            check(False, "자리표시자가 없으면 오류")
        except ValueError:
            check(True, "자리표시자가 없으면 오류")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"---- FAILS: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
