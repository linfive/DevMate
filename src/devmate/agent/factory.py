from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from src.devmate.core.config import settings
from src.devmate.mcp.client import get_mcp_search_tool
from src.devmate.rag.tool import get_rag_tool
from .prompts import DEV_SYSTEM_PROMPT, DEV_SIMPLE_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from .reader import FileReaderTool
from .writer import FileWriterTool

def create_devmate_agent_graph(mode: str = "dev"):
    """工厂方法：初始化大模型、注入工具集并构建 Agent 运行图"""
    
    # 1. 初始化大模型 (Qwen 兼容 OpenAI 接口)
    model_name = settings.MODEL_NAME
    if mode == "chat":
        model_name = settings.ROUTER_MODEL_NAME or settings.MODEL_NAME
    llm = ChatOpenAI(
        model=model_name,
        openai_api_key=settings.API_KEY,
        openai_api_base=settings.AI_BASE_URL,
        temperature=0.1,
        streaming=True,
        extra_body={"enable_thinking": False},
    )

    # 2. 注入工具集
    if mode == "chat":
        tools = []
        system_prompt = CHAT_SYSTEM_PROMPT
    elif mode == "dev_no_tools":
        tools = []
        system_prompt = DEV_SIMPLE_SYSTEM_PROMPT
    else:
        print("--- [Agent Factory] 正在加载工具集 ---")
        tools = [
            get_mcp_search_tool(),
            get_rag_tool(),
            FileReaderTool(),
            FileWriterTool()
        ]
        system_prompt = DEV_SYSTEM_PROMPT

    # 3. 创建并返回 Agent 运行图 (LangGraph 驱动)
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        debug=False
    )
