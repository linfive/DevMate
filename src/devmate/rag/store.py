import os
import uuid
from typing import List
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from src.devmate.core.config import settings

class DocStore:
    """RAG 存储层：负责向量数据库的初始化与持久化"""
    
    def __init__(self, persist_dir: str, collection_name: str):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embeddings = DashScopeEmbeddings(
            model=settings.EMBEDDING_MODEL_NAME,
            dashscope_api_key=settings.API_KEY,
        )
        self.vector_store = None

    def get_or_create_store(self, documents: List[Document] = None) -> Chroma:
        if settings.CHROMA_MODE.lower() == "http":
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                host=settings.CHROMA_SERVER_HOST,
                port=settings.CHROMA_SERVER_PORT,
            )
            if documents:
                ids = [str(uuid.uuid4()) for _ in range(len(documents))]
                self.vector_store.add_documents(documents=documents, ids=ids)
                print("✅ [Store] 向量库写入完成")
            return self.vector_store

        if os.path.exists(self.persist_dir) and not documents:
            print(f"--- [Store] 正在加载现有向量库: {self.persist_dir} ---")
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings
            )
        elif documents:
            print(f"--- [Store] 正在创建并持久化向量库: {self.persist_dir} ---")
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                collection_name=self.collection_name,
                persist_directory=self.persist_dir
            )
            print(f"✅ [Store] 向量库持久化完成")
        else:
            print(f"⚠️ [Store] 向量库不存在且未提供初始化文档")
            
        return self.vector_store
