import os
from typing import Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class FileWriterInput(BaseModel):
    file_path: str = Field(..., description="要写入的文件绝对路径或相对于项目根目录的路径")
    content: str = Field(..., description="要写入文件的完整代码内容")

class FileWriterTool(BaseTool):
    """DevMate 代码生成工具：负责将 Agent 生成的代码实际写入磁盘"""
    name: str = "file_writer"
    description: str = "将生成的代码内容写入到指定的文件路径中。在建议新服务或修改现有代码时使用此工具。"
    args_schema: Type[BaseModel] = FileWriterInput

    def _run(self, file_path: str, content: str) -> str:
        """同步写入文件到 generated/ 沙盒目录"""
        try:
            print(f"\n--- [Tool] file_writer: {file_path} ---", flush=True)
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            
            # 强制将所有生成路径重定向到 generated 文件夹
            # 去除路径开头的斜杠
            clean_path = file_path.lstrip("/").lstrip("\\")
            sandbox_path = os.path.join(project_root, "generated", clean_path)

            # 确保父目录存在
            os.makedirs(os.path.dirname(sandbox_path), exist_ok=True)

            with open(sandbox_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return f"✅ 成功将代码写入沙盒文件: {os.path.relpath(sandbox_path, project_root)}"
        except Exception as e:
            return f"❌ 写入文件失败: {str(e)}"

    async def _arun(self, file_path: str, content: str) -> str:
        """异步写入文件"""
        # 对于简单的文件 IO，直接调用同步版本即可，或者使用 aiofiles
        return self._run(file_path, content)
