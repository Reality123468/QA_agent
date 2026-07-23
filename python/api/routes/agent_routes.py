import json
import asyncio
import logging

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from api.dependencies import verify_api_key
from api.schemas.chat import ChatRequest
from api.schemas.index import IndexRequest
from rag.indexer import index_document, delete_document_chunks
from rag.retriever import hybrid_search
from llm.rag_chain import answer_with_rag
from agent.graph import get_agent_graph
from agent.state import AgentState

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


@router.delete("/index/{doc_id}")
async def delete_document_route(doc_id: int, api_key: str = Depends(verify_api_key)):
    """删除文档在 Qdrant 中的所有向量 chunks"""
    try:
        delete_document_chunks(doc_id)
        return {"status": "deleted", "doc_id": doc_id}
    except Exception as e:
        logger.error(f"Delete failed: {e}", exc_info=True)
        return {"status": "failed", "doc_id": doc_id, "error": str(e)}


@router.post("/chat/stream")
async def chat_stream_route(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
    x_user_role: str = Header(default="ROLE_EMPLOYEE", alias="X-User-Role"),
    x_user_department: str = Header(default="全部", alias="X-User-Department"),
):
    """SSE 流式对话 — 支持三种模式：agent / rag / search-only"""
    security_level = "内部"
    if x_user_role in ("ROLE_LEADER", "ROLE_ADMIN"):
        security_level = "机密"

    history = [
        {"role": h.role, "content": h.content}
        for h in request.history
    ]

    mode = request.mode
    logger.info(f"Chat request mode={mode}, question='{request.question[:50]}...'")

    if mode == "search-only":
        return StreamingResponse(
            _search_only_stream(request.question, x_user_department, security_level),
            media_type="text/event-stream",
        )
    elif mode == "agent":
        return StreamingResponse(
            _agent_stream(request.question, history, x_user_department, security_level),
            media_type="text/event-stream",
        )
    else:
        return StreamingResponse(
            answer_with_rag(
                question=request.question,
                history=history,
                department=x_user_department,
                security_level=security_level,
            ),
            media_type="text/event-stream",
        )


async def _search_only_stream(question: str, department: str, security_level: str):
    """search-only 模式：仅返回检索结果，不做 LLM 生成"""
    yield f"data: {json.dumps({'type': 'thinking', 'content': '正在检索相关文档...'}, ensure_ascii=False)}\n\n"

    hits = await asyncio.to_thread(hybrid_search, question, department=department, security_level=security_level)

    if not hits:
        yield f"data: {json.dumps({'type': 'answer', 'content': '未找到相关文档。'}, ensure_ascii=False)}\n\n"
    else:
        for h in hits[:5]:
            yield f"data: {json.dumps({'type': 'citation', 'content': h['title'], 'data': h}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"


async def _agent_stream(question: str, history: list, department: str, security_level: str):
    """Agent 模式：ReAct 推理循环 + 流式输出"""
    try:
        graph = get_agent_graph()

        # 构建初始状态
        initial_state: AgentState = {
            "messages": [HumanMessage(content=question)],
            "department": department,
            "security_level": security_level,
            "retrieved_docs": [],
        }

        # 使用 config 传递 thread_id 实现多轮对话记忆
        config = {"configurable": {"thread_id": f"agent-{hash(question)}"}}

        # 流式执行 Agent 图
        final_answer = ""
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            kind = event.get("event")

            if kind == "on_chat_model_start":
                # Agent 开始思考
                yield f"data: {json.dumps({'type': 'thought', 'content': '正在分析问题...'}, ensure_ascii=False)}\n\n"

            elif kind == "on_chat_model_stream":
                # Agent 推理过程（tool_calls 的 arguments 或 content）
                chunk = event.get("data", {}).get("chunk", {})
                if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                    for tc in chunk.tool_call_chunks:
                        if tc.name:
                            yield f"data: {json.dumps({'type': 'action', 'content': f'调用工具: {tc.name}', 'data': {'tool': tc.name}}, ensure_ascii=False)}\n\n"

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                yield f"data: {json.dumps({'type': 'action', 'content': f'执行: {tool_name}', 'data': {'tool': tool_name, 'args': tool_input}}, ensure_ascii=False)}\n\n"

            elif kind == "on_tool_end":
                output = event.get("data", {}).get("output", "")
                preview = str(output)[:200] + ("..." if len(str(output)) > 200 else "")
                yield f"data: {json.dumps({'type': 'observation', 'content': preview}, ensure_ascii=False)}\n\n"

            elif kind == "on_chat_model_end":
                msg = event.get("data", {}).get("output", {})
                if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
                    final_answer = msg.content

        # 流式输出最终答案
        if final_answer:
            for char in final_answer:
                yield f"data: {json.dumps({'type': 'answer', 'content': char}, ensure_ascii=False)}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'answer', 'content': '抱歉，我无法回答该问题。'}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    except Exception as e:
        logger.error(f"Agent stream error: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'content': f'Agent 推理失败: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
