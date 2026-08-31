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
      → DeepSeek API   (chat completions + tool calling; no embedding endpoint)
      → Qdrant :6333   (vector search + payload storage)
      → MinIO :9000    (file storage)
  ↕ WebSocket :8081    (index progress broadcast: Python → Java → Browser)
```

### Key data flows

1. **Document indexing:** User uploads file → Java Document saves to MinIO → calls Python `/api/agent/index` → Python downloads from MinIO, loads (images & scanned PDFs go through PaddleOCR-VL MCP OCR first), chunks, embeds, stores in Qdrant → Python POSTs progress to Java `/api/documents/index-progress/{docId}` → Java broadcasts via WebSocket to browser
2. **RAG chat (`mode=rag`):** Question → Java Chat → Python `/api/agent/chat/stream` → hybrid_search Qdrant → DeepSeek LLM generate → SSE stream (thinking → answer tokens → citations → done)
3. **Agent chat (`mode=agent`):** Question → Java Chat → Python → LangGraph ReAct loop (agent_node ⇄ tools_node) → SSE stream (thought → action → observation → ... → answer tokens → done)
4. **Search-only (`mode=search-only`):** Question → Java Chat → Python → hybrid_search Qdrant → SSE stream (thinking → citations → done), no LLM call
5. **Audit & history:** Java Chat saves `AuditLog` (question/answer/responseTime/errorMessage) and `Message` (with citations/agentSteps JSON) for every Q&A. Conversation history persists across sessions.

### LangGraph Agent (ReAct pattern)

The Agent uses LangGraph's `StateGraph` with `MemorySaver` checkpointer for multi-turn reasoning:

```
START → agent_node (LLM decision: search or answer?)
           ↓
    conditional_edge:
    ├── has tool_calls → tools_node → agent_node (loop, max recursion_limit: 10)
    └── no tool_calls → END (final answer)
```

**3 Tools** (defined in `python/agent/tools.py`, converted to OpenAI function-calling format):
- `search_knowledge(query, category, department)` — unified knowledge base search (category="policy"/"tech_doc"/"all")
- `search_employee(query)` — employee org chart and contact info search
- `get_doc_detail(doc_id)` — fetch full document text by ID

**Critical implementation detail:** The agent streams via `graph.astream(stream_mode="values")` — NOT `astream_events(v2)`. The latter only fires `on_chat_model_*` events for LangChain ChatModel wrappers, but `agent_node` calls `chat_sync()` (a direct OpenAI client wrapper), so those events never fire. `stream_mode="values"` emits the full accumulated state after each node, allowing direct message inspection.

**Message conversion:** `_to_api_messages()` in `deepseek_client.py` converts LangChain message types (`msg.type` = "human"/"ai"/"system"/"tool") to OpenAI API format (`role` = "user"/"assistant"/"system"/"tool"). LangChain `AIMessage.tool_calls` uses `{name, args, id}` dicts; the OpenAI API expects `{id, type, function: {name, arguments: json_string}}`.

### Agent 3-tier auto-downgrade

When `mode=agent` is requested, `_agent_stream()` in `agent_routes.py` implements a transparent fallback chain:

```
Tier 1: Agent ReAct reasoning (LangGraph StateGraph)
  ↓ on exception/timeout/no-answer
Tier 2: Downgrade to RAG mode (hybrid_search + LLM generation)
  ↓ on exception/failure
Tier 3: Downgrade to search-only mode (hybrid_search, no LLM)
  ↓ on exception/failure
