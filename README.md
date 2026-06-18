# 🎮 Steam 游戏资讯 Agent

基于 MCP (Model Context Protocol) + LLM 驱动的游戏资讯智能体，支持 Steam 排行榜查询、游戏新闻筛选总结、资讯邮件简报。

## 架构

```
用户自然语言 → client.py (LLM Agent 循环)
                  ├─ Anthropic 兼容 API (DeepSeek) → 推理 + 决策
                  └─ MCP stdio → agent_server.py
                                  ├─ steam_charts   → Steam 排行榜 (Web 抓取)
                                  ├─ gaming_news    → IGN 中国新闻 (Web 抓取)
                                  └─ email_send     → 邮件发送 (SMTP)
```

## 环境要求

- Python 3.12+
- DeepSeek API Key (Anthropic 兼容端点)
- SMTP 邮箱 (可选，仅邮件功能需要)

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key 和 SMTP 信息

# 3. 运行
python client.py
```

## 配置说明

| 环境变量 | 说明 | 必填 |
|----------|------|:--:|
| `ANTHROPIC_BASE_URL` | LLM API 端点 | ✅ |
| `ANTHROPIC_AUTH_TOKEN` | API Key | ✅ |
| `ANTHROPIC_MODEL` | 模型名称 | ✅ |
| `SMTP_HOST` | SMTP 服务器 | 可选 |
| `SMTP_USER` / `SMTP_PASSWORD` | 邮箱账号/授权码 | 可选 |
| `SENDER_NAME` | 发件人名称 | 可选 |

## 项目结构

```
.
├── agent_server.py      # MCP Server，注册 3 个工具
├── client.py            # LLM Agent 客户端，对话循环
├── prompts/
│   └── system.md        # 系统提示词
├── tools/
│   ├── steam_charts.py  # Steam 排行榜抓取
│   ├── ign_news.py      # IGN 中国新闻抓取
│   └── send_email.py    # SMTP 邮件发送
├── requirements.txt
└── .env.example
```
