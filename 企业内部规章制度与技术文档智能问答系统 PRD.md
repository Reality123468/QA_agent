# 企业内部规章制度与技术文档智能问答系统 — 产品需求文档（PRD）

**文档版本**：v4.0
**编制日期**：2026-07-20
**项目类型**：实习项目 / 简历项目
**技术路线**：Java SpringBoot（业务主体）+ Python LangChain Agent（AI智能体）


## 一、文档修订记录

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-07-20 | 初稿（Java + LangChain4j方案） | — |
| v2.0 | 2026-07-20 | 修订（Python LangChain方案） | — |
| v3.0 | 2026-07-20 | 定稿（Java主体 + Python Agent混合架构） | — |
| v4.0 | 2026-07-20 | 架构精简、补充RAG分块策略与ACL实现、新增评估与容错体系 | — |


## 二、项目概述

### 2.1 项目背景

企业在日常运营中积累了大量的内部文档，包括《员工手册》《技术规范》《接口文档》《故障预案》《财务制度》等。这些文档分散在不同部门、不同系统中，员工查找信息效率低下。传统关键词搜索无法理解语义，而直接使用大模型则面临"不知道企业内部知识"和"幻觉"两大问题。

更关键的是，**真实的企业场景中，用户的问题往往不是单一的"查文档"** ——员工可能会问"我下个月要休年假，项目交付来得及吗？"这需要Agent**自主规划**：先查休假政策、再查项目排期、最后综合判断。纯RAG系统只能"查"，而Agent能"想"和"做"。

### 2.2 项目目标

| 序号 | 目标 | 说明 |
|------|------|------|
| 1 | 知识统一管理 | 支持多格式文档（PDF/Word/Markdown/TXT）的统一上传、解析、存储 |
| 2 | 智能语义检索 | 通过混合检索（BM25关键词 + 向量语义）实现精准召回 |
| 3 | Agent自主决策 | 基于LangGraph Agent实现意图识别、任务拆解、多工具调用和自主规划 |
| 4 | 可信答案生成 | 基于检索到的上下文生成答案，并提供原文溯源引用 |
| 5 | 企业级安全 | 基于角色的权限控制（RBAC），不同角色只能看到权限范围内的文档 |
| 6 | 流畅用户体验 | SSE流式输出、异步文档处理、实时进度通知 |

### 2.3 目标用户

| 用户角色 | 使用场景 |
|----------|----------|
| **普通员工** | 查询休假政策、报销流程、技术规范等日常问题 |
| **技术人员** | 查询API接口文档、系统架构、故障处理预案 |
| **HR/行政** | 上传更新制度文档、管理知识库内容 |
| **管理员** | 用户管理、权限配置、系统监控、审计日志查看 |

### 2.4 MVP范围定义

考虑到单人开发周期，项目分为MVP版和完整版两个交付梯度：

| 模块 | MVP（优先交付） | 完整版（后续迭代） |
|------|----------------|-------------------|
| **问答核心** | 混合检索RAG + 溯源引用 | RAG + LangGraph Agent自主规划 |
| **文档管理** | PDF/Markdown上传 + 索引 | Word/TXT + 批量上传 + 版本管理 |
| **用户权限** | JWT登录 + 角色区分 | RBAC细粒度权限 + 部门隔离 |
| **前端** | Swagger UI / Postman 演示 | Vue 3 + Element Plus 完整前端 |
| **中间件** | MySQL + Qdrant + MinIO | 加Redis缓存（可选） |
| **部署** | 手动启动双服务 | Docker Compose一键部署 |

> **策略说明**：MVP聚焦"RAG检索+问答"核心链路，2周内可跑通端到端流程。Agent和前端在第3-4周作为加分项叠加。面试时可先演示MVP的核心能力，再展开Agent规划的技术深度。

### 2.5 非功能性需求

| 类别 | 要求 |
|------|------|
| **性能** | 普通问答响应时间 < 3s（不含LLM生成）；Agent推理总耗时 < 15s |
| **可用性** | 支持Docker Compose一键部署，服务异常自动重启 |
| **可扩展性** | Java与Python服务独立部署，支持水平扩展 |
| **安全性** | JWT认证 + RBAC权限控制；敏感数据脱敏后传输 |
| **可维护性** | 提供结构化日志；Python侧集成LangSmith可观测性 |


