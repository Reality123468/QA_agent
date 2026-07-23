# QA Agent 项目简历描述（STAR 法则）

---

## 一句话概括

> 独立设计并实现企业内部智能问答系统，覆盖文档管理、RAG 检索增强生成、LangGraph Agent 自主推理、流式对话全链路，支持 4 种文档格式，融合 Java Spring Boot 微服务 + Python FastAPI AI 服务 + Docker Compose 全栈编排的异构架构。

---

## STAR 法则完整描述

### S — 情境 (Situation)

企业内部规章制度、技术规范、接口文档等知识分散在不同系统中，员工查找信息效率低下。传统关键词搜索无法理解语义（如"年假怎么休"与"休假政策"的语义关联），而直接使用大语言模型则面临"不知道企业内部知识"和"编造答案"两大隐患。项目需在单人开发、有限周期内交付具备自主推理能力的智能问答系统。

### T — 任务 (Task)

**MVP 阶段：**
1. **多格式文档管理**：支持 PDF / Word / Markdown / TXT 文档的上传、存储与自动索引
2. **RAG 智能问答**：语义检索 → 文档召回 → LLM 生成 → 引用溯源全流程
3. **企业级安全**：JWT 登录认证 + RBAC 权限控制，不同角色只能查看权限范围内的文档
4. **流式交互体验**：SSE 实时流式输出，类似 ChatGPT 的逐字生成效果
5. **一键启动**：5 个服务模块一键拉起

**完整版阶段：**
6. **LangGraph Agent 自主推理**：ReAct 推理循环，4 个 LangChain 工具（政策检索、文档检索、员工查询、文档详情），LLM 自主决策是搜索还是直接回答，支持多步推理（最多 10 轮）
7. **三种对话模式**：RAG 模式（快速检索+生成）、Agent 模式（ReAct 自主推理）、纯检索模式（仅返回匹配文档）
8. **会话历史管理**：JPA 持久化对话和消息，支持多轮对话上下文、历史会话列表、会话删除
9. **WebSocket 实时进度推送**：文档索引时实时广播进度到前端
10. **Docker Compose 全栈编排**：MySQL + Qdrant + MinIO + Python Agent + Java 4 模块 + Nginx 反向代理，一条命令启动

### A — 行动 (Action)

**系统架构设计**
- 设计 **Java Spring Boot（业务层）+ Python FastAPI（AI 层）** 异构架构，7 个 Maven 模块 + 1 个 Vue 3 前端独立部署
- Java 层负责认证授权（Spring Security + JWT）、文档 CRUD + MinIO 存储、SSE 代理转发、审计日志、会话历史持久化、WebSocket 进度广播
- Python 层负责 RAG 流水线 + LangGraph Agent 自主推理，4 个 ReAct 工具（检索+推理循环）
- Docker Compose 编排 6 个容器服务（MySQL + Qdrant + MinIO + Python + Java + Nginx），含健康检查和依赖顺序
- Nginx 反向代理统一入口，前端静态文件服务 + API 路由转发

**RAG + Agent 流水线实现**
- **RAG 流水线**：多源文档下载解析 → 格式感知分块（Markdown 按标题 H2/H3、PDF 按字符 800chunk/150overlap） → 三级 Embedding 降级（DeepSeek API 1536-dim → HuggingFace 本地 384-dim → sklearn HashingVectorizer 384-dim 零依赖兜底） → Qdrant 向量索引（Cosine 相似度 + 部门/密级权限过滤） → Prompt 工程 + 流式生成 + 原文溯源引用
- **Agent 推理**：基于 LangGraph StateGraph 构建 ReAct 循环（agent_node → conditional_edge → tools_node → agent_node），MemorySaver 持久化多轮对话状态。LLM 自主决定调用哪些工具，最多 10 轮推理。tool_calls 通过 OpenAI function-calling 格式与 DeepSeek API 交互
- **关键 Bug**：`astream_events(v2)` 只对 LangChain ChatModel 触发事件，但 agent_node 使用直接 OpenAI API 调用，导致最终答案永远无法提取。改用 `astream(stream_mode="values")` 直接检查状态增量中的消息类型（AIMessage.tool_calls → action，ToolMessage → observation，AIMessage.content → answer），修复了"无限转圈后超时"的阻塞 Bug

**前端交互**
- 基于 Vue 3 + Element Plus + Pinia + TypeScript 构建 SPA 前端，Vue Router 路由守卫 + RBAC 权限
- 用 fetch + ReadableStream + AbortController 手动实现 POST 方式的 SSE 流式解析（原生 EventSource 仅支持 GET），处理 8 种 SSE 事件类型（thinking/answer/citation/thought/action/observation/done/error）
- Agent 推理过程可视化：AgentThinking 组件展示思考→工具调用→观察→回答的完整推理链
- 左侧会话列表（ConversationList），支持历史会话切换和删除
- WebSocket 连接管理，文档上传后实时显示索引进度

