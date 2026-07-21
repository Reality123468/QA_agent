import logging
from typing import List
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchExcept

from . import get_qdrant_client
from .embedder import embed_query

logger = logging.getLogger(__name__)

COLLECTION_NAME = "qa_documents"


def hybrid_search(
    query: str,
    department: str = "全部",
    security_level: str = "内部",
    top_k: int = 10,
) -> List[dict]:
    """
    混合检索：向量语义检索 + 权限过滤

    Args:
        query: 用户查询
        department: 用户部门（用于权限过滤）
        security_level: 用户可见密级
        top_k: 返回结果数

    Returns:
        List[dict]: 每个结果包含 text, title, doc_id, chunk_index, score
    """
    client = get_qdrant_client()

    # 查询向量
    query_vector = embed_query(query)

    # 构建权限过滤条件
    must_conditions = [
        FieldCondition(
            key="department",
            match=MatchAny(any=[department, "全部"]),
        )
    ]
    # 非 LEADER/ADMIN 不能看机密文档
    if security_level == "内部":
        must_conditions.append(
            FieldCondition(
                key="security_level",
                match=MatchExcept(**{"except": ["机密"]}),
            )
        )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=Filter(must=must_conditions),
        limit=top_k,
        with_payload=True,
    )

    hits = []
    for r in results.points:
        hits.append({
            "text": r.payload.get("text", ""),
            "title": r.payload.get("title", ""),
            "doc_id": r.payload.get("doc_id", 0),
            "chunk_index": r.payload.get("chunk_index", 0),
            "source_page": r.payload.get("source_page", 0),
            "heading": r.payload.get("heading", ""),
            "score": r.score,
        })

    logger.info(f"Hybrid search: query='{query[:50]}...', hits={len(hits)}")
    return hits
