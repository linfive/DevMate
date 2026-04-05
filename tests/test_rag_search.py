import sys
import os

# 动态添加项目根目录到 sys.path，确保能找到 src 包
current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.devmate.rag.tool import get_rag_tool

def test_rag_tool():
    """测试 RAG 工具的全链路运行"""
    print("\n--- 正在初始化 RAG Search Tool ---")
    try:
        rag_tool = get_rag_tool()
        print(f"✅ RAG 工具初始化成功: {rag_tool.name}")
        
        # 测试查询 1: 严格遵循 checklist.md 要求
        query1 = "project guidelines"
        print(f"\n--- 正在执行检索 1: '{query1}' ---")
        result1 = rag_tool._run(query1)
        print(f"--- [检索结果 1] ---\n{result1}\n")
        
        # 测试查询 2: 搜索 FastAPI 相关
        query2 = "FastAPI 路由应该怎么写？"
        print(f"\n--- 正在执行检索 2: '{query2}' ---")
        result2 = rag_tool._run(query2)
        print(f"--- [检索结果 2] ---\n{result2}\n")

        print("[SUCCESS] RAG tool verification completed.")
        
    except Exception as e:
        print(f"❌ [FAIL] RAG tool verification failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rag_tool()
