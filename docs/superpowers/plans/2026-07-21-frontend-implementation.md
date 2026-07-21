# 前端交互界面实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 MVP 系统添加 Vue 3 + Element Plus 前端，提供登录注册、SSE 流式对话、文档管理、审计日志四个页面。

**Architecture:** Vue 3 SPA 放在 `java/frontend/` 下。开发时 Vite dev server（5173）proxy 转发 API 到各 Java 模块。生产时 `vite build` 输出到 `spring/src/main/resources/static/`，由 Spring Boot（8084）serve。前端同时加入一键启动器。

**Tech Stack:** Vue 3 (Composition API) + Vite + TypeScript + Element Plus + Pinia + Vue Router 4 + Axios + marked (Markdown 渲染) + @microsoft/fetch-event-source (SSE)

## Global Constraints

- 所有后端 API 响应包裹在 `ApiResult<T>` 中: `{ code: number, message: string, data: T }`
- 成功时 `code === 200`，前端只检查 `code === 200` 判断成功
- 分页响应 `PageResult<T>`: `{ content: T[], totalElements: long, totalPages: int, number: int, size: int }`
- 登录响应 `LoginResponse`: `{ token, username, role, department }`
- 对话请求 `ChatRequest`: `{ question: string, history: { role: string, content: string }[] }`
- 对话 SSE 响应 `ChatResponse`: `{ type: "thinking"|"answer"|"citation"|"done"|"error", content: string, data: any }`
- 文档响应 `DocumentResponse`: `{ id, title, fileName, filePath, fileSize, fileType, department, securityLevel, status, uploadByName, createdAt }`
- 审计日志 `AuditLog`: `{ id, userId, question, answer, toolsCalled, responseTime, tokenUsage, createdAt }`
- JWT token 通过 `Authorization: Bearer <token>` 请求头发送
- `/api/chat/stream` 是 POST 请求，不能用原生 EventSource（仅支持 GET），必须用 fetch + ReadableStream
- `/api/audit/logs` 需要 `ROLE_ADMIN` 角色
- Node.js 已安装在系统中，使用 `npm` 命令

---

### Task 1: Project Scaffolding

**Files:**
- Create: `java/frontend/package.json`
- Create: `java/frontend/vite.config.ts`
- Create: `java/frontend/tsconfig.json`
- Create: `java/frontend/tsconfig.node.json`
- Create: `java/frontend/index.html`
- Create: `java/frontend/src/main.ts`
- Create: `java/frontend/src/App.vue`
- Create: `java/frontend/src/env.d.ts`
- Create: `java/frontend/pom.xml`
- Create: `java/frontend/spring/pom.xml`
- Create: `java/frontend/spring/src/main/java/com/qa/frontend/FrontendApplication.java`
- Create: `java/frontend/spring/src/main/resources/application.yml`
- Modify: `java/pom.xml` — 添加 `<module>frontend</module>`

**Interfaces:**
- Produces: `App.vue` 根组件（router-view），`router/index.ts` 路由实例（由 Task 2 创建），`stores/` 目录（由 Task 2 创建），`api/` 目录（由 Task 2 创建），`views/` 目录（由后续 Tasks 创建）

- [ ] **Step 1: Create `java/frontend/package.json`**

```json
{
  "name": "qa-agent-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.0",
    "element-plus": "^2.7.0",
    "axios": "^1.6.0",
    "marked": "^12.0.0",
    "@element-plus/icons-vue": "^2.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "vue-tsc": "^2.0.0"
  }
}
```

- [ ] **Step 2: Create `java/frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api/auth':      'http://localhost:8080',
      '/api/documents':  'http://localhost:8081',
      '/api/chat':       'http://localhost:8082',
      '/api/audit':      'http://localhost:8083'
    }
  },
  build: {
    outDir: 'spring/src/main/resources/static',
    emptyOutDir: true
  }
})
```

- [ ] **Step 3: Create `java/frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Create `java/frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Create `java/frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>企业智能问答系统</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 6: Create `java/frontend/src/main.ts`**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
```

Note: `zhCn` import from `element-plus/dist/locale/zh-cn.mjs` — add `import zhCn from 'element-plus/dist/locale/zh-cn.mjs'` at top.

- [ ] **Step 7: Create `java/frontend/src/App.vue`**

```vue
<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html, body, #app {
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
</style>
```

- [ ] **Step 8: Create `java/frontend/src/env.d.ts`**

```typescript
/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 9: Create `java/frontend/pom.xml`** (parent module POM, aggregates spring/)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.qa</groupId>
        <artifactId>qa-agent</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>qa-frontend</artifactId>
    <packaging>pom</packaging>
    <name>QA Frontend</name>

    <modules>
        <module>spring</module>
    </modules>
</project>
```

- [ ] **Step 10: Create `java/frontend/spring/pom.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.qa</groupId>
        <artifactId>qa-frontend</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>qa-frontend-spring</artifactId>
    <name>QA Frontend Spring</name>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
            </plugin>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

- [ ] **Step 11: Create `java/frontend/spring/src/main/java/com/qa/frontend/FrontendApplication.java`**

```java
package com.qa.frontend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;
import org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration;
import org.springframework.boot.autoconfigure.security.servlet.SecurityAutoConfiguration;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@SpringBootApplication(exclude = {
    DataSourceAutoConfiguration.class,
    HibernateJpaAutoConfiguration.class,
    SecurityAutoConfiguration.class
})
@ComponentScan(
    basePackages = "com.qa",
    excludeFilters = @ComponentScan.Filter(
        type = FilterType.REGEX,
        pattern = "com\\.qa\\.(auth|document|chat|audit)\\..*"
    )
)
@Controller
public class FrontendApplication {

