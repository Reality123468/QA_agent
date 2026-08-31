# Q&A 系统缺陷修复设计

## 概述

修复企业智能问答系统的 9 个缺陷，涵盖权限加固、状态简化、Token 裁剪、工具链完善、查询改写、摘要压缩、降级防幻觉、工具容错和可观测性。

## 范围

| # | 问题 | 动作 |
|---|------|------|
| #2 | LLM 层 + 工具层越权泄露风险 | 修复 |
| #4 | MemorySaver 冗余，改用无状态 initial_state | 修复 |
| #6 | 对话窗口按 token 而非条数裁剪 | 修复 |
| #7 | search_employee / get_doc_detail 工具完善 | 修复 |
| #8 | 多轮省略追问无查询改写 | 新增 |
| #9 | 摘要压缩（滚动累积 + 持久化） | 修复 |
| #10 | RAG 空结果仍调 LLM 可能幻觉 | 修复 |
| #11 | 工具无重试/熔断 | 新增 |
| #1 | Token 用量记录 + 慢查询告警 | 新增 |

跳过：#3（限流）、#5（嵌入模型升级）。

---

## #2 越权二次校验

### 问题

`security_level` 过滤仅作用于检索层（Qdrant + BM25），存在三个缺口：

1. **tools 硬编码 `security_level="内部"`**：`search_knowledge` 和 `search_employee` 忽略每次请求的用户安全级别
2. **`get_doc_detail` 零过滤**：`get_document_chunks()` 查询 Qdrant 时无 `security_level` 条件，可越权读取机密文档
3. **Agent LLM prompt 无安全约束**：模型不知道自己在为受限用户服务

### 方案

#### 2a. get_doc_detail 检索层加过滤

修改 `python/rag/retriever.py` 的 `get_document_chunks()`：

```python
def get_document_chunks(doc_id: str, security_level: str = "内部") -> List[Dict]:
    must_conditions = [FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
    if security_level:
        must_conditions.append(
            FieldCondition(key="security_level", match=MatchAny(any=[security_level, "内部"]))
        )
    # ... 其余 scroll 逻辑不变
```

#### 2b. Tools 通过 contextvars 动态获取安全级别

新建 `python/agent/context.py`：

```python
import contextvars

current_security_level: contextvars.ContextVar[str] = contextvars.ContextVar(
    "security_level", default="内部"
)
```

在 `tools.py` 中，每个工具从 contextvar 读取安全级别：

```python
from agent.context import current_security_level

def search_knowledge(query, category, department):
    seclevel = current_security_level.get()
    return hybrid_search(query, security_level=seclevel, ...)

def search_employee(query):
    seclevel = current_security_level.get()
    return hybrid_search(query, security_level=seclevel, ...)

def get_doc_detail(doc_id):
    seclevel = current_security_level.get()
    return get_document_chunks(doc_id, security_level=seclevel)
```

在 `agent_routes.py` 请求入口设置 contextvar：

```python
# 在调用 graph.astream() 之前
current_security_level.set(security_level)
```

#### 2c. Agent 用户消息加安全前缀

仅 Agent 模式生效（RAG 模式检索层已过滤，不改动）。在 `nodes.py` 的 `agent_node()` 中，向最新 `HumanMessage.content` 前拼接安全前缀：

```python
SECURITY_PREFIX_MAP = {
    "内部": "[安全级别：内部。禁止在回答中泄露任何标记为「机密」的文档内容。]",
    "机密": "[安全级别：机密。你可以引用所有级别的文档。]",
}
```

**关键约束**：`agent_node` 在一次 ReAct 循环中会被多次调用（agent→tool→agent→…）。**绝对不能 mutate `state["messages"]` 中的原始消息对象**，否则前缀会累积（第一次"内部"、第二次"内部内部"…）。正确做法是构建临时 messages 副本注入前缀后传给 LLM：

```python
# agent_node 内部，构造 LLM 调用的 messages 时
temp_messages = list(state["messages"])  # 浅拷贝
# 找到最后一条 HumanMessage，复制并注入前缀
for i in range(len(temp_messages) - 1, -1, -1):
    if isinstance(temp_messages[i], HumanMessage):
        original = temp_messages[i]
        prefixed_content = f"{security_prefix}\n\n用户问题：{original.content}"
        temp_messages[i] = HumanMessage(content=prefixed_content)
        break  # 只处理最近一条用户消息
# temp_messages 传给 LLM，但 state 中的原始消息不受影响
```

