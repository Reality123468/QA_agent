# 企业内部规章制度与技术文档智能问答系统 — API 接口文档

**文档版本**：v1.0
**编制日期**：2026-07-20
**关联文档**：企业内部规章制度与技术文档智能问答系统 PRD.md (v4.0)、页面清单与原型设计.md (v1.0)

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

### 2.3 用户登出

```
POST /api/auth/logout
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "已登出",
  "data": null
}
```

> 服务端将 Token 加入黑名单（Redis 缓存或内存 Set，TTL 与 Token 剩余有效期一致）。

### 2.4 获取当前用户信息

```
GET /api/auth/me
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
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
| `securityLevel` | string | 是 | 密级：`PUBLIC` / `INTERNAL` / `CONFIDENTIAL` |
| `tags` | string | 否 | 标签，逗号分隔，如 "API,登录,认证" |

**权限**：`ROLE_HR`、`ROLE_ADMIN`

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
    "securityLevel": "PUBLIC",
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
        "securityLevel": "PUBLIC",
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
    "securityLevel": "PUBLIC",
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

**权限**：`ROLE_HR`、`ROLE_ADMIN`（且仅能删除本部门文档，管理员可删除全部）

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

**权限**：`ROLE_HR`、`ROLE_ADMIN`

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
GET /api/documents/{id}/status
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "documentId": 12,
    "status": "INDEXING",
    "progress": 65,
    "message": "正在处理第 30/45 个文本块..."
  }
}
```

| status | 说明 |
|--------|------|
| `UPLOADED` | 已上传，未索引 |
| `INDEXING` | 索引进行中 |
| `COMPLETED` | 索引完成 |
| `FAILED` | 索引失败 |

### 3.7 预览文件

```
GET /api/documents/{id}/preview
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "documentId": 12,
    "fileName": "employee_handbook_v3.2.pdf",
    "fileType": "pdf",
    "previewUrl": "http://localhost:9000/documents/2026/07/employee_handbook_v3.2.pdf?token=xxx"
  }
}
```

> `previewUrl` 为 MinIO 预签名 URL，有效期 15 分钟。

---

## 四、会话管理模块 — `/api/sessions`

### 4.1 会话列表

```
GET /api/sessions?page=1&size=20
Authorization: Bearer <token>
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码，默认 1 |
| `size` | int | 否 | 每页条数，默认 20 |

> 仅返回当前用户的会话，按最后活跃时间倒序。

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "content": [
      {
        "id": 5,
        "title": "年假政策咨询",
        "messageCount": 6,
        "lastQuestion": "年假可以累计到下一年吗？",
        "lastActiveAt": "2026-07-20T14:30:12+08:00",
        "createdAt": "2026-07-20T10:15:00+08:00"
      },
      {
        "id": 4,
        "title": "接口文档查询",
        "messageCount": 4,
        "lastQuestion": "登录接口返回401是什么原因？",
        "lastActiveAt": "2026-07-20T11:15:00+08:00",
        "createdAt": "2026-07-20T11:10:00+08:00"
      }
    ],
    "totalElements": 12,
    "totalPages": 1,
    "number": 1,
    "size": 20
  }
}
```

### 4.2 创建会话

```
POST /api/sessions
Authorization: Bearer <token>
```

**请求体**：

```json
{
  "title": "新会话"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 否 | 会话标题，默认"新会话"，可后续修改 |

**成功响应** (201)：

```json
{
  "code": 200,
  "message": "创建成功",
  "data": {
    "id": 6,
    "title": "新会话",
    "messageCount": 0,
    "lastActiveAt": "2026-07-20T14:35:00+08:00",
    "createdAt": "2026-07-20T14:35:00+08:00"
  }
}
```

### 4.3 重命名会话

```
PUT /api/sessions/{id}
Authorization: Bearer <token>
```

**请求体**：

```json
{
  "title": "报销流程咨询"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 新标题，1-50 字符 |

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "重命名成功",
  "data": null
}
```

### 4.4 删除会话

```
DELETE /api/sessions/{id}
Authorization: Bearer <token>
```

> 删除会话会级联删除该会话下的所有消息记录。

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "会话已删除",
  "data": null
}
```

### 4.5 会话消息列表

