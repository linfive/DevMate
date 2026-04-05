import os
import json
import shutil
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

def _compute_docs_manifest(docs_dir: str) -> dict[str, float]:
    manifest: dict[str, float] = {}
    if not os.path.exists(docs_dir):
        return manifest
    for root, _, files in os.walk(docs_dir):
        for name in files:
            if not name.lower().endswith(".md"):
                continue
            abs_path = os.path.join(root, name)
            rel = os.path.relpath(abs_path, docs_dir).replace("\\", "/")
            try:
                manifest[rel] = os.path.getmtime(abs_path)
            except OSError:
                continue
    return manifest

def _load_manifest(path: str) -> dict[str, float] | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): float(v) for k, v in data.items()}
    except Exception:
        return None
    return None

def _save_manifest(path: str, manifest: dict[str, float]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

def get_rag_tool() -> RAGSearchTool:
    """初始化全链路 RAG 系统并返回工具实例"""
    # 路径配置
    current_file_path = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_file_path, "..", "..", ".."))
    docs_dir = os.path.join(project_root, "docs")
    persist_dir = os.path.join(project_root, ".chroma_db")

    # 1. 存储管理器初始化
    store_manager = DocStore(persist_dir)
    
    current_manifest = _compute_docs_manifest(docs_dir)
    manifest_path = os.path.join(persist_dir, "_devmate_docs_manifest.json")

    if os.path.exists(persist_dir):
        old_manifest = _load_manifest(manifest_path)
        if old_manifest == current_manifest:
            print(f"--- [RAG] 发现现有向量库，跳过初始化 ---")
            vector_store = store_manager.get_or_create_store()
        else:
            print("--- [RAG] 文档已变更，重建向量库 ---")
            try:
                shutil.rmtree(persist_dir)
            except Exception:
                pass
            loader = DocLoader(docs_dir)
            docs = loader.load_markdown()
            splitter = DocSplitter(chunk_size=1000, chunk_overlap=100)
            splits = splitter.split(docs)
            vector_store = store_manager.get_or_create_store(splits if splits else None)
            _save_manifest(manifest_path, current_manifest)
    else:
        print(f"--- [RAG] 向量库不存在，开始初始化全量文档 ---")
        loader = DocLoader(docs_dir)
        docs = loader.load_markdown()
        splitter = DocSplitter(chunk_size=1000, chunk_overlap=100)
        splits = splitter.split(docs)
        vector_store = store_manager.get_or_create_store(splits if splits else None)
        _save_manifest(manifest_path, current_manifest)

    # 4. 检索器
    retriever = DocRetriever(vector_store)

    return RAGSearchTool(retriever=retriever)
