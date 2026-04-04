import os
from langchain_chroma import Chroma

class DocRetriever:
    """RAG 检索层：核心搜索逻辑"""
    
    def __init__(self, vector_store: Chroma):
        self.vector_store = vector_store

    def retrieve(self, query: str, k: int = 4) -> str:
        """执行相似度检索并格式化输出"""
        if not self.vector_store:
            return "Knowledge base is not initialized."

        print(f"--- [Retriever] 正在检索: '{query}' ---")
        results = self.vector_store.similarity_search(query, k=k)
        
        if not results:
            return "No relevant internal documents found."

        formatted_parts = []
        for i, doc in enumerate(results):
            source = os.path.basename(doc.metadata.get("source", "Unknown"))
            content = doc.page_content.strip()
            formatted_parts.append(f"[Result {i+1}] (Source: {source})\n{content}")
            
        return "\n\n---\n\n".join(formatted_parts)
