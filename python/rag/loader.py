import os
import tempfile
import logging
import httpx
import fitz  # PyMuPDF
from urllib.parse import urlparse
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader
from langchain_core.documents import Document

from .ocr_mcp import ocr_parse, is_ocr_available, OcrUnavailableError, OcrError

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "admin123456")

# 支持 OCR 的图片类型
IMAGE_TYPES = {"png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"}

# 扫描版 PDF 判定阈值：总文本字符数低于该值视为无文本层，需走 OCR
SCANNED_PDF_MIN_TEXT_LEN = 50


def _download_from_minio(file_url: str) -> str:
    """Download file from MinIO URL using S3-compatible auth, return local temp path."""
    parsed = urlparse(file_url)
    path_parts = parsed.path.lstrip("/").split("/", 1)
    bucket = path_parts[0]
    object_name = path_parts[1] if len(path_parts) > 1 else ""

    from minio import Minio
    client = Minio(
        parsed.netloc,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )

    suffix = os.path.splitext(object_name)[1] or ".tmp"
    tmp_path = os.path.join(tempfile.gettempdir(), f"qa-doc-{os.urandom(8).hex()}{suffix}")
    logger.info(f"Downloading MinIO object: bucket={bucket}, object={object_name} -> {tmp_path}")
    resp = client.get_object(bucket, object_name)
    with open(tmp_path, "wb") as f:
        for chunk in resp.stream(64 * 1024):
            f.write(chunk)
    resp.close()
    resp.release_conn()
    return tmp_path


def _resolve_path(file_path: str) -> str:
    """If file_path is a URL, download to a temp file and return the local path."""
    if file_path.startswith("http://") or file_path.startswith("https://"):
        if MINIO_ENDPOINT and file_path.startswith(MINIO_ENDPOINT):
            return _download_from_minio(file_path)
        # Generic HTTP download (fallback)
        suffix = os.path.splitext(file_path.split("?")[0])[1] or ".tmp"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        logger.info(f"Downloading from {file_path} to {tmp.name}")
        with httpx.stream("GET", file_path, timeout=30) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_bytes():
                tmp.write(chunk)
        tmp.close()
        return tmp.name
    return file_path


def _ocr_to_documents(local_path: str, file_type: str) -> list:
    """通过 PaddleOCR-VL MCP 识别图片/扫描 PDF，返回 List[Document]。"""
    if not is_ocr_available():
        raise OcrUnavailableError(
            "当前文档为图片/扫描件，需要 OCR 能力，但 PaddleOCR MCP 不可用。"
            "请配置 PADDLEOCR_MCP_PPOCR_SOURCE 与对应凭据后重试。"
        )
    logger.info(f"Running PaddleOCR-VL OCR on {local_path} (type={file_type})")
    markdown = ocr_parse(local_path, file_type=file_type)
    if not markdown.strip():
        raise OcrError("OCR 结果为空")
    doc = Document(
        page_content=markdown,
        metadata={"source": local_path, "ocr": True, "file_type": file_type},
    )
    logger.info(f"OCR completed: {len(markdown)} chars extracted")
    return [doc]


def _is_scanned_pdf(local_path: str) -> bool:
    """判断 PDF 是否扫描版（无文本层或文本极少）。"""
    try:
        with fitz.open(local_path) as pdf:
            page_count = max(pdf.page_count, 1)
            total = 0
            for page in pdf:
                total += len(page.get_text("text") or "")
        avg = total / page_count
        logger.info(f"PDF text-layer check: total={total} chars, pages={page_count}, avg={avg:.1f}")
        # 平均每页文本极少 → 判定为扫描版
        return avg < 20 or total < SCANNED_PDF_MIN_TEXT_LEN
    except Exception as e:
        logger.warning(f"PDF text-layer check failed ({e}); treating as normal PDF")
        return False


def load_document(file_path: str, file_type: str) -> list:
    """根据文件类型加载文档，返回 List[Document]。

    图片（png/jpg/jpeg/bmp/tif/tiff/webp）与扫描版 PDF 通过 PaddleOCR-VL MCP 识别；
    含文本层的 PDF、MD/TXT/DOCX 保持原有解析逻辑。
    """
    local_path = _resolve_path(file_path)
    logger.info(f"Loading document: {file_path} -> {local_path} (type={file_type})")

    ft = file_type.lower()
    if ft in IMAGE_TYPES:
        return _ocr_to_documents(local_path, "image")

    if ft == "pdf":
        loader = PyMuPDFLoader(local_path)
        docs = loader.load()
        # 无文本层（扫描版 PDF）→ 走 OCR
        if _is_scanned_pdf(local_path):
            logger.warning(f"Detected scanned PDF (no text layer), falling back to OCR: {local_path}")
            return _ocr_to_documents(local_path, "pdf")
        return docs

    if ft in ("md", "markdown"):
        try:
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            loader = UnstructuredMarkdownLoader(local_path)
            logger.info("Using UnstructuredMarkdownLoader for .md file")
        except (ImportError, ModuleNotFoundError):
            logger.warning("UnstructuredMarkdownLoader not available, falling back to TextLoader")
            loader = TextLoader(local_path, encoding="utf-8")
        return loader.load()

    if ft == "txt":
        return TextLoader(local_path, encoding="utf-8").load()

    if ft == "docx":
        logger.info("Using Docx2txtLoader for .docx file")
        return Docx2txtLoader(local_path).load()

    raise ValueError(f"Unsupported file type: {file_type}")
