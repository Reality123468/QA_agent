import json
import os
import logging
from typing import Optional

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

_client = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_API_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
    return _client


def _to_api_messages(messages: list) -> list:
    """将 LangChain 消息转为 DeepSeek/OpenAI API 兼容的字典格式"""
    api_messages = []
    for msg in messages:
        if hasattr(msg, "type"):
            msg_type = msg.type
            if msg_type == "human":
                api_messages.append({"role": "user", "content": msg.content})
            elif msg_type == "ai":
                entry = {"role": "assistant", "content": msg.content or ""}
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    entry["tool_calls"] = [
                        {
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("args", {}), ensure_ascii=False),
                            },
                        }
                        for tc in tool_calls
                    ]
                api_messages.append(entry)
            elif msg_type == "system":
                api_messages.append({"role": "system", "content": msg.content})
            elif msg_type == "tool":
                api_messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": getattr(msg, "tool_call_id", ""),
                })
            else:
                api_messages.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, dict) and "role" in msg:
            api_messages.append(msg)
        else:
            logger.warning(f"Unknown message type: {type(msg)}")
    return api_messages


async def chat_stream(messages: list, model: str = "deepseek-v4-pro", temperature: float = 0.3,
                      max_tokens: int = 2048):
    """流式调用 DeepSeek API，逐 token yield"""
    client = get_client()
    api_messages = _to_api_messages(messages)
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"[chat_stream] API call failed: {e}", exc_info=True)
        raise RuntimeError(f"DeepSeek API 调用失败: {e}") from e


async def chat_sync(messages: list, model: str = "deepseek-v4-pro", temperature: float = 0.3,
                    max_tokens: int = 2048, tools: Optional[list] = None):
    """
    非流式调用 DeepSeek API，返回完整响应消息。

    用于 Agent 决策节点（需要 tool_calls 判断下一步动作）。

    Returns:
        ChatCompletionMessage: 包含 content（文本）和 tool_calls（工具调用列表）
    """
    client = get_client()
    api_messages = _to_api_messages(messages)
    logger.info(f"[chat_sync] Converted {len(messages)} messages -> {len(api_messages)} API messages")
    for i, m in enumerate(api_messages):
        logger.info(f"[chat_sync]   msg[{i}]: role={m.get('role')}, content_len={len(str(m.get('content', '')))}")
    kwargs = dict(
        model=model,
        messages=api_messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message
    except Exception as e:
        logger.error(f"[chat_sync] API call failed: {e}", exc_info=True)
        raise RuntimeError(f"DeepSeek API 调用失败: {e}") from e


# ── Token 管理 ────────────────────────────────────────────

TOKEN_BUDGET = 8000   # 输入 token 预算（留足余量给模型输出）
TOKEN_ENCODING = None  # tiktoken 编码器缓存


def _get_encoding():
    """获取 tiktoken 编码器（cl100k_base 兼容 DeepSeek）"""
    global TOKEN_ENCODING
    if TOKEN_ENCODING is None:
        import sys
        import os as _os
        if _os.path.isdir("D:/python-packages") and "D:/python-packages" not in sys.path:
            sys.path.insert(0, "D:/python-packages")
        import tiktoken
        TOKEN_ENCODING = tiktoken.get_encoding("cl100k_base")
    return TOKEN_ENCODING


def count_tokens(messages: list) -> int:
    """估算消息列表的 token 数（含 role 标记开销）"""
    enc = _get_encoding()
    total = 0
    for msg in messages:
        content = ""
        if hasattr(msg, "content"):
            content = msg.content or ""
        elif isinstance(msg, dict) and "content" in msg:
            content = msg["content"] or ""
        total += len(enc.encode(content))

        # tool_calls 额外开销
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            total += len(enc.encode(json.dumps(msg.tool_calls, ensure_ascii=False, default=str)))
        elif isinstance(msg, dict) and msg.get("tool_calls"):
            total += len(enc.encode(json.dumps(msg["tool_calls"], ensure_ascii=False, default=str)))

    # 每条消息 ~4 tokens role 标记
    total += len(messages) * 4
    return total


async def summarize_history(messages: list) -> list:
    """
    压缩对话历史：保留最近 3 条消息不变，之前的历史送给 LLM 做摘要。

    Returns:
        [SystemMessage(摘要), ..., 最近3条原文]
    """
    if len(messages) <= 5:
        return messages

    from langchain_core.messages import SystemMessage

    # 分离：前半段做摘要，后半段保留原文
    keep_count = 3
    old_part = messages[:-keep_count]
    recent_part = messages[-keep_count:]

    # 构建摘要 prompt
    old_text_parts = []
    for m in old_part:
        content = m.content if hasattr(m, "content") else str(m)
        role = m.type if hasattr(m, "type") else m.get("role", "user")
        old_text_parts.append(f"[{role}]: {str(content)[:500]}")
    old_text = "\n".join(old_text_parts)

    summary_prompt = (
        "请将以下对话历史压缩为一段关键事实摘要（不超过300字），"
        "只保留用户问题要点和已确认的答案要点，丢弃推理过程细节：\n\n" + old_text
    )

    try:
        response = await chat_sync(
            messages=[{"role": "user", "content": summary_prompt}],
            model="deepseek-v4-flash",
            temperature=0.0,
            max_tokens=400,
        )
        summary = response.content or ""
        logger.info(f"History summarized: {len(old_part)} msgs -> {len(summary)} chars")
        return [SystemMessage(content=f"[历史摘要] {summary}")] + list(recent_part)
    except Exception as e:
        logger.warning(f"History summarization failed: {e}, falling back to truncation")
        return list(recent_part)


def ensure_token_budget(messages: list, budget: int = TOKEN_BUDGET) -> list:
    """
    确保消息不超出 token 预算。

    策略：
    1. 总数 <= 预算 → 直接返回
    2. 总数 > 预算 → 从头部硬截断旧消息
    3. 截断后只剩 1 条仍超出 → 截断该消息的 content 字段
    """
    total = count_tokens(messages)
    if total <= budget:
        return messages

    logger.info(f"Token budget exceeded: {total} > {budget}, compressing...")

    compressed = list(messages)
    while count_tokens(compressed) > budget and len(compressed) > 1:
        compressed = compressed[1:]

    # 最后手段：截断最后一条消息的 content
    if count_tokens(compressed) > budget and len(compressed) == 1:
        msg = compressed[0]
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            msg.content = msg.content[:budget * 3]  # ~3 chars per token

    logger.info(f"Token budget met: {count_tokens(compressed)} tokens after compression")
    return compressed
