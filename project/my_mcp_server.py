import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from typing import List, Optional

_mcp_client = None

from langchain_core.tools import tool as synctool_wrapper  # 用普通 @tool 装饰器
import asyncio
from typing import Any, Callable

# def _make_sync_tool(original_tool: BaseTool) -> BaseTool:
#     """将只实现了异步的 StructuredTool 转为可同步执行的 Tool"""
#     async def _run_async(**kwargs):
#         # 原始工具仍是异步的，直接调用 ainvoke
#         return await original_tool.ainvoke(kwargs)
#
#     # 定义一个同步函数包装器，内部安全地运行异步任务
#     def sync_func(**kwargs) -> Any:
#         try:
#             loop = asyncio.get_running_loop()
#         except RuntimeError:
#             loop = None
#
#         if loop is None:
#             # 当前没有运行的事件循环，可以新建一个
#             return asyncio.run(_run_async(**kwargs))
#         else:
#             # 已有运行中的循环（如 Jupyter），用 run_until_complete 会报错
#             # 这里可以用 nest_asyncio 或线程方案，但通常工具调用发生在独立线程中
#             # 如果你的环境真的有运行中的循环，建议方案二
#             import nest_asyncio
#             nest_asyncio.apply()
#             return loop.run_until_complete(_run_async(**kwargs))
#
#     # 返回一个新的 Tool 实例，保留原始工具的 name / description
#     return synctool_wrapper(
#         sync_func,
#         name=original_tool.name,
#         description=original_tool.description,
#         args_schema=original_tool.args_schema if hasattr(original_tool, 'args_schema') else None
#     )

from langchain_core.tools import StructuredTool

def _make_sync_tool(original_tool: BaseTool) -> BaseTool:
    async def _run_async(**kwargs):
        return await original_tool.ainvoke(kwargs)

    def sync_func(**kwargs) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_run_async(**kwargs))
        else:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(_run_async(**kwargs))

    return StructuredTool.from_function(
        func=sync_func,
        name=original_tool.name,
        description=original_tool.description,
        args_schema=original_tool.args_schema if hasattr(original_tool, 'args_schema') else None,
    )

def load_mcp_tools_sync(server_config: Optional[dict] = None) -> List[BaseTool]:
    global _mcp_client
    if server_config is None:
        # server_config = {}   # 替换为您的实际配置，例如：
        server_config = {
                    "medical-mcp": {
                        "command": "node",  # 或 "npx"
                        "args": ["/root/.nvm/versions/node/v24.15.0/lib/node_modules/medical-mcp/build/index.js"],  # 替换为你的实际路径
                        "transport": "stdio",
                    }
                }

    try:
        print(1)
        async def _init():
            client=MultiServerMCPClient(server_config)
            print(6)
            tools = await client.get_tools()
            print(7)
            sync_tools = [_make_sync_tool(t) for t in tools] #add
            print(8)
            return client,sync_tools
        loop = asyncio.new_event_loop()
        print(2)
        asyncio.set_event_loop(loop)
        print(3)
        client, tools = loop.run_until_complete(_init())
        print(4)
        loop.close()
        print(5)
        _mcp_client = client
        print(f"✅ MCP 工具加载成功：{[t.name for t in tools]}")
        return tools
    except Exception as e:
        print(f"⚠️ MCP 工具加载失败，将仅使用本地工具：{e}")
        return []

def cleanup_mcp():
    global _mcp_client
    if _mcp_client is not None:
        print("正在关闭 MCP 客户端连接...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_mcp_client.disconnect())
            loop.close()
        except Exception as e:
            print(f"MCP 关闭失败：{e}")
        finally:
            _mcp_client = None
            print("MCP 客户端已关闭。")