    public static void main(String[] args) {
        SpringApplication.run(FrontendApplication.class, args);
    }

    // SPA fallback: all non-/api/** routes → index.html
    @GetMapping(value = {"/{path:[^\\.]*}", "/**/{path:[^\\.]*}"})
    public String forward() {
        return "forward:/index.html";
    }
}
```

- [ ] **Step 12: Create `java/frontend/spring/src/main/resources/application.yml`**

```yaml
server:
  port: 8084

spring:
  main:
    web-application-type: servlet
```

- [ ] **Step 13: 修改 `java/pom.xml`** — 在 `<modules>` 中添加 `<module>frontend</module>`

```xml
<modules>
    <module>common</module>
    <module>auth</module>
    <module>document</module>
    <module>chat</module>
    <module>audit</module>
    <module>launcher</module>
    <module>frontend</module>
</modules>
```

- [ ] **Step 14: Install dependencies and verify build**

```bash
cd E:/vs_code_coding/QA_agent/java/frontend
npm install
```

Expected: npm install 成功，无错误。

- [ ] **Step 15: Verify TypeScript compilation**

```bash
cd E:/vs_code_coding/QA_agent/java/frontend
npx vue-tsc --noEmit
```

Expected: 目前 Vue 源文件为空，编译通过无错误。

- [ ] **Step 16: Commit**

```bash
git add java/frontend/ java/pom.xml
git commit -m "feat: scaffold frontend project with Vite + Vue 3 + Spring Boot wrapper"
```

---

### Task 2: Router, API Layer, and Pinia Stores

**Files:**
- Create: `java/frontend/src/router/index.ts`
- Create: `java/frontend/src/api/index.ts`
- Create: `java/frontend/src/api/auth.ts`
- Create: `java/frontend/src/api/document.ts`
- Create: `java/frontend/src/api/chat.ts`
- Create: `java/frontend/src/api/audit.ts`
- Create: `java/frontend/src/stores/auth.ts`
- Create: `java/frontend/src/stores/chat.ts`
- Create: `java/frontend/src/stores/document.ts`
- Create: `java/frontend/src/utils/sse.ts`
- Modify: `java/frontend/src/main.ts` — 修正 zhCn import

**Interfaces:**
- Consumes: `App.vue` (Task 1), Vue Router/Pinia 实例
- Produces:
  - `router` — Vue Router 实例，含 4 条路由 + beforeEach 守卫
  - `api` 模块 — `authApi.login(username, password): Promise<LoginResponse>`，`authApi.register(...)`，`documentApi.upload(...)`，`documentApi.list(page, size)...`，`chatApi.stream(req, callbacks)`，`auditApi.list(page, size, userId?)`
  - `useAuthStore` — `{ token, userInfo, login(), register(), logout(), isAuthenticated, isAdmin }`
  - `useChatStore` — `{ messages[], isStreaming, sendMessage(), clearHistory() }`
  - `useDocumentStore` — `{ documents[], total, loading, fetchList(), upload(), deleteDoc(), triggerIndex() }`
  - `createSSEStream(url, body, callbacks)` — 基于 fetch + ReadableStream 的 POST SSE 实现

- [ ] **Step 1: Create `java/frontend/src/router/index.ts`**

```typescript
import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/chat'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/documents',
    name: 'Documents',
    component: () => import('@/views/DocumentsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/audit',
    name: 'Audit',
    component: () => import('@/views/AuditView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth !== false && !auth.isAuthenticated) {
    next('/login')
  } else if (to.meta.requiresAdmin && !auth.isAdmin) {
    next('/chat')
  } else {
    next()
  }
})

export default router
```

- [ ] **Step 2: Create `java/frontend/src/api/index.ts`**

```typescript
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '',
  timeout: 30000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => {
    const body = response.data
    if (body.code !== 200) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return response
  },
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      ElMessage.error('登录已过期，请重新登录')
      window.location.href = '/login'
    } else if (error.response?.status === 403) {
      ElMessage.error('权限不足')
    } else if (!error.response) {
      ElMessage.error('网络连接失败，请检查服务是否启动')
    } else {
      ElMessage.error(error.response.data?.message || '请求失败')
    }
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 3: Create `java/frontend/src/api/auth.ts`**

```typescript
import api from './index'

export interface LoginResponse {
  token: string
  username: string
  role: string
  department: string
}

export interface RegisterParams {
  username: string
  password: string
  email: string
  department: string
}

export const authApi = {
  login(username: string, password: string) {
    return api.post('/api/auth/login', { username, password })
      .then(res => res.data.data as LoginResponse)
  },
  register(params: RegisterParams) {
    return api.post('/api/auth/register', params)
      .then(res => res.data)
  }
}
```

- [ ] **Step 4: Create `java/frontend/src/api/document.ts`**

