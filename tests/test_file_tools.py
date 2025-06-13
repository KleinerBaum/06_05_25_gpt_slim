import io
import sys
from pathlib import Path

import fitz
from docx import Document

sys.path.append(str(Path(__file__).resolve().parents[2]))

from vacalyser.logic.file_tools import extract_text_from_file


def _make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_docx_bytes(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_extract_text_from_txt() -> None:
    data = b"hello world"
    result = extract_text_from_file(data, "sample.txt")
    assert isinstance(result, str)
    assert "hello" in result


def test_extract_text_from_pdf() -> None:
    data = _make_pdf_bytes("pdf text")
    result = extract_text_from_file(data, "sample.pdf")
    assert isinstance(result, str)
    assert "pdf text" in result


def test_extract_text_from_docx() -> None:
    data = _make_docx_bytes("docx text")
    result = extract_text_from_file(data, "sample.docx")
    assert isinstance(result, str)
    assert "docx text" in result
