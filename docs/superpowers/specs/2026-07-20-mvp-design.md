# MVP 架构设计文档

**版本**：v1.0  
**日期**：2026-07-20  
**关联 PRD**：企业内部规章制度与技术文档智能问答系统 PRD.md (v4.0)

---

## 一、项目概述

基于 PRD v4.0 的 MVP 范围，构建"混合检索 RAG + LLM 问答"核心链路。2 周内交付端到端可演示系统。

### 已确认决策

| 决策项 | 选择 |
|--------|------|
| 范围 | MVP（RAG 检索+问答 + Vue 3 前端 + 审计日志） |
| 开发顺序 | 先 Java 后 Python |
| Java 构建 | Maven |
| Python 包管理 | Poetry |
| Embedding | DeepSeek API（远程） |
| LLM | DeepSeek API |
| MySQL | 本地已有（root / hwx1314520） |
| Qdrant + MinIO | Docker 部署 |

---

## 二、目录结构

```
QA_agent/
├── java/                              # Java Spring Boot 业务底座
│   ├── pom.xml                        # 父 POM（Spring Boot 3.2.4）
│   ├── common/                        # 通用模块
│   │   ├── pom.xml
│   │   └── src/main/java/com/qa/
│   │       ├── CommonApplication.java
│   │       ├── common/
│   │       │   ├── ApiResult.java           # 统一响应体 {code, message, data}
│   │       │   ├── PageResult.java          # 分页响应
│   │       │   ├── BusinessException.java   # 业务异常
│   │       │   ├── ErrorCode.java           # 错误码枚举
│   │       │   └── GlobalExceptionHandler.java  # 全局异常处理
│   │       └── config/
│   │           └── SwaggerConfig.java       # Swagger/OpenAPI 配置
│   │
│   ├── auth/                          # 认证授权模块
│   │   ├── pom.xml
│   │   └── src/main/java/com/qa/auth/
│   │       ├── AuthApplication.java
│   │       ├── config/
│   │       │   └── SecurityConfig.java      # Spring Security 配置
│   │       ├── controller/
│   │       │   └── AuthController.java      # /api/auth/login, /register
│   │       ├── service/
│   │       │   ├── AuthService.java
│   │       │   └── impl/AuthServiceImpl.java
│   │       ├── dto/
│   │       │   ├── LoginRequest.java
│   │       │   ├── RegisterRequest.java
│   │       │   └── LoginResponse.java
│   │       ├── entity/
│   │       │   └── SysUser.java             # JPA 实体
│   │       ├── repository/
│   │       │   └── UserRepository.java
│   │       └── util/
│   │           └── JwtUtil.java             # JWT 生成/解析
│   │
│   ├── document/                      # 文档管理模块
│   │   ├── pom.xml
│   │   └── src/main/java/com/qa/document/
│   │       ├── DocumentApplication.java
│   │       ├── config/
│   │       │   └── MinioConfig.java         # MinIO 客户端配置
│   │       ├── controller/
│   │       │   └── DocumentController.java  # CRUD + 索引触发
│   │       ├── service/
│   │       │   ├── DocumentService.java
│   │       │   └── impl/DocumentServiceImpl.java
│   │       ├── dto/
│   │       │   ├── DocumentUploadRequest.java
│   │       │   └── DocumentResponse.java
│   │       ├── entity/
│   │       │   └── DocDocument.java         # JPA 实体
│   │       └── repository/
│   │           └── DocumentRepository.java
│   │
│   ├── chat/                          # 对话代理模块（端口 8082）
│       ├── pom.xml
│       └── src/main/java/com/qa/chat/
│           ├── ChatApplication.java
│           ├── config/
│           │   └── WebClientConfig.java     # WebClient Bean
│           ├── controller/
│           │   └── ChatController.java      # POST /api/chat/stream (SSE)
│           ├── service/
│           │   ├── ChatService.java
│           │   └── impl/ChatServiceImpl.java
│           └── dto/
│               ├── ChatRequest.java
│               └── ChatResponse.java
│
│   ├── audit/                          # 审计日志模块（端口 8083）
│   │   ├── pom.xml
│   │   └── src/main/java/com/qa/audit/
│   │       ├── AuditApplication.java
│   │       ├── controller/
│   │       │   └── AuditLogController.java  # GET /api/audit/logs (admin)
│   │       ├── service/
│   │       │   ├── AuditLogService.java
│   │       │   └── impl/AuditLogServiceImpl.java
│   │       ├── entity/
│   │       │   └── AuditLog.java
│   │       └── repository/
│   │           └── AuditLogRepository.java
│
│   ├── launcher/                       # 一键启动器
│   │   ├── pom.xml
│   │   └── src/main/java/com/qa/launcher/
│   │       └── LauncherApplication.java    # ProcessBuilder 启动所有模块
│
│   └── frontend/                       # Vue 3 前端 + Spring Boot 静态服务
│       ├── pom.xml
│       ├── package.json
│       ├── vite.config.ts
│       ├── src/
│       │   ├── main.ts
│       │   ├── App.vue
│       │   ├── router/index.ts
│       │   ├── stores/                     # Pinia: auth, chat, document
│       │   ├── api/                        # Axios + SSE fetch client
│       │   ├── views/                      # Login, Chat, Documents, Audit
│       │   └── components/                 # chat/, common/, document/
│       └── spring/                         # Spring Boot 包装器（端口 8084）
│           └── src/main/java/com/qa/frontend/
│               └── FrontendApplication.java
│
├── python/                            # Python AI 服务
│   ├── pyproject.toml                 # Poetry 配置
│   ├── api/                           # FastAPI 路由与模型
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 启动入口
│   │   ├── dependencies.py            # 依赖注入（API Key 验证）
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── agent_routes.py        # /api/agent/* 路由
│   │   │   └── health_routes.py       # /api/agent/health
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── chat.py                # ChatRequest, ChatResponse
│   │       └── index.py               # IndexRequest, IndexResponse
│   │
│   ├── rag/                           # RAG 检索模块
│   │   ├── __init__.py                # Qdrant 客户端单例
│   │   ├── loader.py                  # DocumentLoader（PDF/Markdown/TXT/DOCX）+ MinIO 下载
│   │   ├── splitter.py                # TextSplitter（分块策略，按文件类型）
│   │   ├── embedder.py                # 三级降级：DeepSeek → HuggingFace → sklearn
│   │   ├── indexer.py                 # 文档索引编排（load→split→embed→store）
│   │   └── retriever.py               # 混合检索 + 权限过滤
│   │
│   └── llm/                           # LLM 调用模块
│       ├── __init__.py
│       ├── deepseek_client.py         # AsyncOpenAI DeepSeek 流式客户端
│       └── rag_chain.py               # RAG 流水线：检索→提示词→LLM 生成→SSE 输出
│
└── docker/
    └── docker-compose.yml             # Qdrant + MinIO 服务编排
```