前缀仅在调用 LLM 时临时注入于副本，不写入 state/checkpoint，不持久化。

### 涉及文件

- `python/rag/retriever.py` — `get_document_chunks()` 加 `security_level` 参数
- `python/agent/context.py` — **新增** — security_level 的 contextvar
- `python/agent/tools.py` — 从 contextvar 读取 security_level
- `python/agent/nodes.py` — 用户消息注入安全前缀
- `python/api/routes/agent_routes.py` — 请求入口设置 contextvar

---

## #4 去掉 MemorySaver（无状态 Agent）

### 问题

`MemorySaver` 按 `thread_id` 在内存中保持会话状态。前端已经每次请求发送全量 history，MemorySaver 冗余且引起：
- 内存泄漏（checkpoint 不过期）
- 服务重启状态丢失
- checkpoint 管理不必要的复杂度

### 方案

1. 从 `python/agent/graph.py` 移除 `MemorySaver` 导入和实例化
2. compile 不传 checkpointer：`compiled = workflow.compile()`
3. `agent_routes.py` 通过 `initial_state` 传入全量 history：

```python
initial_state = {
    "messages": history_messages,  # 从 API history 转换的 LangChain 消息列表
    "department": department,
    "security_level": security_level,
    "retrieved_docs": [],
}
async for chunk in graph.astream(initial_state):
    ...
```

4. 保留 `thread_id`（后续可能用于日志/追踪），仅不再用于状态持久化
5. 确认 `agent_routes.py` 中已有的 history → LangChain 消息转换逻辑正确

### 涉及文件

- `python/agent/graph.py` — 移除 MemorySaver，compile 不传 checkpointer
- `python/api/routes/agent_routes.py` — 改用 initial_state 传入全量 history

---

## #6 Token 预算裁剪

### 问题

`rag_chain.py` 使用 `history[-4:]` 硬截断，长消息可能撑爆上下文。Agent 模式有 `ensure_token_budget()` 但 RAG 模式没复用。

### 方案

1. 统一使用 `deepseek_client.py` 的 `ensure_token_budget()` 做裁剪
2. Token 预算通过环境变量配置：

```
RAG_TOKEN_BUDGET=6000      # 默认 6000
AGENT_TOKEN_BUDGET=8000    # 默认 8000
```

3. `rag_chain.py`：用 `ensure_token_budget(messages, budget=rag_budget)` 替换 `history[-4:]`
4. `nodes.py`：用 `os.getenv("AGENT_TOKEN_BUDGET", 8000)` 替换硬编码的 `TOKEN_BUDGET`
5. Java 侧不改动（继续发全量 history，Python 侧自行裁剪）

### 涉及文件

- `python/llm/deepseek_client.py` — 预算改为从环境变量读取
- `python/llm/rag_chain.py` — 用 `ensure_token_budget()` 替换 `[-4:]`
- `python/agent/nodes.py` — 预算从环境变量读取

---

## #7 工具链完善

### 问题

- `search_employee`：逻辑与 `search_knowledge` 完全相同（搜索同一个 Qdrant），无独立员工数据源。代码没问题，缺的是数据
- `get_doc_detail`：能工作但 3000 字符硬截断，无 chunk 级别导航

### 方案

#### 7a. search_employee（不改代码）

工具逻辑正确，解决方案在运营层面——上传公司通讯录/组织架构文档到系统中。可选的优化：在 tool description 中加一句提示"请在文档管理页面上传公司通讯录/组织架构文档以启用此功能"。

#### 7b. get_doc_detail（分段返回）

改为两步模式：

**第一步：列出 chunk 索引** — 仅传 `doc_id` 时返回章节列表：

