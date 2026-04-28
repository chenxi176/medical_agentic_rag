from typing import List
from langchain_core.tools import tool
from db.parent_store_manager import ParentStoreManager

import requests
import json
import logging
from typing import List, Dict, Any
from langchain_core.tools import tool
import config
from ddgs import DDGS

logger = logging.getLogger(__name__)

class ToolFactory:
    
    def __init__(self, collection):
        self.collection = collection
        self.parent_store_manager = ParentStoreManager()
        self.baidu_api_key = config.BAIDU_API_KEY
    
    def _search_child_chunks(self, query: str, limit: int) -> str:
        """Search for the top K most relevant child chunks.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
        """
        try:
            results = self.collection.similarity_search(query, k=limit, score_threshold=0.7)
            # print('results',results)
            if not results:
                return "NO_RELEVANT_CHUNKS"

            return "\n\n".join([
                f"Parent ID: {doc.metadata.get('parent_id', '')}\n"
                f"File Name: {doc.metadata.get('source', '')}\n"
                f"Content: {doc.page_content.strip()}"
                for doc in results
            ])            

        except Exception as e:
            return f"RETRIEVAL_ERROR: {str(e)}"
    
    def _retrieve_many_parent_chunks(self, parent_ids: List[str]) -> str:
        """Retrieve full parent chunks by their IDs.
    
        Args:
            parent_ids: List of parent chunk IDs to retrieve
        """
        try:
            ids = [parent_ids] if isinstance(parent_ids, str) else list(parent_ids)
            raw_parents = self.parent_store_manager.load_content_many(ids)
            if not raw_parents:
                return "NO_PARENT_DOCUMENTS"

            return "\n\n".join([
                f"Parent ID: {doc.get('parent_id', 'n/a')}\n"
                f"File Name: {doc.get('metadata', {}).get('source', 'unknown')}\n"
                f"Content: {doc.get('content', '').strip()}"
                for doc in raw_parents
            ])            

        except Exception as e:
            return f"PARENT_RETRIEVAL_ERROR: {str(e)}"
    
    def _retrieve_parent_chunks(self, parent_id: str) -> str:
        """Retrieve full parent chunks by their IDs.
    
        Args:
            parent_id: Parent chunk ID to retrieve
        """
        try:
            parent = self.parent_store_manager.load_content(parent_id)
            if not parent:
                return "NO_PARENT_DOCUMENT"

            return (
                f"Parent ID: {parent.get('parent_id', 'n/a')}\n"
                f"File Name: {parent.get('metadata', {}).get('source', 'unknown')}\n"
                f"Content: {parent.get('content', '').strip()}"
            )          

        except Exception as e:
            return f"PARENT_RETRIEVAL_ERROR: {str(e)}"


    # def create_tools(self) -> List:
    #     """Create and return the list of tools."""
    #     search_tool = tool("search_child_chunks")(self._search_child_chunks)
    #     retrieve_tool = tool("retrieve_parent_chunks")(self._retrieve_parent_chunks)
    #
    #     return [search_tool, retrieve_tool]



    def _web_search_tool(self, query: str, max_results: int = 5) -> str:
        """
                使用搜索引擎实时查询互联网上的最新信息。
                当用户询问实时新闻、天气、股价、赛事结果、最新事件，或者本地知识库无法回答的问题时，应该使用此工具。

                参数:
                    query (str): 要搜索的关键词。
                    max_results (int, optional): 需要返回的最大结果数。默认是5，API最大支持50。

                返回:
                    str: 格式化后的搜索结果字符串。
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return f"未找到关于 '{query}' 的结果。"
            output = []
            for idx, r in enumerate(results, 1):
                title = r.get("title", "无标题")
                link = r.get("href", "#")
                body = r.get("body", "无摘要")
                output.append(f"{idx}. [{title}]({link})\n   {body}\n")
            return "\n".join(output)
        except Exception as e:
            return f"搜索失败: {str(e)}"

    def create_tools(self) -> List:
        """创建工具列表，现在包含3个工具"""
        search_tool = tool("search_child_chunks")(self._search_child_chunks)
        retrieve_tool = tool("retrieve_parent_chunks")(self._retrieve_parent_chunks)
        web_tool = tool("web_search")(self._web_search_tool)  # 新增的联网搜索工具

        return [search_tool, retrieve_tool, web_tool]


