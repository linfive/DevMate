import re
from typing import List
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from src.devmate.core.config import settings
from .factory import create_devmate_agent_graph

class DevMateAgent:
    """DevMate 核心 Agent 类：仅负责运行入口与状态管理"""
    
    def __init__(self):
        self.dev_agent_graph = create_devmate_agent_graph(mode="dev")
        self.chat_agent_graph = create_devmate_agent_graph(mode="chat")
        self._intent_llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            openai_api_key=settings.API_KEY,
            openai_api_base=settings.AI_BASE_URL,
            temperature=0,
            streaming=False,
        )
        self._intent_cache: dict[str, str] = {}
        self._intent_cache_max = 128

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

        if any(k in q for k in dev_keywords):
            return "dev"
        if any(k in q for k in chat_keywords):
            return "chat"
        if re.search(r"[{}();<>]|==|!=|=>|->|::", query):
            return "dev"
        return "unknown"

    async def _llm_classify_intent(self, query: str) -> str:
        cached = self._intent_cache.get(query)
        if cached in ("chat", "dev"):
            return cached

        try:
            result = await self._intent_llm.ainvoke(
                [
                    SystemMessage(
                        content="你是一个意图分类器。只能输出 chat 或 dev 其中一个词，不要输出其它内容。chat=闲聊/问候/非技术；dev=编程/代码/报错/工程问题。"
                    ),
                    HumanMessage(content=query),
                ]
            )
            label = (result.content or "").strip().lower()
            if label not in ("chat", "dev"):
                label = "dev"
        except Exception:
            label = "dev"

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
            agent_graph = self.chat_agent_graph if intent == "chat" else self.dev_agent_graph

            if intent != "chat":
                inputs = {
                    "messages": chat_history + [HumanMessage(content=self._augment_query_for_recency(query))]
                }

            result = await agent_graph.ainvoke(inputs)
            
            final_messages = result.get("messages", [])
            if final_messages:
                return self._postprocess_answer(final_messages[-1].content, final_messages)
            return self._postprocess_answer("No response generated.", final_messages)
            
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
            agent_graph = self.chat_agent_graph if intent == "chat" else self.dev_agent_graph

            if intent != "chat":
                inputs = {
                    "messages": chat_history + [HumanMessage(content=self._augment_query_for_recency(query))]
                }

            had_chunk = False
            last_ai_full: str | None = None
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
                                yield delta
                        elif msg_type == "AIMessage":
                            last_ai_full = getattr(msg, "content", "") or ""
                        elif msg_type == "ToolMessage":
                            tool_messages.append(msg)

            if last_ai_full:
                yield self._postprocess_answer(last_ai_full, tool_messages)
                return

            tail = self._postprocess_answer("", tool_messages).strip()
            if tail:
                yield "\n\n" + tail
            return
        except Exception:
            pass

        fallback = await self.aask(query, chat_history)
        yield fallback

# 快捷获取 Agent 实例
_agent_instance = None

def get_devmate_agent() -> DevMateAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DevMateAgent()
    return _agent_instance
