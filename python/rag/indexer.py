import uuid
import logging
from qdrant_client.models import Distance, VectorParams, PointStruct

from . import get_qdrant_client
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


def index_document(doc_info: dict) -> None:
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

    logger.info(f"Indexing document {doc_id}: {title}")

    # 1. 连接 Qdrant 并确保 collection 存在
    client = get_qdrant_client()
    _ensure_collection(client)

    # 2. 如果文档之前索引过，先删除旧 chunks
    _delete_doc_chunks(client, doc_id)

    # 3. 加载文档
    raw_docs = load_document(file_path, file_type)

    # 4. 分块
    chunks = split_documents(raw_docs, file_type)

    # 5. 向量化
    texts = [chunk.page_content for chunk in chunks]
    vectors = embed_texts(texts)

    # 6. 构建 Qdrant points（带 metadata）
    points = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        payload = {
            "doc_id": doc_id,
            "title": title,
            "department": department,
            "security_level": security_level,
            "chunk_index": i,
            "text": chunk.page_content,
            "source_page": chunk.metadata.get("page", 0),
            "heading": chunk.metadata.get("section", ""),
        }
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"qa-doc-{doc_id}-chunk-{i}"))
        points.append(PointStruct(id=point_id, vector=vector, payload=payload))

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info(f"Indexed {len(points)} chunks for document {doc_id}: {title}")


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


def delete_document_chunks(doc_id: int) -> None:
    """公共接口：删除指定文档在 Qdrant 中的所有向量"""
    client = get_qdrant_client()
    _ensure_collection(client)
    _delete_doc_chunks(client, doc_id)
