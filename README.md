# QA Agent — 企业内部智能问答系统

基于 RAG + LangGraph Agent 的企业规章制度与技术文档智能问答系统。支持文档上传自动索引、三种对话模式（RAG / Agent / 纯检索）、ReAct 自主推理、会话历史管理、WebSocket 实时进度推送。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + Element Plus + Pinia + Vite |
| 业务服务 | Java 21 + Spring Boot 3.5 + Maven |
| AI 服务 | Python 3.11 + FastAPI + LangChain + LangGraph |
| 向量数据库 | Qdrant (Docker) |
| 文件存储 | MinIO (Docker) |
| 数据库 | MySQL 8.0 |
| LLM | DeepSeek API (Chat + Embedding) |
| 反向代理 | Nginx (Docker) |

## 系统架构

```
Browser (Vue 3 SPA)
  → Nginx :80        (静态文件 + 反向代理)
    → Java Auth :8080     (JWT 认证)
    → Java Document :8081 (文档管理 + MinIO 上传 + 异步索引)
    → Java Chat :8082     (SSE 代理 + 会话持久化)
    → Java Audit :8083    (问答审计，管理员)
      → Python AI :8000   (RAG 检索 + LangGraph Agent)
        → DeepSeek API    (对话 + 嵌入 + 工具调用)
        → Qdrant :6333    (向量检索，含权限过滤)
        → MinIO :9000     (文档下载)
    ↕ WebSocket :8081     (索引进度广播)
```

### 三种对话模式

| 模式 | 说明 |
|------|------|
| `rag` | RAG 流水线：检索文档 → LLM 生成回答 → 溯源引用 |
| `agent` | LangGraph Agent：ReAct 推理循环（思考→工具调用→观察→回答），支持多步搜索 |
| `search-only` | 仅返回检索结果，不调用 LLM |

### Agent 工具

- `search_policy` — 检索规章制度（按部门权限过滤）
- `search_doc` — 检索技术文档（按标签筛选）
- `search_employee` — 查询员工组织架构（开发中）
- `get_doc_detail` — 获取文档完整详情（开发中）

## 前置条件

- **Java 21+**、**Maven 3.8+**、**Node.js 18+**
- **Python 3.11+**、**Poetry**
- **Docker Desktop**（运行 Qdrant + MinIO + MySQL + Nginx）
- **MySQL 8.0**（本地运行则需自行安装，数据库 `qa_agent` 自动创建）

## 快速启动

### 方式一：Docker Compose 全栈部署（推荐）

```bash
# 1. 配置环境变量
cp docker/.env.docker .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 2. 一键启动全部 6 个服务
cd docker
docker compose up -d

# 3. 访问
# 前端：http://localhost
# MinIO Console：http://localhost:9001
```

### 方式二：本地开发启动

#### 1. 配置环境变量

```bash
cp .env.example .env   # 如不存在则创建
# 编辑 .env，填入：
#   DEEPSEEK_API_KEY=你的API_Key
```

#### 2. 启动基础设施

```bash
cd docker
docker compose up -d mysql qdrant minio
```

#### 3. 启动 Python AI 服务

```bash
cd python
poetry install
poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

验证：`curl http://localhost:8000/api/agent/health` → `{"status":"ok"}`

#### 4. 启动 Java 业务服务

```bash
cd java
mvn clean install -DskipTests

# 一键启动全部模块（auth/document/chat/audit/frontend）
mvn -pl launcher exec:java -Dexec.mainClass="com.qa.launcher.LauncherApplication"
```

访问 http://localhost:5173

#### 5. 逐个启动（可选）

```bash
cd java
mvn -pl auth spring-boot:run      # 端口 8080
mvn -pl document spring-boot:run  # 端口 8081
mvn -pl chat spring-boot:run      # 端口 8082
mvn -pl audit spring-boot:run     # 端口 8083

cd java/frontend
npm install
npm run dev                        # 端口 5173
```

## 服务端口一览

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 (dev) | http://localhost:5173 | Vite 开发服务器 |
| 前端 (prod) | http://localhost | Nginx 静态服务 |
| Python AI | http://localhost:8000 | FastAPI，含 API 文档 `/docs` |
| Java Auth | http://localhost:8080 | JWT 登录/注册 |
| Java Document | http://localhost:8081 | 文档 CRUD + 上传 |
| Java Chat | http://localhost:8082 | 对话 SSE 代理 |
| Java Audit | http://localhost:8083 | 审计日志（管理员） |
| MySQL | localhost:3306 | 业务数据库 |
| Qdrant REST | http://localhost:6333 | 向量数据库 API |
| MinIO API | http://localhost:9000 | 对象存储 |
| MinIO Console | http://localhost:9001 | MinIO 管理界面 |

## API 端点概要

### Python AI (8000)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/agent/health` | 健康检查 |
| POST | `/api/agent/chat/stream` | SSE 流式对话（支持 rag/agent/search-only） |
| POST | `/api/agent/index` | 文档索引 |
| DELETE | `/api/agent/index/{doc_id}` | 删除文档向量 |

### Java (8080-8083)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/register` | 注册 |
| POST | `/api/documents/upload` | 上传文档 |
| GET/POST/DELETE | `/api/documents/**` | 文档 CRUD + 索引触发 |
| POST | `/api/chat/stream` | 对话 SSE（透传 Python） |
| GET | `/api/chat/conversations` | 会话列表 |
| GET/DELETE | `/api/chat/conversations/{id}` | 会话详情/删除 |
| GET | `/api/audit/logs` | 审计日志（管理员） |
| WS | `/ws/index-progress` | 索引进度 WebSocket |

## 使用流程

1. 打开浏览器访问前端页面
2. 注册账号并登录
3. 在「文档管理」页面上传 PDF/DOCX/MD/TXT 文档
4. 等待索引状态变为「已完成」（WebSocket 实时推送进度）
5. 在「智能问答」页面选择对话模式提问：
   - **RAG 模式**：快速检索 + 生成回答
   - **Agent 模式**：多步推理，自动搜索多个工具
   - **纯检索模式**：仅返回匹配文档，不生成回答
6. 左侧边栏可切换/删除历史会话

## 停止服务

- **Docker Compose**：`cd docker && docker compose down`
- **一键启动器**：在启动器终端按 `Ctrl+C`
- **Python 服务**：`Ctrl+C` 停止

## 项目文档

- `CLAUDE.md` — 详细架构说明、开发命令、常见问题
- `docs/superpowers/specs/` — 功能设计文档
- `docs/superpowers/plans/` — 实施计划文档
