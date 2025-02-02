from typing import Any

import pytest
from pytest import CaptureFixture


class CaptureOutput:
    def __init__(self, capsys: CaptureFixture) -> None:
        self.capsys = capsys
        self.capsys_disabled = capsys.disabled()
        self.capsys_disabled.__enter__()

    def __enter__(self) -> "CaptureOutput":
        self.capsys_disabled.__exit__(None, None, None)
        self.capsys.readouterr()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, exc_traceback: Any) -> bool:
        res = self.capsys.readouterr()
        self.out = res.out
        self.err = res.err

        # Disable capsys again
        self.capsys_disabled = self.capsys.disabled()
        self.capsys_disabled.__enter__()
        return False


@pytest.fixture
def capture_output(capsys: CaptureFixture) -> CaptureOutput:
    return CaptureOutput(capsys)
