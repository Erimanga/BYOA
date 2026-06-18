"""
游戏资讯 Agent — MCP Server
提供 3 个工具：Steam 排行榜、IGN 中国新闻、邮件发送。

启动方式：
    python agent_server.py
    或用 MCP Inspector：
    npx @anthropic-ai/mcp-inspector python agent_server.py
"""

from mcp.server.fastmcp import FastMCP

from tools.steam_charts import get_steam_charts
from tools.ign_news import get_gaming_news
from tools.send_email import send_email

mcp = FastMCP(name="游戏资讯助手")


@mcp.tool(
    title="Steam 排行榜",
    description="获取 Steam 实时游戏排行榜。支持热销（topsellers）、热门游玩（mostplayed）、"
                "心愿单（topwishlisted）、新游热门（newreleases）四种榜单，返回 Top 游戏列表。",
)
async def steam_charts(chart_type: str = "topsellers", count: int = 20) -> dict:
    """
    获取 Steam 排行榜。

    chart_type: 榜单类型，可选 topsellers / mostplayed / topwishlisted / newreleases
    count: 返回数量，默认 20，最多 50
    """
    return await get_steam_charts(chart_type=chart_type, count=count)


@mcp.tool(
    title="IGN 中国新闻",
    description="获取 IGN 中国 (ign.com.cn) 最新游戏新闻。包含新闻、评测、前瞻、访谈等类型。",
)
async def gaming_news(count: int = 15) -> dict:
    """
    获取 IGN 中国最新游戏新闻。

    count: 返回数量，默认 15，最多 20
    """
    return await get_gaming_news(count=count)


@mcp.tool(
    title="发送邮件",
    description="将游戏资讯汇总通过邮件发送到指定邮箱。使用前需配置 SMTP 环境变量。",
)
async def email_send(recipient: str, subject: str, body: str) -> dict:
    """
    发送邮件。

    recipient: 收件人邮箱
    subject: 邮件主题
    body: 邮件正文（支持 HTML）
    """
    return await send_email(recipient=recipient, subject=subject, body=body)


if __name__ == "__main__":
    mcp.run(transport="stdio")