## 三、架构设计

### 3.1 总体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端层                                         │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────┐    │
│  │   Vue 3 + Element Plus       │  │   聊天问答界面 (SSE流式)          │    │
│  │   管理后台                    │  │                                  │    │
│  └──────────────────────────────┘  └──────────────────────────────────┘    │
│                                      │                                      │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────┐
│                              接入层  │                                      │
│                          ┌──────────┴──────────┐                          │
│                          │   Nginx 反向代理     │                          │
│                          │   + 静态资源服务     │                          │
│                          └──────────┬──────────┘                          │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────┐
│                        Java 业务底座层 (Spring Boot)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ 认证授权  │ │ 文档上传  │ │ 文档管理  │ │ 对话API  │ │  审计日志    │    │
│  │ JWT+RBAC │ │ 模块     │ │ 模块     │ │ 模块     │ │  模块        │    │
│  └──────────┘ └──────────┘ └──────────┘ └────┬─────┘ └──────────────┘    │
│                                               │                            │
│                           ┌───────────────────┴──────────────┐            │
│                           │  @Async 异步索引调度              │            │
│                           │  Agent HTTP客户端 (WebClient)    │            │
│                           └───────────────────┬──────────────┘            │
└───────────────────────────────────────────────┼────────────────────────────┘
                                                │ HTTP/REST + SSE
┌───────────────────────────────────────────────┼────────────────────────────┐
│                        Python Agent层 (FastAPI + LangChain)               │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI 服务封装                                │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                       │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │              LangGraph Agent (ReAct循环)               │    │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │    │
│  │  │ Thought │ → │ Action  │ → │Observe  │ → │  Judge  │ → ... │    │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘       │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                       │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                        Tool工具集                      │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │    │
│  │  │search_     │ │search_     │ │search_     │ │get_doc_    │    │    │
│  │  │policy      │ │doc         │ │employee    │ │detail      │    │    │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘    │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                       │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    RAG检索模块                                     │    │
│  │  混合检索(Qdrant 向量 + BM25) → Rerank → LCEL流水线              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              存储层                                         │
│  ┌──────────┐ ┌──────────────────────┐ ┌──────────┐ ┌──────────┐        │
│  │  MySQL   │ │  Qdrant (向量+BM25)  │ │  MinIO   │ │  Redis   │        │
│  │(用户/审计)│ │  (向量检索+关键词)   │ │(对象存储)│ │(会话缓存)│        │
│  └──────────┘ └──────────────────────┘ └──────────┘ └──────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 架构分层说明

| 层级 | 职责 | 技术选型 |
|------|------|----------|
| **前端层** | 用户界面展示、SSE流式消费 | Vue 3 + Element Plus |
| **接入层** | 反向代理、负载均衡、静态资源服务 | Nginx |
| **Java业务底座层** | 认证授权、文档管理、审计日志、请求路由 | Spring Boot 3.2.x |
| **Python Agent层** | Agent推理、工具调用、RAG检索增强生成 | FastAPI 0.128.0 + LangChain 1.2.22 + LangGraph 1.0.7 |
| **存储层** | 数据持久化与检索 | MySQL + Qdrant + MinIO + Redis（可选） |

### 3.3 Java + Python 混合架构决策

| 考量维度 | 纯Java方案 (LangChain4j) | 纯Python方案 | 混合架构（本方案） |
|----------|-------------------------|-------------|-------------------|
| Agent/RAG生态成熟度 | 较差，社区插件少 | 最优 | 优（AI逻辑在Python侧） |
| 企业管理功能 | 优（Spring Boot企业级能力） | 需额外开发 | 优（业务在Java侧） |
| 模型部署灵活度 | 差（Java加载模型困难） | 优 | 优（Python侧可本地加载Reranker等模型） |
| 部署复杂度 | 低 | 低 | 中（两个服务需联调） |
| 实习面试价值 | 单一栈 | 缺少Java工程能力 | 展示全栈+跨语言协作能力 |

> **决策结论**：选择混合架构，核心理由是 **(1)** LangChain/LangGraph生态在Python侧远优于Java侧；(2) 本地部署BGE-Reranker等模型需要Python的sentence-transformers库；(3) 实习岗位要求Python AI能力 + Java工程能力，双栈方案在简历中同时覆盖两项技能点。