```python
def get_doc_detail(doc_id: str, chunk_id: str = None) -> str:
    seclevel = current_security_level.get()
    if chunk_id:
        # 返回单个 chunk 完整内容
        chunk = get_chunk_by_id(chunk_id, security_level=seclevel)
        return chunk
    else:
        # 返回 chunk 索引
        chunks = get_document_chunks(doc_id, security_level=seclevel)
        return format_chunk_index(chunks)
        # 输出示例：
        # "## 文档章节\n[chunk_0] 概述\n[chunk_1] 细则\n..."
```

**第二步：按需拉取** — Agent 看到索引后再次调用 `get_doc_detail(doc_id, chunk_id="chunk_0")` 获取完整内容。

`retriever.py` 新增 `get_chunk_by_id(doc_id, chunk_id, security_level)` 函数用于单 chunk 拉取。

### 涉及文件

- `python/rag/retriever.py` — 新增 `get_chunk_by_id()`
- `python/agent/tools.py` — 重写 `get_doc_detail` 为两步模式

---

## #8 查询改写

### 问题

多轮省略追问如"那外包适用吗？"直接拿原句检索。"外包"指什么？缺少上文语境，召回质量差。

### 方案

#### 触发规则（规则预判，避免不必要的 LLM 调用）

| 条件 | 动作 |
|------|------|
| 问题长度 < 10 字 | 触发改写 |
| 含指代词（这个/那个/它/其/这/那/他/她/他们） | 触发改写 |
| 含省略标记（也/还/同样/一样/上面/前面） | 触发改写 |
| 其他 | 原句直接检索 |

#### LLM 改写

命中规则后，将最近 3 轮对话 + 当前问题发给 DeepSeek flash：

```
System: "将用户问题补全为独立完整的检索语句。只输出改写后的问题，不要解释。"
User: "对话历史：
  用户：公司有哪些假期？
  助手：包括年假、病假、事假和婚假...
  用户：那外包适用吗？
改写后的问题："
```

期望输出：`"外包员工是否适用年假、病假、事假和婚假等假期政策？"`

#### 放置位置

在 `rag_chain.py` 的 `answer_with_rag()` 和 `agent/nodes.py` 中，检索之前调用：

```python
if should_rewrite(question, history):
    question = await rewrite_query(question, history)
```

### 涉及文件

- `python/rag/query_rewriter.py` — **新增** — `should_rewrite()` + `rewrite_query()`
- `python/llm/rag_chain.py` — 检索前调用改写
- `python/agent/nodes.py` — Agent 模式下改写后的 query 传入 tool

---

## #9 摘要压缩

### 问题

1. **Bug**：Agent 的 system prompt 被误压进摘要，因为 `summarize_history()` 没区分系统消息和对话消息
2. **RAG 缺失**：`rag_chain.py` 完全不调 `summarize_history()`
3. **无滚动累积压缩**：每次请求从零开始重新摘要，上一轮的摘要白白丢弃

### 方案

#### 9a. 修复 system-prompt 进摘要 bug

在 `deepseek_client.py` 的 `summarize_history()` 中，先过滤掉 `SystemMessage` 再做摘要：

```python
conversation_messages = [m for m in messages if not isinstance(m, SystemMessage)]
if len(conversation_messages) <= 3:
    return messages  # 太少不需要压缩
```

#### 9b. RAG 模式复用 summarize_history

**前置步骤：类型转换**。`rag_chain.py` 收到的 `history` 是前端传来的 `{role, content}` 字典列表（`List[HistoryMessage]` Pydantic 模型），但 `summarize_history()` 内部用 `isinstance(m, SystemMessage)` 做类型判断，期望 LangChain 消息对象。必须先转换为 LangChain 类型再传入：

```python
# rag_chain.py - answer_with_rag() 中
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

def _to_langchain_messages(history: list) -> list:
    role_map = {"user": HumanMessage, "assistant": AIMessage, "system": SystemMessage}
    return [role_map[h.role](content=h.content) for h in history if h.role in role_map]
```

转换完成后，再调用压缩：

```python
lc_history = _to_langchain_messages(history)
if len(lc_history) > 10:
    lc_history = await summarize_history(lc_history)
```

摘要以 `SystemMessage` 插入，前缀 `[历史摘要]`（沿用现有逻辑）。

> 注：`_to_langchain_messages()` 与 `agent_routes.py` 中已有的同类逻辑保持一致，后续可抽取为公共函数。

