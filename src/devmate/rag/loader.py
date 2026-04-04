import os
from typing import List
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_core.documents import Document

class DocLoader:
    """RAG 加载层：负责从文件系统加载文档"""
    
    def __init__(self, docs_dir: str):
        self.docs_dir = docs_dir

    def load_markdown(self) -> List[Document]:
        """加载指定目录下的所有 Markdown 文件"""
        if not os.path.exists(self.docs_dir):
            print(f"⚠️ [Loader] 目录不存在: {self.docs_dir}")
            return []
            
        print(f"--- [Loader] 正在从 {self.docs_dir} 加载文档 ---")
        loader = DirectoryLoader(
            self.docs_dir,
            glob="**/*.md",
            loader_cls=UnstructuredMarkdownLoader
        )
        try:
            documents = loader.load()
            print(f"✅ [Loader] 成功加载 {len(documents)} 个文档")
            return documents
        except Exception as e:
            print(f"❌ [Loader] 加载失败: {str(e)}")
            return []
