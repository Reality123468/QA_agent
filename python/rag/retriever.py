"""
混合检索：BM25 关键词 + Qdrant 向量语义 → RRF 融合。

检索流程:
1. 双路并行召回 Top-20: BM25 关键词 + Qdrant 向量语义
2. RRF (Reciprocal Rank Fusion) 融合: score = 1/(k+rank_dense) + 1/(k+rank_sparse), k=60
3. 返回融合后 Top-10
"""

import logging
from typing import List

from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchExcept, MatchValue

from . import get_qdrant_client
from .embedder import embed_query
from . import bm25_index

logger = logging.getLogger(__name__)

COLLECTION_NAME = "qa_documents"
RRF_K = 60  # RRF 融合平滑参数


def _qdrant_search(
    query_vector: List[float],
    department: str,
    security_level: str,
    top_k: int,
    category: str = "all",
) -> List[dict]:
    """Qdrant 向量语义检索"""
    client = get_qdrant_client()

    must_conditions = [
        FieldCondition(key="department", match=MatchAny(any=[department, "全部"])),
    ]
    if category != "all":
        must_conditions.append(
            FieldCondition(key="doc_type", match=MatchValue(value=category))
        )
    if security_level == "内部":
        must_conditions.append(
            FieldCondition(key="security_level", match=MatchExcept(**{"except": ["机密"]}))
        )

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=Filter(must=must_conditions),
            limit=top_k,
            with_payload=True,
        )
        points = results.points
    except Exception:
        logger.warning("Qdrant query failed (collection may not exist), returning empty")
        points = []

    return [
        {
            "text": p.payload.get("text", ""),
            "title": p.payload.get("title", ""),
            "doc_id": p.payload.get("doc_id", 0),
            "chunk_index": p.payload.get("chunk_index", 0),
            "source_page": p.payload.get("source_page", 0),
            "heading": p.payload.get("heading", ""),
            "doc_type": p.payload.get("doc_type", "general"),
            "score": p.score,
            "source": "vector",
        }
        for p in points
    ]


def _bm25_search(query: str, top_k: int, category: str = "all",
                 department: str = "全部", security_level: str = "内部") -> List[dict]:
    """BM25 关键词检索，结果转为统一格式"""
    results = bm25_index.search(
        query, top_k=top_k, category=category,
        department=department, security_level=security_level,
    )
    hits = []
    for idx, score in results:
        item = bm25_index.get_corpus_item(idx)
        if item:
            hits.append({
                "text": item["text"],
                "title": item["title"],
                "doc_id": item["doc_id"],
                "chunk_index": item["chunk_index"],
                "doc_type": item.get("doc_type", "general"),
                "department": item.get("department", "全部"),
                "security_level": item.get("security_level", "内部"),
                "source_page": 0,
                "heading": "",
                "score": float(score),
                "source": "bm25",
            })
    return hits


def _rrf_fusion(
    dense_hits: List[dict],
    sparse_hits: List[dict],
    k: int = RRF_K,
) -> List[dict]:
    """
    RRF (Reciprocal Rank Fusion) 融合双路结果。

    融合公式: score = 1/(k + rank_dense) + 1/(k + rank_sparse)
    以 (doc_id, chunk_index) 作为唯一键合并。
    """
    rrf_scores: dict[tuple, float] = {}
    hit_map: dict[tuple, dict] = {}

    for rank, hit in enumerate(dense_hits, start=1):
        key = (hit["doc_id"], hit["chunk_index"])
        rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (k + rank)
        if key not in hit_map:
            hit_map[key] = hit

    for rank, hit in enumerate(sparse_hits, start=1):
        key = (hit["doc_id"], hit["chunk_index"])
        rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (k + rank)
        if key not in hit_map:
            hit_map[key] = hit

    # 按 RRF 分数降序
    sorted_keys = sorted(rrf_scores, key=rrf_scores.get, reverse=True)

    return [
        {
            **hit_map[key],
            "score": round(rrf_scores[key], 6),
            "dense_rank": next((i for i, h in enumerate(dense_hits, 1) if (h["doc_id"], h["chunk_index"]) == key), None),
            "sparse_rank": next((i for i, h in enumerate(sparse_hits, 1) if (h["doc_id"], h["chunk_index"]) == key), None),
        }
        for key in sorted_keys
    ]


def hybrid_search(
    query: str,
    department: str = "全部",
    security_level: str = "内部",
    top_k: int = 10,
    category: str = "all",
) -> List[dict]:
    """
    混合检索：BM25 关键词 + 向量语义 → RRF 融合。

    双路各取 Top-20，RRF 融合后返回 Top-{top_k}。

    Args:
        category: 文档类别过滤 — "all"(全部) / "policy"(规章制度) / "tech_doc"(技术文档) / "general"(通用)
    """
    recall_size = 20

    # 并行双路召回
    from concurrent.futures import ThreadPoolExecutor

    query_vector = embed_query(query)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_dense = executor.submit(
            _qdrant_search, query_vector, department, security_level, recall_size, category
        )
        future_sparse = executor.submit(
            _bm25_search, query, recall_size, category, department, security_level
        )
        dense_hits = future_dense.result()
        sparse_hits = future_sparse.result()

    logger.info(
        f"Hybrid recall: vector={len(dense_hits)}, bm25={len(sparse_hits)}"
    )

    # RRF 融合
    fused = _rrf_fusion(dense_hits, sparse_hits)

    result = fused[:top_k]
    logger.info(
        f"Hybrid search: query='{query[:50]}...', fused={len(fused)}, final={len(result)}"
    )
    return result


def get_document_chunks(doc_id: int, max_chunks: int = 20,
                       security_level: str = "内部") -> List[dict]:
    """获取指定文档的所有 chunks（按 chunk_index 排序），支持安全级别过滤"""
    client = get_qdrant_client()
    must_conditions = [FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
    # 安全级别过滤：内部用户不可查看机密文档
    if security_level == "内部":
        must_conditions.append(
            FieldCondition(key="security_level", match=MatchExcept(**{"except": ["机密"]}))
        )
    try:
        results = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(must=must_conditions),
            limit=max_chunks,
            with_payload=True,
        )
        points = results[0]
        points.sort(key=lambda p: p.payload.get("chunk_index", 0))
        return [
            {
                "text": p.payload.get("text", ""),
                "chunk_index": p.payload.get("chunk_index", 0),
                "title": p.payload.get("title", ""),
                "heading": p.payload.get("heading", ""),
            }
            for p in points
        ]
    except Exception:
        logger.warning(f"Failed to get chunks for doc_id={doc_id}", exc_info=True)
        return []


def get_chunk_by_id(doc_id: int, chunk_index: int, security_level: str = "内部") -> dict | None:
    """获取文档的单个 chunk（按 chunk_index 精确定位），支持安全级别过滤"""
    client = get_qdrant_client()
    must_conditions = [
        FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
        FieldCondition(key="chunk_index", match=MatchValue(value=chunk_index)),
    ]
    if security_level == "内部":
        must_conditions.append(
            FieldCondition(key="security_level", match=MatchExcept(**{"except": ["机密"]}))
        )
    try:
        results = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(must=must_conditions),
            limit=1,
            with_payload=True,
        )
        points = results[0]
        if not points:
            return None
        p = points[0]
        return {
            "text": p.payload.get("text", ""),
            "chunk_index": p.payload.get("chunk_index", 0),
            "title": p.payload.get("title", ""),
            "heading": p.payload.get("heading", ""),
        }
    except Exception:
        logger.warning(f"Failed to get chunk doc_id={doc_id} chunk_index={chunk_index}", exc_info=True)
        return None
