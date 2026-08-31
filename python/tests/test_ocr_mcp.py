"""PaddleOCR-VL MCP 客户端模块单元测试。"""
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag import ocr_mcp
from rag.ocr_mcp import OcrError, OcrUnavailableError, is_ocr_available, ocr_parse


class TestIsOcrAvailable:
    @patch("rag.ocr_mcp.shutil.which", return_value="paddleocr_mcp")
    def test_aistudio_requires_token(self, mock_which):
        with patch.object(ocr_mcp, "MCP_AISTUDIO_TOKEN", ""):
            assert is_ocr_available() is False
        with patch.object(ocr_mcp, "MCP_AISTUDIO_TOKEN", "fake-token"):
            assert is_ocr_available() is True

    @patch("rag.ocr_mcp.shutil.which", return_value=None)
    def test_missing_executable(self, mock_which):
        with patch.object(ocr_mcp, "MCP_AISTUDIO_TOKEN", "fake-token"):
            assert is_ocr_available() is False

    @patch("rag.ocr_mcp.shutil.which", return_value="paddleocr_mcp")
    def test_local_always_available(self, mock_which):
        with patch.object(ocr_mcp, "MCP_SOURCE", "local"):
            assert is_ocr_available() is True


class TestOcrParse:
    def test_raises_when_unavailable(self):
        with patch("rag.ocr_mcp.is_ocr_available", return_value=False):
            with pytest.raises(OcrUnavailableError):
                ocr_parse("C:/tmp/doc.png", "image")

    @patch("rag.ocr_mcp.is_ocr_available", return_value=True)
    def test_returns_markdown(self, mock_avail):
        with patch(
            "rag.ocr_mcp._call_paddleocr_vl", new_callable=AsyncMock, return_value="# 标题\n正文"
        ):
            result = ocr_parse("C:/tmp/doc.png", "image")
        assert result == "# 标题\n正文"


class TestExtractText:
    def test_extracts_text_content(self):
        class FakeContent:
            def __init__(self, text):
                self.text = text

        class FakeResult:
            isError = False
            content = [FakeContent("第一段"), FakeContent("第二段")]

        assert ocr_mcp._extract_text(FakeResult()) == "第一段\n第二段"

    def test_handles_empty(self):
        class FakeResult:
            isError = False
            content = []

        assert ocr_mcp._extract_text(FakeResult()) == ""


def _mock_mcp_call(call_tool_result):
    """构造模拟的 stdio MCP 客户端链路。"""
    # 模拟 session.call_tool
    session = MagicMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=call_tool_result)

    # 模拟 ClientSession(read, write) 上下文管理器
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    # 模拟 stdio_client(server_params) 上下文管理器
    stdio_cm = MagicMock()
    stdio_cm.__aenter__ = AsyncMock(return_value=("reader", "writer"))
    stdio_cm.__aexit__ = AsyncMock(return_value=False)

    # 两个符号均在函数体内导入，因此 patch 其在 mcp 包中的真实位置
    patch_stdio = patch("mcp.client.stdio.stdio_client", return_value=stdio_cm)
    patch_session = patch("mcp.ClientSession", return_value=session_cm)
    return patch_stdio, patch_session, session


class TestCallPaddleOCRVL:
    def test_passes_token_and_parses_markdown(self):
        """验证 aistudio 后端传 token、正确解析返回的 Markdown。"""
        class FakeContent:
            text = "# 识别结果\n\n这是一段测试文字。"

        class FakeResult:
            isError = False
            content = [FakeContent()]

        patch_stdio, patch_session, session = _mock_mcp_call(FakeResult())
        with patch_stdio, patch_session, patch.object(ocr_mcp, "MCP_SOURCE", "aistudio"):
            result = asyncio.run(ocr_mcp._call_paddleocr_vl("C:/tmp/a.png", "image"))

        assert result == "# 识别结果\n\n这是一段测试文字。"

        # 校验 CLI 参数
        from mcp import StdioServerParameters
        params = session.call_tool.call_args[0][1]
        assert params["input_data"] == "C:/tmp/a.png"
        assert params["file_type"] == "image"
        assert params["return_images"] is False

    def test_raises_on_tool_error(self):
        """验证 MCP 工具返回 isError=True 时抛出 OcrError。"""
        class FakeContent:
            text = "Authentication failed"

        class FakeResult:
            isError = True
            content = [FakeContent()]

        patch_stdio, patch_session, _ = _mock_mcp_call(FakeResult())
        with patch_stdio, patch_session:
            with pytest.raises(OcrError, match="Authentication failed"):
                asyncio.run(ocr_mcp._call_paddleocr_vl("C:/tmp/a.png", "image"))