```
GET /api/sessions/{id}/messages
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 42,
      "sessionId": 5,
      "role": "user",
      "content": "年假有多少天？",
      "createdAt": "2026-07-20T14:30:12+08:00"
    },
    {
      "id": 43,
      "sessionId": 5,
      "role": "assistant",
      "content": "根据《员工手册》第三章，入职满1年员工享有5天带薪年假。",
      "agentThoughts": [
        {"type": "thought", "content": "用户询问年假政策，需要检索规章制度"},
        {"type": "action", "tool": "search_policy", "args": {"query": "年假", "department": "技术部"}},
        {"type": "observation", "content": "检索到3条相关文档片段"}
      ],
      "citations": [
        {"docId": 12, "title": "员工手册 v3.2", "heading": "第三章 休假制度", "snippet": "入职满1年员工享有5天带薪年假..."},
        {"docId": 15, "title": "考勤管理办法 v1.0", "heading": "第四条 年假计算", "snippet": "年假天数按自然年计算..."}
      ],
      "responseTime": 2300,
      "tokenUsage": {"input": 856, "output": 234},
      "createdAt": "2026-07-20T14:30:14+08:00"
    }
  ]
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
  "sessionId": 5,
  "question": "我下个月想休年假，项目交付来得及吗？"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sessionId` | int | 是 | 会话 ID（需先调用创建会话接口获取） |
| `question` | string | 是 | 用户问题，1-2000 字符 |

**处理流程**：

1. Java 接收请求，验证 JWT，提取用户角色/部门
2. 保存用户消息到数据库
3. 通过 WebClient 调用 Python Agent（携带 `X-User-Role`、`X-User-Department` 等 Header）
4. Java 透传 Python 返回的 SSE 流给前端
5. 流结束后保存完整回答到数据库

**SSE 事件流格式**：

```
event: thought
data: {"type":"thought","content":"用户想了解年假政策，同时关心项目排期。我需要同时查询两方面信息。"}

event: action
data: {"type":"action","tool":"search_policy","args":{"query":"年假天数 申请条件"}}

event: observation
data: {"type":"observation","content":"「员工手册」入职满1年享5天年假，需提前3个工作日申请。"}

event: action
data: {"type":"action","tool":"search_doc","args":{"query":"项目交付排期 Q3"}}

event: observation
data: {"type":"observation","content":"「项目排期表 v2」Q3里程碑为9月30日，当前进度正常，无延期风险。"}

event: answer_chunk
data: {"type":"answer_chunk","content":"根据查询结果，"}

event: answer_chunk
data: {"type":"answer_chunk","content":"您入职已满1年，享有5天带薪年假。"}

event: answer_chunk
data: {"type":"answer_chunk","content":"目前Q3项目排期正常，如果您在8月中旬前休假，不影响项目交付。"}

event: citation
data: {"type":"citation","docId":12,"title":"员工手册 v3.2","heading":"第三章 休假制度","snippet":"入职满1年员工享有5天带薪年假，需提前3个工作日向直属主管提交申请。"}

event: citation
data: {"type":"citation","docId":28,"title":"Q3项目排期表 v2","heading":"里程碑概览","snippet":"9月30日：Q3版本正式交付。当前进度102%，无延期风险。"}

event: done
data: {"type":"done","responseTime":3200,"tokenUsage":{"input":1245,"output":356}}
```

**SSE 事件类型说明**：

| event | 说明 | 前端行为 |
|-------|------|---------|
| `thought` | Agent 推理思考 | 显示在可折叠的思考面板中 |
| `action` | Agent 调用工具 | 显示工具名称和参数 |
| `observation` | 工具返回结果 | 显示检索结果摘要 |
| `answer_chunk` | 答案片段（逐 token） | 逐字追加到回答区域 |
| `citation` | 引用来源 | 追加到回答下方的引用列表 |
| `done` | 流结束 | 停止加载动画，统计展示耗时和 Token |
| `error` | 异常中断 | 显示错误信息 + 已输出部分内容 |

**error 事件示例**：

```
event: error
data: {"type":"error","code":3002,"message":"AI 响应超时，请简化问题后重试","partialAnswer":"根据《员工手册》第三章..."}
```

### 5.2 对话历史列表

