import re
from typing import List
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from src.devmate.core.config import settings
from .factory import create_devmate_agent_graph
from .static_plan_execute import StaticPlanContext, StaticPlanExecute

class DevMateAgent:
    """DevMate 核心 Agent 类：仅负责运行入口与状态管理"""
    
    def __init__(self):
        self._dev_agent_graph = None
        self._chat_agent_graph = None
        self._dev_no_tools_graph = None
        self._intent_llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            openai_api_key=settings.API_KEY,
            openai_api_base=settings.AI_BASE_URL,
            temperature=0,
            streaming=False,
            extra_body={"enable_thinking": False},
        )
        self._static_plan_execute = None
        self._intent_cache: dict[str, str] = {}
        self._intent_cache_max = 128

    def _get_dev_agent_graph(self):
        if self._dev_agent_graph is None:
            self._dev_agent_graph = create_devmate_agent_graph(mode="dev")
        return self._dev_agent_graph

    def _get_chat_agent_graph(self):
        if self._chat_agent_graph is None:
            self._chat_agent_graph = create_devmate_agent_graph(mode="chat")
        return self._chat_agent_graph

    def _get_dev_no_tools_graph(self):
        if self._dev_no_tools_graph is None:
            self._dev_no_tools_graph = create_devmate_agent_graph(mode="dev_no_tools")
        return self._dev_no_tools_graph

    def _get_static_plan_execute(self) -> StaticPlanExecute:
        if self._static_plan_execute is None:
            self._static_plan_execute = StaticPlanExecute()
        return self._static_plan_execute

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

    def _postprocess_answer(self, answer: str, messages: list[BaseMessage] | None) -> str:
        if not messages:
            return answer

        search_web_urls: list[str] = []
        sandbox_writes: list[str] = []

        for m in messages:
            if m.__class__.__name__ != "ToolMessage":
                continue
            content = getattr(m, "content", "") or ""
            if not content:
                continue
            tool_name = (getattr(m, "name", "") or "").strip()
            if tool_name == "search_web" or "URL:" in content or "Search results for" in content:
                search_web_urls.extend(self._extract_urls(content))
            if "成功将代码写入沙盒文件" in content:
                sandbox_writes.append(content.strip())

        if search_web_urls:
            if "来源" not in answer and "Sources" not in answer:
                lines = ["", "### 来源"]
                for u in dict.fromkeys(search_web_urls):
                    lines.append(f"- {u}")
                answer = answer.rstrip() + "\n" + "\n".join(lines) + "\n"

        if sandbox_writes:
            if "generated/" not in answer and "generated\\" not in answer:
                lines = ["", "### 落盘"]
                for t in dict.fromkeys(sandbox_writes):
                    lines.append(f"- {t}")
                answer = answer.rstrip() + "\n" + "\n".join(lines) + "\n"

        return answer

    def _augment_query_for_recency(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return q

        q_lower = q.lower()
        recency_markers = ["最新", "latest", "release", "版本", "version", "更新", "best practice", "best practices"]
        topic_markers = ["fastapi", "pydantic", "react", "next", "langchain", "langgraph", "docker", "python"]

        if any(m in q_lower for m in recency_markers) and any(t in q_lower for t in topic_markers):
            return (
                "要求：先调用 search_web 获取最新信息；回答末尾必须输出 ### 来源 并列出URL。若内容无法从来源确认，必须标注为推测/不确定。\n"
                + q
            )

        return q

    def _should_two_stage_plan_execute(self, query: str) -> bool:
        q = (query or "").strip().lower()
        if not q:
            return False
        markers = [
            "构建", "搭建", "脚手架", "项目", "网站", "生成多文件",
            "选型", "对比", "集成", "接入", "best practice", "best practices", "最佳实践",
            "版本", "升级", "兼容", "迁移",
        ]
        return any(m in q for m in markers)

    def _rule_classify_intent(self, query: str) -> str:
        q = (query or "").strip().lower()
        if not q:
            return "chat"

        chat_keywords = [
            "你好", "hi", "hello", "在吗", "谢谢", "感谢", "早上好", "晚上好", "晚安", "再见", "拜拜",
            "怎么样", "聊聊", "天气", "心情", "吃饭", "睡觉"
        ]
        dev_keywords = [
            "bug", "报错", "错误", "traceback", "exception", "stack", "log", "debug",
            "fastapi", "django", "flask", "react", "next", "vue", "tailwind", "sql", "redis", "docker",
            "api", "接口", "路由", "数据库", "模型", "schema", "pydantic", "依赖注入", "单元测试", "pytest",
            ".py", ".ts", ".tsx", ".js", ".jsx", "class ", "def ", "import ", "from ", "```"
        ]

        greeting_only = re.sub(r"[ \t\r\n\u3000,，.。!！?？;；:：'\"“”‘’()（）\[\]{}<>《》…\-—_~`]+", "", q)
        if greeting_only in {"你好", "您好", "hi", "hello", "在吗", "谢谢", "感谢", "早上好", "晚上好", "晚安", "再见", "拜拜"}:
            return "chat"

        file_ops = [
            "写入", "写到", "保存", "落盘", "生成文件", "创建文件", "新建文件", "输出到文件",
            "file_writer", "generated/", "generated\\",
        ]
        if any(k in q for k in file_ops):
            return "dev_complex"
        if "文件" in q and any(k in q for k in ["写", "生成", "保存", "创建", "新建", "落盘"]):
            return "dev_complex"
        if any(k in q for k in ["py文件", "js文件", "html文件", "css文件", "toml文件"]):
            return "dev_complex"
        if re.search(r"[A-Za-z0-9_.-]+\.(py|js|html|css|toml|json|yml|yaml)\b", query):
            return "dev_complex"

        if any(k in q for k in dev_keywords):
            return "dev_complex"
        if any(k in q for k in chat_keywords):
            return "chat"
        if re.search(r"[{}();<>]|==|!=|=>|->|::", query):
            return "dev_complex"
        return "unknown"

    async def _llm_classify_intent(self, query: str) -> str:
        cached = self._intent_cache.get(query)
        if cached in ("chat", "dev_simple", "dev_complex"):
            return cached

        try:
            result = await self._intent_llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "你是一个意图分类器。只能输出 chat、dev_simple、dev_complex 三者之一，不要输出其它内容。\n"
                            "chat=闲聊/问候/非技术；\n"
                            "dev_simple=简单开发问题（单个算法/函数、语法解释、复杂度分析、少量示例代码），不需要外部检索、不需要多文件生成；\n"
                            "dev_complex=复杂工程问题（构建项目/脚手架、多文件生成、架构设计、最佳实践、版本兼容、第三方集成、报错排查）。\n"
                            "重要：只要用户要求“把代码写入/保存成/生成到某个文件、落盘、创建文件”，无论任务多简单，都必须输出 dev_complex。"
                        )
                    ),
                    HumanMessage(content=query),
                ]
            )
            label = (result.content or "").strip().lower()
            if label not in ("chat", "dev_simple", "dev_complex"):
                label = "dev_complex"
        except Exception:
            label = "dev_complex"

        if len(self._intent_cache) >= self._intent_cache_max:
            self._intent_cache.clear()
        self._intent_cache[query] = label
        return label

    async def aask(self, query: str, chat_history: List[BaseMessage] = None) -> str:
        """异步执行 Agent 问答循环"""
        if chat_history is None:
            chat_history = []
            
        inputs = {
            "messages": chat_history + [HumanMessage(content=query)]
        }
        
        try:
            print(f"\n--- [Agent Core] 收到用户请求: '{query}' ---")
            intent = self._rule_classify_intent(query)
            if intent == "unknown":
                intent = await self._llm_classify_intent(query)
            if intent == "chat":
                agent_graph = self._get_chat_agent_graph()
            elif intent == "dev_simple":
                agent_graph = self._get_dev_no_tools_graph()
            else:
                agent_graph = self._get_dev_agent_graph()

            if intent == "dev_complex":
                if self._should_two_stage_plan_execute(query):
                    ctx = await self._get_static_plan_execute().plan(query)
                    parts: list[str] = [ctx.plan_text, "\n"]
                    async for chunk in self._get_static_plan_execute().execute(query, ctx):
                        parts.append(chunk)
                    return "".join(parts).strip()
                inputs = {"messages": chat_history + [HumanMessage(content=self._augment_query_for_recency(query))]}

            result = await agent_graph.ainvoke(inputs)
            
            final_messages = result.get("messages", [])
            if final_messages:
                answer = self._postprocess_answer(final_messages[-1].content, final_messages)
            else:
                answer = self._postprocess_answer("No response generated.", final_messages)
            return answer
            
        except Exception as e:
            return f"❌ Agent 执行出错: {str(e)}"

    async def astream(self, query: str, chat_history: List[BaseMessage] = None):
        if chat_history is None:
            chat_history = []

        inputs = {
            "messages": chat_history + [HumanMessage(content=query)]
        }

        tool_messages: list[BaseMessage] = []
        try:
            intent = self._rule_classify_intent(query)
            if intent == "unknown":
                intent = await self._llm_classify_intent(query)
            if intent == "chat":
                agent_graph = self._get_chat_agent_graph()
            elif intent == "dev_simple":
                agent_graph = self._get_dev_no_tools_graph()
            else:
                agent_graph = self._get_dev_agent_graph()

            if intent == "dev_complex":
                if self._should_two_stage_plan_execute(query):
                    yield "[tool] search_knowledge_base\n"
                    static_exec = self._get_static_plan_execute()
                    _, rag_text, _, files = await static_exec.fetch_project_template()
                    yield "[model] planner\n"
                    ctx = await static_exec.plan_with_template(query, rag_text, files, must_use_web=True)
                    yield ctx.plan_text.rstrip() + "\n\n"
                    if ctx.use_web and ctx.web_query:
                        yield "### MCP 查询\n"
                        yield f"- search_web: {ctx.web_query}\n\n"
                    async for chunk in static_exec.execute(query, ctx):
                        yield chunk
                    return
                inputs = {"messages": chat_history + [HumanMessage(content=self._augment_query_for_recency(query))]}

            had_chunk = False
            last_ai_full: str | None = None
            ai_chunks: list[str] = []
            async for chunk in agent_graph.astream(inputs, stream_mode="updates"):
                if not isinstance(chunk, dict):
                    continue
                for output in chunk.values():
                    if not isinstance(output, dict):
                        continue
                    msgs = output.get("messages")
                    if not msgs:
                        continue
                    for msg in msgs:
                        msg_type = msg.__class__.__name__
                        if msg_type == "AIMessageChunk":
                            delta = getattr(msg, "content", "") or ""
                            if delta:
                                had_chunk = True
                                ai_chunks.append(delta)
                                yield delta
                        elif msg_type == "AIMessage":
                            last_ai_full = getattr(msg, "content", "") or ""
                        elif msg_type == "ToolMessage":
                            tool_messages.append(msg)
                            tool_name = (getattr(msg, "name", "") or "").strip()
                            if tool_name:
                                yield f"\n[tool] {tool_name}\n"

            if had_chunk:
                tail = self._postprocess_answer("", tool_messages).strip()
                if tail:
                    yield "\n\n" + tail + "\n"
                return

            if last_ai_full:
                yield self._postprocess_answer(last_ai_full, tool_messages)
                return

            tail = self._postprocess_answer("", tool_messages).strip()
            if tail:
                yield "\n\n" + tail
            return
        except Exception as e:
            yield f"❌ Agent 执行出错: {str(e)}"
            return

# 快捷获取 Agent 实例
_agent_instance = None

def get_devmate_agent() -> DevMateAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DevMateAgent()
    return _agent_instance
