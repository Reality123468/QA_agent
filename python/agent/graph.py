"""
LangGraph Agent 图定义。

图结构 (ReAct 循环):
    START
      ↓
  agent_node (LLM 决策)
      ↓
  conditional_edge:
    ├── 有 tool_calls → tools_node → agent_node (循环)
    └── 无 tool_calls → END (返回最终回答)
"""

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState
from agent.nodes import agent_node, tools_node

logger = logging.getLogger(__name__)


def _should_continue(state: AgentState) -> str:
    """条件路由：检查最后一条消息是否有 tool_calls"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


def build_agent_graph() -> StateGraph:
    """构建并编译 Agent StateGraph。

    Returns:
        已编译的 StateGraph，可直接调用 .ainvoke() 或 .astream()
    """
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)

    # 入口 → agent
    workflow.set_entry_point("agent")

    # 条件边：agent 之后根据是否有 tool_calls 决定去向
    workflow.add_conditional_edges("agent", _should_continue, {
        "tools": "tools",
        END: END,
    })

    # tools 之后回到 agent
    workflow.add_edge("tools", "agent")

    # 编译（带内存 checkpointer 支持多轮对话）
    memory = MemorySaver()
    compiled = workflow.compile(checkpointer=memory)

    logger.info("Agent graph compiled successfully")
    return compiled


# 全局单例
_agent_graph = None


def get_agent_graph() -> StateGraph:
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph
