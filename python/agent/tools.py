"""
Agent 工具集 — 封装 rag.retriever.hybrid_search 为 LangChain Tool。

PRD §4.6 定义 4 个工具：
1. search_policy    — 检索规章制度（按部门权限过滤）
2. search_doc       — 检索技术文档（按标签筛选）
3. search_employee  — 查询员工组织架构（MVP 占位）
4. get_doc_detail   — 获取文档完整详情（MVP 占位）
"""

import json
import logging
from typing import Optional

from langchain_core.tools import tool
from rag.retriever import hybrid_search

logger = logging.getLogger(__name__)


@tool
def search_policy(query: str, department: str = "全部") -> str:
    """检索企业内部规章制度，包括员工手册、财务制度、考勤政策、报销流程等。
    当用户询问休假、报销、考勤、薪酬福利等政策类问题时使用此工具。

    Args:
        query: 搜索关键词，如"年假"、"报销"
        department: 用户所属部门，用于权限过滤，默认为"全部"
    """
    logger.info(f"[Tool:search_policy] query='{query}', department='{department}'")
    hits = hybrid_search(query, department=department, security_level="内部", top_k=5)
    if not hits:
        return "未找到相关规章制度。"
    return _format_hits(hits)


@tool
def search_doc(query: str, tags: Optional[str] = None) -> str:
    """检索企业内部技术文档，包括API接口文档、系统架构、故障预案、技术规范等。
    当用户询问技术实现、接口说明、系统设计等技术类问题时使用此工具。

    Args:
        query: 搜索关键词，如"登录接口"、"数据库设计"
        tags: 技术标签，可选，如"Java"、"Python"
    """
    logger.info(f"[Tool:search_doc] query='{query}', tags='{tags}'")
    hits = hybrid_search(query, department="全部", security_level="内部", top_k=5)
    if not hits:
        return "未找到相关技术文档。"
    return _format_hits(hits)


@tool
def search_employee(query: str) -> str:
    """查询企业员工组织架构、角色分工和联系方式。
    当用户询问"XX部门负责人是谁"或"谁负责XX"等组织架构问题时使用。

    Args:
        query: 搜索关键词，如"技术部负责人"
    """
    logger.info(f"[Tool:search_employee] query='{query}'")
    return "员工通讯录功能开发中，暂不可用。如需查询请联系管理员。"


@tool
def get_doc_detail(doc_id: str) -> str:
    """获取指定文档的完整详细内容。当检索片段不足以回答用户问题，
    需要查看文档全文时使用此工具。

    Args:
        doc_id: 文档唯一ID，从检索结果中获取
    """
    logger.info(f"[Tool:get_doc_detail] doc_id='{doc_id}'")
    return "文档详情查询功能开发中，暂不可用。目前仅支持基于检索片段的问答。"


def _format_hits(hits: list) -> str:
    """将检索结果列表格式化为 LLM 可读的文本。"""
    results = []
    for i, h in enumerate(hits[:5], 1):
        title = h.get("title", "未知文档")
        heading = h.get("heading", "")
        text = h.get("text", "")[:300]
        section = f" (章节: {heading})" if heading else ""
        results.append(f"[{i}] 来源: {title}{section}\n    {text}...")
    return "\n\n".join(results)


# 工具注册表（供 graph.py 使用）
ALL_TOOLS = [search_policy, search_doc, search_employee, get_doc_detail]
