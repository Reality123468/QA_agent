"""loader 模块测试：OCR 集成 + 常规文档类型回归。"""
import os
import tempfile
from unittest.mock import patch

import fitz
import pytest

from rag.loader import _is_scanned_pdf, load_document
from rag.ocr_mcp import OcrUnavailableError


def _make_pdf(path, text=None):
    """生成真实的 PDF 文件，text=None 时生成空白（无文本层）PDF。"""
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


class TestImageOcr:
    def test_image_goes_through_ocr(self, tmp_path):
        img = tmp_path / "scan.png"
        img.write_bytes(b"fake-png-bytes")
        with patch("rag.loader._resolve_path", return_value=str(img)):
            with patch("rag.loader._ocr_to_documents") as mock_ocr:
                mock_ocr.return_value = [type("D", (), {"page_content": "# 扫描件", "metadata": {}})()]
                docs = load_document("http://minio/x.png", "png")
        mock_ocr.assert_called_once_with(str(img), "image")
        assert docs[0].page_content == "# 扫描件"

    def test_image_raises_when_ocr_unavailable(self, tmp_path):
        img = tmp_path / "scan.jpg"
        img.write_bytes(b"fake-jpg")
        with patch("rag.loader._resolve_path", return_value=str(img)):
            with patch("rag.loader.is_ocr_available", return_value=False):
                with pytest.raises(OcrUnavailableError):
                    load_document(str(img), "jpg")


class TestScannedPdf:
    def test_is_scanned_pdf_detects_empty_text_layer(self, tmp_path):
        pdf = tmp_path / "empty.pdf"
        _make_pdf(pdf)
        assert _is_scanned_pdf(str(pdf)) is True

    def test_is_scanned_pdf_keeps_text_pdf(self, tmp_path):
        pdf = tmp_path / "text.pdf"
        _make_pdf(pdf, text="This is a text-layer PDF used to verify it is not treated as scanned.")
        assert _is_scanned_pdf(str(pdf)) is False

    def test_scanned_pdf_falls_back_to_ocr(self, tmp_path):
        pdf = tmp_path / "scan.pdf"
        _make_pdf(pdf)
        with patch("rag.loader._resolve_path", return_value=str(pdf)):
            with patch("rag.loader._is_scanned_pdf", return_value=True):
                with patch("rag.loader.PyMuPDFLoader") as mock_loader:
                    mock_loader.return_value.load.return_value = []
                    with patch("rag.loader._ocr_to_documents") as mock_ocr:
                        mock_ocr.return_value = []
                        load_document(str(pdf), "pdf")
        mock_ocr.assert_called_once_with(str(pdf), "pdf")


class TestRegularTypesRegression:
    """回归：有文本层的 PDF / TXT / DOCX 保持原解析路径，不触发 OCR。"""

    def test_txt_loader(self, tmp_path):
        txt = tmp_path / "note.txt"
        txt.write_text("普通文本内容，用于索引。", encoding="utf-8")
        with patch("rag.loader._resolve_path", return_value=str(txt)):
            with patch("rag.loader._ocr_to_documents") as mock_ocr:
                docs = load_document(str(txt), "txt")
        mock_ocr.assert_not_called()
        assert "普通文本内容" in docs[0].page_content

    def test_pdf_with_text_layer_skips_ocr(self, tmp_path):
        pdf = tmp_path / "normal.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        with patch("rag.loader._resolve_path", return_value=str(pdf)):
            with patch("rag.loader._is_scanned_pdf", return_value=False):
                with patch("rag.loader._ocr_to_documents") as mock_ocr:
                    with patch("rag.loader.PyMuPDFLoader") as mock_loader:
                        mock_loader.return_value.load.return_value = ["doc1"]
                        docs = load_document(str(pdf), "pdf")
        mock_ocr.assert_not_called()
        assert docs == ["doc1"]

    def test_docx_loader(self, tmp_path):
        docx = tmp_path / "doc.docx"
        docx.write_bytes(b"fake-docx")
        with patch("rag.loader._resolve_path", return_value=str(docx)):
            with patch("rag.loader._ocr_to_documents") as mock_ocr:
                with patch("rag.loader.Docx2txtLoader") as mock_loader:
                    mock_loader.return_value.load.return_value = ["docx-doc"]
                    docs = load_document(str(docx), "docx")
        mock_ocr.assert_not_called()
        assert docs == ["docx-doc"]

    def test_unsupported_type_raises(self, tmp_path):
        with pytest.raises(ValueError):
            load_document("x.exe", "exe")
