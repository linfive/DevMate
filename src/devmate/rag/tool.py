import os
from langchain.tools import BaseTool
from pydantic import Field
from src.devmate.rag.loader import DocLoader
from src.devmate.rag.splitter import DocSplitter
from src.devmate.rag.store import DocStore
from src.devmate.rag.retriever import DocRetriever

class RAGSearchTool(BaseTool):
    """LangChain 工具包装器，用于检索本地知识库"""
    name: str = "search_knowledge_base"
    description: str = "在本地开发指南和项目文档中检索相关规范、最佳实践或技术细节。当你需要了解内部代码风格或架构要求时，请优先使用此工具。"
    
    retriever: DocRetriever = Field(exclude=True)

    def _run(self, query: str) -> str:
        """执行同步检索"""
        print(f"\n--- [Tool] search_knowledge_base: {query} ---", flush=True)
        return self.retriever.retrieve(query)

    async def _arun(self, query: str) -> str:
        """执行异步检索 (暂用同步实现)"""
        return self._run(query)

def get_rag_tool() -> RAGSearchTool:
    """初始化全链路 RAG 系统并返回工具实例"""
    # 路径配置
    current_file_path = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_file_path, "..", "..", ".."))
    docs_dir = os.path.join(project_root, "docs")
    persist_dir = os.path.join(project_root, ".chroma_db")

    # 1. 存储管理器初始化
    store_manager = DocStore(persist_dir)
    
    # 2. 检查向量库是否已存在
    if os.path.exists(persist_dir):
        print(f"--- [RAG] 发现现有向量库，跳过初始化 ---")
        vector_store = store_manager.get_or_create_store()
    else:
        # 只有在库不存在时才进行加载和切分
        print(f"--- [RAG] 向量库不存在，开始初始化全量文档 ---")
        # 1. 加载
        loader = DocLoader(docs_dir)
        docs = loader.load_markdown()

        # 2. 切分
        splitter = DocSplitter(chunk_size=1000, chunk_overlap=100)
        splits = splitter.split(docs)

        # 3. 存储
        vector_store = store_manager.get_or_create_store(splits if splits else None)

    # 4. 检索器
    retriever = DocRetriever(vector_store)

    return RAGSearchTool(retriever=retriever)