### 3.4 数据流说明

**离线管道（知识准备）** ：

```
用户上传文档 → Java接收 → 存入MinIO → 返回"上传成功"
                                        ↓
                    前端点击"开始索引" → Java通过 @Async 异步调用 Python 索引接口
                                        ↓
                            Python DocumentLoader加载文档
                                        ↓
                            TextSplitter分块 → Embedding向量化
                                        ↓
                     存入Qdrant（同时写入稠密向量 + 稀疏向量用于BM25）
                                        ↓
                            更新MySQL文档状态 → WebSocket推送完成通知
```

**在线管道（问答推理）** ：

```
用户提问 → Java接收（携带JWT用户信息）
                                        ↓
                    Java通过WebClient调用Python Agent API（传递用户角色）
                                        ↓
                    Agent启动ReAct循环：
                    ┌─────────────────────────────────────────┐
                    │ Thought: 分析问题，确定需要哪些工具     │
                    │ Action: 调用工具 (如search_policy)     │
                    │ Observation: 工具返回结果              │
                    │ (循环直至得出最终答案)                 │
                    └─────────────────────────────────────────┘
                                        ↓
                    Agent流式返回（推理过程 + 最终答案）
                                        ↓
                    Java透传SSE流 → 前端逐字展示
                                        ↓
                    Java记录审计日志（含工具调用记录）
```


## 四、功能模块详述

### 4.1 用户认证与权限管理（Java层）

| 项目 | 内容 |
|------|------|
| **功能描述** | 用户注册/登录（JWT Token认证）；基于角色的权限控制（RBAC）；文档级权限控制（ACL） |
| **用户角色** | ROLE_EMPLOYEE（普通员工）、ROLE_LEADER（部门主管）、ROLE_HR（HR）、ROLE_ADMIN（管理员） |
| **技术选型** | Spring Security + JWT + bcrypt |
| **选型理由** | Spring Security是Java生态最成熟的安全框架；JWT无状态特性便于水平扩展；bcrypt为业界标准密码哈希算法 |
| **接口设计** | `POST /api/auth/login` - 登录；`POST /api/auth/register` - 注册；`POST /api/auth/logout` - 登出 |

**权限传递机制**：Java在调用Python Agent时，将用户角色、部门等信息通过HTTP Header（`X-User-Role`、`X-User-Department`）传递，Agent据此进行检索权限过滤。Python侧通过内部API Key进行服务间认证，防止绕过Java层直接调用。

### 4.2 文档上传与管理（Java层）

| 项目 | 内容 |
|------|------|
| **功能描述** | 支持上传PDF、Word（.docx）、Markdown、TXT等多种格式；文档元数据管理（标题、部门、密级、标签） |
| **文档状态** | `UPLOADED` → `INDEXING` → `COMPLETED` / `FAILED` |
| **技术选型** | MinIO（对象存储）+ Apache POI + PDFBox |
| **选型理由** | MinIO兼容S3 API，可私有化部署；POI和PDFBox是Java处理Office和PDF文档的成熟方案 |
| **接口设计** | `POST /api/documents/upload` - 上传；`GET /api/documents` - 列表；`GET /api/documents/{id}` - 详情；`DELETE /api/documents/{id}` - 删除 |

### 4.3 异步文档索引（Java层 + Python RAG层）

| 项目 | 内容 |
|------|------|
| **功能描述** | 文档上传后通过Spring @Async异步调用Python索引接口；任务状态管理；失败自动重试；通过WebSocket实时推送进度 |
| **技术选型** | Spring @Async + FastAPI + WebSocket |
| **选型理由** | RAG文档处理是IO密集型和计算密集型操作，必须异步化。@Async是Spring原生异步方案，降低了引入RabbitMQ的运维成本。WebSocket用于实时推送索引进度到前端 |
| **接口设计** | `POST /api/documents/{id}/index` - 触发索引；`GET /api/documents/status/{id}` - 查询索引状态；WebSocket端点 `/ws/progress` - 进度推送 |

### 4.4 文档分块策略（Python RAG层）

文档分块是整个RAG系统的质量瓶颈。分块过大则检索精度下降，分块过小则上下文丢失。针对不同文档类型制定差异化的分块策略：

