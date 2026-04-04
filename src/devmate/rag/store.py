import os
from typing import List
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from src.devmate.core.config import settings

class DocStore:
    """RAG 存储层：负责向量数据库的初始化与持久化"""
    
    def __init__(self, persist_dir: str):
        self.persist_dir = persist_dir
        self.embeddings = DashScopeEmbeddings(
            model=settings.EMBEDDING_MODEL_NAME,
            dashscope_api_key=settings.API_KEY,
        )
        self.vector_store = None

    def get_or_create_store(self, documents: List[Document] = None) -> Chroma:
        """获取现有存储或根据文档创建新存储"""
        if os.path.exists(self.persist_dir) and not documents:
            print(f"--- [Store] 正在加载现有向量库: {self.persist_dir} ---")
            self.vector_store = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings
            )
        elif documents:
            print(f"--- [Store] 正在创建并持久化向量库: {self.persist_dir} ---")
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.persist_dir
            )
            print(f"✅ [Store] 向量库持久化完成")
        else:
            print(f"⚠️ [Store] 向量库不存在且未提供初始化文档")
            
        return self.vector_store
