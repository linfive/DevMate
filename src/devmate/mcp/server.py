import asyncio
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from tavily import TavilyClient
from devmate.core.config import settings

# 初始化 Tavily 客户端
tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)

# 创建 MCP Server
server = Server("devmate-search-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出可用的搜索工具"""
    return [
        types.Tool(
            name="search_web",
            description="使用 Tavily 搜索引擎在互联网上查找实时信息、API 文档或技术指南。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或问题"
                    },
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "default": "basic",
                        "description": "搜索深度：basic (快速) 或 advanced (更详细)"
                    }
                },
                "required": ["query"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """执行工具调用"""
    if name != "search_web":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments or "query" not in arguments:
        raise ValueError("Missing query argument")

    query = arguments["query"]
    search_depth = arguments.get("search_depth", "basic")

    try:
        # 调用 Tavily API
        # search_depth 在 Tavily SDK 中对应 search_depth 参数
        response = tavily.search(query=query, search_depth=search_depth)
        
        # 格式化搜索结果
        results = []
        for result in response.get("results", []):
            results.append(
                f"Title: {result.get('title')}\nURL: {result.get('url')}\nContent: {result.get('content')}\n"
            )
        
        combined_results = "\n---\n".join(results) if results else "No results found."
        
        return [
            types.TextContent(
                type="text",
                text=f"Search results for '{query}':\n\n{combined_results}"
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error performing search: {str(e)}"
            )
        ]

async def main():
    # 运行 stdio 模式的 MCP Server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="devmate-search-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
