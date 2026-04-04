import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain.tools import BaseTool
from pydantic import Field
from typing import Optional, Type, Any

# 获取 src 目录的绝对路径，确保子进程能找到包
current_file_path = os.path.dirname(os.path.abspath(__file__))
# 从 src/devmate/mcp/ 往上跳三级到项目根目录，再进 src
project_src_node = os.path.abspath(os.path.join(current_file_path, "..", "..", ".."))
src_path = os.path.join(project_src_node, "src")

class MCPSearchTool(BaseTool):
    """LangChain 工具包装器，用于调用 MCP 搜索工具"""
    name: str = "search_web"
    description: str = "使用 Tavily 搜索引擎在互联网上查找实时信息、API 文档或技术指南。"
    
    # 强制指定 server 参数，不让 Pydantic 误认为是 fields
    server_params: StdioServerParameters = Field(exclude=True)

    async def _arun(self, query: str, search_depth: str = "basic") -> str:
        """异步执行工具"""
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 调用 MCP 工具
                    result = await session.call_tool(
                        "search_web", 
                        arguments={"query": query, "search_depth": search_depth}
                    )
                    
                    # 解析结果
                    if result and result.content:
                        return result.content[0].text
                    return "No results found."
        except Exception as e:
            return f"Error calling MCP tool: {str(e)}"

    def _run(self, query: str, search_depth: str = "basic") -> str:
        """同步执行（LangChain 需要，但我们主要用异步）"""
        # 在同步环境中运行异步代码的简易方法
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已经在运行循环中，这种方式可能不适用，但在测试中通常没问题
            import nest_asyncio
            nest_asyncio.apply()
        return asyncio.run(self._arun(query, search_depth))

def get_mcp_search_tool() -> MCPSearchTool:
    """获取包装好的 MCP 搜索工具"""
    # 配置如何启动 MCP Server
    # 使用绝对路径的 PYTHONPATH，解决不同目录下运行的模块导入问题
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "devmate.mcp.server"],
        env={
            "PYTHONPATH": src_path,
            "PATH": os.environ.get("PATH", "") # 保留系统 PATH
        }
    )
    
    return MCPSearchTool(server_params=server_params)
