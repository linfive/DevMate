import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# 获取项目根目录的绝对路径
# 逻辑：config.py 在 src/devmate/core/，往上跳三级到根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
env_path = os.path.join(project_root, ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_path,  # 使用绝对路径锁定 .env
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # === LLM 模型配置 ===
    AI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    API_KEY: str
    MODEL_NAME: str = "qwen-max"
    EMBEDDING_MODEL_NAME: str = "text-embedding-v3"

    # === MCP 网络搜索配置 ===
    TAVILY_API_KEY: str

    # === 可观测性配置 ===
    LANGCHAIN_TRACING_V2: str = "true"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "DevMate"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

# 全局配置实例
settings = Settings()

# 强制将 LangSmith 配置注入到系统环境变量中
# 因为 LangChain 框架主要从 os.environ 中读取这些配置
if settings.LANGCHAIN_TRACING_V2.lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