```
GET /api/chat/history?page=1&size=20&keyword=&dateFrom=&dateTo=
Authorization: Bearer <token>
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码，默认 1 |
| `size` | int | 否 | 每页条数，默认 20 |
| `keyword` | string | 否 | 按问题或答案内容模糊搜索 |
| `dateFrom` | string | 否 | 起始日期，ISO 8601 格式 |
| `dateTo` | string | 否 | 结束日期，ISO 8601 格式 |

> 普通用户仅返回自己的对话记录；管理员可查看全部。

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "content": [
      {
        "sessionId": 5,
        "sessionTitle": "年假政策咨询",
        "messageCount": 6,
        "lastQuestion": "年假可以累计到下一年吗？",
        "lastActiveAt": "2026-07-20T14:30:12+08:00",
        "createdAt": "2026-07-20T10:15:00+08:00"
      }
    ],
    "totalElements": 12,
    "totalPages": 1,
    "number": 1,
    "size": 20
  }
}
```

> 此接口与 `GET /api/sessions` 返回结构相似，增加了 `keyword`、`dateFrom`、`dateTo` 筛选维度。前端 P4（对话历史页）使用此接口替代 sessions 列表。

### 5.3 对话历史详情

```
GET /api/chat/history/{sessionId}
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "sessionId": 5,
    "sessionTitle": "年假政策咨询",
    "messages": [
      {
        "id": 42,
        "role": "user",
        "content": "年假有多少天？",
        "createdAt": "2026-07-20T14:30:12+08:00"
      },
      {
        "id": 43,
        "role": "assistant",
        "content": "根据《员工手册》第三章，入职满1年员工享有5天带薪年假。",
        "citations": [
          {"docId": 12, "title": "员工手册 v3.2", "heading": "第三章 休假制度"}
        ],
        "responseTime": 2300,
        "createdAt": "2026-07-20T14:30:14+08:00"
      }
    ],
    "createdAt": "2026-07-20T10:15:00+08:00"
  }
}
```

---

## 六、用户管理模块 — `/api/users`（管理员）

### 6.1 用户列表

```
GET /api/users?page=1&size=20&keyword=&role=&department=
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码 |
| `size` | int | 否 | 每页条数 |
| `keyword` | string | 否 | 按用户名或邮箱模糊搜索 |
| `role` | string | 否 | 按角色筛选 |
| `department` | string | 否 | 按部门筛选 |

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "content": [
      {
        "id": 1,
        "username": "zhangsan",
        "email": "zhangsan@company.com",
        "department": "技术部",
        "role": "ROLE_EMPLOYEE",
        "enabled": true,
        "createdAt": "2026-07-20T14:30:12+08:00"
      }
    ],
    "totalElements": 45,
    "totalPages": 3,
    "number": 1,
    "size": 20
  }
}
```

### 6.2 创建用户

