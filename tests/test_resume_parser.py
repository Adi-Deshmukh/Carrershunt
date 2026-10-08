from pathlib import Path

import pytest

from app.services.resume_parser import extract_resume_text


def test_extract_txt_resume() -> None:
    text = extract_resume_text("resume.txt", b"John Doe\nPython developer with FastAPI experience.")
    assert "Python developer" in text


def test_reject_unsupported_resume_type() -> None:
    with pytest.raises(ValueError, match="Unsupported resume format"):
        extract_resume_text("resume.csv", b"name,skill")


def test_reject_empty_resume() -> None:
    with pytest.raises(ValueError, match="Resume file is empty"):
        extract_resume_text("resume.txt", b"")