| 文档类型 | 分块器 | chunk_size | overlap | 特殊处理 |
|----------|--------|-----------|---------|---------|
| **规章制度 (Markdown)** | MarkdownHeaderTextSplitter | 512 tokens | 64 | 按 `##` 标题层级分割，保留章节结构 |
| **技术文档 (PDF)** | RecursiveCharacterTextSplitter | 800 tokens | 100 | 使用PyMuPDF提取文本；表格区域用Unstructured库单独提取并转为Markdown表格 |
| **纯文本 (TXT)** | RecursiveCharacterTextSplitter | 1024 tokens | 128 | 按段落 `\n\n` 优先分割 |
| **Word (.docx)** | RecursiveCharacterTextSplitter | 800 tokens | 100 | 用python-docx提取，按段落和标题样式分割 |

**metadata 附加策略**：每个chunk入库时附加以下元数据，用于权限过滤和溯源：

```python
{
    "doc_id": "文档唯一ID",
    "title": "文档标题",
    "department": "所属部门",       # 用于权限过滤
    "security_level": "公开/内部/机密",  # 用于权限过滤
    "chunk_index": 5,               # chunk序号，用于定位原文位置
    "heading": "第三章 休假制度",    # 所在章节标题
    "source_page": 12               # 原文页码（PDF）
}
```

**文档更新/删除**：当文档被删除或更新时，通过Qdrant的 `payload` 过滤删除对应 `doc_id` 的所有chunk，然后重新索引新版本，保证数据一致性。

### 4.5 LangGraph Agent智能体（Python层 — 核心亮点）

| 项目 | 内容 |
|------|------|
| **功能描述** | ReAct推理循环；自主工具调用；多工具协同；最大迭代控制（`max_iterations=10`）；流式推理过程推送 |
| **技术选型** | LangChain 1.2.22 + LangGraph 1.0.7 |
| **选型理由** | LangGraph是2026年构建Agent的标准框架，提供StateGraph显式状态管理、持久化执行（Checkpoint）和流式API。LangChain 1.2.22为当前稳定版，官方明确以LCEL + LangGraph作为构建Agent与RAG的主流范式 |
| **接口设计** | `POST /api/agent/chat` - 对话（流式）；`POST /api/agent/chat/sync` - 对话（同步） |

**Agent系统提示词（核心）** ：

```
你是一名企业智能助手，拥有以下工具可供调用：
1. search_policy(query, department) - 检索企业规章制度
2. search_doc(query, tags) - 检索技术文档
3. search_employee(query) - 查询员工组织架构和通讯录
4. get_doc_detail(doc_id) - 获取某篇文档的完整详细内容

请遵循ReAct模式：先思考（Thought），再行动（Action），观察结果（Observation），
循环直至得出最终答案（Final Answer）。如用户问题涉及权限外内容，礼貌拒绝。
当检索结果不足以回答问题时，明确告知用户"该问题我目前无法准确回答"而不是编造答案。
```

### 4.6 Tool工具集（Python层）

| 工具名称 | 功能描述 | 触发场景 | 参数 |
|----------|----------|----------|------|
| `search_policy` | 检索企业内部规章制度，自动按用户部门过滤权限 | 用户问"年假有多少天" | `query: str`, `department: str` |
| `search_doc` | 检索技术文档，按标签筛选 | 用户问"登录接口怎么调用" | `query: str`, `tags: List[str]` |
| `search_employee` | 查询员工组织架构、角色和联系方式 | 用户问"技术部负责人是谁" | `query: str` |
| `get_doc_detail` | 获取指定文档的完整内容（当检索片段不够时使用） | Agent判断需要查看完整文档 | `doc_id: str` |

**技术选型**：LangChain `@tool` 装饰器 + Pydantic参数校验

**选型理由**：`@tool`装饰器将普通Python函数转化为LangChain可识别的工具，函数的docstring自动成为工具描述。Pydantic提供参数类型校验和自动生成JSON Schema。4个工具覆盖了企业内知识检索的核心场景，每个工具背后有真实数据源支撑。

**代码示例**：

