import os
import sys

# 强制设置标准输出为 UTF-8，解决 Windows 控制台编码问题
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 确保能导入 src 下的代码
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(os.path.join(project_root, "src"))

from devmate.core.config import settings
from langsmith import Client

def verify_connection():
    print(f"--- [LangSmith 连接测试] ---")
    print(f"Project: {settings.LANGCHAIN_PROJECT}")
    print(f"Endpoint: {settings.LANGCHAIN_ENDPOINT}")
    
    # 检查环境变量是否已注入
    tracing_v2 = os.environ.get('LANGCHAIN_TRACING_V2')
    api_key = os.environ.get('LANGCHAIN_API_KEY')
    
    print(f"Tracing Enabled (ENV): {tracing_v2}")
    print(f"API Key Present (ENV): {'Yes' if api_key else 'No'}")
    
    try:
        client = Client()
        # 尝试列出项目以验证 API Key
        # 注意：这里如果 Key 错误会抛出异常
        projects = list(client.list_projects())
        print(f"✅ 连接成功! 你的账号下共有 {len(projects)} 个项目。")
        print(f"请检查官网: https://smith.langchain.com/projects")
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        print("\n检查建议:")
        print("1. 请确保 .env 中的 LANGCHAIN_API_KEY 是正确的。")
        print("2. 检查网络是否能访问 api.smith.langchain.com。")

if __name__ == "__main__":
    verify_connection()
