import os
from typing import Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class FileReaderInput(BaseModel):
    file_path: str = Field(..., description="要读取的文件路径（相对于 generated/ 的路径，或 generated/ 下的绝对路径）")
    with_line_numbers: bool = Field(False, description="是否为每行添加行号")

class FileReaderTool(BaseTool):
    name: str = "file_reader"
    description: str = "读取 generated/ 沙盒目录下的文件内容。在修改现有生成文件前使用。"
    args_schema: Type[BaseModel] = FileReaderInput

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

    def _resolve_sandbox_path(self, file_path: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        generated_root = os.path.abspath(os.path.join(project_root, "generated"))

        if os.path.isabs(file_path):
            candidate = os.path.abspath(file_path)
            if os.path.commonpath([generated_root, candidate]) != generated_root:
                raise ValueError("file_reader 只允许读取 generated/ 目录下的文件")
            return candidate

        clean_path = file_path.lstrip("/").lstrip("\\")
        if clean_path.startswith("generated/") or clean_path.startswith("generated\\"):
            clean_path = clean_path[len("generated/") :] if clean_path.startswith("generated/") else clean_path[len("generated\\") :]

        run_subdir = self._clean_run_subdir(os.environ.get("DEVMATE_RUN_SUBDIR", ""))
        if run_subdir and not clean_path.replace("\\", "/").startswith(run_subdir + "/"):
            clean_path = os.path.join(run_subdir, clean_path)

        candidate = os.path.abspath(os.path.join(generated_root, clean_path))
        if os.path.commonpath([generated_root, candidate]) != generated_root:
            raise ValueError("file_reader 只允许读取 generated/ 目录下的文件")
        return candidate

    def _run(self, file_path: str, with_line_numbers: bool = False) -> str:
        try:
            print(f"\n--- [Tool] file_reader: {file_path} ---", flush=True)
            abs_path = self._resolve_sandbox_path(file_path)
            if not os.path.exists(abs_path):
                return f"❌ 文件不存在: {file_path}"
            if os.path.isdir(abs_path):
                return f"❌ 目标是目录，无法读取: {file_path}"

            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if with_line_numbers:
                lines = content.splitlines()
                numbered = [f"{i:>4}: {line}" for i, line in enumerate(lines, start=1)]
                content = "\n".join(numbered) + ("\n" if content.endswith("\n") else "")

            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            rel_path = os.path.relpath(abs_path, project_root)
            if len(content) > 20000:
                content = content[:20000] + "\n\n[TRUNCATED]"
            return f"✅ 已读取: {rel_path}\n\n{content}"
        except Exception as e:
            return f"❌ 读取失败: {str(e)}"

    async def _arun(self, file_path: str, with_line_numbers: bool = False) -> str:
        return self._run(file_path=file_path, with_line_numbers=with_line_numbers)