```
POST /api/users
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

**请求体**：

```json
{
  "username": "wangwu",
  "password": "Ww@123456",
  "email": "wangwu@company.com",
  "department": "财务部",
  "role": "ROLE_EMPLOYEE"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名 |
| `password` | string | 是 | 密码 |
| `email` | string | 是 | 邮箱 |
| `department` | string | 是 | 部门 |
| `role` | string | 是 | 角色 |

**成功响应** (201)：

```json
{
  "code": 200,
  "message": "用户创建成功",
  "data": {
    "id": 46,
    "username": "wangwu",
    "email": "wangwu@company.com",
    "department": "财务部",
    "role": "ROLE_EMPLOYEE",
    "createdAt": "2026-07-20T14:40:00+08:00"
  }
}
```

### 6.3 更新用户

```
PUT /api/users/{id}
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

**请求体**：

```json
{
  "email": "wangwu_new@company.com",
  "department": "技术部",
  "role": "ROLE_LEADER"
}
```

> 所有字段均为可选，仅更新传入的字段。`username` 不可修改。

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "用户信息已更新",
  "data": {
    "id": 46,
    "username": "wangwu",
    "email": "wangwu_new@company.com",
    "department": "技术部",
    "role": "ROLE_LEADER"
  }
}
```

### 6.4 删除用户

```
DELETE /api/users/{id}
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

> 管理员账户（`ROLE_ADMIN`）不可删除自己。

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "用户已删除",
  "data": null
}
```

### 6.5 重置密码

```
PUT /api/users/{id}/password
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

**请求体**：

```json
{
  "newPassword": "NewPass@123"
}
```

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "密码已重置",
  "data": null
}
```

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

### 7.2 审计日志详情

```
GET /api/audit/logs/{id}
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1287,
    "userId": 1,
    "username": "张三",
    "email": "zhangsan@company.com",
    "department": "技术部",
    "role": "ROLE_EMPLOYEE",
    "sessionId": 5,
    "question": "年假有多少天？",
    "answer": "根据《员工手册》第三章，入职满1年员工享有5天带薪年假。年假需提前3个工作日申请。",
    "toolsCalled": [
      {"tool": "search_policy", "args": {"query": "年假", "department": "技术部"}, "result": "检索到3条相关文档"}
    ],
    "citations": [
      {"docId": 12, "title": "员工手册 v3.2", "heading": "第三章 休假制度"}
    ],
    "responseTime": 2300,
    "tokenUsage": {"input": 856, "output": 234},
    "mode": "agent",
    "createdAt": "2026-07-20T14:30:12+08:00"
  }
}
```

### 7.3 导出审计日志

```
GET /api/audit/logs/export?userId=&keyword=&dateFrom=&dateTo=
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

**响应**：`Content-Type: text/csv`，返回 CSV 文件下载。

**查询参数**：同 7.1 审计日志列表的筛选参数（不含分页）。

**CSV 列**：

```
ID,用户,部门,问题,回答,工具调用,响应耗时(ms),Token输入,Token输出,时间
```

---

## 八、系统概览模块 — `/api/dashboard`（管理员）

### 8.1 统计数据

```
GET /api/dashboard/stats
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "documentCount": 128,
    "userCount": 45,
    "todayQuestionCount": 237,
    "avgResponseTime": 2.3,
    "trends": [
      {"date": "2026-07-14", "count": 185},
      {"date": "2026-07-15", "count": 210},
      {"date": "2026-07-16", "count": 198},
      {"date": "2026-07-17", "count": 225},
      {"date": "2026-07-18", "count": 203},
      {"date": "2026-07-19", "count": 240},
      {"date": "2026-07-20", "count": 237}
    ]
  }
}
```

| 字段 | 来源 | 说明 |
|------|------|------|
| `documentCount` | `doc_document` COUNT | 全部文档总数 |
| `userCount` | `sys_user` COUNT | 全部用户总数 |
| `todayQuestionCount` | `audit_log` WHERE created_at=today | 今日问答总量 |
| `avgResponseTime` | `audit_log` AVG(response_time) WHERE created_at=today | 今日平均响应耗时（秒） |
| `trends` | `audit_log` GROUP BY DATE 近7天 | 每日问答量趋势 |

### 8.2 服务健康状态

```
GET /api/dashboard/health
Authorization: Bearer <token>
```

**权限**：`ROLE_ADMIN`

**成功响应** (200)：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "services": [
      {"name": "Python Agent", "status": "UP", "responseTime": 12, "detail": "FastAPI 0.128.0"},
      {"name": "MySQL", "status": "UP", "responseTime": 3, "detail": "8.0.36"},
      {"name": "Qdrant", "status": "UP", "responseTime": 8, "detail": "v1.10.1, 12850 vectors"},
      {"name": "MinIO", "status": "UP", "responseTime": 15, "detail": "2024-01-01, 2.3GB used"},
      {"name": "Redis", "status": "DOWN", "responseTime": null, "detail": "未启用（MVP阶段可选）"},
      {"name": "LLM API", "status": "DEGRADED", "responseTime": 350, "detail": "DeepSeek-V3, 延迟偏高"}
    ],
    "checkedAt": "2026-07-20T14:30:12+08:00"
  }
}
```

| status | 说明 |
|--------|------|
| `UP` | 正常 |
| `DEGRADED` | 降级（可用但延迟偏高） |
| `DOWN` | 不可用 |

> 此接口会实时探测各个依赖服务的连通性（HTTP ping / TCP connect），前端每 30 秒轮询一次。

---

## 九、WebSocket — `/ws/progress`

### 9.1 索引进度推送

