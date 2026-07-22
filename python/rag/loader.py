import os
import tempfile
import logging
import httpx
from urllib.parse import urlparse
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "admin123456")


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


def load_document(file_path: str, file_type: str) -> list:
    """根据文件类型加载文档，返回 List[Document]"""
    local_path = _resolve_path(file_path)
    logger.info(f"Loading document: {file_path} -> {local_path} (type={file_type})")

    ft = file_type.lower()
    if ft == "pdf":
        loader = PyMuPDFLoader(local_path)
    elif ft in ("md", "markdown"):
        try:
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            loader = UnstructuredMarkdownLoader(local_path)
            logger.info("Using UnstructuredMarkdownLoader for .md file")
        except (ImportError, ModuleNotFoundError):
            logger.warning("UnstructuredMarkdownLoader not available, falling back to TextLoader")
            loader = TextLoader(local_path, encoding="utf-8")
    elif ft == "txt":
        loader = TextLoader(local_path, encoding="utf-8")
    elif ft == "docx":
        loader = Docx2txtLoader(local_path)
        logger.info("Using Docx2txtLoader for .docx file")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    return loader.load()
