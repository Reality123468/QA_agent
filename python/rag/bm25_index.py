"""
BM25 关键词检索索引（内存）。

特性:
- jieba 中文分词 + rank_bm25 BM25Okapi
- 与 Qdrant 向量检索互补，双路召回后 RRF 融合
- 文档增删时同步更新，支持全量重建
"""

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# 全局 BM25 索引状态
# corpus: (doc_id, chunk_index, title, text, doc_type, department, security_level)
_corpus: List[Tuple[int, int, str, str, str, str, str]] = []
_bm25_model = None  # BM25Okapi 实例
_tokenized_corpus: List[List[str]] = []  # 分词后的语料


def _tokenize(text: str) -> List[str]:
    """jieba 分词（去停用词级别的短词）"""
    try:
        import jieba
    except ImportError:
        logger.warning("jieba not installed, falling back to char-level tokenization")
        return list(text)

    tokens = jieba.lcut(text)
    return [t.strip() for t in tokens if len(t.strip()) > 1]


def _rebuild_model():
    """根据当前语料重建 BM25 模型"""
    global _bm25_model, _tokenized_corpus

    if not _corpus:
        _bm25_model = None
        _tokenized_corpus = []
        return

    from rank_bm25 import BM25Okapi

    _tokenized_corpus = [_tokenize(text) for _, _, _, text, _, _, _ in _corpus]
    _bm25_model = BM25Okapi(_tokenized_corpus)
    logger.info(f"BM25 index rebuilt: {len(_corpus)} documents")


def add_texts(texts: List[dict]):
    """
    向 BM25 索引添加文本块。

    texts: [{"doc_id": int, "chunk_index": int, "title": str, "text": str, "doc_type": str}, ...]
    """
    global _corpus

    for t in texts:
        _corpus.append((
            t["doc_id"], t["chunk_index"], t["title"], t["text"],
            t.get("doc_type", "general"),
            t.get("department", "全部"),
            t.get("security_level", "内部"),
        ))

    _rebuild_model()


def remove_doc(doc_id: int):
    """从 BM25 索引中移除指定文档的所有 chunks"""
    global _corpus

    before = len(_corpus)
    _corpus = [item for item in _corpus if item[0] != doc_id]
    removed = before - len(_corpus)

    if removed > 0:
        _rebuild_model()
        logger.info(f"BM25: removed {removed} chunks for doc_id={doc_id}")


def rebuild_from_qdrant(client):
    """从 Qdrant 全量重建 BM25 索引"""
    global _corpus

    try:
        from .retriever import COLLECTION_NAME

        all_points = []
        offset = None
        while True:
            results = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                with_payload=True,
                offset=offset,
            )
            points, next_offset = results
            all_points.extend(points)
            if next_offset is None:
                break
            offset = next_offset

        _corpus = [
            (
                p.payload.get("doc_id", 0),
                p.payload.get("chunk_index", 0),
                p.payload.get("title", ""),
                p.payload.get("text", ""),
                p.payload.get("doc_type", "general"),
                p.payload.get("department", "全部"),
                p.payload.get("security_level", "内部"),
            )
            for p in all_points
        ]
        _rebuild_model()
        logger.info(f"BM25 index rebuilt from Qdrant: {len(_corpus)} chunks")
    except Exception as e:
        logger.warning(f"Failed to rebuild BM25 from Qdrant: {e}")


def search(
    query: str,
    top_k: int = 20,
    category: str = "all",
    department: str = "全部",
    security_level: str = "内部",
) -> List[Tuple[int, float]]:
    """
    BM25 关键词检索。

    Args:
        query: 搜索查询
        top_k: 返回结果数
        category: 文档类型过滤 (all/policy/tech_doc/general)
        department: 部门过滤
        security_level: 密级过滤（"内部" 排除 "机密" 文档）

    Returns:
        List of (corpus_index, bm25_score), sorted by score descending
    """
    if _bm25_model is None or not _corpus:
        logger.warning("BM25 index is empty, returning no results")
        return []

    tokenized_query = _tokenize(query)
    scores = _bm25_model.get_scores(tokenized_query)

    # 按分数降序，可选 category / department / security_level 过滤
    indexed_scores = list(enumerate(scores))
    if category != "all":
        indexed_scores = [
            (i, s) for i, s in indexed_scores
            if _corpus[i][4] == category
        ]
    if department != "全部":
        indexed_scores = [
            (i, s) for i, s in indexed_scores
            if _corpus[i][5] in (department, "全部")
        ]
    if security_level == "内部":
        indexed_scores = [
            (i, s) for i, s in indexed_scores
            if _corpus[i][6] != "机密"
        ]

    indexed_scores.sort(key=lambda x: x[1], reverse=True)

    logger.info(
        f"BM25 search: query='{query[:50]}...', category={category}, "
        f"corpus_size={len(_corpus)}, top_hit_score={indexed_scores[0][1]:.4f}"
        if indexed_scores else ""
    )
    return indexed_scores[:top_k]


def get_corpus_item(index: int) -> Optional[dict]:
    """根据索引获取语料项元数据"""
    if 0 <= index < len(_corpus):
        doc_id, chunk_index, title, text, doc_type, department, security_level = _corpus[index]
        return {
            "doc_id": doc_id,
            "chunk_index": chunk_index,
            "title": title,
            "text": text,
            "doc_type": doc_type,
            "department": department,
            "security_level": security_level,
        }
    return None


def corpus_size() -> int:
    return len(_corpus)