---

## 三、数据库设计（MySQL）

### 3.1 用户表 `sys_user`

```sql
CREATE TABLE sys_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL COMMENT 'bcrypt哈希',
    email VARCHAR(100),
    department VARCHAR(50),
    role VARCHAR(20) DEFAULT 'ROLE_EMPLOYEE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.2 文档表 `doc_document`

```sql
CREATE TABLE doc_document (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    file_name VARCHAR(200) NOT NULL,
    file_path VARCHAR(500) NOT NULL COMMENT 'MinIO存储路径',
    file_size BIGINT NOT NULL,
    file_type VARCHAR(20) NOT NULL COMMENT 'pdf/md/txt/docx',
    department VARCHAR(50) DEFAULT '全部',
    security_level VARCHAR(20) DEFAULT '内部' COMMENT '公开/内部/机密',
    status VARCHAR(20) DEFAULT 'UPLOADED' COMMENT 'UPLOADED/INDEXING/COMPLETED/FAILED',
    upload_by BIGINT,
    version INT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (upload_by) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.3 审计日志表 `audit_log`

```sql
CREATE TABLE audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    question TEXT NOT NULL,
    answer TEXT,
    tools_called JSON,
    response_time INT COMMENT '毫秒',
    token_usage JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 四、接口设计

### 4.1 Java 对外接口

| 方法 | 路径 | 模块（端口） | 说明 | 认证 |
|------|------|-------------|------|------|
| POST | `/api/auth/login` | auth (8080) | 登录，返回 JWT | 否 |
| POST | `/api/auth/register` | auth (8080) | 注册 | 否 |
| POST | `/api/documents/upload` | document (8081) | 上传文档到 MinIO | 是 |
| GET | `/api/documents` | document (8081) | 文档列表（分页） | 是 |
| GET | `/api/documents/{id}` | document (8081) | 文档详情 | 是 |
| DELETE | `/api/documents/{id}` | document (8081) | 删除文档（含 Qdrant 清理） | 是 |
| POST | `/api/documents/{id}/index` | document (8081) | 触发异步索引 | 是 |
| GET | `/api/documents/status/{id}` | document (8081) | 查询索引状态 | 是 |
| POST | `/api/chat/stream` | chat (8082) | SSE 流式对话 | 是 |
| GET | `/api/audit/logs` | audit (8083) | 审计日志查询（管理员） | 是 |

### 4.2 Python 内部接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/agent/index` | 执行文档索引 | API Key |
| POST | `/api/agent/chat/stream` | SSE 流式对话 | API Key |
| GET | `/api/agent/health` | 健康检查 | 否 |

### 4.3 Java → Python 调用协议

**请求头**：`X-API-Key`、`X-User-Role`、`X-User-Department`、`X-Trace-Id`

**索引请求体**：
```json
{
  "document": {
    "id": 1,
    "title": "员工手册",
    "file_path": "s3://documents/employee_handbook.pdf",
    "file_type": "pdf",
    "department": "全部",
    "security_level": "内部"
  },
  "callback_url": "http://java-app:8080/api/documents/status/{id}"
}
```

**对话请求体**：
```json
{
  "question": "年假有多少天？",
  "history": []
}
```

**SSE 响应流**：
```
data: {"type": "thinking", "content": "正在检索相关文档..."}
data: {"type": "answer", "content": "根据员工手册..."}
data: {"type": "citation", "content": {"title": "员工手册", "chunk": "...", "page": 12}}
data: [DONE]
```

---

## 五、Python RAG 检索流程

```
用户Query → deepseek_client.embed() → 查询向量
                                          ↓
              Qdrant并行检索：
              ├── dense 向量检索 (cosine similarity) → Top-10
              └── sparse BM25 检索（Qdrant 原生）→ Top-10
                                          ↓
              RRF (Reciprocal Rank Fusion) 融合 → 合并去重 → Top-10
                                          ↓
              权限过滤（department + security_level payload filter）
                                          ↓
              DeepSeek LLM 作为重排器：对 Top-10 重排序 → Top-5
                                          ↓
              构建 Prompt → DeepSeek LLM 生成答案 + 溯源引用
                                          ↓
              SSE 流式返回
```

---

## 六、Docker Compose（Qdrant + MinIO）

```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qa-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
  minio:
    image: minio/minio:latest
    container_name: qa-minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: admin123456
    volumes:
      - minio_data:/data
    restart: unless-stopped
volumes:
  qdrant_data:
  minio_data:
```

---

## 七、关键技术点

1. **Java 技术栈**：Spring Boot 3.5.16 + Java 21 + Maven 多模块
2. **Embedding 维度**：DeepSeek text-embedding 模型输出 1536 维向量；三级降级（DeepSeek → HuggingFace → sklearn HashingVectorizer）
3. **SSE 透传**：Java WebClient 消费 Python SSE 流，Flux 逐行读取再返回给前端
4. **异步索引**：Java `@Async` + `CompletableFuture` 触发 Python 索引，写入 MySQL 状态
5. **内部认证**：Python 侧中间件校验 `X-API-Key`，防止绕过 Java 直接调用
6. **权限传递**：Java 将 `X-User-Department` 传给 Python，Python 检索时加 Qdrant filter
7. **分块策略**：Markdown 用标题分割，PDF/TXT/DOCX 用递归分割（800/1024 tokens）
8. **一键启动**：launcher 模块通过 ProcessBuilder 启动 4 个 Java 模块 + 前端 Vite，含健康检查和优雅关闭

---

## 八、验收标准

- [ ] 用户可注册/登录，返回 JWT Token
- [ ] 可上传 PDF/Markdown/TXT/DOCX 文档到 MinIO
- [ ] 可触发文档索引，文档状态流转 UPLOADED → INDEXING → COMPLETED
- [ ] 提问后可收到基于知识库的 AI 回答（SSE 流式）
- [ ] 回答附带原文溯源引用（文档名 + 片段）
- [ ] 无关问题时明确拒答（"知识库中暂无相关信息"）
- [ ] 三种降级模式可切换（agent / rag / search-only）
- [ ] Vue 3 前端四个页面均可访问（登录、问答、文档管理、审计日志）
- [ ] 前端 SSE 流式渲染打字机效果和 Markdown 格式化
- [ ] 管理员可查看审计日志（分页 + 按用户筛选）
