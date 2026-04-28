# my_mcp_server.py
import json
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from duckduckgo_search import DDGS  # pip install duckduckgo-search

server = Server("rag-extension-server")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="web_search",
            description="Search the internet for real-time, up-to-date information. Use this when the local knowledge base does NOT contain the answer, especially for current events, weather, news, or any time-sensitive query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询词"},
                    "max_results": {
                        "type": "integer",
                        "description": "返回的最大结果数，默认为5",
                        "default": 5
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
        name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    print('handle_call_tool')
    if name == "web_search":
        print("ok")
        query = arguments["query"]
        max_results = arguments.get("max_results", 5)
        results = perform_web_search(query, max_results)
        # print('results', results)
        formatted = format_search_results(results)
        return [types.TextContent(type="text", text=formatted)]

    raise ValueError(f"Unknown tool: {name}")


def perform_web_search(query: str, max_results: int = 5) -> list[dict]:
    """使用 DuckDuckGo 执行网页搜索"""
    print("Performing web search for query:")
    with DDGS() as ddgs:
        results = []
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title"),
                "href": r.get("href"),
                "body": r.get("body")
            })
        return results


def format_search_results(results: list[dict]) -> str:
    """将搜索结果格式化为易读的文本"""
    if not results:
        return "未找到相关搜索结果。"
    lines = []
    for i, res in enumerate(results, 1):
        lines.append(f"{i}. {res['title']}")
        lines.append(f"   链接: {res['href']}")
        lines.append(f"   摘要: {res['body']}\n")
    return "\n".join(lines)


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="web-search-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
        await asyncio.Event().wait()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())