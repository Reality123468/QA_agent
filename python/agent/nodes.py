"""
LangGraph Agent 节点实现。

节点说明:
- agent_node: 调用 LLM（绑定 tools）进行推理决策
- tools_node: 执行 LLM 请求的工具调用，返回 Observation
"""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage, SystemMessage

from agent.state import AgentState
from agent.tools import ALL_TOOLS
from llm.deepseek_client import chat_sync

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """你是一名企业智能助手，拥有以下工具可以调用：

1. search_policy(query, department) - 检索企业规章制度（员工手册、财务制度、考勤政策等）
2. search_doc(query, tags) - 检索技术文档（API接口、系统架构、故障预案等）
3. search_employee(query) - 查询员工组织架构和通讯录
4. get_doc_detail(doc_id) - 获取指定文档的完整详细内容

请遵循以下工作模式：
- 先思考（Thought）：分析用户问题，确定需要调用哪些工具
- 再行动（Action）：调用合适的工具获取信息
- 观察结果（Observation）：根据工具返回的信息判断是否需要进一步搜索
- 最终回答：基于检索到的信息给出准确答案

重要规则：
- 仅根据工具返回的实际内容回答，不要编造信息
- 如果多次搜索后仍找不到相关信息，明确告知用户"该问题我目前无法准确回答"
- 回答中引用具体的文档名称和章节
- 如果用户问题涉及权限外内容，礼貌拒绝
- 回答简洁、专业、准确"""

# 将 LangChain tools 转为 OpenAI 兼容格式
TOOLS_OPENAI_FORMAT = [
    {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.args_schema.schema() if hasattr(t, 'args_schema') and t.args_schema else {},
        }
    }
    for t in ALL_TOOLS
]

# tool name → tool 映射
TOOL_BY_NAME = {t.name: t for t in ALL_TOOLS}


async def agent_node(state: AgentState) -> dict[str, Any]:
    """Agent 决策节点：调用 LLM 判断下一步动作（调用工具 或 直接回答）"""
    messages = state["messages"]

    # 确保第一条消息是 system prompt
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + list(messages)

    logger.info(f"[AgentNode] invoking LLM with {len(messages)} messages...")
    response = await chat_sync(
        messages=messages,
        model="deepseek-chat",
        temperature=0.3,
        max_tokens=1024,
        tools=TOOLS_OPENAI_FORMAT,
    )

    ai_message = AIMessage(
        content=response.content or "",
        tool_calls=[
            {
                "id": tc.id,
                "name": tc.function.name,
                "args": json.loads(tc.function.arguments),
            }
            for tc in (response.tool_calls or [])
        ] if response.tool_calls else [],
    )

    if response.tool_calls:
        logger.info(f"[AgentNode] LLM requested {len(response.tool_calls)} tool call(s)")
        for tc in response.tool_calls:
            logger.info(f"[AgentNode]   -> {tc.function.name}({tc.function.arguments})")
    else:
        logger.info(f"[AgentNode] LLM final answer (no tool calls)")

    return {"messages": [ai_message]}


async def tools_node(state: AgentState) -> dict[str, Any]:
    """工具执行节点：调用 LLM 请求的工具，返回 Observation"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", []) or []

    tool_messages = []
    for tc in tool_calls:
        tool_name = tc.get("name", "")
        tool_args = tc.get("args", {})
        tool_call_id = tc.get("id", "")

        logger.info(f"[ToolsNode] executing {tool_name}({tool_args})")

        tool_fn = TOOL_BY_NAME.get(tool_name)
        if tool_fn:
            try:
                result = tool_fn.invoke(tool_args)
                tool_messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))
            except Exception as e:
                logger.error(f"[ToolsNode] {tool_name} failed: {e}")
                tool_messages.append(ToolMessage(
                    content=f"工具调用失败: {str(e)}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))
        else:
            tool_messages.append(ToolMessage(
                content=f"未知工具: {tool_name}",
                tool_call_id=tool_call_id,
                name=tool_name,
            ))

    return {"messages": tool_messages}
