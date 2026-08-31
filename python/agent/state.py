"""
AgentState — 共享状态，在 LangGraph 节点间传递。

字段说明:
- messages:    对话历史（使用 LangGraph 的 add_messages reducer 自动合并）
- department:  用户部门，用于 hybrid_search 权限过滤
- security_level: 用户可见的最高密级
- retrieved_docs: hybrid_search 返回的文档列表，供 final answer 引用
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    department: str
    security_level: str
    retrieved_docs: list
    summary: str  # 累积对话摘要（滚动压缩用）