```python
from langchain.tools import tool
from pydantic import BaseModel, Field

class PolicySearchInput(BaseModel):
    query: str = Field(description="搜索关键词，如'年假'、'报销'")
    department: str = Field(default="全部", description="部门名称，用于权限过滤")

@tool(args_schema=PolicySearchInput)
def search_policy(query: str, department: str = "全部") -> str:
    """检索企业内部规章制度，包括员工手册、财务制度、考勤政策等"""
    # 构建Qdrant过滤条件：仅检索当前用户有权查看的文档
    # 调用RAG检索模块
    return result
```

### 4.7 混合检索与RAG（Python层）

| 项目 | 内容 |
|------|------|
| **功能描述** | 双路召回（BM25关键词 + 向量语义检索）；RRF融合排序；检索权限过滤；重排序（Rerank） |
| **技术选型** | LangChain EnsembleRetriever + Qdrant 1.7+（向量检索 + BM25）+ BGE-Reranker |
| **选型理由** | Qdrant v1.10+ 原生支持稠密向量 + 稀疏向量（BM25）双索引，无需额外部署Elasticsearch，大幅降低运维复杂度。BGE-Reranker在中文场景表现优异，本地部署零成本 |
| **检索流程** | 用户Query → 构建权限过滤条件 → 并行BM25+向量双路检索 → RRF融合 → BGE-Reranker精排 → Top-N送入LLM |

#### 4.7.1 权限过滤在向量检索中的实现

RAG中的权限过滤是公认的技术难点。本方案采用**检索前过滤（Pre-filtering）**策略：

```
Qdrant 检索请求示例：
{
  "vector": [0.12, -0.34, ...],        // 用户query的embedding向量
  "sparse_vector": {                     // BM25稀疏向量
    "indices": [15, 23, 87, ...],
    "values": [0.8, 0.3, 0.6, ...]
  },
  "filter": {                            // 权限过滤条件
    "must": [
      {"key": "department", "match": {"any": ["技术部", "全部"}}},
      {"key": "security_level", "match": {"except": ["机密"]}}
    ]
  },
  "limit": 20
}
```

- 每个chunk入库时携带 `department` 和 `security_level` 的payload
- 检索时根据Java层传来的 `X-User-Role` 和 `X-User-Department` 构建Qdrant filter
- 过滤发生在检索之前，保证用户只能召回有权限的文档片段
- 当用户角色为 `ROLE_LEADER` 或以上时，"机密"文档方可被检索

### 4.8 LCEL流水线编排（Python层）

| 项目 | 内容 |
|------|------|
| **功能描述** | 使用LangChain Expression Language编排RAG流水线；支持同步/异步调用与流式输出 |
| **技术选型** | LangChain LCEL（RunnableSequence / RunnableParallel） |
| **选型理由** | LCEL通过 `|` 操作符将组件串联为清晰流水线；RunnableParallel支持并行执行多个检索器 |

**代码示例**：

```python
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

rag_chain = (
    {"context": retriever | reranker, "question": RunnablePassthrough()}
    | prompt
    | llm
    | output_parser
)
```

### 4.9 流式对话（Java层 + Python层协同）

| 项目 | 内容 |
|------|------|
| **功能描述** | Java通过WebClient调用Python Agent的流式接口；Python返回SSE流；Java透传SSE流给前端；Agent推理过程流式展示 |
| **技术选型** | FastAPI StreamingResponse + Spring WebFlux WebClient + SSE |
| **选型理由** | FastAPI的StreamingResponse原生支持SSE流式输出；WebClient是Spring响应式HTTP客户端，支持流式数据消费；Feign不支持流式消费 |
| **接口设计** | `POST /api/chat/stream` - SSE流式对话（Java透传） |

### 4.10 审计日志（Java层）

| 项目 | 内容 |
|------|------|
| **功能描述** | 记录所有用户的问答记录（谁、何时、问了什么、系统回答了什麼）；记录Agent工具调用记录；支持多维度检索 |
| **技术选型** | MySQL + Spring AOP |
| **选型理由** | 企业级应用必须可审计、可追溯。Spring AOP实现无侵入式日志记录 |

**审计日志字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT | 主键 |
| `user_id` | BIGINT | 用户ID |
| `question` | TEXT | 用户问题 |
| `answer` | TEXT | 系统回答 |
| `tools_called` | JSON | Agent调用的工具列表 |
| `response_time` | INT | 响应耗时（毫秒） |
| `created_at` | DATETIME | 创建时间 |


