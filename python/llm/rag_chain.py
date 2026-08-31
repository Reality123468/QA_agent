import json
import asyncio
import os
import time
import logging
from typing import List, AsyncGenerator
from rag.retriever import hybrid_search
from rag.reranker import rerank_listwise
from rag.query_rewriter import should_rewrite, rewrite_query
from llm.deepseek_client import chat_stream, count_tokens, ensure_token_budget, summarize_history

logger = logging.getLogger(__name__)

RAG_TOKEN_BUDGET = int(os.getenv("RAG_TOKEN_BUDGET", "6000"))  # RAG 输入 token 预算

RAG_PROMPT_TEMPLATE = """你是一名企业智能助手。请根据以下参考文档中的信息回答用户问题。

## 要求
- 仅根据参考文档内容回答，不要编造信息
- 如果参考文档中没有相关信息，明确告知用户"该问题我目前无法准确回答"
- 回答中引用具体的文档名称和章节
- 回答准确、简洁、专业

## 参考文档
{context}

## 用户问题
{question}

## 回答
"""


async def answer_with_rag(question: str, history: List[dict] = None,
                          department: str = "全部", security_level: str = "内部") -> AsyncGenerator[str, None]:
    """
    完整 RAG 问答流水线：检索 → 构建 Prompt → LLM 生成 → SSE 流式输出

    Yields: SSE 格式的字符串
    """
    start_time = time.time()

    # Step 1: 思考提示
    yield f"data: {json.dumps({'type': 'thinking', 'content': '正在检索相关文档...'}, ensure_ascii=False)}\n\n"

    # Step 1.5: 查询改写（省略追问 → 独立完整检索语句）
    search_question = question
    if should_rewrite(question):
        search_question = await rewrite_query(question, history or [])

    # Step 2: 检索（Top-10 粗召回）
    hits = await asyncio.to_thread(
        hybrid_search, search_question, department=department, security_level=security_level, top_k=10
    )

    if not hits:
        yield f"data: {json.dumps({'type': 'answer', 'content': '知识库中暂无相关信息，我无法准确回答该问题。'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
        return

    # Step 2.5: Reranker 精排（10 → 5）
    yield f"data: {json.dumps({'type': 'thinking', 'content': f'检索到 {len(hits)} 个候选片段，正在精选最相关内容...'}, ensure_ascii=False)}\n\n"
    hits = await rerank_listwise(question, hits, top_n=5)

    yield f"data: {json.dumps({'type': 'thinking', 'content': f'已精选 {len(hits)} 个相关片段，正在生成回答...'}, ensure_ascii=False)}\n\n"

    # Step 3: 构建上下文和 Prompt
    context = "\n\n---\n\n".join([
        f"[来源: {h['title']}] (章节: {h.get('heading', '未知')})\n{h['text']}"
        for h in hits[:5]
    ])

    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)

    # 历史摘要压缩：超 10 轮或 token 逼近预算时触发
    history_for_llm = history or []
    if history and len(history) > 10:
        from langchain_core.messages import HumanMessage as LCHumanMsg, AIMessage as LCAIMsg
        role_map = {"user": LCHumanMsg, "assistant": LCAIMsg}
        lc_history = [role_map[h["role"]](content=h["content"]) for h in history if h.get("role") in role_map]
        compressed = await summarize_history(lc_history)
        # 转回 dict 格式
        history_for_llm = []
        for m in compressed:
            if hasattr(m, "type"):
                role = {"human": "user", "ai": "assistant", "system": "system"}.get(m.type, "system")
                history_for_llm.append({"role": role, "content": m.content or ""})

    messages = [{"role": "system", "content": prompt}]
    if history_for_llm:
        messages = [{"role": "system", "content": prompt}] + history_for_llm
    messages.append({"role": "user", "content": question})

    # Token 预算检查：超限时先裁剪 context 再按 token 截断历史
    if count_tokens(messages) > RAG_TOKEN_BUDGET:
        logger.info(f"[RAG] token budget exceeded, trimming...")
        # 先尝试减少 context 片段
        trimmed_context = "\n\n---\n\n".join([
            f"[来源: {h['title']}] {h['text'][:500]}"
            for h in hits[:3]
        ])
        prompt = RAG_PROMPT_TEMPLATE.format(context=trimmed_context, question=question)
        messages = [{"role": "system", "content": prompt}]
        if history:
            messages = [{"role": "system", "content": prompt}] + history
        messages.append({"role": "user", "content": question})
        # 再用 token 预算裁剪（替代之前的 history[-4:] 硬截断）
        messages = ensure_token_budget(messages, budget=RAG_TOKEN_BUDGET)

    # Step 4: 流式生成
    full_answer = ""
    try:
        async for token in chat_stream(messages):
            full_answer += token
            yield f"data: {json.dumps({'type': 'answer', 'content': token}, ensure_ascii=False)}\n\n"
    except Exception as e:
        error_detail = str(e) if str(e) else type(e).__name__
        logger.error(f"LLM generation failed: {error_detail}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'content': f'AI服务暂时不可用: {error_detail[:200]}'}, ensure_ascii=False)}\n\n"
        return

    logger.info(f"RAG answer complete ({len(full_answer)} chars): {full_answer[:200]}...")

    # Step 5: Token 用量估算（tiktoken，DeepSeek 流式不返回 usage）
    prompt_tokens = count_tokens(messages)
    completion_tokens = count_tokens([{"role": "assistant", "content": full_answer}])
    yield f"data: {json.dumps({'type': 'token_usage', 'content': '', 'data': {'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'total_tokens': prompt_tokens + completion_tokens}}, ensure_ascii=False)}\n\n"

    # Step 6: 溯源引用
    citations = [
        {"title": h["title"], "heading": h.get("heading", ""), "page": h.get("source_page", 0),
         "chunk": h["text"][:200] + "..."}
        for h in hits[:5]
    ]
    yield f"data: {json.dumps({'type': 'citation', 'content': '', 'data': citations}, ensure_ascii=False)}\n\n"

    # 慢查询告警
    elapsed_ms = int((time.time() - start_time) * 1000)
    SLOW_QUERY_THRESHOLD_MS = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "5000"))
    if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
        logger.warning(f"SLOW_QUERY | question={question[:100]} | time={elapsed_ms}ms | mode=rag")

    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
