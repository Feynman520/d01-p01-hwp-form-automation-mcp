"""engine/mac/session.py — Windows 의 HwpSession 과 같은 모양(start/stop/alive/run(fn)). 상주 프로세스는 없다."""
from __future__ import annotations

from typing import Any, Callable


class MacHandle:
    """COM 한글 객체 자리. hwp_health 가 `list(h.Version)` 으로 판을 읽는다."""

    @property
    def Version(self):  # noqa: N802 — COM 쪽 이름과 맞춘다
        import importlib.metadata as md
        return ["python-hwpx", md.version("python-hwpx")]


class HwpSession:
    def __init__(self, visible: bool = False, new: bool = True):
        self._alive = False
        self.handle = MacHandle()

    @property
    def alive(self) -> bool:
        return self._alive

    def start(self) -> None:
        import hwpx  # noqa: F401  — 없으면 여기서 분명히 실패한다(설치 안내는 오류 문구로)
        self._alive = True

    def stop(self) -> None:
        self._alive = False

    def run(self, fn: Callable[[MacHandle], Any]) -> Any:
        if not self._alive:
            self.start()
        return fn(self.handle)


def preimport_pyhwpx() -> None:
    """Windows 판의 makepy 선생성 자리 — macOS 에는 할 일이 없다."""
    return None
