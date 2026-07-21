from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from api.dependencies import verify_api_key
from api.schemas.chat import ChatRequest
from api.schemas.index import IndexRequest
from rag.indexer import index_document, delete_document_chunks
from llm.rag_chain import answer_with_rag
router = APIRouter()


@router.post("/index")
async def index_document_route(request: IndexRequest, api_key: str = Depends(verify_api_key)):
    """将文档索引到 Qdrant 向量数据库"""
    try:
        index_document(request.document.model_dump())
        return {"status": "completed", "doc_id": request.document.id}
    except Exception as e:
        return {"status": "failed", "doc_id": request.document.id, "error": str(e)}


@router.delete("/index/{doc_id}")
async def delete_document_route(doc_id: int, api_key: str = Depends(verify_api_key)):
    """删除文档在 Qdrant 中的所有向量 chunks"""
    try:
        delete_document_chunks(doc_id)
        return {"status": "deleted", "doc_id": doc_id}
    except Exception as e:
        return {"status": "failed", "doc_id": doc_id, "error": str(e)}


@router.post("/chat/stream")
async def chat_stream_route(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
    x_user_role: str = Header(default="ROLE_EMPLOYEE", alias="X-User-Role"),
    x_user_department: str = Header(default="全部", alias="X-User-Department"),
):
    """SSE 流式对话：RAG 检索 + LLM 生成 + 溯源引用"""
    # 根据角色确定可见密级
    security_level = "内部"
    if x_user_role in ("ROLE_LEADER", "ROLE_ADMIN"):
        security_level = "机密"

    history = [
        {"role": h.role, "content": h.content}
        for h in request.history
    ]

    return StreamingResponse(
        answer_with_rag(
            question=request.question,
            history=history,
            department=x_user_department,
            security_level=security_level,
        ),
        media_type="text/event-stream",
    )