```
ws://localhost:8080/ws/progress?token=<jwt_token>
```

**连接参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `token` | string | 是 | JWT Token（通过查询参数传递，浏览器 WebSocket 不支持自定义 Header） |

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

## 十、Python Agent 内部接口 — `/api/agent`

> 以下接口仅供 Java 后端调用，不对外暴露。认证通过 `X-API-Key` Header 进行。

### 10.1 请求头规范

所有 Java → Python 请求均需携带以下 Header：

| Header | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `X-API-Key` | string | 是 | 内部服务认证密钥（环境变量注入） |
| `X-User-Id` | int | 是 | 当前用户 ID |
| `X-User-Role` | string | 是 | 用户角色 |
| `X-User-Department` | string | 是 | 用户部门 |
| `X-Session-Id` | string | 是（对话接口） | 会话 ID |
| `X-Trace-Id` | string | 是 | 链路追踪 ID（UUID，贯穿 Java→Python） |

### 10.2 流式对话

```
POST /api/agent/chat
X-API-Key: <internal_key>
X-User-Id: 1
X-User-Role: ROLE_EMPLOYEE
X-User-Department: 技术部
X-Session-Id: 5
X-Trace-Id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Accept: text/event-stream
```

**请求体**：

```json
{
  "question": "我下个月想休年假，项目交付来得及吗？",
  "history": [
    {"role": "user", "content": "年假有多少天？"},
    {"role": "assistant", "content": "入职满1年员工享有5天带薪年假。"}
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | 是 | 用户当前问题 |
| `history` | array | 否 | 历史对话上下文，最多保留最近 10 轮 |

**响应**：SSE 流（格式同 5.1 节）。

### 10.3 同步对话

```
POST /api/agent/chat/sync
X-API-Key: <internal_key>
[其他认证头同 10.2]
```

**请求体**：同 10.2。

**成功响应** (200)：

```json
{
  "answer": "根据《员工手册》第三章，入职满1年员工享有5天带薪年假...",
  "citations": [
    {"doc_id": 12, "title": "员工手册 v3.2", "heading": "第三章 休假制度", "snippet": "..."}
  ],
  "tools_called": [
    {"tool": "search_policy", "args": {"query": "年假", "department": "技术部"}}
  ],
  "response_time": 3200,
  "token_usage": {"input": 1245, "output": 356}
}
```

> 同步接口用于降级到纯 RAG 模式或批量评估场景，不用于正常用户交互。

### 10.4 文档索引

```
POST /api/agent/index
X-API-Key: <internal_key>
X-Trace-Id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**请求体**：

```json
{
  "document_id": 12,
  "file_path": "/documents/2026/07/employee_handbook_v3.2.pdf",
  "file_type": "pdf",
  "metadata": {
    "title": "员工手册 v3.2",
    "department": "HR部",
    "security_level": "PUBLIC",
    "uploaded_by": "张三"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `document_id` | int | 是 | 文档 ID（对应 MySQL 记录） |
| `file_path` | string | 是 | MinIO 文件路径，Python 侧通过 MinIO SDK 读取 |
| `file_type` | string | 是 | 文件类型（pdf/docx/md/txt），决定分块策略 |
| `metadata.title` | string | 是 | 文档标题 |
| `metadata.department` | string | 是 | 所属部门（写入 chunk payload 用于权限过滤） |
| `metadata.security_level` | string | 是 | 密级：PUBLIC / INTERNAL / CONFIDENTIAL |

**处理流程**：

1. 从 MinIO 下载文件
2. 根据 `file_type` 选择对应的 DocumentLoader 和 TextSplitter
3. 分块 + BGE-M3 Embedding
4. 写入 Qdrant（稠密向量 + 稀疏向量 + payload 元数据）
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

### 10.5 删除文档索引

```
DELETE /api/agent/index/{document_id}
X-API-Key: <internal_key>
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `document_id` | int | 文档 ID |

**成功响应** (200)：

```json
{
  "success": true,
  "document_id": 12,
  "deleted_chunks": 45,
  "message": "索引已删除"
}
```

> 通过 Qdrant payload filter 匹配 `doc_id`，批量删除对应所有 chunk。

### 10.6 健康检查

```
GET /api/agent/health
```

**成功响应** (200)：

