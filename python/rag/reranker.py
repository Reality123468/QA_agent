"""
Listwise LLM 重排序器。

从混合检索的 Top-10 候选中，用 DeepSeek 一次性重排，选出最相关的 Top-5。
"""

import json
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

RERANK_PROMPT = """请评估以下文档片段与用户问题的相关性，选出最相关的至多 5 条并按相关性从高到低排序。

## 用户问题
{question}

## 候选片段
{candidates}

## 输出格式
只输出一行 JSON 数组，包含选中的候选编号。示例: [3, 1, 7, 5, 2]
不要输出任何其他文本。"""


async def rerank_listwise(
    question: str,
    candidates: List[dict],
    top_n: int = 5,
) -> List[dict]:
    """
    Listwise LLM 重排序：一次性评估所有候选，输出排序后的 Top-K。

    Args:
        question: 用户问题
        candidates: hybrid_search 返回的候选列表（dict 含 text, title, doc_id 等）
        top_n: 返回结果数

    Returns:
        重排序后的候选列表（最多 top_n 条）
    """
    if len(candidates) <= top_n:
        logger.info(f"Rerank skipped: {len(candidates)} candidates <= {top_n}")
        return candidates

    # 构建候选片段文本
    candidate_texts = []
    for i, c in enumerate(candidates):
        text = c.get("text", "")[:400]
        title = c.get("title", "未知")
        heading = c.get("heading", "")
        section = f" ({heading})" if heading else ""
        candidate_texts.append(f"[{i + 1}] 《{title}》{section}: {text}")

    candidates_block = "\n\n".join(candidate_texts)
    prompt = RERANK_PROMPT.format(question=question, candidates=candidates_block)

    try:
        from llm.deepseek_client import chat_sync

        response = await chat_sync(
            messages=[{"role": "user", "content": prompt}],
            model="deepseek-v4-flash",
            temperature=0.0,
            max_tokens=200,
        )
        raw = (response.content or "").strip()
        logger.info(f"Reranker raw output: {raw[:200]}")

        # 解析 JSON 数组
        ranking = _parse_ranking(raw, len(candidates))
        if not ranking:
            logger.warning("Reranker failed to parse ranking, returning original order")
            return candidates[:top_n]

        # 按 LLM 输出的顺序重排
        reranked = []
        seen = set()
        for idx in ranking:
            if idx not in seen and 0 <= idx < len(candidates):
                reranked.append(candidates[idx])
                seen.add(idx)

        result = reranked[:top_n]
        logger.info(f"Reranked: {len(candidates)} -> {len(result)} candidates")
        return result

    except Exception as e:
        logger.warning(f"Reranker call failed: {e}, returning original top-{top_n}")
        return candidates[:top_n]


def _parse_ranking(raw: str, max_candidates: int) -> List[int]:
    """解析 LLM 输出的排序编号列表"""
    # 尝试纯 JSON 解析
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [int(x) - 1 for x in parsed if isinstance(x, (int, float))]
    except json.JSONDecodeError:
        pass

    # 回退正则：匹配 [3,1,7,5,2] 或 3, 1, 7, 5, 2
    match = re.search(r'\[([^\]]+)\]', raw)
    if match:
        nums = re.findall(r'\d+', match.group(1))
        return [int(n) - 1 for n in nums]

    # 最后尝试：提取所有数字
    nums = re.findall(r'\d+', raw)
    if nums:
        return [int(n) - 1 for n in nums]

    return []
