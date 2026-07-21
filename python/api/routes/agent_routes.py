import json
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from api.dependencies import verify_api_key
from api.schemas.chat import ChatRequest
from api.schemas.index import IndexRequest
from rag.indexer import index_document
from rag.retriever import hybrid_search

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/index")
async def index_document_route(request: IndexRequest, api_key: str = Depends(verify_api_key)):
    """将文档索引到 Qdrant 向量数据库"""
    try:
        index_document(request.document.model_dump())
        return {"status": "completed", "doc_id": request.document.id}
    except Exception as e:
        logger.error(f"Index failed: {e}", exc_info=True)
        return {"status": "failed", "doc_id": request.document.id, "error": str(e)}


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """SSE 流式对话（检索部分已接入，LLM 生成暂时占位）"""

    logger.info(f"Chat request: {request.question[:50]}...")

    # 先做检索
    hits = hybrid_search(
        query=request.question,
        department=getattr(request, "department", "全部"),
        security_level=getattr(request, "security_level", "内部"),
    )

    context_texts = [h["text"] for h in hits[:5]]

    async def event_stream():
        yield f"data: {json.dumps({'type': 'thinking', 'content': f'检索到 {len(hits)} 个相关片段'})}\n\n"
        if context_texts:
            yield f"data: {json.dumps({'type': 'answer', 'content': '检索完成，LLM 模块接入后将基于以下上下文生成答案：'})}\n\n"
            for h in hits[:5]:
                yield f"data: {json.dumps({'type': 'citation', 'content': h['title'], 'data': h})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'answer', 'content': '知识库中暂无相关信息'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
