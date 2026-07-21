# 前端交互界面设计文档

**版本**：v1.0  
**日期**：2026-07-21  
**目标**：为 MVP 系统添加 Vue 3 前端，提供登录注册、智能问答、文档管理、审计日志四个页面

---

## 一、架构总览

**部署方式**：在 `java/` 下新建 `frontend` Maven 模块，作为独立 Spring Boot 应用（端口 8084），内嵌 Vue 3 构建产物。

**技术栈**：
- Vue 3 (Composition API) + Vite + TypeScript
- Element Plus（UI 组件库）
- Pinia（状态管理）
- Vue Router 4（路由）
- Axios + EventSource（SSE 流式对话）

**开发与生产**：
- 开发：Vite dev server（5173）proxy 转发 `/api/*` → 后端各模块
- 生产：`vite build` → `frontend/src/main/resources/static/`，Spring Boot serve 静态文件
- 所有非 `/api/*` 请求 fallback 到 `index.html`，支持 Vue Router history 模式

**路由表**：

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录/注册 | 未认证入口 |
| `/chat` | 智能问答 | 主页面，SSE 流式对话 |
| `/documents` | 文档管理 | 上传/列表/删除/索引状态 |
| `/audit` | 审计日志 | 管理员查看问答记录 |

---

## 二、页面设计

### 2.1 登录/注册页 (`/login`)

- 左侧品牌区域（系统标题 + 副标题），右侧表单卡片
- 登录/注册通过 Tab 切换，不跳路由
- 登录字段：用户名 + 密码
- 注册字段：用户名 + 密码 + 确认密码 + 邮箱 + 部门下拉
- 成功后：JWT 存入 localStorage，router 跳转 `/chat`

### 2.2 智能问答页 (`/chat`)

经典聊天布局：

```
┌──────────────────────────────────────────┐
│  Header: 用户头像 + 退出按钮              │
├──────────┬───────────────────────────────┤
│          │                               │
│  会话    │  消息区域                      │
│  列表    │  - 用户气泡（右侧）            │
│  (可选)  │  - AI 气泡（左侧，打字机效果） │
│          │  - 引用卡片（文档名+片段）      │
│          │                               │
│          ├───────────────────────────────┤
│          │  输入区域                      │
│          │  - 文本输入框                  │
│          │  - 发送按钮                    │
├──────────┴───────────────────────────────┤
│  状态栏: "就绪" / "正在生成..."          │
└──────────────────────────────────────────┘
```

- 消息支持 Markdown 渲染（代码块、表格）
- SSE 流式：EventSource 消费 `/api/chat/stream`，"思考中" → "逐字输出" → "完成"
- 引用卡片：每条 AI 回复下方展示引用来源

### 2.3 文档管理页 (`/documents`)

- 上传区域：拖拽 + 文件选择（PDF / MD / TXT / DOCX，≤50MB）
- 上传表单：标题、部门、安全级别
- 文档表格：文件名、大小、类型、部门、安全级别、状态、操作（删除、重新索引）
- 分页组件

### 2.4 审计日志页 (`/audit`)

- 仅管理员可见（路由守卫检查 role）
- 表格：用户、问题（截断）、响应时间、Token 用量、时间
- 点击行展开详情（完整问答内容）
- 分页

---

## 三、数据流与接口对接

### 3.1 API 封装层

统一 Axios 实例：
- 请求拦截器：自动附加 `Authorization: Bearer <JWT>`
- 响应拦截器：401 时清除 token 跳转 `/login`
- SSE 用原生 `EventSource`，手动附加 token 参数

### 3.2 接口对接

| 页面 | 调用接口 | 方式 |
|------|----------|------|
| 登录 | `POST /api/auth/login` | Axios |
| 注册 | `POST /api/auth/register` | Axios |
| 文档列表 | `GET /api/documents?page=&size=` | Axios |
| 文档详情 | `GET /api/documents/{id}` | Axios |
| 上传文档 | `POST /api/documents/upload` (multipart) | Axios |
| 删除文档 | `DELETE /api/documents/{id}` | Axios |
| 触发索引 | `POST /api/documents/{id}/index` | Axios |
| 索引状态 | `GET /api/documents/status/{id}` | Axios |
| 对话 | `POST /api/chat/stream` | EventSource (SSE) |
| 审计日志 | `GET /api/audit/logs?page=&size=` | Axios |

