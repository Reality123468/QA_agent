import json
import os
import logging
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

_client = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_URL)
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


async def chat_stream(messages: list, model: str = "deepseek-chat", temperature: float = 0.3,
                      max_tokens: int = 2048):
    """流式调用 DeepSeek API，逐 token yield"""
    client = get_client()
    api_messages = _to_api_messages(messages)
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


async def chat_sync(messages: list, model: str = "deepseek-chat", temperature: float = 0.3,
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

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message