```typescript
import api from './index'

export interface DocumentItem {
  id: number
  title: string
  fileName: string
  filePath: string
  fileSize: number
  fileType: string
  department: string
  securityLevel: string
  status: string
  uploadByName: string
  createdAt: string
}

export interface PageResult<T> {
  content: T[]
  totalElements: number
  totalPages: number
  number: number
  size: number
}

export const documentApi = {
  list(page: number = 1, size: number = 20) {
    return api.get('/api/documents', { params: { page, size } })
      .then(res => res.data.data as PageResult<DocumentItem>)
  },
  getById(id: number) {
    return api.get(`/api/documents/${id}`)
      .then(res => res.data.data as DocumentItem)
  },
  upload(file: File, title: string, department: string, securityLevel: string) {
    const form = new FormData()
    form.append('file', file)
    form.append('title', title)
    form.append('department', department)
    form.append('securityLevel', securityLevel)
    return api.post('/api/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data.data as DocumentItem)
  },
  delete(id: number) {
    return api.delete(`/api/documents/${id}`).then(res => res.data)
  },
  triggerIndex(id: number) {
    return api.post(`/api/documents/${id}/index`).then(res => res.data)
  },
  getStatus(id: number) {
    return api.get(`/api/documents/status/${id}`).then(res => res.data.data as string)
  }
}
```

- [ ] **Step 5: Create `java/frontend/src/api/chat.ts`**

```typescript
import { useAuthStore } from '@/stores/auth'

export interface HistoryMessage {
  role: string  // 'user' | 'assistant'
  content: string
}

export interface SSEEvent {
  type: 'thinking' | 'answer' | 'citation' | 'done' | 'error'
  content: string
  data: any
}

export interface SSECallbacks {
  onMessage: (event: SSEEvent) => void
  onError: (error: Error) => void
  onDone: () => void
}

export function createChatStream(
  question: string,
  history: HistoryMessage[],
  callbacks: SSECallbacks
): AbortController {
  const controller = new AbortController()
  const token = localStorage.getItem('token')

  fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ question, history: history || [] }),
    signal: controller.signal
  }).then(async response => {
    if (!response.ok) {
      if (response.status === 401) {
        callbacks.onError(new Error('请先登录'))
        return
      }
      callbacks.onError(new Error(`HTTP ${response.status}`))
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      callbacks.onError(new Error('无法读取响应流'))
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('data: ')) {
          const data = trimmed.substring(6)
          if (data === '[DONE]') {
            callbacks.onDone()
            return
          }
          try {
            const parsed: SSEEvent = JSON.parse(data)
            callbacks.onMessage(parsed)
          } catch {
            // skip unparseable lines
          }
        }
      }
    }
    callbacks.onDone()
  }).catch(err => {
    if (err.name !== 'AbortError') {
      callbacks.onError(err)
    }
  })

  return controller
}
```

- [ ] **Step 6: Create `java/frontend/src/api/audit.ts`**

```typescript
import api from './index'
import type { PageResult } from './document'

export interface AuditLogItem {
  id: number
  userId: number
  question: string
  answer: string
  toolsCalled: string | null
  responseTime: number | null
  tokenUsage: string | null
  createdAt: string
}

export const auditApi = {
  list(page: number = 1, size: number = 20, userId?: number) {
    return api.get('/api/audit/logs', { params: { page, size, userId } })
      .then(res => res.data.data as PageResult<AuditLogItem>)
  }
}
```

- [ ] **Step 7: Create `java/frontend/src/stores/auth.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, LoginResponse } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref<LoginResponse | null>(
    JSON.parse(localStorage.getItem('userInfo') || 'null')
  )

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'ROLE_ADMIN')

  async function login(username: string, password: string) {
    const data = await authApi.login(username, password)
    token.value = data.token
    userInfo.value = data
    localStorage.setItem('token', data.token)
    localStorage.setItem('userInfo', JSON.stringify(data))
  }

  async function register(username: string, password: string, email: string, department: string) {
    await authApi.register({ username, password, email, department })
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  return { token, userInfo, isAuthenticated, isAdmin, login, register, logout }
})
```

- [ ] **Step 8: Create `java/frontend/src/stores/chat.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref, nextTick } from 'vue'
import { createChatStream, SSEEvent, HistoryMessage } from '@/api/chat'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  isStreaming: boolean
  timestamp: number
}

export interface Citation {
  title: string
  chunk: string
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  let abortController: AbortController | null = null
  const historyMessages = ref<HistoryMessage[]>([])

  function generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substring(2)
  }

  function sendMessage(question: string) {
    if (isStreaming.value) return

    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: question,
      citations: [],
      isStreaming: false,
      timestamp: Date.now()
    }
    messages.value.push(userMsg)

    const assistantMsg: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: '',
      citations: [],
      isStreaming: true,
      timestamp: Date.now()
    }
    messages.value.push(assistantMsg)
    isStreaming.value = true

    abortController = createChatStream(
      question,
      historyMessages.value,
      {
        onMessage(event: SSEEvent) {
          const msg = messages.value.find(m => m.id === assistantMsg.id)
          if (!msg) return

          switch (event.type) {
            case 'thinking':
              msg.content = event.content
              break
            case 'answer':
              if (msg.content.startsWith('思考中')) msg.content = ''
              msg.content += event.content || ''
              break
            case 'citation':
              if (event.data) {
                msg.citations.push({
                  title: event.data.title || '',
                  chunk: event.data.chunk || event.content || ''
                })
              }
              break
            case 'error':
              msg.content = '回答出错: ' + (event.content || '未知错误')
              msg.isStreaming = false
              isStreaming.value = false
              break
            case 'done':
              msg.isStreaming = false
              isStreaming.value = false
              break
          }
        },
        onError(error: Error) {
          const msg = messages.value.find(m => m.id === assistantMsg.id)
          if (msg) {
            msg.content = '连接失败: ' + error.message
            msg.isStreaming = false
          }
          isStreaming.value = false
        },
        onDone() {
          const msg = messages.value.find(m => m.id === assistantMsg.id)
          if (msg) {
            msg.isStreaming = false
          }
          isStreaming.value = false
          historyMessages.value.push({ role: 'user', content: question })
          historyMessages.value.push({ role: 'assistant', content: msg?.content || '' })
          if (historyMessages.value.length > 20) {
            historyMessages.value = historyMessages.value.slice(-20)
          }
        }
      }
    )
  }

  function stopStreaming() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    isStreaming.value = false
  }

  function clearHistory() {
    messages.value = []
    historyMessages.value = []
  }

  return { messages, isStreaming, sendMessage, stopStreaming, clearHistory }
})
```

