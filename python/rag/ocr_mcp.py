"""
PaddleOCR-VL MCP 客户端模块

通过 MCP 协议（stdio 传输）调用 PaddleOCR MCP server 的 `paddleocr_vl` 工具，
对图片 / 扫描版 PDF 进行版面解析并输出 Markdown 文本，供 RAG 索引流程使用。

接入方式（与 paddleocr-mcp 官方 CLI 保持一致，均通过环境变量配置）：

    PADDLEOCR_MCP_MODEL                  模型名（默认 PaddleOCR-VL-1.6）
    PADDLEOCR_MCP_PPOCR_SOURCE           推理后端：aistudio / qianfan / local / self_hosted
    PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN  AI Studio 访问令牌（aistudio 后端必填）
    PADDLEOCR_MCP_QIANFAN_API_KEY        千帆 API Key（qianfan 后端必填）
    PADDLEOCR_MCP_SELF_HOSTED_BASE_URL   自建服务地址（self_hosted 后端必填）

说明：
- 本模块在「同步」上下文（文档索引的同步批处理流程）中调用，内部用 `asyncio.run()`
  独立事件循环驱动 MCP 客户端，因此调用方必须运行在非事件循环线程
  （`index_document_route` 已通过 `asyncio.to_thread` 满足该约束）。
- OCR 不可用（未安装 paddleocr_mcp / 未配置凭据）时抛出 `OcrUnavailableError`，
  上层可据此优雅降级；调用失败抛出 `OcrError`。
"""

import asyncio
import logging
import os
import shutil
from typing import List

logger = logging.getLogger(__name__)

# ── 环境变量配置（默认值与 paddleocr-mcp 官方 CLI 对齐）──
MCP_MODEL = os.getenv("PADDLEOCR_MCP_MODEL", "PaddleOCR-VL-1.6")
MCP_SOURCE = os.getenv("PADDLEOCR_MCP_PPOCR_SOURCE", "aistudio")
MCP_AISTUDIO_TOKEN = os.getenv("PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN", "")
MCP_QIANFAN_API_KEY = os.getenv("PADDLEOCR_MCP_QIANFAN_API_KEY", "")
MCP_SELF_HOSTED_BASE_URL = os.getenv("PADDLEOCR_MCP_SELF_HOSTED_BASE_URL", "")

MCP_TOOL_NAME = "paddleocr_vl"


class OcrUnavailableError(RuntimeError):
    """OCR 服务不可用（依赖缺失 / 凭据未配置）"""


class OcrError(RuntimeError):
    """OCR 调用失败"""


def is_ocr_available() -> bool:
    """OCR 是否可用：paddleocr_mcp 可执行文件存在，且已按后端配置凭据。"""
    executable = shutil.which("paddleocr_mcp")
    if not executable:
        return False
    if MCP_SOURCE == "aistudio":
        return bool(MCP_AISTUDIO_TOKEN)
    if MCP_SOURCE == "qianfan":
        return bool(MCP_QIANFAN_API_KEY)
    if MCP_SOURCE == "self_hosted":
        return bool(MCP_SELF_HOSTED_BASE_URL)
    if MCP_SOURCE == "local":
        return True
    return False


def ocr_parse(file_path: str, file_type: str = "image") -> str:
    """同步入口：调用 PaddleOCR-VL MCP 识别图片 / 扫描 PDF，返回 Markdown 文本。

    Args:
        file_path: 本地文件的绝对路径（AI Studio 后端支持绝对路径 / URL / Base64）。
        file_type: "image" 或 "pdf"。
    """
    if not is_ocr_available():
        raise OcrUnavailableError(
            "PaddleOCR MCP 不可用：请确认已安装 paddleocr-mcp，并配置 "
            f"PADDLEOCR_MCP_PPOCR_SOURCE={MCP_SOURCE} 所需的凭据。"
        )
    return asyncio.run(_call_paddleocr_vl(file_path, file_type))


async def _call_paddleocr_vl(file_path: str, file_type: str) -> str:
    """async 内部实现：通过 MCP stdio 客户端调用 paddleocr_vl 工具。"""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    # 构造 CLI 参数（优先读环境变量，与官方文档一致）
    args = ["--model", MCP_MODEL, "--ppocr_source", MCP_SOURCE]
    if MCP_SOURCE == "aistudio":
        args += ["--aistudio_access_token", MCP_AISTUDIO_TOKEN]
    elif MCP_SOURCE == "qianfan":
        args += ["--qianfan_api_key", MCP_QIANFAN_API_KEY]
    elif MCP_SOURCE == "self_hosted":
        args += ["--self-hosted-base-url", MCP_SELF_HOSTED_BASE_URL]

    server_params = StdioServerParameters(
        command="paddleocr_mcp",
        args=args,
        env={**os.environ.copy(), "PADDLEOCR_MCP_PPOCR_SOURCE": MCP_SOURCE},
    )

    logger.info(
        f"Calling PaddleOCR-VL MCP: model={MCP_MODEL} source={MCP_SOURCE} "
        f"file_type={file_type} file={os.path.basename(file_path)}"
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                MCP_TOOL_NAME,
                {
                    "input_data": file_path,
                    "file_type": file_type,
                    "output_mode": "simple",
                    "return_images": False,
                },
            )

    # 解析 MCP 返回结果
    if getattr(result, "isError", False):
        detail = _extract_text(result) or "PaddleOCR-VL 调用失败（未返回详情）"
        raise OcrError(f"PaddleOCR-VL 调用失败: {detail[:500]}")

    text = _extract_text(result)
    if not text or text.strip() in ("", "No document content detected"):
        raise OcrError("PaddleOCR-VL 未识别到文档内容")
    return text


def _extract_text(result) -> str:
    """从 MCP CallToolResult 中提取全部文本片段。"""
    parts: List[str] = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()