## 五、评估体系

AI系统的质量不能仅凭主观感受判断，需要建立可量化的评估指标。

### 5.1 检索质量评估

| 指标 | 评估框架 | 方法 | 目标值 |
|------|---------|------|--------|
| 命中率 (Hit Rate) | RAGAS | 测试集中用户问题检索后，正确答案文档是否在Top-5中 | > 85% |
| 平均倒数排名 (MRR) | RAGAS | 第一个相关文档在召回结果中的平均排名倒数 | > 0.7 |
| 召回覆盖率 (Recall@K) | 手动标注 | Top-10中相关文档占所有相关文档的比例 | > 90% |

### 5.2 答案质量评估

| 指标 | 方法 | 目标值 |
|------|------|--------|
| 忠实度 (Faithfulness) | RAGAS：答案中的每个claim是否能在检索的context中找到支撑 | > 80% |
| 答案相关性 (Answer Relevancy) | RAGAS：答案与问题的语义相关性 | > 80% |
| 拒答率 | 构造10条知识库外的无关问题，验证系统是否正确拒绝回答 | 90%拒答 |

### 5.3 测试集构建

准备50-100条典型企业问答作为评估数据集，覆盖以下几种类型：
- **事实型查询**："年假有多少天？"（有明确答案，可直接验证）
- **跨文档推理**："年假和病假的申请流程有什么区别？"
- **权限边界**："某机密项目的技术方案是什么？"（应由非授权用户验证拒绝）
- **无关问题**："今天天气怎么样？"（应拒答）

### 5.4 可观测性

| 工具 | 用途 |
|------|------|
| LangSmith | Agent推理过程追踪、工具调用链可视化、Token消耗统计 |
| Spring Boot Actuator | Java服务健康检查、Metrics收集 |
| Python logging | 结构化日志 + 请求级Trace ID贯穿Java→Python调用链 |


## 六、容错与降级策略

### 6.1 异常场景处理矩阵

| 故障场景 | 处理策略 | 用户看到的效果 |
|----------|----------|---------------|
| Python Agent 服务不可用 | Java检测连接失败，立即返回降级响应 | "AI服务暂时繁忙，请稍后重试" + 记录告警日志 |
| LLM API 调用超时（>30s） | WebClient设置60s读取超时，Agent侧30s超时自动中断 | 返回已输出的部分内容 + "回答被中断，请简化问题重试" |
| LLM API 限流/配额耗尽 | 捕获429状态码，3次指数退避重试（1s/2s/4s） | 重试用尽后提示"服务请求过多，请稍后再试" |
| Qdrant 不可用 | 检索异常被Agent捕获 | "知识库暂时无法访问，请联系管理员" |
| 文档解析失败（PDF损坏/乱码） | Python侧捕获异常，标记文档状态为FAILED | 前端显示"索引失败：文件解析异常" + 失败原因 |
| Agent 超过最大迭代次数 | LangGraph `max_iterations=10` 触发中断 | 返回"该问题过于复杂，我暂时无法回答，建议拆分为多个简单问题" |
| Token超限（上下文过长） | 动态裁剪较早的对话轮次 + 减少检索Top-N | 用户无感知，确保不超出模型上下文窗口 |

### 6.2 降级层次

```
Level 1: Agent模式 (LangGraph ReAct)
    ↓ 降级（Agent不可用时）
Level 2: 纯RAG模式 (跳过Agent，直接检索 + LLM生成)
    ↓ 降级（LLM不可用时）
Level 3: 关键词搜索模式 (仅返回检索到的文档片段，不做生成)
```

Java侧通过配置项 `agent.mode` (agent / rag / search-only) 控制当前运行的级别，可在不重启服务的情况下切换。


## 七、技术栈总览

