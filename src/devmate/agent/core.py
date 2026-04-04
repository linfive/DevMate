import os
from typing import List, Any, Dict, Union
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from src.devmate.core.config import settings
from src.devmate.mcp.client import get_mcp_search_tool
from src.devmate.rag.tool import get_rag_tool

class DevMateAgent:
    """DevMate 核心 Agent 类：基于 LangChain 1.x 的 create_agent (LangGraph 驱动)"""
    
    def __init__(self):
        # 1. 初始化大模型
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            openai_api_key=settings.API_KEY,
            openai_api_base=settings.AI_BASE_URL,
            temperature=0.1,
            streaming=True
        )

        # 2. 初始化工具集
        print("--- [Agent] 正在加载 MCP Search Tool ---")
        mcp_tool = get_mcp_search_tool()
        
        print("--- [Agent] 正在加载 RAG Search Tool ---")
        rag_tool = get_rag_tool()
        
        self.tools = [mcp_tool, rag_tool]

        # 3. 系统提示词
        self.system_prompt = """你是一个名为 DevMate 的智能编程助手。
你的目标是协助开发者解决技术难题、提供代码建议并确保代码符合项目规范。

你可以使用以下工具：
1. search_knowledge_base: 在本地项目文档和规范中查找。当你需要了解项目特有的架构、代码风格或内部约定（如 src/api/ 目录结构、前端组件规范）时，请务必优先使用此工具。
2. search_web: 在互联网上查找最新的 API 文档、技术新闻或通用编程问题的解答。

决策逻辑：
- 如果问题涉及项目特定的规则（例如“我们项目的路由怎么写？”），先检索本地知识库。
- 如果问题涉及通用的新技术或 API（例如“React 19 的新特性是什么？”），使用网络搜索。
- 如果两个工具都有助于回答，可以先后调用。

请始终以专业、简洁且易于理解的方式回答。回答请使用中文。"""

        # 4. 使用 LangChain 1.x 的 create_agent 创建 Agent 图
        # 这在内部使用 LangGraph 构建了一个循环图
        self.agent_graph = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
            debug=False # 设置为 True 可以看到详细的步骤
        )

    async def aask(self, query: str, chat_history: List[BaseMessage] = None) -> str:
        """异步执行 Agent 问答"""
        if chat_history is None:
            chat_history = []
            
        inputs = {
            "messages": chat_history + [HumanMessage(content=query)]
        }
        
        try:
            print(f"\n--- [Agent] 收到用户请求: '{query}' ---")
            result = await self.agent_graph.ainvoke(inputs)
            
            final_messages = result.get("messages", [])
            if final_messages:
                return final_messages[-1].content
            return "No response generated."
            
        except Exception as e:
            return f"❌ Agent 执行出错: {str(e)}"

# 快捷获取 Agent 实例
_agent_instance = None

def get_devmate_agent() -> DevMateAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DevMateAgent()
    return _agent_instance
