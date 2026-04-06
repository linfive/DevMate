import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from langchain.tools import BaseTool
from pydantic import Field
from typing import Optional, Type, Any
from src.devmate.core.config import settings

# 获取项目根目录的绝对路径，确保子进程能找到 src 包
current_file_path = os.path.dirname(os.path.abspath(__file__))
# client.py 位于 src/devmate/mcp/，往上跳 3 级到项目根目录 (DevMate)
project_root = os.path.abspath(os.path.join(current_file_path, "..", "..", ".."))

class MCPSearchTool(BaseTool):
    """LangChain 工具包装器，用于调用 MCP 搜索工具"""
    name: str = "search_web"
    description: str = "使用 Tavily 搜索引擎在互联网上查找实时信息、API 文档或技术指南。"
    
    # 强制指定 server 参数，不让 Pydantic 误认为是 fields
    server_params: StdioServerParameters = Field(exclude=True)

    def _sanitize_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = []
        for ch in text:
            code = ord(ch)
            if 0xD800 <= code <= 0xDFFF:
                cleaned.append("\ufffd")
            else:
                cleaned.append(ch)
        return "".join(cleaned)

    async def _arun(self, query: str, search_depth: str = "basic") -> str:
        """异步执行工具"""
        try:
            print(f"\n--- [Tool] search_web: {query} ---", flush=True)
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
                        return self._sanitize_text(result.content[0].text)
                    return "No results found."
        except Exception as e:
            return f"Error calling MCP tool: {str(e)}"

    def _run(self, query: str, search_depth: str = "basic") -> str:
        """同步执行（LangChain 需要，但我们主要用异步）"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果当前线程没有 loop，创建一个新的
            return asyncio.run(self._arun(query, search_depth))


class MCPSearchToolSSE(BaseTool):
    name: str = "search_web"
    description: str = "使用 Tavily 搜索引擎在互联网上查找实时信息、API 文档或技术指南。"

    url: str = Field(exclude=True)

    def _sanitize_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = []
        for ch in text:
            code = ord(ch)
            if 0xD800 <= code <= 0xDFFF:
                cleaned.append("\ufffd")
            else:
                cleaned.append(ch)
        return "".join(cleaned)

    async def _arun(self, query: str, search_depth: str = "basic") -> str:
        try:
            print(f"\n--- [Tool] search_web: {query} ---", flush=True)
            async with sse_client(self.url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "search_web",
                        arguments={"query": query, "search_depth": search_depth},
                    )
                    if result and result.content:
                        return self._sanitize_text(result.content[0].text)
                    return "No results found."
        except Exception as e:
            return f"Error calling MCP tool: {str(e)}"

    def _run(self, query: str, search_depth: str = "basic") -> str:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return asyncio.run(self._arun(query, search_depth))

        if loop.is_running():
            try:
                import nest_asyncio

                nest_asyncio.apply()
                return asyncio.run(self._arun(query, search_depth))
            except ImportError:
                return "Error calling MCP tool: nest_asyncio is required only for sync calls inside a running event loop. Use the async tool path instead."
        else:
            return asyncio.run(self._arun(query, search_depth))
            
        if loop.is_running():
            # 如果 loop 已经在运行（例如在异步环境的线程池中），使用 nest_asyncio
            try:
                import nest_asyncio
                nest_asyncio.apply()
                return asyncio.run(self._arun(query, search_depth))
            except ImportError:
                return "Error calling MCP tool: nest_asyncio is required only for sync calls inside a running event loop. Use the async tool path instead."
        else:
            # 如果有 loop 但没运行
            return asyncio.run(self._arun(query, search_depth))

def get_mcp_search_tool() -> BaseTool:
    url = settings.DEVMATE_MCP_URL or os.environ.get("DEVMATE_MCP_URL")
    if url:
        return MCPSearchToolSSE(url=url)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.devmate.mcp.server"],
        env={
            "PYTHONPATH": project_root,
            "PATH": os.environ.get("PATH", ""),
        },
        cwd=project_root,
    )

    return MCPSearchTool(server_params=server_params)
