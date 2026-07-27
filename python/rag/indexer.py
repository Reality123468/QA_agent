import uuid
import json
import logging
import urllib.request
from typing import Optional
from qdrant_client.models import Distance, VectorParams, PointStruct

from . import get_qdrant_client
from . import bm25_index
from .loader import load_document
from .splitter import split_documents
from .embedder import embed_texts, get_vector_size

logger = logging.getLogger(__name__)

COLLECTION_NAME = "qa_documents"


def _ensure_collection(client):
    """确保 collection 存在"""
    vector_size = get_vector_size()
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    if COLLECTION_NAME not in collection_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection '{COLLECTION_NAME}' with vector_size={vector_size}")
    else:
        logger.info(f"Collection '{COLLECTION_NAME}' already exists")


def _send_progress(progress_url: Optional[str], doc_id: int, status: str, message: str):
    """向 Java 后端发送索引进度"""
    if not progress_url:
        return
    try:
        data = json.dumps({"status": status, "message": message}).encode("utf-8")
        req = urllib.request.Request(
            progress_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logger.warning(f"Failed to send progress to {progress_url}: {e}")


def index_document(doc_info: dict, progress_url: Optional[str] = None) -> None:
    """
    完整索引流程：加载文档 → 分块 → 向量化 → 存入 Qdrant

    doc_info 字段:
        - id: 文档ID
        - title: 标题
        - file_path: MinIO 文件路径
        - file_type: pdf/md/txt
        - department: 所属部门
        - security_level: 密级
    """
    doc_id = doc_info["id"]
    title = doc_info["title"]
    file_path = doc_info["file_path"]
    file_type = doc_info["file_type"]
    department = doc_info.get("department", "全部")
    security_level = doc_info.get("security_level", "内部")
    doc_type = _infer_doc_type(title)

    logger.info(f"Indexing document {doc_id}: {title} (doc_type={doc_type})")
    _send_progress(progress_url, doc_id, "INDEXING", "开始索引...")

    # 1. 连接 Qdrant 并确保 collection 存在
    client = get_qdrant_client()
    _ensure_collection(client)

    # 2. 如果文档之前索引过，先删除旧 chunks
    _delete_doc_chunks(client, doc_id)

    # 3. 加载文档
    _send_progress(progress_url, doc_id, "INDEXING", "正在加载文档...")
    raw_docs = load_document(file_path, file_type)

    # 4. 分块
    _send_progress(progress_url, doc_id, "INDEXING", f"正在分块 ({len(raw_docs)} 个文档)...")
    chunks = split_documents(raw_docs, file_type)
    _send_progress(progress_url, doc_id, "INDEXING", f"分块完成，共 {len(chunks)} 个片段")

    # 5. 向量化
    _send_progress(progress_url, doc_id, "INDEXING", "正在向量化...")
    texts = [chunk.page_content for chunk in chunks]
    vectors = embed_texts(texts)
    _send_progress(progress_url, doc_id, "INDEXING", f"向量化完成，{len(vectors)} 个向量")

    # 6. 构建 Qdrant points（带 metadata）
    _send_progress(progress_url, doc_id, "INDEXING", "正在存储到向量库...")
    points = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        payload = {
            "doc_id": doc_id,
            "title": title,
            "department": department,
            "security_level": security_level,
            "doc_type": doc_type,
            "chunk_index": i,
            "text": chunk.page_content,
            "source_page": chunk.metadata.get("page", 0),
            "heading": chunk.metadata.get("section", ""),
        }
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"qa-doc-{doc_id}-chunk-{i}"))
        points.append(PointStruct(id=point_id, vector=vector, payload=payload))

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info(f"Indexed {len(points)} chunks for document {doc_id}: {title}")

    # 同步 BM25 索引
    _send_progress(progress_url, doc_id, "INDEXING", "正在同步 BM25 索引...")
    bm25_index.remove_doc(doc_id)
    bm25_index.add_texts([
        {"doc_id": doc_id, "chunk_index": i, "title": title, "text": texts[i], "doc_type": doc_type}
        for i in range(len(texts))
    ])

    _send_progress(progress_url, doc_id, "COMPLETED", f"索引完成，共 {len(points)} 个片段")


def _infer_doc_type(title: str) -> str:
    """根据文档标题推断文档类型"""
    policy_keywords = ["制度", "规定", "办法", "手册", "考勤", "休假", "报销", "福利", "薪酬", "差旅", "行政"]
    tech_keywords = ["接口", "API", "架构", "技术", "数据库", "部署", "故障", "预案", "运维", "开发", "代码", "测试"]

    for kw in policy_keywords:
        if kw in title:
            return "policy"
    for kw in tech_keywords:
        if kw in title:
            return "tech_doc"
    return "general"


def _delete_doc_chunks(client, doc_id: int):
    """删除指定文档的所有 chunks"""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="doc_id",
                    match=MatchValue(value=doc_id),
                )
            ]
        ),
    )
    logger.info(f"Deleted existing chunks for doc {doc_id}")
    bm25_index.remove_doc(doc_id)


def delete_document_chunks(doc_id: int) -> None:
    """公共接口：删除指定文档在 Qdrant 中的所有向量"""
    client = get_qdrant_client()
    _ensure_collection(client)
    _delete_doc_chunks(client, doc_id)
