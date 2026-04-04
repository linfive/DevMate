from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class DocSplitter:
    """RAG 切分层：负责将长文档切分为语义块"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def split(self, documents: List[Document]) -> List[Document]:
        """对文档列表进行切分"""
        if not documents:
            return []
            
        print(f"--- [Splitter] 正在切分 {len(documents)} 个原始文档 ---")
        splits = self.splitter.split_documents(documents)
        print(f"✅ [Splitter] 成功生成 {len(splits)} 个文档片段")
        return splits
