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

    def _clean_run_subdir(self, run_subdir: str) -> str:
        s = (run_subdir or "").strip().replace("\\", "/").strip("/")
        if not s:
            return ""
        if ".." in s.split("/"):
            return ""
        if any(ch.isspace() for ch in s):
            return ""
        if not all(ch.isalnum() or ch in "/._-" for ch in s):
            return ""
        return s

    def _run(self, file_path: str, content: str) -> str:
        """同步写入文件到 generated/ 沙盒目录"""
        try:
            print(f"\n--- [Tool] file_writer: {file_path} ---", flush=True)
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            
            # 强制将所有生成路径重定向到 generated 文件夹
            # 去除路径开头的斜杠，并防止传入 generated/ 前缀导致套娃
            clean_path = file_path.lstrip("/").lstrip("\\")
            if clean_path.startswith("generated/") or clean_path.startswith("generated\\"):
                clean_path = clean_path[len("generated/") :] if clean_path.startswith("generated/") else clean_path[len("generated\\") :]
            run_subdir = self._clean_run_subdir(os.environ.get("DEVMATE_RUN_SUBDIR", ""))
            if run_subdir:
                sandbox_path = os.path.join(project_root, "generated", run_subdir, clean_path)
            else:
                sandbox_path = os.path.join(project_root, "generated", clean_path)

            # 确保父目录存在
            os.makedirs(os.path.dirname(sandbox_path), exist_ok=True)

            with open(sandbox_path, "w", encoding="utf-8") as f:
                f.write(content)
            rel = os.path.relpath(sandbox_path, project_root)
            print(f"--- [Tool] file_writer wrote: {rel} ---", flush=True)
            return f"✅ 成功将代码写入沙盒文件: {rel}"
        except Exception as e:
            msg = str(e)
            print(f"--- [Tool] file_writer error: {msg} ---", flush=True)
            return f"❌ 写入文件失败: {msg}"

    async def _arun(self, file_path: str, content: str) -> str:
        """异步写入文件"""
        # 对于简单的文件 IO，直接调用同步版本即可，或者使用 aiofiles
        return self._run(file_path, content)
