from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
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