| 层级 | 技术选型 | 版本 | 说明 |
|------|----------|------|------|
| **编程语言** | Java + Python | Java 21 / Python 3.11 | 双栈融合 |
| **Java框架** | Spring Boot | 3.2.4+ | 企业级业务底座 |
| **Java HTTP客户端** | Spring WebFlux WebClient | — | 支持SSE流式消费 |
| **Python Web框架** | FastAPI | 0.128.0 | AI服务封装 |
| **Python Agent框架** | LangChain + LangGraph | 1.2.22 / 1.0.7 | Agent核心 |
| **LLM API** | DeepSeek-V3 | — | 国内合规、高性价比 |
| **Embedding模型** | BGE-M3 / text-embedding-v3 | — | 中文语义向量，支持稀疏+稠密双表征 |
| **Reranker模型** | BGE-Reranker-v2-m3 | — | 本地部署，二次精排 |
| **向量数据库** | Qdrant | 1.10+ | 向量检索 + BM25双索引合一 |
| **关系数据库** | MySQL | 8.0+ | 业务数据 |
| **对象存储** | MinIO | RELEASE.2024+ | 文档存储 |
| **缓存（可选）** | Redis | 7.0+ | 会话缓存，MVP阶段可省略 |
| **前端** | Vue 3 + Element Plus | — | 管理后台 |
| **可观测性** | LangSmith | — | Agent追踪 |
| **容器化** | Docker + Docker Compose | — | 一键部署 |


## 八、接口设计

### 8.1 Java服务接口（对外）

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/auth/login` | POST | 用户登录 | 否 |
| `/api/auth/register` | POST | 用户注册 | 否 |
| `/api/documents/upload` | POST | 上传文档 | 是 |
| `/api/documents` | GET | 文档列表 | 是 |
| `/api/documents/{id}` | GET | 文档详情 | 是 |
| `/api/documents/{id}` | DELETE | 删除文档 | 是 |
| `/api/documents/{id}/index` | POST | 触发文档索引 | 是 |
| `/api/chat/stream` | POST | SSE流式对话 | 是 |
| `/api/chat/history` | GET | 对话历史 | 是 |
| `/api/audit/logs` | GET | 审计日志（管理员） | 是 |

### 8.2 Python Agent接口（内部）

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/agent/chat` | POST | 对话（流式SSE） | 内部API Key |
| `/api/agent/chat/sync` | POST | 对话（同步） | 内部API Key |
| `/api/agent/index` | POST | 文档索引 | 内部API Key |
| `/api/agent/health` | GET | 健康检查 | 否 |

### 8.3 Java调用Python协议

**请求头**：

| Header | 说明 |
|--------|------|
| `X-API-Key` | 内部服务认证密钥 |
| `X-User-Id` | 用户ID |
| `X-User-Role` | 用户角色（如 ROLE_EMPLOYEE） |
| `X-User-Department` | 用户部门 |
| `X-Session-Id` | 会话ID（多轮对话） |
| `X-Trace-Id` | 链路追踪ID |

**请求体**：

```json
{
  "question": "我下个月想休年假，项目交付来得及吗？",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**响应（SSE流）** ：

```
event: thought
data: {"content": "用户想休年假，需要先查政策"}

event: action
data: {"tool": "search_policy", "args": {"query": "年假天数"}}

event: observation
data: {"content": "入职满1年享5天年假"}

