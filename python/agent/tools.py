"""
Agent 工具集 — 封装 rag.retriever.hybrid_search 为 LangChain Tool。

工具列表:
1. search_knowledge  — 统一知识库检索（制度 + 技术文档）
2. search_employee   — 查询员工组织架构
3. get_doc_detail    — 获取文档完整详情
"""

import logging
from typing import Optional

from langchain_core.tools import tool
from rag.retriever import hybrid_search, get_document_chunks, get_chunk_by_id
from agent.context import current_security_level

logger = logging.getLogger(__name__)


@tool
def search_knowledge(query: str, category: str = "all", department: str = "全部") -> str:
    """统一知识库检索工具，覆盖企业规章制度和技术文档。
    根据用户问题自动判断应检索的类别：
    - category="policy": 检索规章制度（员工手册、财务制度、考勤政策、报销流程、休假规定等）
    - category="tech_doc": 检索技术文档（API接口、系统架构、故障预案、技术规范等）
    - category="all": 同时检索所有类型（默认）

    Args:
        query: 搜索关键词，如"年假天数"、"登录接口"、"数据库架构"
        category: 文档类别 — policy(规章制度) / tech_doc(技术文档) / all(全部)
        department: 用户所属部门，用于权限过滤，默认为"全部"
    """
    seclevel = current_security_level.get()
    logger.info(f"[Tool:search_knowledge] query='{query}', category='{category}', department='{department}', seclevel='{seclevel}'")
    hits = hybrid_search(
        query, department=department, security_level=seclevel,
        top_k=5, category=category,
    )
    if not hits:
        return f"未找到相关{'规章制度' if category == 'policy' else '技术文档' if category == 'tech_doc' else '文档'}。"
    return _format_hits(hits)


@tool
def search_employee(query: str) -> str:
    """查询企业员工组织架构、角色分工和联系方式。
    当用户询问"XX部门负责人是谁"或"谁负责XX"等组织架构问题时使用。

    Args:
        query: 搜索关键词，如"技术部负责人"
    """
    logger.info(f"[Tool:search_employee] query='{query}'")
    seclevel = current_security_level.get()
    hits = hybrid_search(query, department="全部", security_level=seclevel, top_k=5)
    if not hits:
        return "未找到相关人员信息。请确认查询关键词后重试，或联系管理员。"
    return _format_hits(hits)


@tool
def get_doc_detail(doc_id: int, chunk_index: int = None) -> str:
    """获取指定文档的内容。两步使用：
    1. 仅传 doc_id：返回文档的章节索引（chunk 标题列表 + chunk_index 编号）
    2. 传 doc_id + chunk_index：返回该 chunk 的完整文本内容

    当检索片段不足以回答用户问题，或需要查看文档某章节详细内容时使用。
    建议先获取章节索引，再根据需要拉取具体章节。

    Args:
        doc_id: 文档唯一ID（整数），从检索结果中获取
        chunk_index: 可选，指定要获取的章节编号。不传则返回章节索引列表
    """
    seclevel = current_security_level.get()
    logger.info(f"[Tool:get_doc_detail] doc_id={doc_id}, chunk_index={chunk_index}, seclevel='{seclevel}'")

    if chunk_index is not None:
        # ── Step 2: 返回单个 chunk 完整内容 ──
        chunk = get_chunk_by_id(doc_id, chunk_index, security_level=seclevel)
        if not chunk:
            return f"未找到文档 ID={doc_id} 的章节 chunk_index={chunk_index}，该章节可能已被删除或权限不足。"
        title = chunk.get("title", "未知文档")
        heading = chunk.get("heading", "")
        heading_label = f" (章节: {heading})" if heading else ""
        return f"文档《{title}》{heading_label}\n\n{chunk['text']}"
    else:
        # ── Step 1: 返回章节索引 ──
        chunks = get_document_chunks(doc_id, security_level=seclevel)
        if not chunks:
            return f"未找到文档 ID={doc_id} 的内容，文档可能已被删除或您无权查看。"
        title = chunks[0].get("title", "未知文档")
        lines = [f"文档《{title}》共 {len(chunks)} 个章节："]
        for c in chunks:
            ci = c.get("chunk_index", 0)
            heading = c.get("heading", "")
            preview = c.get("text", "")[:80].replace("\n", " ")
            label = f" (章节: {heading})" if heading else ""
            lines.append(f"  [chunk_index={ci}]{label} {preview}...")
        return "\n".join(lines)


def _format_hits(hits: list) -> str:
    """将检索结果列表格式化为 LLM 可读的文本。"""
    results = []
    for i, h in enumerate(hits[:5], 1):
        title = h.get("title", "未知文档")
        heading = h.get("heading", "")
        text = h.get("text", "")[:300]
        doc_type = h.get("doc_type", "")
        type_label = {"policy": "[制度]", "tech_doc": "[技术]", "general": "[通用]"}.get(doc_type, "")
        section = f" (章节: {heading})" if heading else ""
        results.append(f"[{i}] {type_label} 来源: {title}{section}\n    {text}...")
    return "\n\n".join(results)


# 工具注册表（供 nodes.py / graph.py 使用）
ALL_TOOLS = [search_knowledge, search_employee, get_doc_detail]
