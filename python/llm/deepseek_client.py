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


async def chat_stream(messages: list, model: str = "deepseek-chat", temperature: float = 0.3,
                      max_tokens: int = 2048):
    """流式调用 DeepSeek API，逐 token yield"""
    client = get_client()
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
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
    kwargs = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message
