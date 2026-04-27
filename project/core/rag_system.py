import uuid
from langchain_ollama import ChatOllama
import config
from db.vector_db_manager import VectorDbManager
from db.parent_store_manager import ParentStoreManager
from document_chunker import DocumentChuncker
from rag_agent.tools import ToolFactory
from rag_agent.graph import create_agent_graph
from core.observability import Observability

#添加 1
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools  # 需要安装 langchain-mcp-adapters

import asyncio
from langchain_core.tools import StructuredTool

class RAGSystem:

    def __init__(self, collection_name=config.CHILD_COLLECTION):
        self.collection_name = collection_name
        self.vector_db = VectorDbManager()
        self.parent_store = ParentStoreManager()
        self.chunker = DocumentChuncker()
        self.observability = Observability()
        self.agent_graph = None
        self.thread_id = str(uuid.uuid4())
        self.recursion_limit = config.GRAPH_RECURSION_LIMIT
        #添加2
        self.mcp_tools = []  # 存储从 MCP 加载的工具
        self.mcp_session = None  # MCP 会话对象




    #添加3
    async def _init_mcp_session(self):
        """异步初始化 MCP 会话，返回原始异步工具列表"""
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "my_mcp_server"]
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.mcp_session = session
                self.mcp_tools = await load_mcp_tools(session)
                print(f"✅ Loaded {len(self.mcp_tools)} MCP tools (async): {[t.name for t in self.mcp_tools]}")
        # """异步初始化 MCP 会话"""
        # # print("🔧 Starting MCP session...")
        # server_params = StdioServerParameters(
        #     command="python",  # 或你的 MCP 服务器启动命令
        #     args=["-m", "my_mcp_server"]
        # )
        # try:
        #     async with stdio_client(server_params) as (read, write):
        #         # print("📡 stdio_client connected")
        #         async with ClientSession(read, write) as session:
        #             await session.initialize()
        #             self.mcp_session = session
        #             # 加载该 MCP 服务器提供的所有工具
        #             raw_mcp_tools = await load_mcp_tools(session)
        #             # print("🤝 Session initialized")
        #             self.mcp_tools = [make_sync_tool(t) for t in raw_mcp_tools]
        #             # print(f"🔄 Converted to sync tools: {[t.name for t in self.mcp_tools]}")
        # except Exception as e:
        #     print(f"❌ MCP initialization failed: {e}")
        #     import traceback
        #     traceback.print_exc()
        #     self.mcp_tools = []



    def initialize(self):
        self.vector_db.create_collection(self.collection_name)
        collection = self.vector_db.get_collection(self.collection_name)

        llm = ChatOllama(model=config.LLM_MODEL, temperature=config.LLM_TEMPERATURE)
        tools = ToolFactory(collection).create_tools()

        # if getattr(config, 'ENABLE_MCP', False):
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        #     loop.run_until_complete(self._init_mcp_session())
        #     all_tools = local_tools + self.mcp_tools
        #     print(f"✅ Loaded {len(self.mcp_tools)} MCP tools: {[t.name for t in self.mcp_tools]}")
        # else:
        #     all_tools = local_tools
        # print('tools=',tools)
        self.agent_graph = create_agent_graph(llm,tools)


    def get_config(self):
        cfg = {"configurable": {"thread_id": self.thread_id}, "recursion_limit": self.recursion_limit}
        handler = self.observability.get_handler()
        if handler:
            cfg["callbacks"] = [handler]
        return cfg

    def reset_thread(self):
        try:
            self.agent_graph.checkpointer.delete_thread(self.thread_id)
        except Exception as e:
            print(f"Warning: Could not delete thread {self.thread_id}: {e}")
        self.thread_id = str(uuid.uuid4())