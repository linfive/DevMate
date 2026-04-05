import asyncio
import os
import sys

# 确保能导入 src 包（把项目根目录加入 sys.path）
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.devmate.mcp.client import get_mcp_search_tool
from src.devmate.core.config import settings

async def test_mcp_search():
    """测试 MCP 搜索工具"""
    print("--- 正在初始化 MCP Search Tool ---")
    
    # 获取工具
    search_tool = get_mcp_search_tool()
    
    # 模拟用户查询
    query = "什么是大模型"
    print(f"--- 正在搜索关键词: '{query}' ---")
    
    try:
        # 运行异步查询
        result = await search_tool._arun(query=query, search_depth="basic")
        
        print("\n--- [Search Results Summary] ---")
        if "Error" in result:
            print(f"[FAIL] Test failed: {result}")
        else:
            print(f"[SUCCESS] Test passed! Result snippet:\n")
            # 打印结果的前 500 个字符
            print(result[:500].encode('utf-8', errors='replace').decode('utf-8') + "...")
            
    except Exception as e:
        print(f"[ERROR] Exception during execution: {str(e)}")

if __name__ == "__main__":
    # 检查 API Key 是否已配置
    if settings.TAVILY_API_KEY == "your_tavily_api_key":
        print("❌ 错误: 请先在 .env 中配置真实的 TAVILY_API_KEY")
        sys.exit(1)
        
    # 运行异步测试
    asyncio.run(test_mcp_search())
