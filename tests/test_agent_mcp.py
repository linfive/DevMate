import asyncio
import os
import sys
import io

# 强制设置标准输出为 UTF-8，解决 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')



from src.devmate.core.config import settings
from src.devmate.mcp.client import get_mcp_search_tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

async def test_agent_with_mcp():
    """测试 Agent 自主调用 MCP 搜索工具 (使用最新 LangChain 1.x 架构)"""
    print("--- [Agent + MCP Test] 初始化中 ---")
    
    # 1. 初始化 LLM
    llm = ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=settings.API_KEY,
        base_url=settings.AI_BASE_URL,
        temperature=0
    )
    
    # 2. 获取 MCP 搜索工具
    search_tool = get_mcp_search_tool()
    tools = [search_tool]
    
    # 3. 创建 Agent (使用最新的 create_agent 函数)
    agent_graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt="你是一个专业的编程助手。如果用户提出的问题需要实时信息，请务必使用 search_web 工具进行搜索。"
    )
    
    # 4. 提问一个需要实时信息的问题
    question = "2024年4月最新的 FastAPI 版本是多少？它有哪些主要更新？"
    print(f"\n--- [User Question]: {question} ---\n")
    
    inputs = {"messages": [{"role": "user", "content": question}]}
    
    try:
        # 5. 运行 Agent 并流式输出过程
        print("--- [Agent Thinking & Tool Calling] ---")
        final_response = ""
        
        # 这里的 stream 模式会展示工具调用和模型思考的每一个步骤
        async for chunk in agent_graph.astream(inputs, stream_mode="updates"):
            for node_name, output in chunk.items():
                print(f"\n[Node: {node_name}]")
                
                if "messages" in output:
                    last_msg = output["messages"][-1]
                    # 如果是 AI 消息
                    if hasattr(last_msg, "content") and last_msg.content:
                        print(f"Content: {last_msg.content}")
                        final_response = last_msg.content
                    
                    # 如果包含工具调用
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for tc in last_msg.tool_calls:
                            print(f"Calling Tool: {tc['name']} with args: {tc['args']}")
        
        print("\n--- [Agent Final Summary] ---")
        if final_response:
            print(final_response)
        else:
            print("No final response received.")
    
    except Exception as e:
        # 打印详细的异常堆栈，方便定位
        import traceback
        print(f"\n[ERROR] Agent execution failed:")
        traceback.print_exc()

if __name__ == "__main__":
    # 检查配置
    if settings.API_KEY == "your_qwen_api_key" or settings.TAVILY_API_KEY == "your_tavily_api_key":
        print("❌ 错误: 请先在 .env 中配置真实的 API_KEY 和 TAVILY_API_KEY")
        sys.exit(1)
        
    asyncio.run(test_agent_with_mcp())