Tier 4: Fallback message ("系统暂时无法处理您的问题...")
```

Each downgrade emits an SSE `downgrade` event so the frontend can display the transition.

### API conventions

- All Java REST responses wrapped in `ApiResult<T>`: `{ code: 200, message: "success", data: T }`
- Frontend checks `code === 200` to determine success
- Java → Python uses `X-API-Key` header authentication (default: `qa-agent-internal-api-key-2026`)
- Python SSE format: `data: {"type":"answer","content":"..."}\n\n` (note: no mandatory space after `data:`, but parsing tolerates it)
- **Critical:** Java uses camelCase in DTOs; Python Pydantic uses snake_case. When Java constructs Map bodies for Python, keys must be snake_case (e.g., `file_path`, `file_type`, `callback_url`)
- **Critical:** Pydantic v2 rejects `null` for `List[HistoryMessage]` — Java must send `[]` not `null` for empty history
- Java Chat sends `X-User-Role`, `X-User-Department`, `X-Conversation-Id` headers to Python for permission filtering

### SSE event types

| Type | Direction | Meaning |
|------|-----------|---------|
| `thinking` | Python → Browser | RAG pipeline step (retrieving, reranking, generating) |
| `answer` | Python → Browser | LLM answer text (token-by-token for rag, char-by-char for agent) |
| `citation` | Python → Browser | Source document reference with metadata |
| `thought` | Python → Browser | Agent begins reasoning |
| `action` | Python → Browser | Agent calls a tool (includes tool name + args) |
| `observation` | Python → Browser | Tool execution result (first 200 chars) |
| `downgrade` | Python → Browser | Agent degraded to fallback mode (includes from/to in data) |
| `done` | Python → Browser | Stream complete |
| `error` | Python → Browser | Stream error (includes error detail string) |

### Permission Model

Role-based access control with 4 roles. Department stored in JWT claims + `UserPrincipal` POJO (`java/common/`):

| Permission | ROLE_EMPLOYEE | ROLE_LEADER | ROLE_HR | ROLE_ADMIN |
|------------|:---:|:---:|:---:|:---:|
| Q&A (all modes) | ✓ | ✓ | ✓ | ✓ |
| Document mgmt (own dept) | ✗ | ✓ | ✓ | ✓ |
| Document mgmt (all depts) | ✗ | ✗ | ✓ | ✓ |
| Audit log (view + delete) | ✗ | ✗ | ✗ | ✓ |

Role mapping on registration (`AuthServiceImpl.mapPositionToRole()`):
- "普通员工" → ROLE_EMPLOYEE
- "部门主管" → ROLE_LEADER
- "人事专员" → ROLE_HR
- "部门经理" → ROLE_ADMIN

Implementation details:
- `@EnableMethodSecurity` on `SecurityConfig.java` — required for `@PreAuthorize` to take effect
- `DocumentController.java` class-level: `@PreAuthorize("!hasAuthority('ROLE_EMPLOYEE')")`
- `AuditLogController.java` delete endpoints: `@PreAuthorize("hasAuthority('ROLE_ADMIN')")`
- `DocumentServiceImpl.list()`: ROLE_LEADER → `findByDepartment()`; ROLE_HR/ROLE_ADMIN → `findAll()`
- `GlobalExceptionHandler`: maps error code 4003 → HTTP 403, 4004 → HTTP 404
- Frontend: `authStore.canManageDocuments` (non-employee), `authStore.isAdmin` controls nav visibility

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
# Start with HuggingFace offline (HF blocked in China; embedder uses sklearn fallback)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
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

# Search-only mode
curl -s -N -X POST "http://localhost:8000/api/agent/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: qa-agent-internal-api-key-2026" \
  -H "X-User-Role: ROLE_EMPLOYEE" \
  -d '{"question":"test","mode":"search-only","history":[]}'
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
- `audit_log` — audit module (user_id, question TEXT, answer TEXT, tools_called JSON, response_time INT, token_usage JSON, error_message TEXT, created_at)

## Windows-Specific Pitfalls

- `mvn` and `npm` in Java `ProcessBuilder` need `.cmd` suffix and full path resolution
- MinIO Python client's `fget_object()` fails on Windows due to file locking; use `get_object().stream()` instead
- Launcher `main()` must call `Thread.currentThread().join()` to prevent JVM exit killing child processes
- CRLF/LF warnings on git operations are cosmetic and harmless
- Chinese characters in curl requests may fail with `Invalid UTF-8 middle byte` on Windows — use `-d @file.json` with a temp file, or test via the frontend browser
- When killing and restarting Python services, ensure old processes don't linger on the port (use `netstat -ano | grep :8000` to verify)
- HuggingFace is blocked in China — Python AI must be started with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` to skip HF HTTP checks. BGE-M3 is the **primary embedder**: weights are cached locally, `sentence-transformers`/`torch` come from the portable install on `D:/python-packages` (auto-inserted into `sys.path`), and init validates `encode()` with a 30s `ThreadPoolExecutor` timeout to avoid hangs

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
│   │   ├── main.py                     # FastAPI entry point, CORS, startup pre-warming (Qdrant + BM25 + embedder)
│   │   ├── dependencies.py             # X-API-Key verification
│   │   ├── routes/agent_routes.py      # /index, /index/{id}, /chat/stream (rag/agent/search-only + 3-tier downgrade)
│   │   ├── routes/health_routes.py     # /health
│   │   └── schemas/                    # ChatRequest, ChatResponse, HistoryMessage, IndexRequest
│   ├── agent/
│   │   ├── state.py                    # AgentState TypedDict (messages, department, security_level, retrieved_docs)
│   │   ├── tools.py                    # 3 tools: search_knowledge, search_employee, get_doc_detail
│   │   ├── nodes.py                    # agent_node (LLM + tool_calls), tools_node (ToolMessage execution)
│   │   └── graph.py                    # StateGraph: agent → conditional_edge → tools → agent (loop)
│   ├── rag/
│   │   ├── loader.py                   # Downloads from MinIO/HTTP, loads PDF/MD/TXT/DOCX; images & scanned PDFs → OCR
│   │   ├── ocr_mcp.py                  # PaddleOCR-VL MCP client (stdio) — paddleocr_vl tool → Markdown
│   │   ├── splitter.py                 # Chunking (MD by headings, PDF/DOCX by size)
│   │   ├── embedder.py                 # Embedding fallback: BGE-M3 (1024-dim) → DeepSeek API (1536) → sklearn (384)
│   │   ├── indexer.py                  # Qdrant upsert + HTTP progress callbacks to Java
│   │   ├── retriever.py               # Hybrid search (BM25 + vector) with RRF fusion, department/security_level filters
│   │   └── bm25_index.py              # BM25 keyword index rebuilt from Qdrant on startup
│   ├── eval/
│   │   └── __init__.py                 # Evaluation utilities
│   └── llm/
│       ├── rag_chain.py               # RAG pipeline: retrieve → rerank → prompt → LLM stream → citations
│       └── deepseek_client.py         # chat_stream (yield tokens) + chat_sync (non-streaming with tools) + token management
├── java/
│   ├── pom.xml                         # Parent POM (Spring Boot 3.5.16, Java 21)
│   ├── common/                         # ApiResult, PageResult, ErrorCode, BusinessException, UserPrincipal
│   ├── auth/                           # JWT auth + @EnableMethodSecurity + JwtAuthFilter (UserPrincipal from JWT)
│   ├── document/                       # Document CRUD, MinIO upload, async Python indexing, role-based access
│   │   ├── ws/IndexProgressHandler.java    # WebSocket handler for real-time index progress
│   │   └── config/WebSocketConfig.java     # WebSocket endpoint registration
│   ├── chat/                           # SSE proxy to Python, conversation/audit persistence, error detail capture
│   │   ├── entity/Conversation.java    # JPA: id, userId, title, timeestamps
│   │   ├── entity/Message.java         # JPA: role, content, citations(JSON), agentSteps(JSON)
│   │   ├── dto/ChatRequest.java        # question, history, mode, conversationId
│   │   ├── dto/ChatResponse.java       # type, content, data (builder pattern)
│   │   └── service/impl/ChatServiceImpl.java  # SSE proxy + conversation/audit persistence + error extraction
│   ├── audit/                          # Q&A history CRUD + batch delete (admin-only via @PreAuthorize)
│   ├── launcher/                       # ProcessBuilder one-click launcher
│   └── frontend/                       # Vue 3 SPA (Vite + Element Plus + Pinia)
│       └── src/
│           ├── api/chat.ts             # SSE fetch-based stream client (Fetch API + AbortController)
│           ├── api/audit.ts            # Audit log API (list + delete + batchDelete)
│           ├── router/index.ts         # /chat, /documents (non-employee), /audit (admin), /login
│           ├── stores/                 # Pinia: auth (role checks), chat (messages + conversations), document
│           ├── components/chat/        # ChatInput, ChatMessage, AgentThinking, ConversationList
│           └── views/                  # ChatView, DocumentsView, AuditView (with batch delete), LoginView
```

## OCR (PaddleOCR-VL MCP)

Images (png/jpg/jpeg/bmp/tif/tiff/webp) and scanned PDFs (no text layer) are recognized via the PaddleOCR-VL MCP server (`paddleocr-mcp` package), tool `paddleocr_vl`, returning Markdown that then enters the normal chunk/embed/index pipeline.

- **Module:** `python/rag/ocr_mcp.py` — starts `paddleocr_mcp` subprocess over MCP stdio, calls the `paddleocr_vl` tool with a local absolute path + `file_type` ("image"/"pdf").
- **Detection:** `_is_scanned_pdf()` in `loader.py` uses PyMuPDF; if average chars/page < 20 (or total < 50) the PDF is treated as scanned and falls back to OCR. Text-layer PDFs keep the original `PyMuPDFLoader` path.
- **Config (env vars):** `PADDLEOCR_MCP_MODEL` (default `PaddleOCR-VL-1.6`), `PADDLEOCR_MCP_PPOCR_SOURCE` (default `aistudio`), `PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN` (required for aistudio). qianfan/self_hosted/local sources are supported via their respective env vars.
- **Threading constraint:** the OCR module uses `asyncio.run()` internally, so `/api/agent/index` and `/api/agent/index/{id}` routes execute `index_document`/`delete_document_chunks` inside `asyncio.to_thread` (also prevents blocking the event loop).
- **Graceful degradation:** if `paddleocr_mcp` is missing or credentials are unconfigured, `is_ocr_available()` returns False and image/scanned-PDF indexing fails with a clear `OcrUnavailableError`; regular documents are unaffected.

## RAG & Agent Pipeline Details

- **Embedding:** 3-tier fallback — BGE-M3 local (1024-dim; primary) → DeepSeek API via OpenAIEmbeddings (1536-dim) → sklearn HashingVectorizer (384-dim, guaranteed). BGE-M3 is loaded offline from the local HF cache (portable `D:/python-packages` install) and its `encode()` is smoke-tested under a 30s timeout before being activated. DeepSeek has no dedicated embedding endpoint (returns 404 on `deepseek-chat`), so its tier only activates if an OpenAI-compatible embedder is reachable.
- **Chunking:** MD uses MarkdownHeaderTextSplitter by H2/H3 headings; PDF/TXT/DOCX uses RecursiveCharacterTextSplitter (800 char chunks, 150 overlap)
- **Retrieval:** Hybrid BM25 (keyword) + Qdrant vector (semantic) dual-recall → RRF fusion. BM25 always works; vector search depends on embedder compatibility with stored vectors. `_ensure_collection()` in `indexer.py` checks the collection's `vector_size` against the current embedder on every index/delete — if they mismatch (e.g. embedder tier changed) it recreates the collection and rebuilds BM25, avoiding silent write failures. `department` filter uses MatchAny(["Tech", "全部"]); `security_level` filter excludes "机密" for non-privileged users (ROLE_EMPLOYEE, ROLE_LEADER). Returns empty results gracefully if collection doesn't exist.
- **Reranker:** `rerank_listwise()` in `python/rag/reranker.py` — uses DeepSeek LLM to score and re-rank top-10 candidates down to top-5 before prompt construction.
- **RAG prompt:** System prompt instructs LLM to answer only from reference docs, cite sources, admit gaps honestly
- **Agent prompt:** Defines Thought→Action→Observation ReAct workflow with 3 tools. Emphasizes no fabrication, cite sources, refuse out-of-scope questions.
- **Agent streaming:** Uses `graph.astream(stream_mode="values")` with `recursion_limit: 10`. Each chunk is the full accumulated state; new messages are identified by tracking `msg_count`. Tool call messages (AIMessage with tool_calls) and tool results (ToolMessage with tool_call_id) are yielded as SSE action/observation events. The final AIMessage without tool_calls is the answer.
- **Tool calling:** Agent tools are converted to OpenAI function-calling format. `chat_sync()` passes `tools` + `tool_choice="auto"` to DeepSeek API. Response tool_calls are parsed into AIMessage tool_calls dicts `{id, name, args}`.
- **Token management:** `TOKEN_BUDGET = 8000`. `count_tokens()` uses tiktoken `cl100k_base`. `summarize_history()` compresses older messages via DeepSeek flash model. `ensure_token_budget()` hard-truncates from head if budget exceeded.
- **Error handling:** All Python LLM/embedding calls wrapped in try/catch with detailed error messages. Errors propagate via SSE `error` events → Java `doOnError` → `AuditLog.errorMessage`. Frontend displays error details in audit log view.
