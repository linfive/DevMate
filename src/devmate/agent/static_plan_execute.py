import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from src.devmate.core.config import settings
from src.devmate.mcp.client import get_mcp_search_tool
from src.devmate.rag.tool import get_rag_tool
from .writer import FileWriterTool

@dataclass(frozen=True)
class StaticPlanContext:
    plan_text: str
    files: list[dict]
    urls: list[str]
    web_text: str
    rag_text: str
    use_web: bool
    web_query: str
    run_subdir: str

class StaticPlanExecute:
    def __init__(self) -> None:
        self._planner_llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            openai_api_key=settings.API_KEY,
            openai_api_base=settings.AI_BASE_URL,
            temperature=0,
            streaming=False,
            extra_body={"enable_thinking": False},
        )
        self._executor_llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            openai_api_key=settings.API_KEY,
            openai_api_base=settings.AI_BASE_URL,
            temperature=0,
            streaming=False,
            extra_body={"enable_thinking": False},
        )
        self._search_web_tool = get_mcp_search_tool()
        self._rag_tool = get_rag_tool()
        self._file_writer = FileWriterTool()
        self._run_subdir = ""

    def _new_run_subdir(self, user_query: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        digest = hashlib.sha256((user_query or "").encode("utf-8")).hexdigest()[:8]
        q = (user_query or "").strip()
        q = re.sub(r"[，。！？；：,.!?;:\r\n\t\u3000]+", " ", q).strip()
        q = re.sub(r"^(请|帮我|帮忙|麻烦|能否|能不能|我想|我要|想要|想做|我需要|希望)\s*", "", q).strip()
        q = re.sub(r"^(构建|搭建|开发|实现|做)\s*(一个|一套)?\s*", "", q).strip()
        q = re.sub(r"\s*(的网站项目|的网站|项目)$", "", q).strip()
        q = re.sub(r"\s+", "-", q).strip("-")
        q = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "", q)
        slug = (q or "task")[:16].strip("-._") or "task"
        return f"run-{stamp}-{slug}-{digest}"

    def _strip_code_fences(self, text: str) -> str:
        t = (text or "").strip()
        if t.startswith("```") and t.endswith("```"):
            lines = t.splitlines()
            if len(lines) >= 3:
                return "\n".join(lines[1:-1]).strip()
        return t

    def _clip(self, text: str, limit: int) -> str:
        t = text or ""
        if len(t) <= limit:
            return t
        return t[:limit] + "\n...[truncated]...\n"

    def _sanitize_file_content(self, content: str, file_path: str) -> str:
        raw = (content or "").replace("\r\n", "\n")
        if not raw.strip():
            return ""
        lines = raw.splitlines()
        cleaned: list[str] = []
        stop_markers = ("### 落盘", "### 来源", "### 文件清单", "### 计划", "--- [Tool]")
        for line in lines:
            s = line.strip()
            if not s:
                cleaned.append("")
                continue
            if any(s.startswith(m) for m in stop_markers):
                break
            if s.startswith("### File:"):
                continue
            if s.startswith("```"):
                continue
            cleaned.append(line)
        text = "\n".join(cleaned).strip()
        if not text:
            return ""
        text = re.sub(r"`(https?://[^`\s]+)`", r"\1", text)

        def _unquote_url(m: re.Match) -> str:
            quote = m.group(1)
            url = m.group(2).strip()
            return f"{quote}{url}{quote}"

        text = re.sub(r"([\"'])\s*`(https?://[^`]+)`\s*\1", _unquote_url, text)
        if not text.endswith("\n"):
            text += "\n"
        return text

    def _check_python_syntax(self, content: str, file_path: str) -> str | None:
        try:
            compile(content, file_path, "exec")
            return None
        except SyntaxError as e:
            line = e.lineno or 0
            col = e.offset or 0
            msg = (e.msg or "SyntaxError").strip()
            text = (e.text or "").rstrip("\n")
            pointer = (" " * max(col - 1, 0) + "^") if col else ""
            details = f"{msg} at {file_path}:{line}:{col}"
            if text:
                details += f"\n{text}\n{pointer}"
            return details

    async def _fix_python_syntax(
        self,
        user_query: str,
        file_path: str,
        rag_text: str,
        current_content: str,
        error_text: str,
    ) -> str:
        system = (
            "你是 DevMate 的 Python 语法修复器。\n"
            "任务：修复给定 Python 文件中的语法错误。\n"
            "要求：只输出修复后的目标文件完整内容；不要输出任何解释；不要输出 Markdown；不要输出代码块围栏。\n"
            "约束：必须保持与当前文件相同的功能意图；不要添加无关功能；不要引入模板未允许的新依赖。\n"
        )
        user = (
            f"用户请求：{user_query}\n"
            f"文件：{file_path}\n\n"
            f"语法错误：\n{error_text}\n\n"
            f"项目模板（RAG）：\n{self._clip(rag_text, 6000)}\n\n"
            f"当前文件内容：\n{self._clip(current_content, 12000)}\n"
        )
        result = await self._executor_llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        fixed = (result.content or "").strip()
        fixed = self._strip_code_fences(fixed)
        fixed = self._sanitize_file_content(fixed, file_path)
        return fixed

    def _extract_urls(self, text: str) -> list[str]:
        if not text:
            return []
        urls = re.findall(r"https?://[^\s)]+", text)
        deduped: list[str] = []
        seen: set[str] = set()
        for u in urls:
            u = u.rstrip(".,;\"'`")
            if u not in seen:
                seen.add(u)
                deduped.append(u)
        return deduped

    def _fallback_web_query(self, user_query: str, rag_text: str) -> str:
        return self._rewrite_web_query(user_query) or "项目 最佳实践"

    def _rewrite_web_query(self, user_query: str) -> str:
        q = (user_query or "").strip()
        if not q:
            return ""
        q = re.sub(r"[，。！？；：,.!?;:\r\n\t\u3000]+", " ", q).strip()
        q = re.sub(r"^(请|帮我|帮忙|麻烦|能否|能不能|我想|我要|想要|想做|我需要|希望)\s*", "", q).strip()
        q = re.sub(r"^(构建|搭建|开发|实现|做)\s*(一个|一套)?\s*", "", q).strip()
        q = re.sub(r"\s*(的网站项目|的网站|项目)$", "", q).strip()
        q = re.sub(r"\s+", " ", q).strip()
        if "最佳实践" not in q and "best practice" not in q.lower():
            q = f"{q} 最佳实践".strip()
        return q

    def _extract_json_object(self, text: str) -> dict | None:
        t = self._strip_code_fences(text)
        start = t.find("{")
        end = t.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = t[start : end + 1]
        try:
            data = json.loads(candidate)
        except Exception:
            return None
        if isinstance(data, dict):
            return data
        return None

    def _infer_file_type(self, path: str) -> str:
        p = (path or "").lower()
        if p.endswith(".html"):
            return "text/html"
        if p.endswith(".css"):
            return "text/css"
        if p.endswith(".js"):
            return "application/javascript"
        if p.endswith(".toml"):
            return "text/toml"
        if p.endswith(".py"):
            return "text/x-python"
        return "text/plain"

    def _extract_required_paths_from_template(self, rag_text: str) -> list[str]:
        t = (rag_text or "").strip()
        if not t:
            return []

        candidates: list[str] = []
        candidates.extend(re.findall(r"`([^`]+)`", t))
        candidates.extend(re.findall(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)", t))
        candidates.extend(re.findall(r"(?<![A-Za-z0-9_.-])(\.[A-Za-z0-9_.-]+)", t))
        paths: list[str] = []
        seen: set[str] = set()
        for c in candidates:
            p = (c or "").strip()
            if not p:
                continue
            p = p.rstrip(".,;:!?")
            if p.startswith("http://") or p.startswith("https://") or "://" in p:
                continue
            if p.startswith("/"):
                continue
            if any(ch.isspace() for ch in p):
                continue
            if p.upper().startswith("GET/") or p.upper().startswith("GET"):
                continue
            if "/" in p:
                last = p.split("/")[-1]
                if last != "__init__.py" and re.match(r"^[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,8}$", last) is None:
                    continue
            elif p.startswith("."):
                if re.match(r"^\.[A-Za-z0-9][A-Za-z0-9_.-]{0,30}$", p) is None:
                    continue
            else:
                continue
            if p not in seen:
                seen.add(p)
                paths.append(p)
        return paths

    async def fetch_web(self, web_query: str) -> tuple[str, str, list[str]]:
        web_text = await self._search_web_tool._arun(web_query)
        urls = self._extract_urls(web_text)
        return web_query, web_text, urls

    async def fetch_project_template(self) -> tuple[str, str, list[str], list[dict]]:
        queries = ["project_template 文件清单", "项目模板 文件清单", "project_template"]
        last_text = ""
        for rag_template_query in queries:
            rag_text = await self._rag_tool._arun(rag_template_query)
            last_text = rag_text
            template_paths = self._extract_required_paths_from_template(rag_text)
            if template_paths:
                files = [{"path": p, "type": self._infer_file_type(p)} for p in template_paths]
                return rag_template_query, rag_text, template_paths, files
        raise ValueError("未能从项目模板中解析必须文件清单，请检查 docs/project_template.md 的文件清单段落是否被检索到（需包含反引号包裹的文件路径列表）")

    async def plan_decision(self, user_query: str, rag_text: str, must_use_web: bool) -> dict:
        planner_system = (
            "你是 DevMate 的 Planner。你必须输出严格 JSON（不要输出解释、不要输出 Markdown、不要输出代码块）。\n"
            "目标：为用户请求生成计划，并决定是否需要调用 MCP(search_web)。\n"
            "约束：必须严格遵循“项目模板（RAG）”里的目录结构、文件清单与实现约束。\n"
            "只输出 JSON，schema:\n"
            "{\n"
            "  \"plan_steps\": [\"Step1...\", \"Step2...\"],\n"
            "  \"use_web\": true,\n"
            "  \"web_query\": \"...\"\n"
            "}\n"
            "规则：\n"
            f"- must_use_web={str(must_use_web).lower()} 时，你必须输出 use_web=true。\n"
            "- 复杂/需要外部资料的任务 use_web=true，并给出高质量的中文 web_query（不要直接复述用户原句）。\n"
            "- web_query 必须包含“最佳实践”四个字，并且必须与用户原句不同。\n"
            "- 简单且无需外部资料的任务 use_web=false，web_query 置空字符串。\n"
        )
        planner_user = (
            f"用户请求：{user_query}\n\n"
            f"项目模板（RAG）：\n{rag_text}\n"
        )

        data: dict = {}
        try:
            result = await self._planner_llm.ainvoke(
                [SystemMessage(content=planner_system), HumanMessage(content=planner_user)]
            )
            parsed = self._extract_json_object((result.content or "").strip())
            if isinstance(parsed, dict):
                data = parsed
        except Exception:
            data = {}

        plan_steps: list[str] = []
        raw_steps = data.get("plan_steps")
        if isinstance(raw_steps, list):
            plan_steps = [str(s).strip() for s in raw_steps if str(s).strip()]
        if plan_steps and not all(s.lower().startswith("step") for s in plan_steps):
            plan_steps = [f"Step{i+1}: {s}" for i, s in enumerate(plan_steps)]

        use_web = (bool(data.get("use_web")) if "use_web" in data else False) or bool(must_use_web)
        web_query = str(data.get("web_query") or "").strip()

        normalized_user = (user_query or "").strip()
        if use_web and (not web_query or web_query == normalized_user):
            web_query = self._fallback_web_query(user_query, rag_text)
        if not plan_steps:
            if use_web:
                plan_steps = [
                    "Step1: search_knowledge_base（读取 project_template 并对齐目录与文件清单）",
                    "Step2: Planner 生成 MCP 查询词与执行步骤",
                    "Step3: search_web（按 Planner 生成的查询词检索外部资料）",
                    "Step4: 输出文件清单（来自项目模板）",
                    "Step5: 逐文件生成内容并调用 file_writer 落盘到 generated/",
                    "Step6: 输出 ### 落盘清单 与 ### 来源",
                ]
            else:
                plan_steps = [
                    "Step1: search_knowledge_base（读取 project_template 并对齐目录与文件清单）",
                    "Step2: 输出文件清单（来自项目模板）",
                    "Step3: 逐文件生成内容并调用 file_writer 落盘到 generated/",
                    "Step4: 输出 ### 落盘清单",
                ]

        plan_text = "### 计划\n" + "\n".join(plan_steps) + "\n"
        return {
            "plan_text": plan_text,
            "use_web": use_web,
            "web_query": web_query,
        }

    async def plan_with_template(self, user_query: str, rag_text: str, files: list[dict], must_use_web: bool) -> StaticPlanContext:
        decision = await self.plan_decision(user_query, rag_text, must_use_web=must_use_web)
        plan_text = str(decision.get("plan_text") or "").strip() + "\n"
        use_web = bool(decision.get("use_web"))
        web_query = str(decision.get("web_query") or "").strip()
        run_subdir = self._new_run_subdir(user_query)
        self._run_subdir = run_subdir
        return StaticPlanContext(
            plan_text=plan_text,
            files=files,
            urls=[],
            web_text="",
            rag_text=rag_text,
            use_web=use_web,
            web_query=web_query,
            run_subdir=run_subdir,
        )

    async def plan(self, user_query: str) -> StaticPlanContext:
        _, rag_text, _, files = await self.fetch_project_template()
        return await self.plan_with_template(user_query, rag_text, files, must_use_web=True)

    def _language_tag_for_type(self, file_type: str, path: str) -> str:
        p = (path or "").lower()
        if p.endswith(".py"):
            return "python"
        if p.endswith(".html"):
            return "html"
        if p.endswith(".css"):
            return "css"
        if p.endswith(".js"):
            return "javascript"
        if p.endswith(".toml"):
            return "toml"
        t = (file_type or "").lower()
        if "python" in t:
            return "python"
        if "html" in t:
            return "html"
        if "css" in t:
            return "css"
        if "javascript" in t:
            return "javascript"
        if "toml" in t:
            return "toml"
        return ""

    async def _generate_file_content(
        self,
        user_query: str,
        file_path: str,
        file_type: str,
        web_text: str,
        rag_text: str,
    ) -> str:
        system = (
            "你是 DevMate 的 Executor。你只输出目标文件的完整内容，不要输出任何解释，不要输出 Markdown，不要输出代码块围栏。\n"
            "硬约束：必须严格遵循“项目模板（RAG）”的实现约束与文件清单。\n"
            "禁止引入模板未允许的技术栈或额外依赖。\n"
            "外部信息约束：你输出的任何外部 URL（例如 CDN、瓦片服务、第三方 API）必须出现在 Web 搜索结果（web_text）中；否则禁止输出该 URL。\n"
            "如果 web_text 中没有合适的地图 CDN/瓦片 URL，则前端不集成地图，只输出可用的列表与基本交互。\n"
        )
        user = (
            f"用户请求：{user_query}\n"
            f"文件：{file_path}\n"
            f"type: {file_type}\n\n"
            f"项目模板（RAG）：\n{self._clip(rag_text, 8000)}\n\n"
            f"Web 搜索结果（节选）：\n{self._clip(web_text, 8000)}\n"
        )

        result = await self._executor_llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        content = (result.content or "").strip()
        stripped = self._strip_code_fences(content)
        if stripped and not stripped.endswith("\n"):
            stripped += "\n"
        return stripped

    async def execute(self, user_query: str, ctx: StaticPlanContext) -> AsyncIterator[str]:
        yield "[model] executor\n"
        os.environ["DEVMATE_RUN_SUBDIR"] = ctx.run_subdir
        yield "### 沙盒目录\n"
        yield f"- generated/{ctx.run_subdir}\n\n"
        web_text = ctx.web_text
        urls = ctx.urls
        if ctx.use_web and not web_text:
            if ctx.web_query:
                yield f"[tool] search_web: {ctx.web_query}\n"
                _, web_text, urls = await self.fetch_web(ctx.web_query)

        yield "### 文件清单\n"
        for f in ctx.files:
            yield f"- {f.get('path')}\n"
        yield "\n"

        written: list[str] = []
        for f in ctx.files:
            path = str(f.get("path", "")).strip()
            if not path:
                continue
            file_type = str(f.get("type", "")).strip()
            yield f"[model] executor: {path}\n"
            content = ""
            last_error = ""
            for _ in range(3):
                try:
                    content = await self._generate_file_content(user_query, path, file_type, web_text, ctx.rag_text)
                    content = self._sanitize_file_content(content, path)
                    if not content.strip():
                        last_error = "内容清洗后为空"
                        content = ""
                except Exception as e:
                    last_error = str(e)
                    content = ""
                if content:
                    break

            if not content and not path.endswith("__init__.py"):
                reason = f"\n原因：{last_error}\n" if last_error else "\n"
                yield f"❌ 生成失败：{path}{reason}"
                return

            if path.lower().endswith(".py") and content:
                yield f"[tool] syntax_check: {path}\n"
                err = self._check_python_syntax(content, path)
                if err:
                    yield f"[model] fixer: {path}\n"
                fix_attempts = 0
                while err and fix_attempts < 2:
                    fix_attempts += 1
                    try:
                        content = await self._fix_python_syntax(user_query, path, ctx.rag_text, content, err)
                    except Exception as e:
                        last_error = str(e)
                        content = ""
                        break
                    if not content:
                        last_error = "修复后内容为空"
                        break
                    yield f"[tool] syntax_check: {path}\n"
                    err = self._check_python_syntax(content, path)
                if err:
                    yield f"❌ 语法检查失败：{path}\n原因：{err}\n"
                    return
            yield f"[tool] file_writer: {path}\n"
            self._file_writer._run(path, content)
            written.append(path)


            lang = self._language_tag_for_type(file_type, path)
            yield f"### File: {path}\n"
            if lang:
                yield f"```{lang}\n{content}```\n\n"
            else:
                yield f"```\n{content}```\n\n"

        yield "### 落盘清单\n"
        yield "```plaintext\n"
        for p in written:
            yield f"{p}\n"
        yield "```\n\n"

        if urls:
            yield "### 来源\n"
            for u in dict.fromkeys(urls):
                yield f"- {u}\n"
            yield "\n"
