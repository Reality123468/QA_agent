import json
import asyncio
import time
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

AGENT_STREAM_TIMEOUT = 120  # Agent 整体推理超时（秒）


@router.post("/index")
async def index_document_route(request: IndexRequest, api_key: str = Depends(verify_api_key)):
    """将文档索引到 Qdrant 向量数据库"""
    try:
        progress_url = request.progress_url
        index_document(request.document.model_dump(), progress_url=progress_url)
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
    """Agent 模式：ReAct 推理循环 + 流式输出（含 3 级自动降级）

    降级链路：
    1. Agent 异常/超时 → RAG 模式
    2. RAG 检索失败 → search-only 模式
    3. 全部失败 → 兜底回复
    """
    agent_failed = False

    # ── Tier 1: Agent ReAct 推理 ──
    try:
        graph = get_agent_graph()

        initial_state: AgentState = {
            "messages": [HumanMessage(content=question)],
            "department": department,
            "security_level": security_level,
            "retrieved_docs": [],
        }

        config = {
            "configurable": {"thread_id": f"agent-{hash(question)}"},
            "recursion_limit": 10,
        }

        yield f"data: {json.dumps({'type': 'thought', 'content': '正在分析问题...'}, ensure_ascii=False)}\n\n"

        start_time = time.time()
        final_answer = ""
        msg_count = 0
        async for chunk in graph.astream(initial_state, config=config, stream_mode="values"):
            elapsed = time.time() - start_time
            if elapsed > AGENT_STREAM_TIMEOUT:
                logger.warning(f"[_agent_stream] Timed out after {elapsed:.0f}s")
                agent_failed = True
                break
            msgs = chunk.get("messages", [])
            if len(msgs) <= msg_count:
                continue
            new_msgs = msgs[msg_count:]
            msg_count = len(msgs)
            for msg in new_msgs:
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        tc_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                        tc_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                        yield f"data: {json.dumps({'type': 'action', 'content': f'执行: {tc_name}', 'data': {'tool': tc_name, 'args': tc_args}}, ensure_ascii=False)}\n\n"
                    continue

                is_tool_msg = hasattr(msg, "tool_call_id") and getattr(msg, "tool_call_id", None)
                if is_tool_msg:
                    preview = str(msg.content)[:200] + ("..." if len(str(msg.content)) > 200 else "")
                    yield f"data: {json.dumps({'type': 'observation', 'content': preview}, ensure_ascii=False)}\n\n"
                    continue

                content = getattr(msg, "content", None)
                if content:
                    final_answer = content

        if not agent_failed and final_answer:
            for char in final_answer:
                yield f"data: {json.dumps({'type': 'answer', 'content': char}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
            return

        agent_failed = True

    except Exception as e:
        logger.error(f"Agent stream error: {e}", exc_info=True)
        agent_failed = True

    # ── Tier 2: 降级到 RAG 模式 ──
    if agent_failed:
        yield f"data: {json.dumps({'type': 'downgrade', 'content': 'Agent 不可用，切换到知识库检索模式', 'data': {'from': 'agent', 'to': 'rag'}}, ensure_ascii=False)}\n\n"
        try:
            has_any_output = False
            async for sse in answer_with_rag(
                question=question, history=history,
                department=department, security_level=security_level,
            ):
                has_any_output = True
                yield sse
            if has_any_output:
                return
        except Exception as e:
            logger.error(f"RAG downgrade also failed: {e}", exc_info=True)

    # ── Tier 3: 降级到 search-only 模式 ──
    yield f"data: {json.dumps({'type': 'downgrade', 'content': 'AI 服务不可用，返回关键词检索结果', 'data': {'from': 'rag', 'to': 'search-only'}}, ensure_ascii=False)}\n\n"
    try:
        has_results = False
        async for sse in _search_only_stream(question, department, security_level):
            has_results = True
            yield sse
        if has_results:
            return
    except Exception as e:
        logger.error(f"search-only downgrade also failed: {e}", exc_info=True)

    # ── Tier 4: 兜底回复 ──
    yield f"data: {json.dumps({'type': 'answer', 'content': '系统暂时无法处理您的问题，请稍后重试或联系管理员。'}, ensure_ascii=False)}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
