# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Enterprise internal Q&A system (MVP) — RAG-based intelligent assistant for company policy and technical documents. Two-layer architecture: Java Spring Boot business services + Python FastAPI AI service, with Qdrant vector DB and MinIO object storage via Docker.

## Architecture

```
Browser (Vue 3 SPA, port 5173 dev / port 80 prod via Nginx)
  → Java Chat :8082    (SSE proxy to Python, conversation persistence)
  → Java Auth :8080    (JWT login/register)
  → Java Document :8081 (CRUD + MinIO upload + triggers Python indexing)
  → Java Audit :8083   (Q&A history, admin-only)
    → Python AI :8000  (FastAPI — RAG retrieval + LangGraph Agent + DeepSeek LLM)
      → DeepSeek API   (embeddings + chat completions with tool calling)
      → Qdrant :6333   (vector search)
      → MinIO :9000    (file storage)
  ↕ WebSocket :8081    (index progress broadcast: Python → Java → Browser)
```

### Key data flows

1. **Document indexing:** User uploads file → Java Document saves to MinIO → calls Python `/api/agent/index` → Python downloads from MinIO, chunks, embeds, stores in Qdrant → Python POSTs progress to Java `/api/documents/index-progress/{docId}` → Java broadcasts via WebSocket to browser
2. **RAG chat (`mode=rag`):** Question → Java Chat → Python `/api/agent/chat/stream` → hybrid_search Qdrant → DeepSeek LLM generate → SSE stream (thinking → answer tokens → citations → done)
3. **Agent chat (`mode=agent`):** Question → Java Chat → Python → LangGraph ReAct loop (agent_node ⇄ tools_node) → SSE stream (thought → action → observation → ... → answer tokens → done)
4. **Search-only (`mode=search-only`):** Question → Java Chat → Python → hybrid_search Qdrant → SSE stream (thinking → citations → done), no LLM call
5. **Audit & history:** Java Chat saves `AuditLog` (question/answer/responseTime) and `Message` (with citations/agentSteps JSON) for every Q&A. Conversation history persists across sessions.

### LangGraph Agent (ReAct pattern)

The Agent uses LangGraph's `StateGraph` with `MemorySaver` checkpointer for multi-turn reasoning:

```
START → agent_node (LLM decision: search or answer?)
           ↓
    conditional_edge:
    ├── has tool_calls → tools_node → agent_node (loop, max recursion_limit: 10)
    └── no tool_calls → END (final answer)
```

**4 Tools** (defined in `python/agent/tools.py`, converted to OpenAI function-calling format):
- `search_policy(query, department)` — search policies with department filter
- `search_doc(query, tags)` — search technical docs
- `search_employee(query)` — placeholder ("功能开发中")
- `get_doc_detail(doc_id)` — placeholder ("功能开发中")

**Critical implementation detail:** The agent streams via `graph.astream(stream_mode="values")` — NOT `astream_events(v2)`. The latter only fires `on_chat_model_*` events for LangChain ChatModel wrappers, but `agent_node` calls `chat_sync()` (a direct OpenAI client wrapper), so those events never fire. `stream_mode="values"` emits the full accumulated state after each node, allowing direct message inspection.

**Message conversion:** `_to_api_messages()` in `deepseek_client.py` converts LangChain message types (`msg.type` = "human"/"ai"/"system"/"tool") to OpenAI API format (`role` = "user"/"assistant"/"system"/"tool"). LangChain `AIMessage.tool_calls` uses `{name, args, id}` dicts; the OpenAI API expects `{id, type, function: {name, arguments: json_string}}`.

### API conventions

- All Java REST responses wrapped in `ApiResult<T>`: `{ code: 200, message: "success", data: T }`
- Frontend checks `code === 200` to determine success
- Java → Python uses `X-API-Key` header authentication (default: `qa-agent-internal-api-key-2026`)
- Python SSE format: `data: {"type":"answer","content":"..."}\n\n` (note: no mandatory space after `data:`, but parsing tolerates it)
- **Critical:** Java uses camelCase in DTOs; Python Pydantic uses snake_case. When Java constructs Map bodies for Python, keys must be snake_case (e.g., `file_path`, `file_type`, `callback_url`)
- **Critical:** Pydantic v2 rejects `null` for `List[HistoryMessage]` — Java must send `[]` not `null` for empty history

### SSE event types