- [ ] **Step 9: Create `java/frontend/src/stores/document.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { documentApi, DocumentItem } from '@/api/document'
import { ElMessage } from 'element-plus'

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<DocumentItem[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchList(page: number = 1, size: number = 20) {
    loading.value = true
    try {
      const result = await documentApi.list(page, size)
      documents.value = result.content
      total.value = result.totalElements
    } finally {
      loading.value = false
    }
  }

  async function upload(file: File, title: string, department: string, securityLevel: string) {
    await documentApi.upload(file, title, department, securityLevel)
    ElMessage.success('上传成功')
    await fetchList()
  }

  async function deleteDoc(id: number) {
    await documentApi.delete(id)
    ElMessage.success('已删除')
    await fetchList()
  }

  async function triggerIndex(id: number) {
    await documentApi.triggerIndex(id)
    ElMessage.success('索引任务已触发')
    await fetchList()
  }

  return { documents, total, loading, fetchList, upload, deleteDoc, triggerIndex }
})
```

- [ ] **Step 10: Create `java/frontend/src/utils/sse.ts`**

```typescript
// SSE utility — kept separate so it can be reused if needed later.
// Currently chat.ts uses the inline fetch+ReadableStream approach directly,
// since it needs to pass JWT token from localStorage.
export function parseSSELine(line: string): any | null {
  const trimmed = line.trim()
  if (!trimmed || trimmed.startsWith(':')) return null
  if (trimmed.startsWith('data: ')) {
    const data = trimmed.substring(6)
    if (data === '[DONE]') return { __done: true }
    try { return JSON.parse(data) } catch { return null }
  }
  return null
}
```

- [ ] **Step 11: Fix `java/frontend/src/main.ts`** — 确保 zhCn import 正确

Read existing `main.ts` and replace with:

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
```

- [ ] **Step 12: Verify TypeScript compilation**

```bash
cd E:/vs code_coding/QA_agent/java/frontend
npx vue-tsc --noEmit
```

Expected: 编译成功。目前还没有 views，但这些 lazy-loaded，不影响编译。

- [ ] **Step 13: Commit**

```bash
git add java/frontend/src/
git commit -m "feat: add router, API layer, and Pinia stores"
```

---

### Task 3: Login and Register Page

**Files:**
- Create: `java/frontend/src/views/LoginView.vue`
- Create: `java/frontend/src/components/common/AppHeader.vue`

**Interfaces:**
- Consumes: `useAuthStore` (Task 2), `router` (Task 2)
- Produces: `LoginView` 组件 — 登录/注册 Tab 切换表单，成功后跳转 /chat

- [ ] **Step 1: Create `java/frontend/src/components/common/AppHeader.vue`**

```vue
<template>
  <el-header class="app-header">
    <div class="header-left">
      <h2>企业智能问答系统</h2>
    </div>
    <div class="header-right">
      <el-menu
        mode="horizontal"
        :default-active="currentRoute"
        router
        :ellipsis="false"
      >
        <el-menu-item index="/chat">智能问答</el-menu-item>
        <el-menu-item index="/documents">文档管理</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/audit">审计日志</el-menu-item>
      </el-menu>
      <el-dropdown class="user-dropdown">
        <span class="user-info">
          <el-icon><UserFilled /></el-icon>
          {{ auth.userInfo?.username }}
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              {{ auth.userInfo?.department }} · {{ auth.userInfo?.role }}
            </el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const currentRoute = computed(() => route.path)

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 60px;
}
.header-left h2 {
  font-size: 18px;
  color: #303133;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.header-right .el-menu {
  border-bottom: none;
}
.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
}
</style>
```

- [ ] **Step 2: Create `java/frontend/src/views/LoginView.vue`**

```vue
<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>企业智能问答系统</h1>
        <p>基于 AI 的企业内部知识库助手</p>
      </div>
      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            label-position="top"
          >
            <el-form-item label="用户名" prop="username">
              <el-input v-model="loginForm.username" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                class="w-full"
                :loading="loginLoading"
                @click="handleLogin"
              >
                登 录
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            label-position="top"
          >
            <el-form-item label="用户名" prop="username">
              <el-input v-model="registerForm.username" placeholder="3-50个字符" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="至少6位"
                show-password
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="registerForm.confirmPassword"
                type="password"
                placeholder="再次输入密码"
                show-password
              />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="registerForm.email" placeholder="选填" />
            </el-form-item>
            <el-form-item label="部门" prop="department">
              <el-select v-model="registerForm.department" placeholder="请选择" class="w-full">
                <el-option label="技术部" value="技术部" />
                <el-option label="产品部" value="产品部" />
                <el-option label="人事部" value="人事部" />
                <el-option label="财务部" value="财务部" />
                <el-option label="法务部" value="法务部" />
                <el-option label="全部" value="全部" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                class="w-full"
                :loading="registerLoading"
                @click="handleRegister"
              >
                注 册
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElForm } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()

const activeTab = ref('login')
const loginLoading = ref(false)
const registerLoading = ref(false)
const loginFormRef = ref<FormInstance>()
const registerFormRef = ref<FormInstance>()

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
  department: ''
})

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const validateConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度3-50个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 100, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!loginFormRef.value) return
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  loginLoading.value = true
  try {
    await auth.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/chat')
  } catch {
    // api interceptor already shows error message
  } finally {
    loginLoading.value = false
  }
}

async function handleRegister() {
  if (!registerFormRef.value) return
  const valid = await registerFormRef.value.validate().catch(() => false)
  if (!valid) return

  registerLoading.value = true
  try {
    await auth.register(
      registerForm.username,
      registerForm.password,
      registerForm.email,
      registerForm.department
    )
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    loginForm.username = registerForm.username
  } catch {
    // api interceptor already shows error message
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}
.login-header {
  text-align: center;
  margin-bottom: 24px;
}
.login-header h1 {
  font-size: 24px;
  color: #303133;
  margin-bottom: 8px;
}
.login-header p {
  font-size: 14px;
  color: #909399;
}
.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}
.w-full {
  width: 100%;
}
</style>
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd E:/vs code_coding/QA_agent/java/frontend
npx vue-tsc --noEmit
```

Expected: 编译通过，无错误。

- [ ] **Step 4: Verify dev server starts**

```bash
cd E:/vs code_coding/QA_agent/java/frontend
npm run dev
```

Expected: Vite dev server 在 `http://localhost:5173` 启动。打开浏览器访问，应看到登录页（自动重定向到 /login）。

- [ ] **Step 5: Commit**

```bash
git add java/frontend/src/views/LoginView.vue java/frontend/src/components/common/AppHeader.vue
git commit -m "feat: add login and register page"
```

---

### Task 4: Chat Page with SSE Streaming

**Files:**
- Create: `java/frontend/src/views/ChatView.vue`
- Create: `java/frontend/src/components/chat/MessageList.vue`
- Create: `java/frontend/src/components/chat/MessageBubble.vue`
- Create: `java/frontend/src/components/chat/CitationCard.vue`
- Create: `java/frontend/src/components/chat/ChatInput.vue`
- Modify: `java/frontend/src/views/LoginView.vue` — 若已登录直接跳转

**Interfaces:**
- Consumes: `useChatStore` (Task 2), `useAuthStore` (Task 2), `AppHeader` (Task 3), `marked` (npm dep), SSE `createChatStream` (Task 2)
- Produces: `ChatView` 完整聊天页 — 消息列表 + SSE 流式 + Markdown 渲染 + 引用卡片 + 输入框

- [ ] **Step 1: Create `java/frontend/src/components/chat/CitationCard.vue`**

```vue
<template>
  <div class="citation-card">
    <div class="citation-header">
      <el-icon><Document /></el-icon>
      <span class="citation-title">{{ citation.title }}</span>
    </div>
    <div class="citation-chunk">{{ citation.chunk }}</div>
  </div>
</template>

<script setup lang="ts">
import type { Citation } from '@/stores/chat'

defineProps<{
  citation: Citation
}>()
</script>

<style scoped>
.citation-card {
  margin-top: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-left: 3px solid #409eff;
  border-radius: 4px;
  font-size: 13px;
}
.citation-header {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #409eff;
  margin-bottom: 4px;
}
.citation-title {
  font-weight: 600;
}
.citation-chunk {
  color: #606266;
  line-height: 1.5;
}
</style>
```

- [ ] **Step 2: Create `java/frontend/src/components/chat/MessageBubble.vue`**

```vue
<template>
  <div class="message-row" :class="message.role">
    <div class="message-bubble" :class="message.role">
      <div class="message-content" v-html="renderedContent"></div>
      <div v-if="message.isStreaming" class="typing-cursor">|</div>
      <CitationCard
        v-for="(c, idx) in message.citations"
        :key="idx"
        :citation="c"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import type { ChatMessage } from '@/stores/chat'
import CitationCard from './CitationCard.vue'

const props = defineProps<{
  message: ChatMessage
}>()

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  if (props.message.role === 'user') return escapeHtml(props.message.content)
  try {
    return marked.parse(props.message.content) as string
  } catch {
    return escapeHtml(props.message.content)
  }
})

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.message-row {
  display: flex;
  margin-bottom: 16px;
}
.message-row.user {
  justify-content: flex-end;
}
.message-row.assistant {
  justify-content: flex-start;
}
.message-bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
}
.message-bubble.user {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.message-bubble.assistant {
  background: #f0f2f5;
  color: #303133;
  border-bottom-left-radius: 4px;
}
.message-content :deep(pre) {
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}
.message-content :deep(code) {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
}
.message-content :deep(p) {
  margin: 4px 0;
}
.message-content :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
}
.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 4px 8px;
}
.typing-cursor {
  display: inline;
  animation: blink 1s infinite;
  color: #409eff;
}
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
```

- [ ] **Step 3: Create `java/frontend/src/components/chat/MessageList.vue`**

```vue
<template>
  <div class="message-list" ref="listRef">
    <div v-if="messages.length === 0" class="empty-state">
      <el-empty description="开始提问吧" />
    </div>
    <MessageBubble
      v-for="msg in messages"
      :key="msg.id"
      :message="msg"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { ChatMessage } from '@/stores/chat'
import MessageBubble from './MessageBubble.vue'

const props = defineProps<{
  messages: ChatMessage[]
}>()

const listRef = ref<HTMLElement>()

watch(
  () => props.messages.length,
  () => nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
)

watch(
  () => props.messages[props.messages.length - 1]?.content,
  () => nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
)
</script>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
</style>
```

- [ ] **Step 4: Create `java/frontend/src/components/chat/ChatInput.vue`**

```vue
<template>
  <div class="chat-input-area">
    <el-input
      v-model="inputText"
      type="textarea"
      :rows="3"
      placeholder="输入您的问题，按 Enter 发送，Shift+Enter 换行"
      :disabled="disabled"
      @keydown.enter.exact.prevent="handleSend"
    />
    <el-button
      type="primary"
      :disabled="!inputText.trim() || disabled"
      :loading="disabled"
      @click="handleSend"
    >
      发送
    </el-button>
    <el-button
      v-if="disabled"
      type="warning"
      @click="$emit('stop')"
    >
      停止
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ disabled: boolean }>()
const emit = defineEmits<{
  send: [text: string]
  stop: []
}>()

const inputText = ref('')

function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text)
  inputText.value = ''
}
</script>

<style scoped>
.chat-input-area {
  padding: 16px 24px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
</style>
```

- [ ] **Step 5: Create `java/frontend/src/views/ChatView.vue`**

```vue
<template>
  <div class="chat-layout">
    <AppHeader />
    <div class="chat-body">
      <MessageList :messages="chat.messages" />
      <ChatInput
        :disabled="chat.isStreaming"
        @send="chat.sendMessage"
        @stop="chat.stopStreaming"
      />
    </div>
    <div class="status-bar">
      {{ chat.isStreaming ? '正在生成...' : '就绪' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/common/AppHeader.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import { useChatStore } from '@/stores/chat'

const chat = useChatStore()
</script>

<style scoped>
.chat-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.status-bar {
  padding: 4px 24px;
  background: #f5f7fa;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
}
</style>
```

- [ ] **Step 6: Add auto-redirect in LoginView** — 在 `<script setup>` 顶部加入：

```typescript
import { onMounted } from 'vue'

onMounted(() => {
  if (auth.isAuthenticated) {
    router.replace('/chat')
  }
})
```

- [ ] **Step 7: Verify TypeScript compilation**

```bash
cd E:/vs code_coding/QA_agent/java/frontend
npx vue-tsc --noEmit
```

Expected: 编译通过。

- [ ] **Step 8: Commit**

```bash
git add java/frontend/src/views/ChatView.vue java/frontend/src/views/LoginView.vue java/frontend/src/components/chat/
git commit -m "feat: add chat page with SSE streaming and markdown rendering"
```

---

### Task 5: Document Management and Audit Log Pages

**Files:**
- Create: `java/frontend/src/views/DocumentsView.vue`
- Create: `java/frontend/src/components/document/UploadDialog.vue`
- Create: `java/frontend/src/components/document/DocumentTable.vue`
- Create: `java/frontend/src/views/AuditView.vue`

**Interfaces:**
- Consumes: `useDocumentStore` (Task 2), `useAuthStore` (Task 2), `AppHeader` (Task 3), `documentApi` (Task 2), `auditApi` (Task 2)
- Produces: `DocumentsView` — 文档上传/列表/删除/索引，`AuditView` — 审计日志表格+展开详情

- [ ] **Step 1: Create `java/frontend/src/components/document/UploadDialog.vue`**

```vue
<template>
  <el-dialog
    v-model="visible"
    title="上传文档"
    width="480px"
    @close="resetForm"
  >
    <el-form ref="formRef" :model="form" label-position="top">
      <el-form-item label="标题" required>
        <el-input v-model="form.title" placeholder="文档标题" />
      </el-form-item>
      <el-form-item label="文件" required>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          :before-upload="beforeUpload"
          accept=".pdf,.md,.txt,.docx"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽文件至此或点击上传</div>
          <template #tip>
            <div class="el-upload__tip">
              支持 PDF / MD / TXT / DOCX，≤ 50MB
            </div>
          </template>
        </el-upload>
      </el-form-item>
      <el-form-item label="部门">
        <el-select v-model="form.department" class="w-full">
          <el-option label="全部" value="全部" />
          <el-option label="技术部" value="技术部" />
          <el-option label="产品部" value="产品部" />
          <el-option label="人事部" value="人事部" />
          <el-option label="财务部" value="财务部" />
          <el-option label="法务部" value="法务部" />
        </el-select>
      </el-form-item>
      <el-form-item label="安全级别">
        <el-radio-group v-model="form.securityLevel">
          <el-radio value="公开">公开</el-radio>
          <el-radio value="内部">内部</el-radio>
          <el-radio value="机密">机密</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="uploading" @click="handleUpload">
        上传
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadInstance, UploadFile } from 'element-plus'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  upload: [file: File, title: string, department: string, securityLevel: string]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})
</script>
```

Wait — `computed` needs importing. Let me fix this to be a complete file:

