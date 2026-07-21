import json
import asyncio
from typing import AsyncGenerator


async def format_sse(event_type: str, content: str, data: dict = None) -> str:
    """将响应格式化为 SSE data 行"""
    payload = {"type": event_type, "content": content}
    if data:
        payload["data"] = data
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def stream_answer(answer_generator) -> AsyncGenerator[str, None]:
    """包装 LLM 流式输出为 SSE 格式"""
    full_answer = ""
    async for token in answer_generator:
        full_answer += token
        yield f"data: {json.dumps({'type': 'answer', 'content': token}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
