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

    # 编译（无 checkpointer）
    # 单次请求内 agent_node ⇄ tools_node 的状态流转由 LangGraph 运行时维护；
    # 跨轮对话上下文由前端每轮发送的全量 history 提供，无需服务端持久化。
    # 若将来需多实例共享 / 服务端托管历史，可换 RedisSaver 并恢复 thread_id 路由。
    compiled = workflow.compile()

    logger.info("Agent graph compiled successfully")
    return compiled


# 全局单例
_agent_graph = None


def get_agent_graph() -> StateGraph:
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph
