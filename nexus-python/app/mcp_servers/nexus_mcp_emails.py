import os
import email
import smtplib
import logging
from email.message import EmailMessage
from email.policy import default
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    filename="mcp_email.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

server = FastMCP("email")

# ============ 配置（从环境变量读取，不要硬编码） ============
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")  # 根据邮箱改
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))  # SSL 端口
SMTP_USER = os.getenv("SMTP_USER", "")  # 邮箱账号
SMTP_PASS = os.getenv("SMTP_PASS", "")  # 授权码


@server.tool()
def parse_email(raw_email: str) -> dict:
    """
    解析原始邮件（RFC 5322 格式），提取头信息和正文。
    """
    try:
        msg = email.message_from_string(raw_email, policy=default)

        result = {
            "from": msg.get("From", ""),
            "to": msg.get("To", ""),
            "subject": msg.get("Subject", ""),
            "date": msg.get("Date", ""),
            "text": "",
            "html": "",
            "attachments": []
        }

        # 遍历所有部分，提取正文和附件
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disp = part.get("Content-Disposition", "")

            # 附件判断：有 filename 就是附件
            filename = part.get_filename()
            if filename:
                result["attachments"].append({
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(part.get_payload(decode=True) or b"")
                })
                continue

            # 提取纯文本正文
            if content_type == "text/plain" and not result["text"]:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    result["text"] = payload.decode(charset, errors="replace")

            # 提取 HTML 正文
            elif content_type == "text/html" and not result["html"]:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    result["html"] = payload.decode(charset, errors="replace")

        return {"success": True, "data": result}

    except Exception as e:
        logging.error(f"parse_email failed: {e}")
        return {"success": False, "error": str(e)}


@server.tool()
def send_email(from_addr: str, to: str, subject: str, text: str) -> dict:
    """
    通过 SMTP 发送邮件。
    """
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS]):
        return {"success": False, "error": "SMTP 环境变量未配置"}

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)

        logging.info(f"Email sent to {to}")
        return {"success": True, "message": "邮件已发送"}

    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"SMTP auth failed: {e}")
        return {"success": False, "error": "SMTP 认证失败，请检查账号和授权码"}

    except Exception as e:
        logging.error(f"send_email failed: {e}")
        return {"success": False, "error": str(e)}
