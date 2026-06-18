"""
邮件发送工具 — 通过 SMTP 将游戏资讯汇总发送到指定邮箱。
配置通过环境变量读取（或 .env 文件）。
"""

import os
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_NAME = os.getenv("SENDER_NAME", "游戏资讯助手")


async def send_email(recipient: str, subject: str, body: str) -> dict[str, Any]:
    """
    发送邮件。

    Args:
        recipient: 收件人邮箱地址
        subject:   邮件主题
        body:      邮件正文（支持 HTML）

    Returns:
        { success, message }
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        return {
            "success": False,
            "message": (
                "邮件发送未配置。请设置环境变量："
                "SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD。"
                "示例（QQ 邮箱）："
                "SMTP_HOST=smtp.qq.com, SMTP_PORT=587, "
                "SMTP_USER=your@qq.com, SMTP_PASSWORD=授权码"
            ),
        }

    # 基本校验
    if not recipient or "@" not in recipient:
        return {"success": False, "message": f"收件人邮箱格式不正确：{recipient}"}

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr((str(Header(SENDER_NAME, "utf-8")), SMTP_USER))
        msg["To"] = recipient
        msg["Subject"] = subject

        # 纯文本备用
        plain_body = _html_to_plain(body)
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(body, "html", "utf-8"))

        # 发送
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipient, msg.as_string())

        return {
            "success": True,
            "message": f"邮件已成功发送至 {recipient}",
            "subject": subject,
        }

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "SMTP 认证失败，请检查邮箱账号和授权码"}
    except smtplib.SMTPConnectError:
        return {"success": False, "message": f"无法连接 SMTP 服务器 {SMTP_HOST}:{SMTP_PORT}"}
    except Exception as e:
        return {"success": False, "message": f"邮件发送失败：{str(e)}"}


def _html_to_plain(html: str) -> str:
    """简单的 HTML 转纯文本。"""
    from html.parser import HTMLParser

    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.lines: list[str] = []
            self.skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4"):
                self.lines.append("\n")
            if tag in ("style", "script", "head"):
                self.skip = True

        def handle_endtag(self, tag):
            if tag in ("p", "div", "li", "h1", "h2", "h3", "h4"):
                self.lines.append("\n")
            if tag in ("style", "script", "head"):
                self.skip = False

        def handle_data(self, data):
            if not self.skip:
                self.lines.append(data.strip())

    parser = Parser()
    parser.feed(html)
    return "".join(parser.lines)
