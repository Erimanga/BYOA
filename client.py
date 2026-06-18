"""
游戏资讯 Agent — LLM 驱动客户端
通过 MCP stdio 连接 agent_server，使用 Anthropic API (DeepSeek) 做推理，
实现「系统提示词 + 工具调用 + 任务调度」的完整 Agent 循环。

用法：
    python client.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# ── 配置 ──────────────────────────────────────────────

PROJECT_DIR = Path(__file__).parent
SYSTEM_PROMPT = (PROJECT_DIR / "prompts" / "system.md").read_text(encoding="utf-8")

API_KEY = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# ── 工具转换 ──────────────────────────────────────────


def mcp_tools_to_anthropic(mcp_tools) -> list[dict]:
    """将 MCP 工具定义列表转换为 Anthropic API 工具格式。"""
    converted = []
    for t in mcp_tools:
        converted.append({
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
        })
    return converted


# ── 结果提取 ──────────────────────────────────────────


def _extract_tool_result(result) -> str:
    """从 MCP CallToolResult 中提取文本内容（JSON 字符串）。"""
    if hasattr(result, "content") and result.content:
        for block in result.content:
            if hasattr(block, "text"):
                return block.text
            if hasattr(block, "data"):
                return json.dumps(block.data, ensure_ascii=False)
    return str(result)


# ── 主循环 ────────────────────────────────────────────


async def main() -> None:
    """启动 LLM 驱动的游戏资讯 Agent。"""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["agent_server.py"],
    )

    if not API_KEY:
        print("❌ 未设置 ANTHROPIC_AUTH_TOKEN 环境变量，请先配置 API Key。")
        return

    anthropic = Anthropic(api_key=API_KEY, base_url=BASE_URL)

    print("=" * 55)
    print("  🎮 游戏资讯 Agent — LLM 驱动")
    print("=" * 55)

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                mcp_tools = tools_result.tools
                anthropic_tools = mcp_tools_to_anthropic(mcp_tools)

                print(f"\n✅ 已连接 MCP Server，加载 {len(mcp_tools)} 个工具：")
                for t in mcp_tools:
                    print(f"   • {t.name} — {t.description[:55]}...")

                print("\n" + "-" * 55)
                print("  输入自然语言指令（如「查热销榜前10」）")
                print("  输入 quit 退出")
                print("-" * 55)

                messages: list[dict] = []

                while True:
                    user_input = input("\n🧑 你: ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() == "quit":
                        print("再见！")
                        break

                    messages.append({"role": "user", "content": user_input})

                    # ── Agent 循环：反复调用 LLM 直到不再需要工具 ──
                    while True:
                        print("   ⏳ 思考中...", end="\r")
                        response = anthropic.messages.create(
                            model=MODEL,
                            max_tokens=4096,
                            system=SYSTEM_PROMPT,
                            tools=anthropic_tools,
                            messages=messages,
                        )

                        tool_use_blocks = [
                            b for b in response.content if b.type == "tool_use"
                        ]

                        # 过滤掉 thinking blocks，只保留 text / tool_use
                        clean_content = [
                            b for b in response.content
                            if b.type in ("text", "tool_use")
                        ]

                        if not tool_use_blocks:
                            # 纯文本回复 — 输出并退出循环
                            print(" " * 20, end="\r")  # 清除 "思考中"
                            text_parts = [
                                b.text for b in clean_content if b.type == "text"
                            ]
                            reply = "\n".join(text_parts)
                            print(f"\n🤖 助手:\n{reply}")
                            messages.append({
                                "role": "assistant",
                                "content": clean_content,
                            })
                            break

                        # ── 有工具调用：并行执行 ──
                        messages.append({
                            "role": "assistant",
                            "content": clean_content,
                        })

                        async def _run_one(block):
                            """执行单个工具调用，返回 tool_result。"""
                            tool_name = block.name
                            tool_input = (
                                block.input if isinstance(block.input, dict) else {}
                            )
                            print(
                                f"\n🔧 调用: {tool_name}("
                                f"{json.dumps(tool_input, ensure_ascii=False)})"
                            )
                            try:
                                result = await session.call_tool(
                                    tool_name, tool_input
                                )
                                result_text = _extract_tool_result(result)
                                preview = result_text[:120].replace("\n", " ")
                                print(f"   ✅ 返回: {preview}...")
                            except Exception as e:
                                result_text = json.dumps(
                                    {"error": str(e)}, ensure_ascii=False
                                )
                                print(f"   ❌ 错误: {e}")
                            return {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text,
                            }

                        # 并行执行所有工具调用
                        tool_results = await asyncio.gather(
                            *[_run_one(b) for b in tool_use_blocks]
                        )
                        tool_results = list(tool_results)

                        messages.append({"role": "user", "content": tool_results})
                        # 回到循环顶部，让 LLM 处理工具结果

    except FileNotFoundError:
        print("❌ 找不到 agent_server.py，请在 BYOA 目录下运行")
    except KeyboardInterrupt:
        print("\n再见！")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
