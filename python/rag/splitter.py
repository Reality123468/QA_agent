import logging
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

logger = logging.getLogger(__name__)


def split_documents(docs: List[Document], file_type: str) -> List[Document]:
    """根据文件类型使用不同分块策略"""
    logger.info(f"Splitting {len(docs)} documents, file_type={file_type}")

    if file_type == "md":
        # Markdown: 按标题层级分割
        headers_to_split_on = [
            ("##", "section"),
            ("###", "subsection"),
        ]
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )
        chunks = []
        for doc in docs:
            md_chunks = splitter.split_text(doc.page_content)
            for chunk in md_chunks:
                chunk.metadata.update(doc.metadata)
            chunks.extend(md_chunks)
        return chunks

    elif file_type == "pdf":
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )
    else:  # txt, docx
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024,
            chunk_overlap=128,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

    return splitter.split_documents(docs)
