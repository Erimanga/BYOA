"""
IGN 中国游戏新闻工具 — 抓取 IGN 中国最新游戏资讯。
数据来源：https://www.ign.com.cn/article
"""

from typing import Any

import httpx
from bs4 import BeautifulSoup

NEWS_URL = "https://www.ign.com.cn/article"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 文章类型中文映射
TYPE_LABELS = {
    "NEWS":      "新闻",
    "REVIEW":    "评测",
    "PREVIEW":   "前瞻",
    "INTERVIEW": "访谈",
    "FEATURE":   "专题",
    "GUIDE":     "攻略",
    "VIDEO":     "视频",
}


async def get_gaming_news(count: int = 15) -> dict[str, Any]:
    """
    获取 IGN 中国最新游戏新闻。

    Args:
        count: 返回条数，默认 15，最多 20

    Returns:
        { source, total, articles: [{title, url, type, time_ago, description, image_url, category}] }
    """
    count = min(count, 20)

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(NEWS_URL, headers=HEADERS)

        if resp.status_code != 200:
            return {"error": f"请求 IGN 中国失败，HTTP {resp.status_code}"}

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("article", class_="article")

        if not articles:
            return {"error": "未能从 IGN 中国页面解析出新闻列表，页面结构可能已变更"}

        news_list: list[dict[str, Any]] = []
        for art in articles[:count]:
            item = _parse_article(art)
            if item:
                news_list.append(item)

        return {
            "source": "IGN 中国",
            "url": NEWS_URL,
            "total": len(news_list),
            "articles": news_list,
        }

    except httpx.TimeoutException:
        return {"error": "请求 IGN 中国超时，请稍后重试"}
    except Exception as e:
        return {"error": f"获取新闻时出错：{str(e)}"}


def _parse_article(art) -> dict[str, Any] | None:
    """从单个 <article> 元素解析新闻信息。"""
    try:
        # 文章类型
        art_classes = art.get("class", [])
        art_type_raw = next((c for c in art_classes if c in TYPE_LABELS), "")
        art_type = TYPE_LABELS.get(art_type_raw, art_type_raw)

        # 标题与链接
        title_link = art.select_one("h3 a")
        if not title_link:
            return None
        title = title_link.select_one(".caption")
        title = title.get_text(strip=True) if title else title_link.get_text(strip=True)
        url = title_link.get("href", "")

        # 封面图
        img = art.select_one("img.thumb")
        image_url = img.get("data-src") or img.get("src", "") if img else ""

        # 相对时间
        time_el = art.select_one(".info-mobile")
        time_ago = time_el.get_text(strip=True) if time_el else ""

        # 描述
        info_el = art.select_one(".info")
        description = ""
        if info_el:
            import re
            full_text = info_el.get_text(" ", strip=False).replace("\xa0", " ")
            # 文本格式："5 小时，8 分钟  -  描述文字"（换行分隔）
            parts = re.split(r"\s*[-—]\s+", full_text.strip(), maxsplit=1)
            if len(parts) == 2:
                description = parts[1].strip()

        # 分类
        category_el = art.select_one(".info-bottom a")
        category = category_el.get_text(strip=True) if category_el else ""

        return {
            "title": title,
            "url": url,
            "type": art_type,
            "time_ago": time_ago,
            "description": description,
            "image_url": image_url,
            "category": category,
        }
    except Exception:
        return None