| Type | Direction | Meaning |
|------|-----------|---------|
| `thinking` | Python → Browser | RAG pipeline step (retrieving, generating) |
| `answer` | Python → Browser | LLM answer text (token-by-token for rag, char-by-char for agent) |
| `citation` | Python → Browser | Source document reference with metadata |
| `thought` | Python → Browser | Agent begins reasoning |
| `action` | Python → Browser | Agent calls a tool (includes tool name + args) |
| `observation` | Python → Browser | Tool execution result (first 200 chars) |
| `done` | Python → Browser | Stream complete |
| `error` | Python → Browser | Stream error |

## Common Commands

### Infrastructure (Docker Desktop required)

```bash
# Development (Qdrant + MinIO only)
cd docker && docker compose up -d qdrant minio
docker compose down

# Full deployment (MySQL + Qdrant + MinIO + Python + Java + Nginx)
cd docker && docker compose --profile full up -d
# Or if no profiles defined:
cd docker && docker compose up -d
```

### Python AI service

```bash
cd python
poetry install                        # Install dependencies
poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Java (all modules must compile together)

```bash
cd java
mvn clean install -DskipTests         # Full build
mvn -pl <module> spring-boot:run      # Run single module (e.g., -pl auth)

# One-click launcher (starts all 5 modules: auth/document/chat/audit/frontend)
mvn -pl launcher exec:java -Dexec.mainClass="com.qa.launcher.LauncherApplication"
```

### Frontend

```bash
cd java/frontend
npm install
npm run dev                           # Vite dev server on :5173, proxies API to Java modules
```

### Run a single test

```bash
cd java
mvn -pl <module> test -Dtest=<TestClass> -DfailIfNoTests=false
```

### Direct API testing (Python)

```bash
# RAG mode
curl -s -N -X POST "http://localhost:8000/api/agent/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: qa-agent-internal-api-key-2026" \
  -H "X-User-Role: ROLE_EMPLOYEE" \
  -d '{"question":"test","mode":"rag","history":[]}'

# Agent mode
curl -s -N -X POST "http://localhost:8000/api/agent/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: qa-agent-internal-api-key-2026" \
  -H "X-User-Role: ROLE_EMPLOYEE" \
  -d '{"question":"test","mode":"agent","history":[]}'
