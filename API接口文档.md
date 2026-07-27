# 企业内部规章制度与技术文档智能问答系统 — API 接口文档

**文档版本**：v1.1
**编制日期**：2026-07-25
**关联文档**：企业内部规章制度与技术文档智能问答系统 PRD.md (v4.1)

---

## 一、文档约定

### 1.1 接口基址

| 环境 | Java 服务（业务底座） | Python Agent 服务（AI 引擎） |
|------|---------------------|---------------------------|
| 本地开发 | `http://localhost:8080` | `http://localhost:8000` |
| Docker Compose | `http://nginx:80/api` | `http://python-agent:8000`（仅 Java 可达） |

> Python Agent 服务不对前端暴露，仅 Java 后端通过内部网络调用。

### 1.2 通用规范

| 项目 | 规范 |
|------|------|
| 请求体格式 | `application/json`（除文件上传使用 `multipart/form-data`） |
| 响应体格式 | `application/json` |
| 字符编码 | UTF-8 |
| 时间格式 | ISO 8601（`2026-07-20T14:30:12+08:00`） |
| 分页参数 | `page`（从 1 开始）、`size`（默认 20，最大 100） |
| 分页响应 | `{ "content": [...], "totalElements": N, "totalPages": N, "number": N, "size": N }` |
| 认证方式 | JWT Bearer Token（Header: `Authorization: Bearer <token>`） |
| 流式响应 | SSE（`text/event-stream`） |

### 1.3 统一响应结构

**成功响应**：

```json
{
  "code": 200,
  "message": "success",
  "data": { }
}
```