#### 9c. 滚动累积压缩 + Java 持久化

**Java 侧**：`Conversation` 实体新增 `summary` 字段：

```java
@Column(columnDefinition = "TEXT")
private String summary;  // 累积的对话摘要
```

对话数据返回给前端时携带 summary，前端在后续 `ChatRequest` 中传回。

**Python 侧**：`ChatRequest` schema 新增 `summary` 字段。`summarize_history()` 合并已有摘要与新消息：

```python
def summarize_history(messages, existing_summary: str = None):
    conv_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
    if existing_summary:
        prompt = f"之前的对话摘要：{existing_summary}\n\n新对话内容："
    else:
        prompt = "对话内容："
    # 调用 flash LLM 压缩，输出 ≤500 字摘要
    # 返回 SystemMessage("[历史摘要] xxx")，保留最后 3 条非系统消息
```

新的累积摘要通过 SSE `summary` 事件返回前端持久化：

```
data: {"type":"summary","content":"用户询问了假期政策、外包适用性..."}\n\n
```

### 涉及文件

- `python/llm/deepseek_client.py` — 修 system message 过滤 + 加 existing_summary 参数
- `python/llm/rag_chain.py` — 生成前加历史压缩
- `python/api/routes/agent_routes.py` — 接收 summary、发送 summary SSE、合并累积摘要
- `python/api/schemas/chat_schemas.py` — ChatRequest 加 summary 字段
- `java/chat/src/main/java/com/qa/chat/entity/Conversation.java` — 加 summary 列
- `java/chat/src/main/java/com/qa/chat/dto/ChatRequest.java` — 加 summary 字段

---

## #10 降级防幻觉

### 问题

Tier 2（RAG 降级）调用 `answer_with_rag()` 时，如果 `hybrid_search` 返回空结果，LLM 仍然被调用，无参考文档时模型可能编造答案。

### 方案

在 `rag_chain.py` 的 `answer_with_rag()` 中，检索后加空结果判断：

```python
async def answer_with_rag(question, history, ...):
    docs = await hybrid_search(question, ...)
    if not docs:
        return None  # 无法回答
    # ... 其余 RAG pipeline
```

在 `agent_routes.py` 降级路径中处理 None：

```python
result = await answer_with_rag(question, history, ...)
if result is None:
    yield sse("answer", "抱歉，我在知识库中未找到与您问题相关的信息，无法给出准确回答。建议您：\n1. 换个方式描述您的问题\n2. 联系相关部门获取最新政策信息")
    yield sse("done", "")
    return
```

原有的 Tier 3（search-only）和 Tier 4（兜底话术）保留，仅处理异常/错误场景。

### 涉及文件

- `python/llm/rag_chain.py` — 空检索返回 None
- `python/api/routes/agent_routes.py` — 降级路径处理 None，输出优雅拒答

---

## #11 工具重试 + 熔断

### 问题

工具调用无重试逻辑和熔断保护。Qdrant 短暂抖动或 DeepSeek API 偶发超时直接导致失败。

### 方案

#### 11a. tenacity 重试

在 `nodes.py` 的 `tools_node` 中用 `tenacity` 包装工具执行：

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, QdrantException)),
)
async def execute_tool_with_retry(tool_call):
    return await execute_tool(tool_call)
```

可重试错误：网络、超时、Qdrant 连接。不重试：参数错误、认证失败、空结果。

#### 11b. 轻量熔断器（同时支持 sync 和 async）

工具执行路径是 `async def execute_tool_with_retry → await execute_tool(...)`。同步版 `call()` 会把 coroutine 当结果返回而不 await，导致逻辑直接坏。因此 CircuitBreaker 必须提供 async 方法：

```python
# 新文件: python/common/circuit_breaker.py
import time
from enum import Enum
from typing import Callable, Awaitable, Union

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerOpenError(Exception):
    pass

