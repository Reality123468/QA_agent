# 图片/扫描件 OCR 支持（PaddleOCR-VL MCP）设计

**版本**：v1.0
**日期**：2026-08-31
**关联**：企业内部规章制度与技术文档智能问答系统 PRD.md；CLAUDE.md

---

## 一、背景与目标

系统当前仅支持上传 `pdf / md / txt / docx`，无法处理**图片**（JPG/PNG 等）与**扫描版 PDF**（无文本层），这类文档无法进入 RAG 知识库。

本次迭代通过接入 **PaddleOCR-VL-1.6 的 MCP Server**（`paddleocr-mcp` 的 `paddleocr_vl` 工具），为文档索引流程增加 OCR 能力：

1. 图片格式上传后自动 OCR，识别文字进入知识库；
2. 扫描版 PDF（无文本层）自动回退 OCR；
3. 有文本层的 PDF 保持原 PyMuPDF 解析逻辑，**零回归**；
4. 通过环境变量选择推理后端（aistudio / qianfan / local / self_hosted），默认 AI Studio。

## 二、技术方案

### 2.1 接入链路

```
Java Document :8081（上传图片/扫描 PDF → MinIO）
  → Python /api/agent/index
    → rag.loader.load_document()
      ├── 图片 → rag.ocr_mcp.ocr_parse(file, "image")   ┐
      ├── 扫描 PDF → rag.ocr_mcp.ocr_parse(file, "pdf")  ├─ MCP stdio 调用
      └── 文本 PDF/MD/TXT/DOCX → 原解析逻辑（不变）       ┘
    → 分块 → 向量化 → Qdrant
```

### 2.2 MCP 客户端（`python/rag/ocr_mcp.py`）

- 通过 **MCP 协议（stdio 传输）** 启动 `paddleocr_mcp` 子进程，调用 `paddleocr_vl` 工具；
- 工具输入 `input_data` 传本地文件绝对路径，`file_type` 区分 `image` / `pdf`；
- 输出为 Markdown 文本（版面解析结果），供后续分块索引；
- 模型名：`PaddleOCR-VL-1.6`（MCP 侧 SUPPORTED_MODELS 包含该版本，映射到 `paddleocr_vl` 工具）。

### 2.3 关键实现细节

1. **事件循环约束**：`asyncio.run()` 不能在已有事件循环的线程中调用。原 `/api/agent/index` 路由在 async 函数内同步执行 `index_document`（运行于事件循环线程），现改为 `await asyncio.to_thread(index_document, ...)`，既释放事件循环，又让 OCR 模块内部能安全 `asyncio.run()`。
2. **扫描 PDF 判定**：`_is_scanned_pdf()` 用 PyMuPDF 统计文本层，平均每页字符 < 20 或全文 < 50 字符判定为扫描件，回退 OCR。
3. **优雅降级**：OCR 依赖缺失 / 凭据未配置时 `is_ocr_available() == False`，图片与扫描 PDF 索引直接报错并明确提示（避免静默产生空索引）；常规文档不受影响。
4. **凭据不落盘**：AI Studio token 仅通过环境变量传入子进程，不写入日志。

### 2.4 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PADDLEOCR_MCP_MODEL` | `PaddleOCR-VL-1.6` | 模型名（支持 `-1.5` / `-1.6`） |
| `PADDLEOCR_MCP_PPOCR_SOURCE` | `aistudio` | 推理后端 |
| `PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN` | 空 | AI Studio 令牌（aistudio 必填） |
| `PADDLEOCR_MCP_QIANFAN_API_KEY` | 空 | 千帆 Key（qianfan 必填） |
| `PADDLEOCR_MCP_SELF_HOSTED_BASE_URL` | 空 | 自建服务地址（self_hosted 必填） |

## 三、涉及文件

| 文件 | 动作 |
|------|------|
| `python/rag/ocr_mcp.py` | **新增** — MCP 客户端模块 |
| `python/rag/loader.py` | 修改 — 图片/扫描 PDF 走 OCR；常规类型不变 |
| `python/rag/indexer.py` | 修改 — 图片索引阶段进度提示 |
| `python/api/routes/agent_routes.py` | 修改 — index/delete 改 `asyncio.to_thread` |
| `python/pyproject.toml` | 修改 — 新增 `paddleocr-mcp` 依赖；版本声明与实际环境对齐 |
| `python/tests/test_ocr_mcp.py` | **新增** — OCR 客户端单元测试 |
| `python/tests/test_loader.py` | **新增** — loader OCR 集成与回归测试 |
| `java/document/.../DocumentServiceImpl.java` | 修改 — 上传类型白名单增加图片 |
| `java/frontend/.../UploadDialog.vue` | 修改 — 上传接受类型与提示 |
| `.env` / `.env.example` | 修改 — OCR 环境变量 |

## 四、测试计划

1. 单元测试（`python/tests/`）：
   - OCR 模块：可用性判断、参数构造、结果解析、错误路径；
   - loader：图片走 OCR、扫描 PDF 回退 OCR、文本 PDF/TXT/DOCX 回归、不支持类型报错。
2. 集成测试：配置 AI Studio token 后，真实调用 OCR 识别一张包含文字的图片，验证输出 Markdown。
3. 全栈冒烟：Docker 启动 Qdrant/MinIO → Python → Java → 前端，上传图片并索引进问答库，问答验证召回。

## 五、风险与注意事项

- **AI Studio API 限流/配额**：批量索引大量图片前需关注配额。
- **OCR 耗时**：版面解析较慢，索引进度条已通过 WebSocket 呈现，属可接受范围。
- **本地推理**：`local` 后端需下载 PaddleOCR-VL 模型权重（数 GB），仅建议 GPU/高端机器使用。
- **Windows 路径**：MCP stdio 子进程传递的绝对路径需为系统可访问路径（temp 目录），已由 `_resolve_path()` 保证。
