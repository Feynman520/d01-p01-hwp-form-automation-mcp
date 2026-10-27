"""engine/mac — macOS 엔진: 한컴 없이 HWPX/HWP 를 다룬다(python-hwpx, Apache-2.0).

Windows 판(engine/convert·extract·fields·save·session)과 **같은 모듈 이름·같은 함수·같은 반환**이라 server.py 는
엔진만 고른다. 함수의 첫 인자 `hwp` 는 COM 의 한글 객체 대신 session.MacHandle 이다(쓰지 않는다).
HWPX→PDF 는 한컴 렌더러가 없어 내용 확인용 근사 PDF(HTML → LibreOffice)이며 결과에 approximate=True 를 싣는다.
"""
