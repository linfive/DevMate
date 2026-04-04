import sys
import os
import asyncio
from typing import List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# 动态添加 src 路径到 PYTHONPATH
current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, ".."))
src_path = os.path.join(project_root, "src")
sys.path.append(src_path)

from src.devmate.agent.core import get_devmate_agent

async def test_agent_full():
    """测试 Agent 全链路：模型自主决策并调用工具"""
    print("\n--- 正在初始化 DevMate Agent ---")
    try:
        agent = get_devmate_agent()
        print("✅ Agent 初始化成功！\n")
        
        chat_history: List[BaseMessage] = []
        
        # 场景 1: 本地知识库检索 (触发 search_knowledge_base)
        query1 = "项目的前端组件开发规范是什么？"
        print(f"\n[Test 1] {query1}")
        response1 = await agent.aask(query1, chat_history)
        print(f"\n[Agent Response 1]:\n{response1}\n")
        chat_history.append(HumanMessage(content=query1))
        chat_history.append(AIMessage(content=response1))
        
        # 场景 2: 互联网搜索 (触发 search_web)
        query2 = "最新的 React 19 有什么显著的新特性？"
        print(f"\n[Test 2] {query2}")
        response2 = await agent.aask(query2, chat_history)
        print(f"\n[Agent Response 2]:\n{response2}\n")
        chat_history.append(HumanMessage(content=query2))
        chat_history.append(AIMessage(content=response2))

        # 场景 3: 综合决策 (可能先后调用两个工具)
        query3 = "基于我们项目的 FastAPI 规范，如果要实现一个根据 hiking trail ID 检索详细信息的路由，我该怎么写？"
        print(f"\n[Test 3] {query3}")
        response3 = await agent.aask(query3, chat_history)
        print(f"\n[Agent Response 3]:\n{response3}\n")

        print("[SUCCESS] Agent end-to-end verification completed.")
        
    except Exception as e:
        print(f"❌ [FAIL] Agent verification failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_full())
