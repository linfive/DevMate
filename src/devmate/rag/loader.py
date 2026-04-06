import os
from pathlib import Path
from typing import List
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
        docs_path = Path(self.docs_dir)
        documents: List[Document] = []
        for path in docs_path.rglob("*.md"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"Error loading file {path}")
                print(f"❌ [Loader] 加载失败: {str(e)}")
                continue
            rel = str(path.relative_to(docs_path)).replace("\\", "/")
            documents.append(Document(page_content=text, metadata={"source": rel}))

        print(f"✅ [Loader] 成功加载 {len(documents)} 个文档")
        return documents