```vue
<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  upload: [file: File, title: string, department: string, securityLevel: string]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v)
})

const uploading = ref(false)
const formRef = ref()
const uploadRef = ref()

const form = reactive({
  title: '',
  department: '全部',
  securityLevel: '内部'
})

let selectedFile: File | null = null

const ALLOWED_TYPES = ['pdf', 'md', 'txt', 'docx']
const MAX_SIZE = 50 * 1024 * 1024

function beforeUpload(file: File): boolean {
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  if (!ALLOWED_TYPES.includes(ext)) {
    ElMessage.error('不支持的文件类型，仅支持 PDF / MD / TXT / DOCX')
    return false
  }
  if (file.size > MAX_SIZE) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return false // prevent auto upload, we handle it manually
}

function handleFileChange(file: UploadFile) {
  if (file.raw) {
    selectedFile = file.raw
  }
}

function handleFileRemove() {
  selectedFile = null
}

async function handleUpload() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入文档标题')
    return
  }
  if (!selectedFile) {
    ElMessage.warning('请选择文件')
    return
  }

  uploading.value = true
  try {
    emit('upload', selectedFile, form.title, form.department, form.securityLevel)
    visible.value = false
    resetForm()
  } finally {
    uploading.value = false
  }
}

function resetForm() {
  form.title = ''
  form.department = '全部'
  form.securityLevel = '内部'
  selectedFile = null
  uploadRef.value?.clearFiles()
}
</script>

<style scoped>
.w-full { width: 100%; }
</style>
```

Make sure the full `<template>` block (shown above) is included in the file.

- [ ] **Step 2: Create `java/frontend/src/components/document/DocumentTable.vue`**

```vue
<template>
  <el-table :data="documents" v-loading="loading" stripe>
    <el-table-column prop="id" label="ID" width="60" />
    <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
    <el-table-column prop="fileName" label="文件名" min-width="180" show-overflow-tooltip />
    <el-table-column prop="fileType" label="类型" width="70" />
    <el-table-column label="大小" width="90">
      <template #default="{ row }">
        {{ formatSize(row.fileSize) }}
      </template>
    </el-table-column>
    <el-table-column prop="department" label="部门" width="90" />
    <el-table-column label="安全级别" width="90">
      <template #default="{ row }">
        <el-tag
          :type="levelTag(row.securityLevel)"
          size="small"
        >
          {{ row.securityLevel }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="110">
      <template #default="{ row }">
        <el-tag :type="statusTag(row.status)" size="small">
          {{ statusLabel(row.status) }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="160" fixed="right">
      <template #default="{ row }">
        <el-button text type="primary" size="small" @click="$emit('index', row.id)">
          索引
        </el-button>
        <el-popconfirm
          title="确定删除此文档?"
          @confirm="$emit('delete', row.id)"
        >
          <template #reference>
            <el-button text type="danger" size="small">删除</el-button>
          </template>
        </el-popconfirm>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { DocumentItem } from '@/api/document'

defineProps<{
  documents: DocumentItem[]
  loading: boolean
}>()

defineEmits<{
  delete: [id: number]
  index: [id: number]
}>()

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / 1024 / 1024).toFixed(1) + 'MB'
}

function levelTag(level: string): string {
  const map: Record<string, string> = { '公开': 'success', '内部': 'warning', '机密': 'danger' }
  return map[level] || 'info'
}

function statusTag(status: string): string {
  const map: Record<string, string> = { 'UPLOADED': 'info', 'INDEXING': 'warning', 'COMPLETED': 'success', 'FAILED': 'danger' }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = { 'UPLOADED': '已上传', 'INDEXING': '索引中', 'COMPLETED': '已完成', 'FAILED': '失败' }
  return map[status] || status
}
</script>
```

- [ ] **Step 3: Create `java/frontend/src/views/DocumentsView.vue`**

```vue
<template>
  <div class="documents-layout">
    <AppHeader />
    <div class="documents-body">
      <div class="toolbar">
        <h3>文档管理</h3>
        <el-button type="primary" @click="uploadVisible = true">
          <el-icon><Plus /></el-icon>
          上传文档
        </el-button>
      </div>
      <div class="table-wrap">
        <DocumentTable
          :documents="store.documents"
          :loading="store.loading"
          @delete="handleDelete"
          @index="store.triggerIndex"
        />
      </div>
      <div class="pagination-wrap" v-if="store.total > 20">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="store.total"
          :page-size="20"
          @current-change="store.fetchList"
        />
      </div>
    </div>
    <UploadDialog
      v-model="uploadVisible"
      @upload="handleUpload"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import AppHeader from '@/components/common/AppHeader.vue'
import DocumentTable from '@/components/document/DocumentTable.vue'
import UploadDialog from '@/components/document/UploadDialog.vue'
import { useDocumentStore } from '@/stores/document'

const store = useDocumentStore()
const uploadVisible = ref(false)

onMounted(() => {
  store.fetchList()
})

function handleUpload(file: File, title: string, department: string, securityLevel: string) {
  store.upload(file, title, department, securityLevel)
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此文档?', '确认删除', { type: 'warning' })
    await store.deleteDoc(id)
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.documents-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.documents-body {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar h3 {
  font-size: 18px;
  color: #303133;
}
.table-wrap {
  background: #fff;
  border-radius: 8px;
}
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
```

- [ ] **Step 4: Create `java/frontend/src/views/AuditView.vue`**

