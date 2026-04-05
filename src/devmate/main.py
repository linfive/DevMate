import asyncio
import os
import sys
import io

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
if script_dir in sys.path:
    sys.path.remove(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.devmate.agent.core import get_devmate_agent
from langchain_core.messages import HumanMessage, AIMessage

# 强制设置标准输出为 UTF-8，解决 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def chat_loop():
    """主 Agent 交互循环"""
    print("\n" + "="*50)
    print("🤖 DevMate AI 编程助手已启动")
    print("输入 'exit' 或 'quit' 退出，输入 'clear' 清空历史")
    print("="*50 + "\n")

    agent = get_devmate_agent()
    chat_history = []

    while True:
        try:
            user_input = input("👤 您: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["exit", "quit"]:
                print("👋 再见！")
                break
                
            if user_input.lower() == "clear":
                chat_history = []
                print("🧹 对话历史已清空")
                continue

            # 调用 Agent
            print("\n🤖 DevMate:\n", end="")
            parts = []
            async for delta in agent.astream(user_input, chat_history):
                print(delta, end="", flush=True)
                parts.append(delta)
            print("\n")
            response = "".join(parts)
            
            # 更新历史
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=response))
            
            # 保持历史长度，避免 Token 爆炸 (保留最近 10 轮)
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]

        except KeyboardInterrupt:
            print("\n👋 程序已终止")
            break
        except Exception as e:
            print(f"❌ 发生错误: {str(e)}")

def main():
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
