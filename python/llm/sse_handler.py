import json


async def format_sse(event_type: str, content: str, data: dict = None) -> str:
    """将响应格式化为 SSE data 行"""
    payload = {"type": event_type, "content": content}
    if data:
        payload["data"] = data
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