**工程化**
- 编写 ProcessBuilder 一键启动器，自动解析 mvn/npm 可执行文件路径，跨平台兼容（Windows `.cmd` 后缀处理），并发启动 + 端口健康检查 + JVM ShutdownHook 优雅关闭
- Docker 多阶段构建：Java Maven build → fat JAR；Vue Node build → Nginx serve；Python Poetry install → uvicorn
- 解决 Windows 平台特有兼容问题：MinIO 文件锁冲突、Java ProcessBuilder PATH 不继承、JVM 主线程退出导致子进程终止、curl 中文字符 UTF-8 编码
- LangChain → OpenAI API 消息格式转换（`msg.type` vs `role`），Pydantic v2 null 值校验差异，跨语言 JSON 字段映射（camelCase ↔ snake_case）

### R — 结果 (Result)

| 指标 | 数值 |
|------|------|
| 代码总量 | ~8,000+ 行（Java ~4,000 / Python ~1,500 / 前端 ~2,500） |
| 服务模块 | 7 Java Maven 模块 + 1 Python 服务 + 1 Vue 3 前端 |
| Docker 容器 | 6 个（MySQL + Qdrant + MinIO + Python + Java + Nginx） |
| 支持文档格式 | 4 种（PDF / DOCX / Markdown / TXT） |
| 对话模式 | 3 种（RAG / Agent 自主推理 / 纯检索） |
| Agent 工具 | 4 个 LangChain Tool（政策/文档/员工/详情检索） |
| SSE 事件类型 | 8 种（thinking/answer/citation/thought/action/observation/done/error） |
| 向量检索 | Qdrant，Cosine 相似度 + 部门/密级权限过滤 |
| Embedding 策略 | 三级降级（API 1536-dim → 本地 384-dim → 零依赖 384-dim） |
| LLM 集成 | DeepSeek API，流式生成 + function-calling 工具调用 |
| 开发周期 | MVP 2.5 天（27 提交）+ 完整版扩展（10 提交） |
| 关键 Bug 修复 | Agent 无限循环、消息格式转换、Pydantic null 校验、SSE 事件缺失等 |

---

## 简历精简版（适合项目经历栏位）

### 企业内部智能问答系统（RAG + LangGraph Agent）— 独立开发

- 设计并实现 **Java Spring Boot + Python FastAPI** 两层异构架构，7 个 Maven 模块 + 1 个 AI 服务，Docker Compose 6 容器全栈编排
- 构建 **RAG 检索增强生成流水线**：多格式文档解析 → 格式感知分块 → 三级 Embedding 降级 → Qdrant 向量检索 + RBAC 权限过滤 → LLM 流式生成 + 原文溯源
- 实现 **LangGraph Agent 自主推理**：ReAct 循环 + 4 个工具 + OpenAI function-calling，支持多步搜索和三种对话模式切换
- 实现 **Vue 3 + TypeScript** 前端：POST 方式 SSE 流式解析（8 种事件类型）、Agent 推理过程可视化、WebSocket 实时索引进度、会话历史管理
- 使用 **Docker Compose** 一键部署 6 个服务（MySQL + Qdrant + MinIO + Python + Java + Nginx），编写 ProcessBuilder 本地开发启动器
- 解决 Windows 跨平台兼容问题（ProcessBuilder PATH 继承、MinIO 文件锁、跨语言消息格式转换、Pydantic null 校验）

---

## 面试准备：可能的追问

1. **为什么选择 Java + Python 混合架构？** — Java 生态成熟，适合企业级业务逻辑、权限管理和数据持久化；Python 在 AI/ML 领域生态最完善，LangChain + LangGraph 让 Agent 开发效率极高。通过 HTTP + API Key 解耦，未来可独立扩展或替换 LLM 提供商。

2. **Agent 模式相比 RAG 模式有什么优势？** — RAG 模式是单次检索+生成，Agent 模式是 ReAct 推理循环：LLM 先分析问题→决定调用哪些工具→观察结果→判断是否需要进一步搜索→最终回答。Agent 适合需要多步推理的复杂问题（如"年假和病假的申请流程有什么区别"需要分别查询两种政策）。

3. **Agent 流式输出遇到了什么问题？** — 最初使用 LangGraph 的 `astream_events(v2)` 监听 LLM 事件，但发现 `on_chat_model_*` 事件只会对 LangChain ChatModel 包装器触发，而 agent_node 直接调用 OpenAI 客户端。最终改用 `astream(stream_mode="values")` 直接从状态增量中提取 AIMessage 和 ToolMessage，区分工具调用（action）、工具结果（observation）和最终回答（answer）。

4. **为什么 Embedding 要设计三级降级？** — DeepSeek API 可能因网络/额度问题不可用，HuggingFace 模型需要手动安装依赖。三级降级保证系统在任何环境都能跑通，这对演示项目和 CI/CD 尤为重要。

5. **SSE 为什么不用原生 EventSource？** — EventSource 只支持 GET 请求，无法携带 JSON body 传递对话历史、模式和用户信息。用 fetch + ReadableStream 手动解析可以在保持 POST 能力的同时处理 8 种不同事件类型。

6. **如何保证检索结果与用户权限匹配？** — Qdrant 查询时通过 `Filter` 条件过滤：部门 MatchAny，密级 MatchExcept（非特权用户排除"机密"文档）。权限过滤在数据库层完成，保证效率和安全性。

7. **如何避免 LLM 幻觉？** — Prompt 工程要求"仅根据参考文档内容回答"、"找不到相关信息时明确告知"。Agent 模式额外具备多步搜索能力，会尝试不同关键词和工具组合。同时通过 citation 溯源让用户验证答案来源。
