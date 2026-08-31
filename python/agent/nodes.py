"""
LangGraph Agent 节点实现。

节点说明:
- agent_node: 调用 LLM（绑定 tools）进行推理决策
- tools_node: 执行 LLM 请求的工具调用，返回 Observation
"""

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage, SystemMessage, HumanMessage

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from agent.state import AgentState
from agent.tools import ALL_TOOLS
from agent.context import current_security_level
from common.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from llm.deepseek_client import chat_sync, count_tokens, summarize_history, ensure_token_budget, TOKEN_BUDGET

logger = logging.getLogger(__name__)

AGENT_LLM_TIMEOUT = 30  # Agent LLM 调用超时（秒）
TOOL_EXEC_TIMEOUT = 15   # 单个工具执行超时（秒）

AGENT_SYSTEM_PROMPT = """你是一名企业智能助手，拥有以下工具可以调用：

1. search_knowledge(query, category, department) - 统一知识库检索
   - category="policy": 检索规章制度（员工手册、财务制度、考勤政策等）
   - category="tech_doc": 检索技术文档（API接口、系统架构、故障预案等）
   - category="all": 同时检索所有类型
2. search_employee(query) - 查询员工组织架构和通讯录
3. get_doc_detail(doc_id) - 获取指定文档的完整详细内容

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

# 安全前缀映射 — 注入到 Agent 用户消息中，约束 LLM 不泄露越权内容
SECURITY_PREFIX_MAP = {
    "内部": "[安全级别：内部。禁止在回答中泄露任何标记为「机密」的文档内容。]",
    "机密": "[安全级别：机密。你可以引用所有级别的文档。]",
}

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

# per-tool 熔断器（独立计数）
TOOL_CIRCUITS = {
    "search_knowledge": CircuitBreaker("search_knowledge"),
    "search_employee": CircuitBreaker("search_employee"),
    "get_doc_detail": CircuitBreaker("get_doc_detail"),
}

# 可重试的异常类型
RETRYABLE_EXCEPTIONS = (asyncio.TimeoutError, ConnectionError, TimeoutError, OSError)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)
async def _execute_with_retry(tool_fn, tool_args):
    """带重试的工具执行（tenacity 指数退避：1s → 2s → 4s，最多 3 次）"""
    return await asyncio.wait_for(
        asyncio.to_thread(tool_fn.invoke, tool_args),
        timeout=TOOL_EXEC_TIMEOUT,
    )


async def agent_node(state: AgentState) -> dict[str, Any]:
    """Agent 决策节点：调用 LLM 判断下一步动作（调用工具 或 直接回答）"""
    messages = state["messages"]

    # 确保第一条消息是 system prompt
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + list(messages)

    # Token 预算检查 + 历史压缩
    token_count = count_tokens(messages)
    if token_count > TOKEN_BUDGET:
        logger.info(f"[AgentNode] token budget exceeded ({token_count} > {TOKEN_BUDGET}), summarizing history...")
        SystemMessage_cls = SystemMessage
        try:
            existing_summary = state.get("summary", "")
            messages = await asyncio.wait_for(
                summarize_history(messages, existing_summary=existing_summary if existing_summary else None),
                timeout=30,
            )
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"[AgentNode] History summarization failed ({e}), falling back to truncation")
            messages = list(messages)
        # summarize_history 返回 [系统摘要, ...最近消息]，前面插入 Agent system prompt
        messages = [SystemMessage_cls(content=AGENT_SYSTEM_PROMPT)] + list(messages)
        messages = ensure_token_budget(messages)

    # ── 安全前缀注入 ──
    # 构建临时 messages 副本，在最后一条 HumanMessage 前注入安全前缀。
    # 绝不 mutate state["messages"]——agent_node 在 ReAct 循环中可能被多次调用，
    # 直接修改原始消息会导致前缀累积。
    seclevel = current_security_level.get()
    security_prefix = SECURITY_PREFIX_MAP.get(seclevel, SECURITY_PREFIX_MAP["内部"])
    temp_messages = list(messages)  # 浅拷贝
    for i in range(len(temp_messages) - 1, -1, -1):
        if isinstance(temp_messages[i], HumanMessage):
            original = temp_messages[i]
            temp_messages[i] = HumanMessage(content=f"{security_prefix}\n\n用户问题：{original.content}")
            break

    logger.info(f"[AgentNode] invoking LLM with {len(temp_messages)} messages (~{count_tokens(temp_messages)} tokens)...")
    try:
        response = await asyncio.wait_for(
            chat_sync(
                messages=temp_messages,
                model="deepseek-v4-pro",
                temperature=0.3,
                max_tokens=1024,
                tools=TOOLS_OPENAI_FORMAT,
            ),
            timeout=AGENT_LLM_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(f"[AgentNode] LLM call timed out after {AGENT_LLM_TIMEOUT}s")
        return {"messages": [AIMessage(content="AI 推理超时，请简化问题后重试。")]}
    except Exception as e:
        error_msg = str(e) if str(e) else type(e).__name__
        logger.error(f"[AgentNode] LLM call failed: {error_msg}", exc_info=True)
        return {"messages": [AIMessage(content=f"AI 服务暂时不可用 ({error_msg[:100]})，请稍后重试。")]}

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
            breaker = TOOL_CIRCUITS.get(tool_name)
            try:
                if breaker:
                    result = await breaker.acall(_execute_with_retry, tool_fn, tool_args)
                else:
                    result = await _execute_with_retry(tool_fn, tool_args)
                tool_messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))
            except CircuitBreakerOpenError:
                logger.warning(f"[ToolsNode] {tool_name} blocked by circuit breaker")
                tool_messages.append(ToolMessage(
                    content=f"工具 {tool_name} 暂时不可用（服务已熔断），请简化问题或更换查询方式。",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))
            except asyncio.TimeoutError:
                logger.error(f"[ToolsNode] {tool_name} timed out after retries")
                tool_messages.append(ToolMessage(
                    content=f"工具 {tool_name} 多次执行超时，请稍后重试。",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))
            except Exception as e:
                error_msg = str(e) if str(e) else type(e).__name__
                logger.error(f"[ToolsNode] {tool_name} failed: {error_msg}", exc_info=True)
                tool_messages.append(ToolMessage(
                    content=f"工具 {tool_name} 调用失败: {error_msg[:200]}",
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