event: final
data: {"answer": "...", "citations": [...]}
```


## 九、数据库设计

### 9.1 用户表（`sys_user`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT | 主键 |
| `username` | VARCHAR(50) | 用户名（唯一） |
| `password` | VARCHAR(255) | bcrypt哈希 |
| `email` | VARCHAR(100) | 邮箱 |
| `department` | VARCHAR(50) | 部门 |
| `role` | VARCHAR(20) | 角色 |
| `created_at` | DATETIME | 创建时间 |

### 9.2 文档表（`doc_document`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT | 主键 |
| `title` | VARCHAR(200) | 文档标题 |
| `file_name` | VARCHAR(200) | 原始文件名 |
| `file_path` | VARCHAR(500) | MinIO存储路径 |
| `file_size` | BIGINT | 文件大小（字节） |
| `file_type` | VARCHAR(20) | 文件类型（pdf/docx/md/txt） |
| `department` | VARCHAR(50) | 所属部门 |
| `security_level` | VARCHAR(20) | 密级（公开/内部/机密） |
| `status` | VARCHAR(20) | 状态 |
| `upload_by` | BIGINT | 上传人ID |
| `version` | INT | 版本号 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

### 9.3 审计日志表（`audit_log`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT | 主键 |
| `user_id` | BIGINT | 用户ID |
| `question` | TEXT | 用户问题 |
| `answer` | TEXT | 系统回答 |
| `tools_called` | JSON | 工具调用记录 |
| `response_time` | INT | 响应耗时（毫秒） |
| `token_usage` | JSON | Token消耗 |
| `created_at` | DATETIME | 创建时间 |


## 十、部署方案

### 10.1 Docker Compose服务编排

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `java-app` | 自定义（Spring Boot） | 8080 | 业务底座 |
| `python-agent` | 自定义（FastAPI） | 8000 | AI Agent服务 |
| `mysql` | mysql:8.0 | 3306 | 业务数据库 |
| `qdrant` | qdrant/qdrant:latest | 6333 | 向量检索 + BM25 |
| `minio` | minio/minio:latest | 9000 | 文档对象存储 |
| `redis` | redis:7.0 | 6379 | 会话缓存（可选，MVP可省略） |
| `nginx` | nginx:latest | 80 | 反向代理 + 静态资源 |

### 10.2 环境变量配置

| 变量 | 说明 | 示例 |
|------|------|------|
| `JAVA_APP_PORT` | Java服务端口 | 8080 |
| `PYTHON_AGENT_URL` | Python Agent地址 | http://python-agent:8000 |
| `AGENT_INTERNAL_API_KEY` | Python服务内部认证密钥 | 随机生成 |
| `LLM_API_KEY` | 大模型API密钥 | sk-xxx |
| `LLM_MODEL` | 模型名称 | deepseek-chat |
| `EMBEDDING_MODEL` | Embedding模型 | BAAI/bge-m3 |
| `RERANKER_MODEL` | Reranker模型 | BAAI/bge-reranker-v2-m3 |
| `MYSQL_*` | MySQL配置 | — |
| `QDRANT_*` | Qdrant配置 | — |
| `MINIO_*` | MinIO配置 | — |
| `REDIS_*` | Redis配置（可选） | — |


## 十一、项目里程碑

| 阶段 | 周期 | 核心产出 | 验收标准 |
|------|------|----------|----------|
| **Phase 1: MVP** | 第1-2周 | Java端认证+文档上传；Python端FastAPI+RAG检索+LLM问答 | 上传文档→提问→收到带溯源的AI回答 |
| **Phase 2: Agent** | 第3-4周 | LangGraph Agent + 工具集 + ReAct推理循环 | Agent可自主调用多个工具完成复合问题 |
| **Phase 3: 联调** | 第5周 | Java-Python联调：权限传递+SSE流式透传+审计日志 | 端到端流式对话可用 |
| **Phase 4: 评估** | 第6周 | RAGAS评估 + 测试集构建 + 性能优化 | 命中率>85%，忠实度>80% |
| **Phase 5: 界面** | 第7-8周 | Vue 3 管理后台 + 问答界面 + WebSocket进度通知 | 全流程可视化 |
| **Phase 6: 部署** | 第9-10周 | Docker Compose编排 + 测试 + README + 简历项目描述 | 一键部署可演示 |

> **策略**：MVP在前2周完成核心链路闭环，确保任何时候都有可演示的内容。后续每个Phase都是增量叠加，即使某个Phase延期也不影响已有功能的展示。


## 十二、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| LLM API调用延迟高 | 用户体验差 | 使用国内API（DeepSeek），网络延迟<100ms；SSE流式输出让用户感知更快 |
| Agent陷入死循环 | 资源浪费 | 设置`max_iterations=10`，超时自动终止；返回部分推理过程供用户判断 |
| PDF文档解析质量差 | 检索效果不达标 | 投入时间验证PyMuPDF vs Unstructured在不同PDF类型上的表现；表格密集的PDF考虑手工预处理 |
| Java与Python服务通信超时 | 请求失败 | 设置合理超时（连接10s，读取60s）；实现3次指数退避重试 |
| 向量库数据量增长 | 检索性能下降 | Qdrant支持水平扩展；评估后可按部门分Collection隔离 |
| Python生态版本不稳定 | 依赖冲突 | 使用Poetry锁定依赖版本；LangChain 1.x API已趋于稳定 |
| 单人开发时间不足 | 延期交付 | MVP优先策略：每周五有一个可演示的版本，功能按优先级叠加 |
