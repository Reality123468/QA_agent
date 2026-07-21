import logging
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader

logger = logging.getLogger(__name__)


def load_document(file_path: str, file_type: str) -> list:
    """根据文件类型加载文档，返回 List[Document]"""
    logger.info(f"Loading document: {file_path} (type={file_type})")

    if file_type == "pdf":
        loader = PyMuPDFLoader(file_path)
    elif file_type == "md":
        # Prefer UnstructuredMarkdownLoader if available, otherwise fall back to TextLoader
        try:
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            loader = UnstructuredMarkdownLoader(file_path)
            logger.info("Using UnstructuredMarkdownLoader for .md file")
        except (ImportError, ModuleNotFoundError):
            logger.warning(
                "UnstructuredMarkdownLoader not available (install 'unstructured' package). "
                "Falling back to TextLoader for .md file."
            )
            loader = TextLoader(file_path, encoding="utf-8")
    elif file_type == "txt":
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    return loader.load()