### 3.3 Pinia Store

**authStore** — `token`, `userInfo {username, role, department}`, `login()`, `register()`, `logout()`, `isAuthenticated`, `isAdmin`

**chatStore** — `messages[]`, `isStreaming`, `sendMessage()` (追加用户消息 → EventSource → 逐条追加 AI token → 完成后记录审计), `clearHistory()`

**documentStore** — `list[]`, `total`, `upload()`, `fetchList()`, `deleteDocument()`, `triggerIndex()`

### 3.4 路由守卫

```typescript
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.isAuthenticated) next('/login')
  else if (to.path === '/audit' && !auth.isAdmin) next('/chat')
  else next()
})
```

### 3.5 错误处理

- 全局：ElMessage 弹出错误信息（来自 `ApiResult.code + message`）
- 网络异常："网络连接失败，请检查服务是否启动"
- SSE 中断：显示"连接已断开"并重试按钮

---

## 四、文件结构

```
java/frontend/
├── pom.xml
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html                          # Vite HTML 入口
├── src/
│   ├── main.ts                         # Vue 入口，注册 Router/Pinia/Element Plus
│   ├── App.vue                         # 根组件，<router-view>
│   ├── router/index.ts                 # 路由定义 + 守卫
│   ├── stores/
│   │   ├── auth.ts                     # authStore
│   │   ├── chat.ts                     # chatStore
│   │   └── document.ts                 # documentStore
│   ├── api/
│   │   ├── index.ts                    # Axios 实例 + 拦截器
│   │   ├── auth.ts                     # login(), register()
│   │   ├── document.ts                 # upload(), list(), delete(), index()
│   │   ├── chat.ts                     # chatStream() (SSE)
│   │   └── audit.ts                    # list()
│   ├── views/
│   │   ├── LoginView.vue               # 登录/注册页
│   │   ├── ChatView.vue                # 智能问答页
│   │   ├── DocumentsView.vue           # 文档管理页
│   │   └── AuditView.vue               # 审计日志页
│   ├── components/
│   │   ├── chat/
│   │   │   ├── MessageList.vue         # 消息列表
│   │   │   ├── MessageBubble.vue       # 单条消息气泡
│   │   │   ├── CitationCard.vue        # 引用来源卡片
│   │   │   └── ChatInput.vue           # 输入区域
│   │   ├── document/
│   │   │   ├── UploadDialog.vue        # 上传弹窗
│   │   │   └── DocumentTable.vue       # 文档表格
│   │   └── common/
│   │       └── AppHeader.vue           # 顶部导航栏
│   └── utils/
│       └── sse.ts                      # SSE EventSource 封装（带 JWT token）
└── spring/                             # Spring Boot 包装层
    ├── pom.xml                         # 独立 POM（spring-boot-starter-web）
    └── src/main/
        ├── java/com/qa/frontend/
        │   └── FrontendApplication.java  # 端口 8084，SPA fallback controller
        └── resources/
            ├── application.yml
            └── static/                 # vite build 输出到此
```

Vite 构建配置：`build.outDir = 'spring/src/main/resources/static'`

---

## 五、Vite 代理配置

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api/auth':     'http://localhost:8080',
      '/api/documents': 'http://localhost:8081',
      '/api/chat':     'http://localhost:8082',
      '/api/audit':    'http://localhost:8083',
    }
  },
  build: {
    outDir: 'src/main/resources/static'
  }
})
```

---

## 六、验收标准

- [ ] 用户可注册新账号并登录，登录后进入聊天页
- [ ] 未登录访问任何页面自动跳转 `/login`
- [ ] 聊天页输入问题后，SSE 流式展示 AI 回答（打字机效果）
- [ ] AI 回答末尾展示引用来源卡片
- [ ] 文档管理页可上传文件、浏览列表、删除、触发索引
- [ ] 审计日志页仅管理员可见，可浏览和查看详情
- [ ] 普通用户看不到审计日志入口，直接访问 `/audit` 被重定向
- [ ] 后端不可用时显示明确的错误提示
