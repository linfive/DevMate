import sys
import os
import asyncio
import io
from typing import List
from langchain_core.messages import HumanMessage, BaseMessage

# 强制设置标准输出为 UTF-8，解决 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 动态添加项目根目录到 sys.path，确保能找到 src 包
current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.devmate.agent.core import get_devmate_agent

async def validate_phase_4():
    """
    第四阶段验收脚本：验证 Agent 的综合编程辅助能力
    验收点：
    1. Agent 循环与工具自主调用 (MCP & RAG)
    2. 提示词工程规范 (必须包含文件路径)
    3. 可观测性集成 (后台生成 Trace)
    """
    print("\n" + "="*50)
    print("🚀 [Phase 4 Validation] 正在启动 Agent 核心验收")
    print("="*50)

    try:
        agent = get_devmate_agent()
        chat_history: List[BaseMessage] = []

        # 设计一个需要同时查阅【内部文档】和【外部实时技术】的复杂编程任务
        complex_query = (
            "请基于我们项目的 FastAPI 目录规范，参考 2024 年最新的 React 19 最佳实践，"
            "为我生成一个简单的『徒步路线评论』提交接口的代码，并告诉我前端对应的组件应该放哪。"
        )

        print(f"\n[User Task]: {complex_query}\n")
        print("--- [Agent 思考中，请稍候...] ---")
        
        response = await agent.aask(complex_query, chat_history)

        print("\n" + "-"*30 + " [Agent 回答] " + "-"*30)
        print(response)
        print("-" * 75)

        # 自动化规范检查
        print("\n[自动检查 - 提示词工程规范]:")
        pass_check = True
        if "### File:" in response:
            print("✅ 通过：回复中包含建议的文件路径。")
        else:
            print("❌ 失败：回复中未发现 '### File:' 格式的文件标注。")
            pass_check = False

        if "src/api/" in response or "src/devmate/" in response:
            print("✅ 通过：Agent 识别并遵循了项目的目录结构。")
        else:
            print("⚠️ 警告：回复中未明确体现项目特定的目录结构。")

        print("\n" + "="*50)
        print("💡 [可观测性人工验收指引]:")
        print("1. 请登录 https://smith.langchain.com/")
        print("2. 在 'DevMate' 项目下查看最新的 Trace。")
        print("3. 验证是否看到 'search_knowledge_base' 和 'search_web' 的调用记录。")
        print("="*50 + "\n")

        if pass_check:
            print("[SUCCESS] Phase 4 technical requirements met.")
        else:
            print("[PARTIAL] Phase 4 logic works but prompt compliance needs attention.")

    except Exception as e:
        print(f"❌ 验收过程中发生异常: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(validate_phase_4())