**分页响应**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "content": [],
    "totalElements": 156,
    "totalPages": 8,
    "number": 1,
    "size": 20
  }
}
```

**错误响应**：

```json
{
  "code": 400,
  "message": "用户名已存在",
  "data": null,
  "timestamp": "2026-07-20T14:30:12+08:00"
}
```

### 1.4 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证（Token 无效或过期） |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如用户名重复） |
| 413 | 上传文件过大 |
| 422 | 请求格式正确但参数不符合业务规则 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |
| 503 | 服务暂不可用（降级模式） |

### 1.5 错误码枚举

| 业务码 | 说明 |
|--------|------|
| 200 | 成功 |
| 1001 | 用户名或密码错误 |
| 1002 | 用户名已存在 |
| 1003 | Token 已过期 |
| 1004 | Token 格式错误 |
| 2001 | 文件类型不支持 |
| 2002 | 文件大小超出限制 |
| 2003 | 文档索引失败 |
| 2004 | 文档不存在 |
| 2005 | 文档状态不允许该操作 |
| 3001 | AI 服务不可用 |
| 3002 | AI 响应超时 |
| 3003 | 会话不存在 |
| 4001 | 用户不存在 |
| 4002 | 无权限执行此操作 |
| 5001 | 服务内部错误 |

---

## 二、认证模块 — `/api/auth`

### 2.1 用户注册

```
POST /api/auth/register
```

**请求体**：

```json
{
  "username": "zhangsan",
  "password": "Abc@123456",
  "email": "zhangsan@company.com",
  "department": "技术部"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名，3-50 字符，字母开头 |
| `password` | string | 是 | 密码，8-32 字符，需含大小写字母和数字 |
| `email` | string | 是 | 邮箱地址 |
| `department` | string | 是 | 部门（技术部/HR部/财务部/运维部/市场部） |

**成功响应** (201)：

```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "email": "zhangsan@company.com",
    "department": "技术部",
    "role": "ROLE_EMPLOYEE",
    "createdAt": "2026-07-20T14:30:12+08:00"
  }
}
```

> 新注册用户默认角色为 `ROLE_EMPLOYEE`，需管理员提升权限。

### 2.2 用户登录

```
POST /api/auth/login
```

**请求体**：

```json
{
  "username": "zhangsan",
  "password": "Abc@123456"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名 |
| `password` | string | 是 | 密码 |

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiJ9...",
    "tokenType": "Bearer",
    "expiresIn": 86400,
    "user": {
      "id": 1,
      "username": "zhangsan",
      "email": "zhangsan@company.com",
      "department": "技术部",
      "role": "ROLE_EMPLOYEE"
    }
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `token` | string | JWT Token，后续请求放入 Authorization Header |
| `tokenType` | string | 固定为 "Bearer" |
| `expiresIn` | int | Token 有效期（秒），默认 24 小时 |
| `user.id` | int | 用户 ID |
| `user.role` | string | 角色：`ROLE_EMPLOYEE` / `ROLE_LEADER` / `ROLE_HR` / `ROLE_ADMIN` |

### 2.3 获取当前用户信息

> 用户信息在登录响应中返回，前端存储在 Pinia auth store 中。无独立 `/api/auth/me` 端点。

---

## 三、文档管理模块 — `/api/documents`

### 3.1 上传文档

```
POST /api/documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 文件，支持 pdf/docx/md/txt，最大 20MB |
| `title` | string | 是 | 文档标题，1-200 字符 |
| `department` | string | 是 | 所属部门 |
| `securityLevel` | string | 是 | 密级：`公开` / `内部` / `机密` |
| `tags` | string | 否 | 标签，逗号分隔，如 "API,登录,认证" |

**权限**：所有登录用户

**成功响应** (201)：

```json
{
  "code": 200,
  "message": "上传成功",
  "data": {
    "id": 12,
    "title": "员工手册 v3.2",
    "fileName": "employee_handbook_v3.2.pdf",
    "fileSize": 2048576,
    "fileType": "pdf",
    "department": "HR部",
    "security_level": "公开",
    "status": "UPLOADED",
    "tags": ["制度", "考勤", "休假"],
    "uploadBy": 1,
    "version": 1,
    "createdAt": "2026-07-20T14:30:12+08:00"
  }
}
```

**错误示例**：

```json
{
  "code": 2001,
  "message": "不支持的文件类型，仅支持 PDF、Word、Markdown、TXT",
  "data": null,
  "timestamp": "2026-07-20T14:30:12+08:00"
}
```

### 3.2 文档列表

```
GET /api/documents?page=1&size=20&department=&status=&keyword=
Authorization: Bearer <token>
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码，默认 1 |
| `size` | int | 否 | 每页条数，默认 20 |
| `department` | string | 否 | 按部门筛选 |
| `securityLevel` | string | 否 | 按密级筛选 |
| `status` | string | 否 | 按状态筛选：`UPLOADED` / `INDEXING` / `COMPLETED` / `FAILED` |
| `keyword` | string | 否 | 按标题模糊搜索 |

**权限过滤规则**：

| 角色 | 可见范围 |
|------|---------|
| `ROLE_EMPLOYEE` | `PUBLIC` + 本部门 `INTERNAL` |
| `ROLE_LEADER` | 本部门全部 |
| `ROLE_HR` | `PUBLIC` + `INTERNAL` |
| `ROLE_ADMIN` | 全部 |

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "content": [
      {
        "id": 12,
        "title": "员工手册 v3.2",
        "fileName": "employee_handbook_v3.2.pdf",
        "fileSize": 2048576,
        "fileType": "pdf",
        "department": "HR部",
        "security_level": "公开",
        "status": "COMPLETED",
        "tags": ["制度", "考勤", "休假"],
        "uploadBy": 1,
        "uploadByName": "张三",
        "version": 1,
        "createdAt": "2026-07-20T14:30:12+08:00",
        "updatedAt": "2026-07-20T15:00:00+08:00"
      }
    ],
    "totalElements": 128,
    "totalPages": 7,
    "number": 1,
    "size": 20
  }
}
```

### 3.3 文档详情

```
GET /api/documents/{id}
Authorization: Bearer <token>
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | int | 文档 ID |

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 12,
    "title": "员工手册 v3.2",
    "fileName": "employee_handbook_v3.2.pdf",
    "filePath": "/documents/2026/07/employee_handbook_v3.2.pdf",
    "fileSize": 2048576,
    "fileType": "pdf",
    "department": "HR部",
    "security_level": "公开",
    "status": "COMPLETED",
    "tags": ["制度", "考勤", "休假"],
    "uploadBy": 1,
    "uploadByName": "张三",
    "version": 1,
    "chunkCount": 45,
    "indexedAt": "2026-07-20T15:05:00+08:00",
    "createdAt": "2026-07-20T14:30:12+08:00",
    "updatedAt": "2026-07-20T15:00:00+08:00"
  }
}
```

### 3.4 删除文档

```
DELETE /api/documents/{id}
Authorization: Bearer <token>
```

**权限**：所有登录用户（且仅能删除本部门文档，管理员可删除全部）

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "文档已删除",
  "data": null
}
```

> 删除操作会级联：MinIO 文件 → Qdrant 向量数据 → MySQL 记录。

### 3.5 触发文档索引

```
POST /api/documents/{id}/index
Authorization: Bearer <token>
```

**权限**：所有登录用户

> 仅 `UPLOADED` 或 `FAILED` 状态的文档可触发索引。调用后状态变更为 `INDEXING`，Java 后端异步调用 Python `/api/agent/index`。

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "索引任务已提交",
  "data": {
    "documentId": 12,
    "status": "INDEXING"
  }
}
```

