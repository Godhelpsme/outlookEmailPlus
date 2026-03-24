from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from outlook_web.db import get_db

_TEMP_EMAIL_RICH_KEYS = (
    "attachments",
    "inline_attachments",
    "inlineAttachments",
    "inline_images",
    "inlineImages",
    "resources",
    "images",
    "cid_map",
    "cidMap",
)


def _serialize_temp_email_payload(message: Dict[str, Any]) -> str:
    try:
        return json.dumps(message or {}, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(message or "")


def _load_temp_email_payload(raw_content: Any) -> Dict[str, Any]:
    if isinstance(raw_content, dict):
        return raw_content
    if not isinstance(raw_content, str) or not raw_content.strip():
        return {}
    try:
        payload = json.loads(raw_content)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _score_temp_email_payload(payload: Any) -> int:
    payload_dict = _load_temp_email_payload(payload)
    if not payload_dict:
        return 0

    score = 0
    if str(payload_dict.get("html_content") or payload_dict.get("body_html") or "").strip():
        score += 20
    for key in _TEMP_EMAIL_RICH_KEYS:
        value = payload_dict.get(key)
        if isinstance(value, dict) and value:
            score += 30
        elif isinstance(value, list) and value:
            score += 30
    score += min(len(payload_dict), 20)
    return score


def _choose_richer_temp_email_payload(existing_payload: Any, incoming_payload: Any) -> str:
    existing_score = _score_temp_email_payload(existing_payload)
    incoming_score = _score_temp_email_payload(incoming_payload)
    if incoming_score >= existing_score:
        normalized = _load_temp_email_payload(incoming_payload) or incoming_payload
        return _serialize_temp_email_payload(normalized)
    normalized = _load_temp_email_payload(existing_payload) or existing_payload
    return _serialize_temp_email_payload(normalized)


def get_temp_email_group_id() -> int:
    """获取临时邮箱分组的 ID"""
    db = get_db()
    cursor = db.execute("SELECT id FROM groups WHERE name = '临时邮箱'")
    row = cursor.fetchone()
    return row["id"] if row else 2


def load_temp_emails() -> List[Dict]:
    """加载所有临时邮箱"""
    db = get_db()
    cursor = db.execute("SELECT * FROM temp_emails ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_temp_email_by_address(email_addr: str) -> Optional[Dict]:
    """根据邮箱地址获取临时邮箱"""
    db = get_db()
    cursor = db.execute("SELECT * FROM temp_emails WHERE email = ?", (email_addr,))
    row = cursor.fetchone()
    return dict(row) if row else None


def add_temp_email(email_addr: str) -> bool:
    """添加临时邮箱"""
    db = get_db()
    try:
        db.execute("INSERT INTO temp_emails (email) VALUES (?)", (email_addr,))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def delete_temp_email(email_addr: str) -> bool:
    """删除临时邮箱及其所有邮件"""
    db = get_db()
    try:
        db.execute("DELETE FROM temp_email_messages WHERE email_address = ?", (email_addr,))
        db.execute("DELETE FROM temp_emails WHERE email = ?", (email_addr,))
        db.commit()
        return True
    except Exception:
        return False


def save_temp_email_messages(email_addr: str, messages: List[Dict]) -> int:
    """保存临时邮件到数据库"""
    db = get_db()
    saved = 0
    for msg in messages:
        try:
            message_id = str(msg.get("id") or "").strip()
            if not message_id:
                continue

            existing = get_temp_email_message_by_id(message_id)
            content = str(msg.get("content") or msg.get("body_text") or "")
            html_content = str(msg.get("html_content") or msg.get("body_html") or "")
            from_address = str(msg.get("from_address") or "")
            subject = str(msg.get("subject") or "")
            timestamp = msg.get("timestamp", 0)
            raw_content = _serialize_temp_email_payload(msg)

            if existing:
                if not content:
                    content = str(existing.get("content") or "")
                if not html_content:
                    html_content = str(existing.get("html_content") or "")
                if not from_address:
                    from_address = str(existing.get("from_address") or "")
                if not subject:
                    subject = str(existing.get("subject") or "")
                if not timestamp:
                    timestamp = existing.get("timestamp", 0)
                raw_content = _choose_richer_temp_email_payload(existing.get("raw_content"), msg)

            has_html = bool(msg.get("has_html") or html_content or (existing and existing.get("has_html")))
            db.execute(
                """
                INSERT OR REPLACE INTO temp_email_messages
                (message_id, email_address, from_address, subject, content, html_content, has_html, timestamp, raw_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    email_addr,
                    from_address,
                    subject,
                    content,
                    html_content,
                    1 if has_html else 0,
                    timestamp,
                    raw_content,
                ),
            )
            saved += 1
        except Exception:
            continue
    db.commit()
    return saved


def get_temp_email_messages(email_addr: str) -> List[Dict]:
    """获取临时邮箱的所有邮件（从数据库）"""
    db = get_db()
    cursor = db.execute(
        """
        SELECT * FROM temp_email_messages
        WHERE email_address = ?
        ORDER BY timestamp DESC
        """,
        (email_addr,),
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_temp_email_message_by_id(message_id: str) -> Optional[Dict]:
    """根据 ID 获取临时邮件"""
    db = get_db()
    cursor = db.execute("SELECT * FROM temp_email_messages WHERE message_id = ?", (message_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def delete_temp_email_message(message_id: str) -> bool:
    """删除临时邮件"""
    db = get_db()
    try:
        db.execute("DELETE FROM temp_email_messages WHERE message_id = ?", (message_id,))
        db.commit()
        return True
    except Exception:
        return False


def get_temp_email_count() -> int:
    """获取临时邮箱数量"""
    db = get_db()
    cursor = db.execute("SELECT COUNT(*) as count FROM temp_emails")
    row = cursor.fetchone()
    return row["count"] if row else 0
