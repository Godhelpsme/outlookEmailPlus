from __future__ import annotations

import html
import json
from typing import Any

from flask import jsonify, request

from outlook_web.audit import log_audit
from outlook_web.repositories import tags as tags_repo
from outlook_web.security.auth import login_required


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    净化用户输入，防止XSS攻击
    - 转义HTML特殊字符
    - 限制长度
    - 移除控制字符
    """
    if not text:
        return ""

    # 限制长度
    text = text[:max_length]

    # 移除控制字符（保留换行和制表符）
    text = "".join(char for char in text if char.isprintable() or char in "\n\t")

    # 转义HTML特殊字符
    text = html.escape(text, quote=True)

    return text


# ==================== 标签 API ====================


@login_required
def api_get_tags() -> Any:
    """获取所有标签"""
    return jsonify({"success": True, "tags": tags_repo.get_tags()})


@login_required
def api_add_tag() -> Any:
    """添加标签"""
    data = request.json
    name = sanitize_input(data.get("name", "").strip(), max_length=50)
    color = data.get("color", "#1a1a1a")

    if not name:
        return jsonify({"success": False, "error": "标签名称不能为空"})

    tag_id = tags_repo.add_tag(name, color)
    if tag_id:
        log_audit(
            "create",
            "tag",
            str(tag_id),
            json.dumps({"name": name, "color": color}, ensure_ascii=False),
        )
        return jsonify({"success": True, "tag": {"id": tag_id, "name": name, "color": color}})
    else:
        return jsonify({"success": False, "error": "标签名称已存在"})


@login_required
def api_delete_tag(tag_id: int) -> Any:
    """删除标签"""
    if tags_repo.delete_tag(tag_id):
        log_audit("delete", "tag", str(tag_id), "删除标签")
        return jsonify({"success": True, "message": "标签已删除"})
    else:
        return jsonify({"success": False, "error": "删除失败"})


# 注意: api_batch_manage_tags 将在 accounts 模块迁移时处理
# 路由 /api/accounts/tags 定义在 routes/accounts.py 中
