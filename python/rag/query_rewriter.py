"""
查询改写：将多轮对话中的省略追问补全为独立完整的检索语句。

触发规则（规则预判，避免不必要的 LLM 调用）：
- 问题长度 < 10 字
- 含指代词（这个/那个/它/其/这/那/他/她/他们）
- 含省略标记（也/还/同样/一样/上面/前面）

命中规则时用 DeepSeek flash 改写；否则原句直接返回。
"""

import logging
import re

from llm.deepseek_client import chat_sync

logger = logging.getLogger(__name__)

# 指代词匹配
DEMONSTRATIVE_PATTERN = re.compile(
    r"这[个些样]?|那[个些样]?|它|其|他|她|他们|她们|它们"
)

# 省略/承上标记
ELLIPSIS_PATTERN = re.compile(r"也|还|同样|一样|上面|前面|之前|刚才|上面说的|前面提到的")

# 最小触发长度
MIN_QUESTION_LENGTH = 10

REWRITE_SYSTEM_PROMPT = (
    "你是一个查询改写助手。你的任务是将对话中的省略追问补全为独立完整的检索语句。\n"
    "规则：\n"
    "1. 分析对话历史，理解上文讨论的主题\n"
    "2. 将用户当前的简短追问展开为独立、完整的检索查询\n"
    "3. 只输出改写后的问题，不要添加任何解释或前缀\n"
    "4. 如果问题已经完整独立，原样返回"
)

REWRITE_USER_TEMPLATE = """对话历史：
{history_text}

用户当前追问：{question}

改写为独立完整的检索语句："""


def should_rewrite(question: str) -> bool:
    """规则预判：是否需要查询改写"""
    q = question.strip()
    # 条件 1: 短问题
    if len(q) < MIN_QUESTION_LENGTH:
        return True
    # 条件 2: 含指代词
    if DEMONSTRATIVE_PATTERN.search(q):
        return True
    # 条件 3: 含省略标记
    if ELLIPSIS_PATTERN.search(q):
        return True
    return False


async def rewrite_query(question: str, history: list) -> str:
    """
    调用 LLM 将省略追问改写为独立完整的检索语句。

    Args:
        question: 用户原始追问
        history: 对话历史（dict 列表: [{role, content}, ...] 或 LangChain 消息对象列表）

    Returns:
        改写后的独立完整问题（失败时返回原始 question）
    """
    if not history:
        return question

    # 构建历史文本（兼容 dict 和 LangChain 消息对象）
    history_parts = []
    for h in history[-6:]:  # 最多取最近 6 条（3 轮）
        if hasattr(h, "content"):
            content = h.content or ""
            role = h.type if hasattr(h, "type") else "unknown"
        elif isinstance(h, dict):
            content = h.get("content", "")
            role = h.get("role", "unknown")
        else:
            continue
        # 截断过长内容
        content = str(content)[:300]
        label = {"user": "用户", "assistant": "助手", "human": "用户", "ai": "助手"}.get(role, role)
        history_parts.append(f"{label}：{content}")

    if not history_parts:
        return question

    history_text = "\n".join(history_parts)
    user_prompt = REWRITE_USER_TEMPLATE.format(history_text=history_text, question=question)

    try:
        response = await chat_sync(
            messages=[
                {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model="deepseek-v4-flash",
            temperature=0.0,
            max_tokens=256,
        )
        rewritten = (response.content or "").strip()
        if rewritten and len(rewritten) > 2:
            logger.info(f"[QueryRewriter] '{question[:50]}' -> '{rewritten[:80]}'")
            return rewritten
        else:
            logger.warning(f"[QueryRewriter] empty/invalid rewrite result, using original")
            return question
    except Exception as e:
        logger.warning(f"[QueryRewriter] LLM rewrite failed: {e}, using original question")
        return question