class CircuitBreaker:
    def __init__(self, name, failure_threshold=5, recovery_timeout=60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0

    async def acall(self, coro_func: Callable[..., Awaitable], *args, **kwargs):
        """异步工具调用入口 — await 内部的 coroutine，正确处理返回值"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(f"熔断器 {self.name} 已开路")

        try:
            result = await coro_func(*args, **kwargs)  # 关键：await，不是直接调用
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

使用方式：

```python
# nodes.py - tools_node 中
breaker = tool_circuits["search_knowledge"]
result = await breaker.acall(execute_tool_with_retry, tool_call)
```

每个工具一个熔断器实例，通过 `breaker.acall(execute_tool_with_retry, tool_call)` 调用：

```python
tool_circuits = {
    "search_knowledge": CircuitBreaker("search_knowledge"),
    "search_employee": CircuitBreaker("search_employee"),
    "get_doc_detail": CircuitBreaker("get_doc_detail"),
}
```

熔断开路时返回明确错误信息，Agent 据此告知用户："搜索服务暂时不可用，请稍后重试。"

### 涉及文件

- `python/common/circuit_breaker.py` — **新增** — CircuitBreaker 类
- `python/agent/nodes.py` — 工具执行加 retry + circuit breaker
- `python/pyproject.toml` — 加 `tenacity` 依赖

---

## #1 可观测性（Token 用量 + 慢查询告警）

### 问题

- `AuditLog.tokenUsage` 字段存在但从未填充
- 无 token 成本可视化
- 响应时间虽已记录但无慢查询告警

### 方案

#### 1a. Token 用量记录

在 `rag_chain.py` 和 `nodes.py` 中，LLM 调用完成后用 tiktoken（已在用）估算用量，通过 SSE 事件传回 Java：

```python
token_usage = {
    "prompt_tokens": count_tokens(prompt_messages),
    "completion_tokens": count_tokens(generated_text),
}
yield sse("token_usage", json.dumps(token_usage))
```

> 注：DeepSeek 流式 API 不在最终 chunk 返回 usage，因此用量为 tiktoken 估算值。

Java `ChatServiceImpl` 解析 `token_usage` SSE 事件并写入 `AuditLog.tokenUsage`。

#### 1b. 慢查询告警

Python 侧配置阈值，超时打 WARN 日志：

```python
SLOW_QUERY_THRESHOLD_MS = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "5000"))

if response_time_ms > SLOW_QUERY_THRESHOLD_MS:
    logger.warning(f"SLOW_QUERY | question={question[:100]} | time={response_time_ms}ms | mode={mode}")
```

Java 侧同样在 `ChatServiceImpl` 流结束后加 WARN 日志。

#### 1c. 不做仪表板

本次迭代不做成本计算和可视化仪表板。

### 涉及文件

- `python/llm/rag_chain.py` — SSE 发送 token_usage
- `python/agent/nodes.py` — SSE 发送 token_usage
- `python/api/routes/agent_routes.py` — 慢查询 WARN 日志
- `java/chat/src/main/java/com/qa/chat/service/impl/ChatServiceImpl.java` — 解析 token_usage、慢查询日志

---

## 实施顺序

按依赖关系排列：

1. **#2 越权二次校验** — 安全基础；contextvars 模式需先落地，后续工具改动依赖它
2. **#4 去掉 MemorySaver** — 简化 Agent 代码；让 #9 的摘要逻辑更清晰
3. **#6 Token 裁剪** — 统一预算逻辑；#9 的摘要压缩需要感知 token 预算
4. **#7 工具链** — 依赖 #2（contextvars）、#4（state 变化）、#6（预算）
5. **#8 查询改写** — 独立功能；与 #7 可并行
6. **#9 摘要压缩** — 依赖 #4、#6；滚动摘要需要 #6 的预算感知
7. **#10 降级防幻觉** — 简单改动；在 #8 之后做（改写可能影响检索结果）
8. **#11 工具容错** — 独立；在 #7 之后做（工具已定型）
9. **#1 可观测性** — 最后；跨 Python + Java，等上面全部稳定后再加

## 风险

- **contextvars + asyncio**：`contextvars` 在 async 环境下正确传播（跟随 `await`），但必须在调用 tools 的同一个 task 中设置。用并发请求测试验证
- **移除 MemorySaver**：如果前端有 bug 没发全量 history，对话将丢失上下文。加 fallback 日志（history 为空时 WARN）
- **熔断器内存状态**：单实例没问题，多实例需后续升级为 Redis 版熔断器
