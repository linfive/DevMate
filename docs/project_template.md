# 项目模板（最小骨架）

## 1. 目录结构（必须）

```
<project-root>/
  frontend/
    index.html
    styles.css
    app.js
    assets/
  backend/
    pyproject.toml
    src/
      api/
        main.py
        routes/
        deps.py
      core/
        config.py
      schemas/
      services/
    tests/
  .gitignore
```

## 2. 文件清单（必须）

前端（纯静态）：
- `frontend/index.html`
- `frontend/styles.css`
- `frontend/app.js`

后端（backend）：
- `backend/pyproject.toml`
- `backend/src/__init__.py`
- `backend/src/api/__init__.py`
- `backend/src/api/main.py`
- `backend/src/api/deps.py`
- `backend/src/api/routes/__init__.py`
- `backend/src/api/routes/health.py`
- `backend/src/api/routes/trails.py`
- `backend/src/core/__init__.py`
- `backend/src/core/config.py`
- `backend/src/schemas/__init__.py`
- `backend/src/schemas/trail.py`
- `backend/src/services/__init__.py`
- `backend/src/services/trail_service.py`
- `backend/tests/test_health.py`

仓库根目录：
- `.gitignore`

## 3. 实现约束（必须）

- 禁止：React/Vite/Tailwind/TypeScript
- 前端地图：Leaflet（CDN）
- 前端请求：`http://localhost:8000/api/trails`
- 后端：FastAPI 分层目录 + Pydantic v2
- 禁止：数据库/SQLAlchemy
- 路由：`GET /health`，`GET /api/trails`

## 4. 命名约定

- Python：`snake_case`
- FastAPI 路由文件：业务域命名（`health.py`, `trails.py`）
- Pydantic Schema：`PascalCase`，文件名业务域（`trail.py`）

## 5. 运行方式（默认）

前端（PowerShell）：
- `cd generated/frontend`
- `python -m http.server 5173`

后端（PowerShell）：
- `cd generated/backend`
- `uv run uvicorn src.api.main:app --reload --port 8000`

## 6. 生成输出格式约定（用于 DevMate 落盘）

- 每个文件：`### File: <path>` + 代码块
- 结束：`### 落盘清单`（完整路径列表）
