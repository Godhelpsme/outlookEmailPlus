from __future__ import annotations

import logging
from typing import Any

from flask import jsonify, request

from outlook_web.audit import log_audit
from outlook_web.db import get_db
from outlook_web.repositories import temp_emails as temp_emails_repo
from outlook_web.security.auth import login_required
from outlook_web.services import gptmail

logger = logging.getLogger(__name__)


# ==================== 临时邮箱 API ====================


@login_required
def api_get_temp_emails() -> Any:
    """获取所有临时邮箱"""
    emails = temp_emails_repo.load_temp_emails()
    return jsonify({"success": True, "emails": emails})


@login_required
def api_generate_temp_email() -> Any:
    """生成新的临时邮箱"""
    data = request.json or {}
    prefix = data.get("prefix")
    domain = data.get("domain")

    # 调用改进后的 generate_temp_email，返回 (email_addr, error_msg)
    email_addr, error_msg = gptmail.generate_temp_email(prefix, domain)

    if email_addr:
        # 成功生成邮箱地址
        if temp_emails_repo.add_temp_email(email_addr):
            log_audit("create", "temp_email", email_addr, "生成临时邮箱")
            logger.info(f"临时邮箱生成成功: {email_addr}")
            return jsonify({"success": True, "email": email_addr, "message": "临时邮箱创建成功"})
        else:
            logger.warning(f"临时邮箱已存在: {email_addr}")
            return jsonify({"success": False, "error": "邮箱已存在"})
    else:
        # 生成失败，返回详细错误信息
        logger.error(f"临时邮箱生成失败: {error_msg}, prefix={prefix}, domain={domain}")
        return jsonify({"success": False, "error": error_msg or "生成临时邮箱失败，请稍后重试"})


@login_required
def api_delete_temp_email(email_addr: str) -> Any:
    """删除临时邮箱"""
    if temp_emails_repo.delete_temp_email(email_addr):
        log_audit("delete", "temp_email", email_addr, "删除临时邮箱")
        return jsonify({"success": True, "message": "临时邮箱已删除"})
    else:
        return jsonify({"success": False, "error": "删除失败"})


@login_required
def api_get_temp_email_messages(email_addr: str) -> Any:
    """获取临时邮箱的邮件列表"""
    api_messages = gptmail.get_temp_emails_from_api(email_addr)

    if api_messages:
        temp_emails_repo.save_temp_email_messages(email_addr, api_messages)

    messages = temp_emails_repo.get_temp_email_messages(email_addr)

    formatted = []
    for msg in messages:
        formatted.append(
            {
                "id": msg.get("message_id"),
                "from": msg.get("from_address", "未知"),
                "subject": msg.get("subject", "无主题"),
                "body_preview": (msg.get("content", "") or "")[:200],
                "date": msg.get("created_at", ""),
                "timestamp": msg.get("timestamp", 0),
                "has_html": msg.get("has_html", 0),
            }
        )

    return jsonify(
        {
            "success": True,
            "emails": formatted,
            "count": len(formatted),
            "method": "GPTMail",
        }
    )


@login_required
def api_get_temp_email_message_detail(email_addr: str, message_id: str) -> Any:
    """获取临时邮件详情"""
    msg = temp_emails_repo.get_temp_email_message_by_id(message_id)

    if not msg:
        api_msg = gptmail.get_temp_email_detail_from_api(message_id)
        if api_msg:
            temp_emails_repo.save_temp_email_messages(email_addr, [api_msg])
            msg = temp_emails_repo.get_temp_email_message_by_id(message_id)

    if msg:
        return jsonify(
            {
                "success": True,
                "email": {
                    "id": msg.get("message_id"),
                    "from": msg.get("from_address", "未知"),
                    "to": email_addr,
                    "subject": msg.get("subject", "无主题"),
                    "body": (msg.get("html_content") if msg.get("has_html") else msg.get("content", "")),
                    "body_type": "html" if msg.get("has_html") else "text",
                    "date": msg.get("created_at", ""),
                    "timestamp": msg.get("timestamp", 0),
                },
            }
        )
    else:
        return jsonify({"success": False, "error": "邮件不存在"})


@login_required
def api_delete_temp_email_message(email_addr: str, message_id: str) -> Any:
    """删除临时邮件"""
    gptmail.delete_temp_email_from_api(message_id)
    if temp_emails_repo.delete_temp_email_message(message_id):
        log_audit(
            "delete",
            "temp_email_message",
            message_id,
            f"删除临时邮件（email={email_addr}）",
        )
        return jsonify({"success": True, "message": "邮件已删除"})
    else:
        return jsonify({"success": False, "error": "删除失败"})


@login_required
def api_clear_temp_email_messages(email_addr: str) -> Any:
    """清空临时邮箱的所有邮件"""
    gptmail.clear_temp_emails_from_api(email_addr)
    db = get_db()
    try:
        row = db.execute(
            "SELECT COUNT(*) as c FROM temp_email_messages WHERE email_address = ?",
            (email_addr,),
        ).fetchone()
        deleted_count = row["c"] if row else 0
        db.execute("DELETE FROM temp_email_messages WHERE email_address = ?", (email_addr,))
        db.commit()
        log_audit(
            "delete",
            "temp_email_messages",
            email_addr,
            f"清空临时邮箱邮件（count={deleted_count}）",
        )
        return jsonify({"success": True, "message": "邮件已清空"})
    except Exception:
        return jsonify({"success": False, "error": "清空失败"})


@login_required
def api_refresh_temp_email_messages(email_addr: str) -> Any:
    """刷新临时邮箱的邮件"""
    api_messages = gptmail.get_temp_emails_from_api(email_addr)

    if api_messages is not None:
        saved = temp_emails_repo.save_temp_email_messages(email_addr, api_messages)
        messages = temp_emails_repo.get_temp_email_messages(email_addr)

        formatted = []
        for msg in messages:
            formatted.append(
                {
                    "id": msg.get("message_id"),
                    "from": msg.get("from_address", "未知"),
                    "subject": msg.get("subject", "无主题"),
                    "body_preview": (msg.get("content", "") or "")[:200],
                    "date": msg.get("created_at", ""),
                    "timestamp": msg.get("timestamp", 0),
                    "has_html": msg.get("has_html", 0),
                }
            )

        return jsonify(
            {
                "success": True,
                "emails": formatted,
                "count": len(formatted),
                "new_count": saved,
                "method": "GPTMail",
            }
        )
    else:
        return jsonify({"success": False, "error": "获取邮件失败"})
