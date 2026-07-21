import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from api.dependencies import verify_api_key
from api.schemas.chat import ChatRequest
from api.schemas.index import IndexRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/index")
async def index_document(request: IndexRequest, api_key: str = Depends(verify_api_key)):
    """异步索引文档（暂为骨架，RAG 模块实现后补齐）"""
    logger.info(f"Index request received for doc {request.document.id}: {request.document.title}")
    # 骨架：返回成功，后续 rag 模块替换此处
    return {"status": "indexing", "doc_id": request.document.id}


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """SSE 流式对话（暂为骨架，LLM 模块实现后补齐）"""
    logger.info(f"Chat request: {request.question[:50]}...")
    # 骨架：返回占位响应，后续 llm 模块替换此处
    async def event_stream():
        import json
        yield f"data: {json.dumps({'type': 'answer', 'content': '系统正在建设中，请稍后重试'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