```json
{
  "status": "healthy",
  "version": "0.128.0",
  "checks": {
    "qdrant": "connected",
    "qdrant_vectors": 12850,
    "llm_api": "reachable",
    "embedding_model": "BAAI/bge-m3",
    "reranker_model": "BAAI/bge-reranker-v2-m3"
  },
  "timestamp": "2026-07-20T14:30:12+08:00"
}
```

> 此接口不要求 `X-API-Key`，供 Nginx 健康检查和 Java Dashboard 调用。

---

## 十一、数据模型汇总

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

## 十二、接口调用链路

### 12.1 问答链路（核心）

```
前端 POST /api/chat/stream ──────────────────────────────────────┐
    │                                                              │
    ▼                                                              │
Java ChatController                                               │
    ├── 1. JWT 认证 → 提取 userId/role/department                   │
    ├── 2. 保存 user message → MySQL                               │
    ├── 3. WebClient → Python POST /api/agent/chat                 │
    │       ├── Header: X-API-Key, X-User-Role, X-User-Department  │
    │       └── Body: { question, history }                        │
    │                                                              │
    ▼                                                              │
Python Agent (LangGraph)                                          │
    ├── 4. ReAct 循环: Thought → Action → Observation              │
    │       ├── search_policy / search_doc → Qdrant               │
    │       └── Qdrant filter: { department, security_level }      │
    ├── 5. LLM 生成 + Rerank                                      │
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

## 十三、安全规范

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

## 十四、接口索引

| 序号 | 方法 | 路径 | 说明 | 认证 | 权限 |
|------|------|------|------|------|------|
| 1 | POST | `/api/auth/register` | 用户注册 | 否 | — |
| 2 | POST | `/api/auth/login` | 用户登录 | 否 | — |
| 3 | POST | `/api/auth/logout` | 用户登出 | JWT | 登录用户 |
| 4 | GET | `/api/auth/me` | 当前用户信息 | JWT | 登录用户 |
| 5 | POST | `/api/documents/upload` | 上传文档 | JWT | HR/Admin |
| 6 | GET | `/api/documents` | 文档列表 | JWT | 登录用户 |
| 7 | GET | `/api/documents/{id}` | 文档详情 | JWT | 登录用户 |
| 8 | DELETE | `/api/documents/{id}` | 删除文档 | JWT | HR/Admin |
| 9 | POST | `/api/documents/{id}/index` | 触发索引 | JWT | HR/Admin |
| 10 | GET | `/api/documents/{id}/status` | 索引状态 | JWT | 登录用户 |
| 11 | GET | `/api/documents/{id}/preview` | 预览文件 | JWT | 登录用户 |
| 12 | GET | `/api/sessions` | 会话列表 | JWT | 登录用户 |
| 13 | POST | `/api/sessions` | 创建会话 | JWT | 登录用户 |
| 14 | PUT | `/api/sessions/{id}` | 重命名会话 | JWT | 登录用户 |
| 15 | DELETE | `/api/sessions/{id}` | 删除会话 | JWT | 登录用户 |
| 16 | GET | `/api/sessions/{id}/messages` | 会话消息 | JWT | 登录用户 |
| 17 | POST | `/api/chat/stream` | SSE 流式对话 | JWT | 登录用户 |
| 18 | GET | `/api/chat/history` | 对话历史列表 | JWT | 登录用户 |
| 19 | GET | `/api/chat/history/{sessionId}` | 对话历史详情 | JWT | 登录用户 |
| 20 | GET | `/api/users` | 用户列表 | JWT | Admin |
| 21 | POST | `/api/users` | 创建用户 | JWT | Admin |
| 22 | PUT | `/api/users/{id}` | 更新用户 | JWT | Admin |
| 23 | DELETE | `/api/users/{id}` | 删除用户 | JWT | Admin |
| 24 | PUT | `/api/users/{id}/password` | 重置密码 | JWT | Admin |
| 25 | GET | `/api/audit/logs` | 审计日志列表 | JWT | Admin |
| 26 | GET | `/api/audit/logs/{id}` | 审计日志详情 | JWT | Admin |
| 27 | GET | `/api/audit/logs/export` | 导出审计 CSV | JWT | Admin |
| 28 | GET | `/api/dashboard/stats` | 统计数据 | JWT | Admin |
| 29 | GET | `/api/dashboard/health` | 服务健康 | JWT | Admin |
| 30 | WS | `/ws/progress` | 索引进度推送 | JWT | 登录用户 |

**Python 内部接口**：

| 序号 | 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|------|
| 31 | POST | `/api/agent/chat` | 流式对话（SSE） | X-API-Key |
| 32 | POST | `/api/agent/chat/sync` | 同步对话 | X-API-Key |
| 33 | POST | `/api/agent/index` | 文档索引 | X-API-Key |
| 34 | DELETE | `/api/agent/index/{document_id}` | 删除索引 | X-API-Key |
| 35 | GET | `/api/agent/health` | 健康检查 | 否 |

---

## 十五、附录：SSE 流式响应完整示例

以下为一个完整的 SSE 流式对话响应示例（从 `POST /api/chat/stream` 到前端接收），模拟用户问题："我下个月想休年假，项目交付来得及吗？"

```
<<< HTTP/1.1 200 OK
<<< Content-Type: text/event-stream
<<< Cache-Control: no-cache
<<< Connection: keep-alive
<<< X-Trace-Id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
<<< X-Session-Id: 5
<<<

