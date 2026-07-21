import json
import logging
from typing import List, AsyncGenerator
from rag.retriever import hybrid_search
from llm.deepseek_client import chat_stream

logger = logging.getLogger(__name__)

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
    # Step 1: 思考提示
    yield f"data: {json.dumps({'type': 'thinking', 'content': '正在检索相关文档...'}, ensure_ascii=False)}\n\n"

    # Step 2: 检索
    hits = hybrid_search(question, department=department, security_level=security_level)

    if not hits:
        yield f"data: {json.dumps({'type': 'answer', 'content': '知识库中暂无相关信息，我无法准确回答该问题。'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
        return

    yield f"data: {json.dumps({'type': 'thinking', 'content': f'检索到 {len(hits)} 个相关片段，正在生成回答...'}, ensure_ascii=False)}\n\n"

    # Step 3: 构建上下文和 Prompt
    context = "\n\n---\n\n".join([
        f"[来源: {h['title']}] (章节: {h.get('heading', '未知')})\n{h['text']}"
        for h in hits[:5]
    ])

    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)

    messages = [{"role": "system", "content": prompt}]
    if history:
        messages = [{"role": "system", "content": prompt}] + history
    messages.append({"role": "user", "content": question})

    # Step 4: 流式生成
    full_answer = ""
    try:
        for token in chat_stream(messages):
            full_answer += token
            yield f"data: {json.dumps({'type': 'answer', 'content': token}, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': 'AI服务暂时不可用，请稍后重试'})}\n\n"
        return

    # Step 5: 溯源引用
    citations = [
        {"title": h["title"], "heading": h.get("heading", ""), "page": h.get("source_page", 0),
         "chunk": h["text"][:200] + "..."}
        for h in hits[:5]
    ]
    yield f"data: {json.dumps({'type': 'citation', 'content': '', 'data': citations}, ensure_ascii=False)}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
