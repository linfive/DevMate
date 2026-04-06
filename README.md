## DevMate

DevMate 是一个 AI 驱动的编程助手（CLI 交互），具备：
- MCP 网络搜索（Tavily）
- 本地文档 RAG 检索（ChromaDB）
- 代码生成并写入到 `generated/` 沙盒目录
- 可观测性（LangSmith Trace）

本项目提供 `docker compose` 一键启动（包含 App + Vector DB + MCP Server 三服务），并支持在容器内完成端到端交互与验证。

---

## 目录结构

```text
DevMate/
├── src/
│   └── devmate/
│       ├── agent/                      # Agent 核心逻辑
│       │   ├── core.py                 # 运行入口与状态管理
│       │   ├── factory.py              # Agent 图构建与工具注入
│       │   ├── prompts.py              # 系统提示词管理
│       │   ├── reader.py               # 沙盒文件读取工具（generated/）
│       │   ├── writer.py               # 沙盒文件写入工具（generated/）
│       │   └── static_plan_execute.py  # 规划-执行（含落盘、语法检查等）
│       ├── mcp/                        # MCP Client 与 Server
│       │   ├── server.py               # Tavily 搜索 MCP Server（stdio / SSE）
│       │   └── client.py               # MCP Client 工具包装（stdio / SSE）
│       ├── rag/                        # RAG 模块（loader/splitter/store/retriever/tool）
│       │   ├── loader.py               # 文档加载器（docs/）
│       │   ├── splitter.py             # 文本切分策略
│       │   ├── store.py                # 向量库管理（ChromaDB）
│       │   ├── retriever.py            # 检索核心逻辑
│       │   └── tool.py                 # RAG 工具包装（search_knowledge_base）
│       ├── core/
│       │   └── config.py               # 环境加载与注入（.env）
│       └── main.py                     # 应用启动入口（CLI）
├── docs/                               # 本地知识库（Markdown）
├── tests/                              # 测试脚本
├── generated/                          # 生成输出（Volume）
├── .chroma_db/                         # 向量数据库持久化目录（Volume / Git 忽略）
├── .devmate_state/                     # RAG manifest（Volume）
├── docker/
│   ├── Dockerfile                      # 镜像构建（Python 3.13 + uv）
│   └── docker-compose.yml              # 可选：从 docker/ 目录启动的 compose
├── docker-compose.yml                  # 三服务编排入口（推荐使用）
├── pyproject.toml                      # 依赖声明（uv）
├── uv.lock                             # 锁文件（uv）
├── .env.example                        # 环境变量模板
├── .gitignore
└── README.md
```

---

## 配置（.env）

在项目根目录准备 `.env`（不要提交到仓库）。

- **LLM（对话/规划/生成）**
  - `AI_BASE_URL`：模型 API Base URL（OpenAI-compatible）
  - `API_KEY`：模型鉴权 Key
  - `MODEL_NAME`：主模型（dev 模式默认使用）
  - `ROUTER_MODEL_NAME`：可选，chat/路由模型；不填则默认使用 `MODEL_NAME`

- **Embedding（RAG 向量化）**
  - `EMBEDDING_MODEL_NAME`：Embedding 模型名

- **MCP（网络搜索 / Tavily）**
  - `TAVILY_API_KEY`

- **可观测性（LangSmith）**
  - `LANGCHAIN_TRACING_V2=true`
  - `LANGCHAIN_API_KEY`
  - `LANGCHAIN_PROJECT`（默认 `DevMate`）
  - `LANGCHAIN_ENDPOINT`（默认 `https://api.smith.langchain.com`）

- **三服务内部通信（docker compose 会注入，一般无需手动写入 .env）**
  - `DEVMATE_MCP_URL`：devmate 连接 mcp-search 的 SSE 地址
  - `CHROMA_MODE`：`http`（三服务）或 `local`
  - `CHROMA_SERVER_HOST` / `CHROMA_SERVER_PORT`

项目已提供 `.env.example` 作为模板。

---

## Docker 一键启动（三服务）

在项目根目录执行：

```powershell
docker compose up -d 
```

预期看到三个服务都为 Up：
- `devmate`：主应用（CLI）
- `mcp-search`：MCP 搜索服务（SSE）
- `chromadb`：向量库服务（HTTP）

停止并清理：

```powershell
docker compose down
```

---

## 如何交互（CLI）

推荐使用 `exec -it` 进入容器内启动交互式 CLI：

```powershell
docker compose exec -it devmate python -m src.devmate.main
```

在提示符下输入需求，例如：
- `我想构建一个展示附近徒步路线的网站项目。`

退出：
- 输入 `exit` / `quit`

---

## 验证清单（MCP / RAG / 落盘 / 可观测性）

### 1) 验证 MCP Search（联网搜索）

运行测试脚本：

```powershell
docker compose exec devmate python tests/test_mcp_search.py
```

预期：
- 输出中出现 `[SUCCESS] Test passed!`
- 日志中能看到 `--- [Tool] search_web: ... ---`

### 2) 验证 RAG（本地文档检索 + 向量库）

运行测试脚本：

```powershell
docker compose exec devmate python tests/test_rag_search.py
```

预期：
- 输出中出现 `RAG 工具初始化成功`
- 检索结果包含来自 `docs/` 的片段（例如 `internal_fastapi_guidelines.md`、`project_template.md`）

### 3) 验证文件生成落盘（Volume）

DevMate 的写文件工具会强制将输出写入 `generated/`（宿主机目录挂载到容器内 `/app/generated`）。

可以用 CLI 跑一次生成任务后检查宿主机：

```powershell
dir .\generated
```

预期：
- 出现类似 `generated/run-YYYYMMDD-.../` 的新目录

### 4) 验证 LangSmith Trace（可观测性）

前提：`.env` 中配置了 `LANGCHAIN_TRACING_V2=true` 和 `LANGCHAIN_API_KEY`。

步骤：
1. 运行一次 CLI 交互任务（触发 MCP/RAG/落盘更好观察）
2. 登录 `https://smith.langchain.com/`
3. 进入 `LANGCHAIN_PROJECT` 指定的项目（默认 `DevMate`）
4. 查看最新 Trace，确认能看到：
   - `search_web` 工具调用（MCP）
   - `search_knowledge_base` 工具调用（RAG）

---