event: thought
data: {"type":"thought","content":"用户想了解年假政策并评估项目排期。我需要：1) 查询年假政策；2) 查询当前项目排期。"}

event: action
data: {"type":"action","tool":"search_policy","args":{"query":"年假天数 申请条件"}}

event: observation
data: {"type":"observation","content":"「员工手册 v3.2」第三章：入职满1年享5天年假，需提前3个工作日申请。\n「考勤管理办法 v1.0」第四条：年假按自然年计算，不跨年累计。"}

event: thought
data: {"type":"thought","content":"已获取年假政策。现在需要查看项目排期以评估是否有时间冲突。"}

event: action
data: {"type":"action","tool":"search_doc","args":{"query":"Q3项目排期 里程碑 交付日期"}}

event: observation
data: {"type":"observation","content":"「Q3项目排期表 v2」：9月30日Q3正式交付。当前进度102%，无延期风险。\n本周迭代：7月21日-7月25日，Sprint 12，功能模块X。"}

event: thought
data: {"type":"thought","content":"综合信息：年假5天可用，项目排期正常。建议用户在8月中旬前休假不影响交付。"}

event: answer_chunk
data: {"type":"answer_chunk","content":"根据"}

event: answer_chunk
data: {"type":"answer_chunk","content":"查询结果，"}

event: answer_chunk
data: {"type":"answer_chunk","content":"您入职已满1年，"}

event: answer_chunk
data: {"type":"answer_chunk","content":"享有5天带薪年假，"}

event: answer_chunk
data: {"type":"answer_chunk","content":"需提前3个工作日向直属主管申请。\n\n"}

event: answer_chunk
data: {"type":"answer_chunk","content":"关于项目排期，"}

event: answer_chunk
data: {"type":"answer_chunk","content":"Q3项目的最终交付日期为9月30日，"}

event: answer_chunk
data: {"type":"answer_chunk","content":"当前进度正常（102%），无延期风险。\n\n"}

event: answer_chunk
data: {"type":"answer_chunk","content":"**建议**：如果您在8月中旬前安排休假，"}

event: answer_chunk
data: {"type":"answer_chunk","content":"不会影响项目交付。"}

event: citation
data: {"type":"citation","docId":12,"title":"员工手册 v3.2","heading":"第三章 休假制度","snippet":"入职满1年员工享有5天带薪年假，需提前3个工作日向直属主管提交书面申请。"}

event: citation
data: {"type":"citation","docId":15,"title":"考勤管理办法 v1.0","heading":"第四条 年假计算与累计","snippet":"年假天数按自然年计算，当年度未休完的年假不跨年累计至下一年度。"}

event: citation
data: {"type":"citation","docId":28,"title":"Q3项目排期表 v2","heading":"里程碑与交付节点","snippet":"2026-09-30：Q3版本正式交付。当前整体进度102%，各模块无延期风险。"}

event: done
data: {"type":"done","responseTime":3200,"tokenUsage":{"input":1245,"output":356}}
```

---

**文档结束**