```vue
<template>
  <div class="audit-layout">
    <AppHeader />
    <div class="audit-body">
      <h3>审计日志</h3>
      <el-table
        :data="logs"
        v-loading="loading"
        stripe
        @expand-change="handleExpand"
        class="audit-table"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <div class="expand-section">
                <h4>问题</h4>
                <p>{{ row.question }}</p>
              </div>
              <div class="expand-section">
                <h4>回答</h4>
                <p>{{ row.answer || '(无)' }}</p>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="userId" label="用户ID" width="80" />
        <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
        <el-table-column label="响应时间" width="100">
          <template #default="{ row }">
            {{ row.responseTime ? row.responseTime + 'ms' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="时间" width="170" />
      </el-table>
      <div class="pagination-wrap" v-if="total > 20">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="20"
          @current-change="fetchPage"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppHeader from '@/components/common/AppHeader.vue'
import { auditApi, AuditLogItem } from '@/api/audit'

const logs = ref<AuditLogItem[]>([])
const total = ref(0)
const loading = ref(false)

async function fetchPage(page: number = 1) {
  loading.value = true
  try {
    const result = await auditApi.list(page, 20)
    logs.value = result.content
    total.value = result.totalElements
  } finally {
    loading.value = false
  }
}

function handleExpand(_row: any, expandedRows: any[]) {
  // expand logic handled by el-table internally
}

onMounted(() => fetchPage())
</script>

<style scoped>
.audit-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.audit-body {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
}
.audit-body h3 {
  font-size: 18px;
  color: #303133;
  margin-bottom: 16px;
}
.audit-table {
  background: #fff;
  border-radius: 8px;
}
.expand-content {
  padding: 12px 40px;
}
.expand-section {
  margin-bottom: 12px;
}
.expand-section h4 {
  font-size: 14px;
  color: #909399;
  margin-bottom: 4px;
}
.expand-section p {
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
}
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
```

- [ ] **Step 5: Verify TypeScript compilation**

```bash
cd E:/vs code_coding/QA_agent/java/frontend
npx vue-tsc --noEmit
```

Expected: 编译通过。

- [ ] **Step 6: Commit**

```bash
git add java/frontend/src/views/DocumentsView.vue java/frontend/src/views/AuditView.vue java/frontend/src/components/document/
git commit -m "feat: add document management and audit log pages"
```

---

### Task 6: Launcher Integration and Final Verification

**Files:**
- Modify: `java/launcher/src/main/java/com/qa/launcher/LauncherApplication.java` — 添加 frontend 模块
- Modify: `java/frontend/src/views/LoginView.vue` — 确保 auto-redirect 工作

**Interfaces:**
- Consumes: `LauncherApplication` (existing), `package.json` scripts

- [ ] **Step 1: Read current `LauncherApplication.java`** and modify to add frontend module

在 `LauncherApplication.java` 中修改：

```java
private static final String[] MODULES = {"auth", "document", "chat", "audit", "frontend"};
private static final int[] PORTS = {8080, 8081, 8082, 8083, 5173};
```

对于 frontend 模块，不使用 `mvn spring-boot:run`，而是用 `npm run dev`。修改启动循环，在 `i == 4` (frontend) 时使用不同的 ProcessBuilder：

```java
// Inside the for loop, before ProcessBuilder:
if (i == 4) {
    // Frontend: use npm instead of mvn
    File frontendDir = new File(javaDir, "frontend");
    ProcessBuilder pb = new ProcessBuilder(
        isWindows() ? "npm.cmd" : "npm", "run", "dev"
    );
    pb.directory(frontendDir);
    pb.redirectErrorStream(true);
    pb.redirectOutput(ProcessBuilder.Redirect.to(logFile));
    // ... same start logic
}
```

For the health check, Vite dev server doesn't respond to `/api/auth/login` (it's a static file server + proxy), so the health check for port 5173 should just try `/`:

```java
private static boolean isPortReady(int port) {
    try {
        String path = port == 5173 ? "/" : "/api/auth/login";
        URL url = new URL("http://localhost:" + port + path);
        // ... rest unchanged
    }
}
```

The exact code changes for LauncherApplication.java should match the existing pattern closely. The key additions:

1. Extend MODULES to 5 entries including "frontend"
2. Extend PORTS to 5 entries including 5173
3. Add a check inside the start loop: `boolean isFrontend = module.equals("frontend");`
4. Use `npm run dev` for frontend, `mvn -pl {module} spring-boot:run` for others
5. Health check uses `/` for port 5173, `/api/auth/login` for others

- [ ] **Step 2: Update `java/pom.xml`** — verify `<module>frontend</module>` is present (done in Task 1 Step 13)

- [ ] **Step 3: Verify full build**

```bash
cd E:/vs code_coding/QA_agent/java/frontend
npm run build
```

Expected: Vite builds successfully, output in `spring/src/main/resources/static/`.

```bash
cd E:/vs code_coding/QA_agent/java
mvn clean install -DskipTests -pl frontend/spring -am
```

Expected: Spring Boot wrapper builds successfully.

- [ ] **Step 4: Verify launcher compiles**

```bash
cd E:/vs code_coding/QA_agent/java
mvn compile -pl launcher
```

Expected: Launcher compiles with new frontend module.

- [ ] **Step 5: Commit**

```bash
git add java/launcher/src/main/java/com/qa/launcher/LauncherApplication.java
git commit -m "feat: add frontend module to one-click launcher"
```

---

## Verification

Full system startup:
```bash
cd E:/vs code_coding/QA_agent/java
mvn clean install -DskipTests
mvn -pl launcher exec:java
```

Expected: All 5 modules start, frontend is accessible at `http://localhost:5173`, login redirect works, chat SSE streaming works, document upload works, audit log page visible for admin users.