### 3.6 查询索引状态

```
GET /api/documents/status/{id}
Authorization: Bearer <token>
```

> 文档状态可通过 `GET /api/documents/{id}` 的 `status` 字段获取。索引进度通过 WebSocket `/ws/index-progress` 实时推送。

---

## 四、会话管理模块 — `/api/chat/conversations`

会话自动创建（首次发送消息时），无需手动创建。

### 4.1 会话列表

```
GET /api/chat/conversations
Authorization: Bearer <token>
```

> 仅返回当前用户的会话，按更新时间倒序。

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 5,
      "title": "年假政策咨询",
      "createdAt": "2026-07-20T10:15:00",
      "updatedAt": "2026-07-20T14:30:12"
    }
  ]
}
```

### 4.2 会话详情（含消息列表）

```
GET /api/chat/conversations/{id}
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 5,
    "title": "年假政策咨询",
    "messages": [
      {
        "id": 42,
        "role": "user",
        "content": "年假有多少天？",
        "timestamp": "2026-07-20T14:30:12"
      },
      {
        "id": 43,
        "role": "assistant",
        "content": "根据《员工手册》第三章，入职满1年员工享有5天带薪年假。",
        "citations": "[{\"docId\":12,\"title\":\"员工手册 v3.2\"}]",
        "agentSteps": "[{\"type\":\"action\",\"tool\":\"search_policy\"}]",
        "timestamp": "2026-07-20T14:30:14"
      }
    ],
    "createdAt": "2026-07-20T10:15:00",
    "updatedAt": "2026-07-20T14:30:14"
  }
}
```

### 4.3 删除会话

```
DELETE /api/chat/conversations/{id}
Authorization: Bearer <token>
```

> 删除会话会级联删除该会话下的所有消息记录。

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

---

## 五、智能问答模块 — `/api/chat`

### 5.1 SSE 流式对话

```
POST /api/chat/stream
Authorization: Bearer <token>
Accept: text/event-stream
```

**请求体**：

```json
{
  "question": "我下个月想休年假，项目交付来得及吗？",
  "mode": "agent",
  "history": [],
  "conversationId": 5
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | 是 | 用户问题，1-2000 字符 |
| `mode` | string | 否 | 对话模式：`rag`（默认）/ `agent` / `search-only` |
| `history` | array | 否 | 历史对话上下文 `[{role, content}]`，不可为 null（空则传 `[]`） |
| `conversationId` | int | 否 | 会话 ID（首次消息不传，后续传同一个 ID 保持连续） |

**处理流程**：

1. Java 接收请求，验证 JWT，提取用户角色/部门
2. 通过 WebClient 调用 Python `/api/agent/chat/stream`（携带 `X-API-Key`、`X-User-Role`、`X-User-Department` Header）
3. Java 透传 Python 返回的 SSE 流给前端
4. 流结束后 Java 保存 conversation、message 和 audit_log 到 MySQL

**SSE 事件流格式**（仅 `data:` 行，无 `event:` 前缀）：

```
data: {"type":"thought","content":"正在分析问题..."}

data: {"type":"action","content":"执行: search_policy","data":{"tool":"search_policy","args":{"query":"年假天数"}}}

data: {"type":"observation","content":"入职满1年享5天年假，需提前3个工作日申请。"}

data: {"type":"answer","content":"根"}

data: {"type":"answer","content":"据"}

data: {"type":"answer","content":"查询结果，您入职已满1年，享有5天带薪年假。"}

data: {"type":"citation","content":"员工手册 v3.2","data":{"title":"员工手册 v3.2","heading":"第三章 休假制度"}}

data: {"type":"done","content":""}
```

**SSE 事件类型（8 种）**：

| type | 说明 | 模式 | 数据格式 |
|------|------|------|---------|
| `thinking` | RAG 检索步骤 | rag | `{"type":"thinking","content":"正在检索..."}` |
| `answer` | 答案文本（逐 token） | rag/agent | `{"type":"answer","content":"..."}` |
| `citation` | 溯源引用文档 | rag/agent | `{"type":"citation","content":"标题","data":{...}}` |
| `thought` | Agent 开始推理 | agent | `{"type":"thought","content":"正在分析问题..."}` |
| `action` | Agent 工具调用 | agent | `{"type":"action","content":"执行: tool","data":{"tool":"..","args":{...}}}` |
| `observation` | 工具返回结果 | agent | `{"type":"observation","content":"前200字符..."}` |
| `done` | 流结束 | 全部 | `{"type":"done","content":""}` |
| `error` | 异常中断 | 全部 | `{"type":"error","content":"错误信息"}` |

> 实际格式仅有 `data:` 行，无 `event:` 前缀。前端使用 fetch + ReadableStream + AbortController 手动解析（原生 EventSource 仅支持 GET 请求）。

---

> 用户管理模块（`/api/users` CRUD）和系统概览模块（`/api/dashboard`）尚未实现。

---

## 七、审计日志模块 — `/api/audit`（管理员）

### 7.1 审计日志列表

```
GET /api/audit/logs?page=1&size=20&userId=&keyword=&dateFrom=&dateTo=
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码 |
| `size` | int | 否 | 每页条数 |
| `userId` | int | 否 | 按用户 ID 筛选 |
| `keyword` | string | 否 | 按问题/答案内容模糊搜索 |
| `dateFrom` | string | 否 | 起始日期（`YYYY-MM-DD`） |
| `dateTo` | string | 否 | 结束日期（`YYYY-MM-DD`） |

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "content": [
      {
        "id": 1287,
        "userId": 1,
        "username": "张三",
        "department": "技术部",
        "question": "年假有多少天？",
        "answer": "根据《员工手册》第三章，入职满1年员工享有5天带薪年假...",
        "toolsCalled": [
          {"tool": "search_policy", "args": {"query": "年假", "department": "技术部"}}
        ],
        "responseTime": 2300,
        "tokenUsage": {"input": 856, "output": 234},
        "createdAt": "2026-07-20T14:30:12+08:00"
      }
    ],
    "totalElements": 156,
    "totalPages": 8,
    "number": 1,
    "size": 20
  }
}
```

> 审计日志详情（单条）、导出 CSV 功能尚未实现。

---

## 七、WebSocket — `/ws/index-progress`

### 7.1 索引进度推送

```
ws://localhost:8081/ws/index-progress?token=<jwt_token>
```

> WebSocket 运行在 Java Document 服务（端口 8081）。

**连接参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `token` | string | 是 | JWT Token（浏览器 WebSocket 不支持自定义 Header，通过 URL 参数传递） |

**服务端推送消息格式**：

```json
{
  "type": "index_progress",
  "data": {
    "documentId": 12,
    "status": "INDEXING",
    "progress": 65,
    "message": "正在处理第 30/45 个文本块..."
  }
}
```

```json
{
  "type": "index_complete",
  "data": {
    "documentId": 12,
    "status": "COMPLETED",
    "chunkCount": 45
  }
}
```

```json
{
  "type": "index_failed",
  "data": {
    "documentId": 12,
    "status": "FAILED",
    "message": "文件解析异常：PDF 第 5 页乱码"
  }
}
```

| type | 说明 |
|------|------|
| `index_progress` | 索引进度更新 |
| `index_complete` | 索引成功完成 |
| `index_failed` | 索引失败 |

> 前端在文档管理页（P3）建立此 WebSocket 连接，实时更新表格中的状态列和进度。

---

## 八、Python Agent 内部接口 — `/api/agent`

> 以下接口仅供 Java 后端调用，不对外暴露。认证通过 `X-API-Key` Header（默认值：`qa-agent-internal-api-key-2026`）。

### 8.1 请求头规范

| Header | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `X-API-Key` | string | 是 | 内部服务认证密钥 |
| `X-User-Role` | string | 是 | 用户角色（用于密级判断） |
| `X-User-Department` | string | 是 | 用户部门（用于权限过滤） |

### 8.2 流式对话

```
POST /api/agent/chat/stream
X-API-Key: qa-agent-internal-api-key-2026
X-User-Role: ROLE_EMPLOYEE
X-User-Department: 技术部
Content-Type: application/json
```

**请求体**：

```json
{
  "question": "我下个月想休年假，项目交付来得及吗？",
  "mode": "agent",
  "history": [
    {"role": "user", "content": "年假有多少天？"},
    {"role": "assistant", "content": "入职满1年员工享有5天带薪年假。"}
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | 是 | 用户当前问题 |
| `mode` | string | 否 | 对话模式：`rag`（默认）/ `agent` / `search-only` |
| `history` | array | 否 | 历史对话上下文（空则传 `[]`，不可为 null） |

**响应**：SSE 流（格式同 5.1 节，8 种事件类型）。

### 8.3 文档索引

```
POST /api/agent/index
X-API-Key: <internal_key>
X-Trace-Id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**请求体**：

```json
{
  "document": {
    "id": 12,
    "title": "员工手册 v3.2",
    "file_path": "/documents/2026/07/employee_handbook_v3.2.pdf",
    "file_type": "pdf",
    "department": "HR部",
    "security_level": "公开"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `document.id` | int | 是 | 文档 ID（对应 MySQL doc_document 记录） |
| `document.title` | string | 是 | 文档标题 |
| `document.file_path` | string | 是 | MinIO 文件路径 |
| `document.file_type` | string | 是 | 文件类型（pdf/docx/md/txt） |
| `document.department` | string | 是 | 所属部门（写入 chunk payload） |
| `document.security_level` | string | 是 | 密级（公开/内部/机密） |

**处理流程**：

1. 从 MinIO 下载文件
2. 根据 `file_type` 选择对应的 DocumentLoader 和 TextSplitter
3. 分块 + Embedding 向量化（三级降级策略）
4. 写入 Qdrant（vector + payload: doc_id/title/department/security_level/chunk_index）
5. 回调 Java 更新文档状态

**成功响应** (200)：

```json
{
  "success": true,
  "document_id": 12,
  "chunk_count": 45,
  "message": "索引完成"
}
```

**失败响应**：

```json
{
  "success": false,
  "document_id": 12,
  "error": "PDF 解析失败：文件损坏或加密",
  "message": "索引失败"
}
```

### 8.4 删除文档索引

```
DELETE /api/agent/index/{doc_id}
X-API-Key: <internal_key>
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `doc_id` | int | 文档 ID |

**成功响应** (200)：

```json
{
  "status": "deleted",
  "doc_id": 12
}
```

> 通过 Qdrant payload filter 匹配 `doc_id`，批量删除对应所有 chunk。

### 8.5 健康检查

```
GET /api/agent/health
```

**成功响应** (200)：

```json
{
  "status": "ok",
  "service": "qa-agent-python"
}
```

> 不要求 `X-API-Key`，供 Nginx 健康检查和 Java 侧连通性检测。

---

## 九、数据模型汇总

### 11.1 枚举值定义

| 枚举类型 | 可选值 |
|----------|--------|
| `UserRole` | `ROLE_EMPLOYEE`、`ROLE_LEADER`、`ROLE_HR`、`ROLE_ADMIN` |
| `Department` | `技术部`、`HR部`、`财务部`、`运维部`、`市场部` |
| `SecurityLevel` | `PUBLIC`（公开）、`INTERNAL`（内部）、`CONFIDENTIAL`（机密） |
| `DocumentStatus` | `UPLOADED`、`INDEXING`、`COMPLETED`、`FAILED` |
| `AgentMode` | `agent`（Agent 规划）、`rag`（纯 RAG）、`search-only`（仅检索） |

### 11.2 分页请求参数（通用）

| 参数 | 位置 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | Query | int | 1 | 页码，从 1 开始 |
| `size` | Query | int | 20 | 每页条数，最大 100 |
| `sort` | Query | string | `createdAt,desc` | 排序字段与方向 |

### 11.3 JWT Token Payload 结构

```json
{
  "sub": "1",
  "username": "zhangsan",
  "role": "ROLE_EMPLOYEE",
  "department": "技术部",
  "iat": 1753000212,
  "exp": 1753086612
}
```

---

## 十、接口调用链路

### 12.1 问答链路（核心）

```
前端 POST /api/chat/stream ──────────────────────────────────────┐
    │                                                              │
    ▼                                                              │
Java ChatController                                               │
    ├── 1. JWT 认证 → 提取 userId/role/department                   │
    ├── 2. 保存 user message → MySQL                               │
    ├── 3. WebClient → Python POST /api/agent/chat/stream           │
    │       ├── Header: X-API-Key, X-User-Role, X-User-Department  │
    │       └── Body: { question, mode, history }                  │
    │                                                              │
    ▼                                                              │
Python Agent (LangGraph)                                          │
    ├── 4. ReAct 循环: Thought → Action → Observation              │
    │       ├── search_policy / search_doc → Qdrant               │
    │       └── Qdrant filter: { department, security_level }      │
    ├── 5. LLM 生成（Prompt 工程约束反幻觉）                      │
    └── 6. SSE 流式返回 ──────────────────────────────────────┐    │
    │                                                          │    │
    ▼                                                          │    │
Java 透传 SSE → 前端逐字渲染                                    │    │
    │                                                          │    │
    ▼                                                          │    │
Java 保存 answer + audit_log → MySQL                          │    │
    └──────────────────────────────────────────────────────────┘────┘
```

### 12.2 文档索引链路

```
前端 POST /api/documents/{id}/index
    │
    ▼
Java DocumentController
    ├── 1. 校验文档状态 (UPLOADED / FAILED)
    ├── 2. 更新状态为 INDEXING
    ├── 3. @Async 异步调用
    │       └── WebClient → Python POST /api/agent/index
    │             ├── Body: { document_id, file_path, file_type, metadata }
    │             └── Python: DocumentLoader → TextSplitter → Embedding → Qdrant
    │
    ▼
Python 回调 / WebSocket 推送
    ├── 成功: 更新状态 COMPLETED + chunk_count
    └── 失败: 更新状态 FAILED + error_message
```

---

## 十一、安全规范

| 规范项 | 实现方式 |
|--------|---------|
| **传输安全** | 生产环境强制 HTTPS；开发环境允许 HTTP |
| **认证** | JWT Bearer Token，过期时间 24h |
| **Java→Python 认证** | `X-API-Key` 预共享密钥（环境变量 `AGENT_INTERNAL_API_KEY`） |
| **密码存储** | bcrypt 哈希（cost=12） |
| **密码规则** | 8-32 字符，至少含大写字母、小写字母、数字 |
| **文件上传** | 类型白名单 + 大小限制 20MB + 病毒扫描（可选） |
| **SQL 注入** | Spring Data JPA 参数化查询 |
| **XSS** | 前端输出转义 + Content-Security-Policy Header |
| **CORS** | 仅允许前端域名跨域 |
| **频率限制** | 登录接口：5 次/分钟；问答接口：30 次/分钟（基于 IP + userId） |
| **敏感数据** | 审计日志中的问题/答案不脱敏（内部系统），密码绝不输出到日志 |
| **日志安全** | 日志中不记录 Token、密码等敏感信息；输出 `X-Trace-Id` 用于链路追踪 |

---

## 十二、接口索引

| 序号 | 方法 | 路径 | 说明 | 认证 | 权限 |
|------|------|------|------|------|------|
| 1 | POST | `/api/auth/register` | 用户注册 | 否 | — |
| 2 | POST | `/api/auth/login` | 用户登录 | 否 | — |
| 3 | POST | `/api/documents/upload` | 上传文档 | JWT | 所有登录用户 |
| 4 | GET | `/api/documents` | 文档列表 | JWT | 所有登录用户 |
| 5 | GET | `/api/documents/{id}` | 文档详情 | JWT | 所有登录用户 |
| 6 | DELETE | `/api/documents/{id}` | 删除文档 | JWT | 所有登录用户 |
| 7 | POST | `/api/documents/{id}/index` | 触发索引 | JWT | 所有登录用户 |
| 8 | GET | `/api/documents/status/{id}` | 索引状态 | JWT | 所有登录用户 |
| 9 | POST | `/api/chat/stream` | SSE 流式对话 | JWT | 所有登录用户 |
| 10 | GET | `/api/chat/conversations` | 会话列表 | JWT | 所有登录用户 |
| 11 | GET | `/api/chat/conversations/{id}` | 会话详情（含消息） | JWT | 所有登录用户 |
| 12 | DELETE | `/api/chat/conversations/{id}` | 删除会话 | JWT | 所有登录用户 |
| 13 | GET | `/api/audit/logs` | 审计日志列表 | JWT | Admin |
| 14 | WS | `/ws/index-progress` | 索引进度推送 | JWT | 所有登录用户 |

**Python 内部接口**：

| 序号 | 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|------|
| 15 | POST | `/api/agent/chat/stream` | SSE 流式对话（支持 rag/agent/search-only） | X-API-Key |
| 16 | POST | `/api/agent/index` | 文档索引 | X-API-Key |
| 17 | DELETE | `/api/agent/index/{doc_id}` | 删除文档向量 | X-API-Key |
| 18 | GET | `/api/agent/health` | 健康检查 | 否 |

---

## 十三、附录：SSE 流式响应完整示例

以下为 Agent 模式完整的 SSE 流（从 `POST /api/chat/stream` 到前端接收），模拟用户问题："Who is responsible for the tech department?"

```
<<< HTTP/1.1 200 OK
<<< Content-Type: text/event-stream
<<< Cache-Control: no-cache
<<< Connection: keep-alive
<<<

data: {"type":"thought","content":"正在分析问题..."}

data: {"type":"action","content":"执行: search_employee","data":{"tool":"search_employee","args":{"query":"技术部负责人"}}}

data: {"type":"observation","content":"未找到相关人员信息。"}

data: {"type":"action","content":"执行: search_employee","data":{"tool":"search_employee","args":{"query":"技术部"}}}

data: {"type":"observation","content":"未找到相关人员信息。"}

data: {"type":"answer","content":"抱歉，我目前无法准确回答这个问题。"}

data: {"type":"answer","content":"经过多次尝试搜索，系统中均未返回相关人员信息。"}

data: {"type":"done","content":""}
```

> 实际格式仅有 `data:` 行，无 `event:` 前缀。`answer` 事件中的 content 为单字符逐 token 输出。

---

**文档结束**