```

### Service ports

| Service | Port |
|---------|------|
| Python AI | 8000 |
| Java Auth | 8080 |
| Java Document | 8081 |
| Java Chat | 8082 |
| Java Audit | 8083 |
| Frontend (dev) | 5173 |
| Frontend (prod, via Nginx) | 80 |
| MySQL | 3306 |
| Qdrant REST | 6333 |
| Qdrant gRPC | 6334 |
| MinIO API | 9000 |
| MinIO Console | 9001 |

## Database Schema

JPA `ddl-auto: update` auto-creates tables. Key tables:

- `sys_user` — auth module (username, password, role, department)
- `doc_document` — document module (title, file_path, file_type, department, security_level, index_status)
- `conversation` — chat module (user_id, title, created_at, updated_at)
- `chat_message` — chat module (conversation_id, role, content TEXT, citations TEXT JSON, agent_steps TEXT JSON, timestamp)
- `audit_log` — audit module (user_id, question TEXT, answer TEXT, tools_called JSON, response_time INT, token_usage JSON, created_at)

## Windows-Specific Pitfalls

- `mvn` and `npm` in Java `ProcessBuilder` need `.cmd` suffix and full path resolution
- MinIO Python client's `fget_object()` fails on Windows due to file locking; use `get_object().stream()` instead
- Launcher `main()` must call `Thread.currentThread().join()` to prevent JVM exit killing child processes
- CRLF/LF warnings on git operations are cosmetic and harmless
- Chinese characters in curl requests may fail with `Invalid UTF-8 middle byte` on Windows — use `-d @file.json` with a temp file, or test via the frontend browser
- When killing and restarting Python services, ensure old processes don't linger on the port (use `netstat -ano | grep :8000` to verify)

## Project Structure

```
QA_agent/
├── docker/
│   ├── docker-compose.yml              # 6 services: mysql, qdrant, minio, python-agent, java-app, nginx
│   ├── Dockerfile.nginx                # Multi-stage: Node build + Nginx serve
│   └── .env.docker                     # Docker environment variables template
├── .env                                # API keys + MinIO credentials (gitignored)
├── python/
│   ├── api/
│   │   ├── main.py                     # FastAPI entry point, CORS, two routers under /api/agent
│   │   ├── dependencies.py             # X-API-Key verification
│   │   ├── routes/agent_routes.py      # /index, /index/{id}, /chat/stream (rag/agent/search-only)
│   │   ├── routes/health_routes.py     # /health
│   │   └── schemas/                    # ChatRequest, ChatResponse, HistoryMessage, IndexRequest
│   ├── agent/
│   │   ├── state.py                    # AgentState TypedDict (messages, department, security_level, retrieved_docs)
│   │   ├── tools.py                    # 4 LangChain tools: search_policy, search_doc, search_employee, get_doc_detail
│   │   ├── nodes.py                    # agent_node (LLM + tool_calls), tools_node (ToolMessage execution)
│   │   └── graph.py                    # StateGraph: agent → conditional_edge → tools → agent (loop)
│   ├── rag/
│   │   ├── loader.py                   # Downloads from MinIO/HTTP, loads PDF/MD/TXT/DOCX
│   │   ├── splitter.py                 # Chunking (MD by headings, PDF/DOCX by size)
│   │   ├── embedder.py                 # Embedding (DeepSeek API → HuggingFace → sklearn HashingVectorizer)
│   │   ├── indexer.py                  # Qdrant upsert + HTTP progress callbacks to Java
│   │   └── retriever.py               # Hybrid search with department/security_level filters
│   └── llm/
│       ├── rag_chain.py               # RAG pipeline: retrieve → prompt → LLM stream → citations
│       └── deepseek_client.py         # chat_stream (yield tokens) + chat_sync (non-streaming with tools)
├── java/
│   ├── pom.xml                         # Parent POM (Spring Boot 3.5.16, Java 21)
│   ├── common/                         # ApiResult, PageResult, ErrorCode, BusinessException
│   ├── auth/                           # JWT auth (login, register, SecurityConfig, JwtAuthFilter)
│   ├── document/                       # Document CRUD, MinIO upload, async Python indexing
│   │   ├── ws/IndexProgressHandler.java    # WebSocket handler for real-time index progress
│   │   └── config/WebSocketConfig.java     # WebSocket endpoint registration
│   ├── chat/                           # SSE proxy to Python, conversation persistence, audit logging
│   │   ├── entity/Conversation.java    # JPA: id, userId, title, timeestamps
│   │   ├── entity/Message.java         # JPA: role, content, citations(JSON), agentSteps(JSON)
│   │   ├── dto/ChatRequest.java        # question, history, mode, conversationId
│   │   ├── dto/ChatResponse.java       # type, content, data (builder pattern)
│   │   └── service/impl/ChatServiceImpl.java  # SSE proxy + conversation/audit persistence
│   ├── audit/                          # Q&A history query (admin-only, paginated)
│   ├── launcher/                       # ProcessBuilder one-click launcher
│   └── frontend/                       # Vue 3 SPA (Vite + Element Plus + Pinia)
│       └── src/
│           ├── api/chat.ts             # SSE fetch-based stream client (Fetch API + AbortController)
│           ├── router/index.ts         # /chat, /documents, /audit (admin), /login
│           ├── stores/                 # Pinia: auth, chat (messages + conversations), document
│           ├── components/chat/        # ChatInput, ChatMessage, AgentThinking, ConversationList
│           └── views/                  # ChatView, DocumentsView, AuditView, LoginView
```

## RAG & Agent Pipeline Details

- **Embedding:** 3-tier fallback — DeepSeek API (1536-dim) → HuggingFace `all-MiniLM-L6-v2` (384-dim, local) → sklearn HashingVectorizer (384-dim, guaranteed). First successful init wins.
- **Chunking:** MD uses MarkdownHeaderTextSplitter by H2/H3 headings; PDF/TXT/DOCX uses RecursiveCharacterTextSplitter (800 char chunks, 150 overlap)
- **Retrieval:** Semantic search via Qdrant with `department` (MatchAny) and `security_level` (MatchExcept for non-privileged users) filters. Returns empty results gracefully if collection doesn't exist.
- **RAG prompt:** System prompt instructs LLM to answer only from reference docs, cite sources, admit gaps honestly
- **Agent prompt:** Defines Thought→Action→Observation ReAct workflow. 4 tools available. Emphasizes no fabrication, cite sources, refuse out-of-scope questions.
- **Agent streaming:** Uses `graph.astream(stream_mode="values")` with `recursion_limit: 10`. Each chunk is the full accumulated state; new messages are identified by tracking `msg_count`. Tool call messages (AIMessage with tool_calls) and tool results (ToolMessage with tool_call_id) are yielded as SSE action/observation events. The final AIMessage without tool_calls is the answer.
- **Tool calling:** Agent tools are converted to OpenAI function-calling format. `chat_sync()` passes `tools` + `tool_choice="auto"` to DeepSeek API. Response tool_calls are parsed into AIMessage tool_calls dicts `{id, name, args}`.
