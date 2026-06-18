"""
Steam 排行榜工具 — 获取 Steam 热销 / 热门 / 心愿单 / 新游排行榜。
数据来源：蒸汽平台 (store.steamchina.com) 搜索页，国内可访问。
"""

from typing import Any

import httpx
from bs4 import BeautifulSoup

# 蒸汽平台搜索页 — 不同 filter 对应不同榜单
CHART_URLS = {
    "topsellers":    "https://store.steamchina.com/search/?filter=topsellers",
    "mostplayed":    "https://store.steamchina.com/search/?filter=mostplayed",
    "topwishlisted": "https://store.steamchina.com/search/?filter=topwishlisted",
    "newreleases":   "https://store.steamchina.com/search/?filter=newreleases",
}

CHART_LABELS = {
    "topsellers":    "热销排行",
    "mostplayed":    "热门游玩",
    "topwishlisted": "心愿单排行",
    "newreleases":   "新游热门",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


async def get_steam_charts(chart_type: str = "topsellers", count: int = 20) -> dict[str, Any]:
    """
    获取 Steam 排行榜（数据来源：蒸汽平台）。

    Args:
        chart_type: 榜单类型 — topsellers | mostplayed | topwishlisted | newreleases
        count:      返回条数，默认 20，最多 50

    Returns:
        { chart_name, chart_type, total, games: [{rank, name, app_id, price, category, cover_url}] }
    """
    if chart_type not in CHART_URLS:
        return {
            "error": (
                f"不支持的榜单类型 '{chart_type}'。"
                f"可选：{', '.join(CHART_URLS.keys())}"
            )
        }

    url = CHART_URLS[chart_type]
    label = CHART_LABELS[chart_type]
    count = min(count, 50)  # 蒸汽平台每页最多 50 条

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)

        if resp.status_code != 200:
            return {"error": f"请求失败，HTTP {resp.status_code}"}

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("a[data-ds-appid]")

        if not rows:
            return {"error": "未能从页面中解析出排行榜数据，页面结构可能已变更"}

        games: list[dict[str, Any]] = []
        for rank, row in enumerate(rows[:count], start=1):
            game = _parse_game_row(row, rank)
            if game:
                games.append(game)

        return {
            "chart_name": f"Steam {label}",
            "chart_type": chart_type,
            "total": len(games),
            "games": games,
        }

    except httpx.TimeoutException:
        return {"error": "请求 Steam 超时，请稍后重试"}
    except Exception as e:
        return {"error": f"获取排行榜时出错：{str(e)}"}


def _parse_game_row(row, rank: int) -> dict[str, Any] | None:
    """从单个搜索结果行中提取游戏信息。"""
    try:
        app_id = row.get("data-ds-appid", "")
        if not app_id:
            return None

        # 游戏名
        title_el = row.select_one(".title")
        name = title_el.text.strip() if title_el else "Unknown"

        # 价格
        price_el = (
            row.select_one(".discount_final_price")
            or row.select_one(".search_price")
        )
        price = _clean_text(price_el) if price_el else "N/A"

        # 折扣信息
        discount_el = row.select_one(".discount_pct")
        discount = _clean_text(discount_el) if discount_el else ""

        # 原始价格（有折扣时显示）
        original_el = row.select_one(".discount_original_price")
        original_price = _clean_text(original_el) if original_el else ""

        # 分类 / 标签
        category_el = row.select_one(".search_category")
        category = _clean_text(category_el) if category_el else ""

        # 封面图
        img = row.select_one("img")
        cover_url = img.get("src", "") if img else ""

        # 发行日期
        date_el = row.select_one(".search_released")
        released = _clean_text(date_el) if date_el else ""

        # 评测
        review_el = row.select_one(".search_review_summary")
        review = _clean_text(review_el) if review_el else ""

        return {
            "rank": rank,
            "name": name,
            "app_id": int(app_id),
            "price": price,
            "original_price": original_price,
            "discount": discount,
            "category": category,
            "review": review,
            "released": released,
            "cover_url": cover_url,
        }
    except Exception:
        return None


def _clean_text(el) -> str:
    """去除多余空白。"""
    return " ".join(el.get_text(separator=" ", strip=True).split())
