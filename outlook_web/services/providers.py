from __future__ import annotations

from typing import Any, Dict, List

# 对齐：PRD-00005 / FD-00005 / TDD-00005
# 职责：集中维护“邮箱提供商”元数据与 IMAP 文件夹映射，避免前后端重复维护默认 host/port 与 folder 兼容策略。

# 邮箱提供商配置（用于前端选择与默认 IMAP host/port）
MAIL_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "outlook": {
        "label": "Outlook",
        "imap_host": "outlook.live.com",
        "imap_port": 993,
        "account_type": "outlook",
        "note": "使用 OAuth2 认证（client_id + refresh_token）",
    },
    "gmail": {
        "label": "Gmail",
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "account_type": "imap",
        "note": "需开启 IMAP，并使用应用专用密码（非登录密码）",
    },
    "qq": {
        "label": "QQ 邮箱",
        "imap_host": "imap.qq.com",
        "imap_port": 993,
        "account_type": "imap",
        "note": "需开启 IMAP 服务，使用授权码（非 QQ 密码）",
    },
    "163": {
        "label": "163 邮箱",
        "imap_host": "imap.163.com",
        "imap_port": 993,
        "account_type": "imap",
        "note": "需开启 IMAP 服务，使用授权码",
    },
    "126": {
        "label": "126 邮箱",
        "imap_host": "imap.126.com",
        "imap_port": 993,
        "account_type": "imap",
        "note": "需开启 IMAP 服务，使用授权码",
    },
    "yahoo": {
        "label": "Yahoo 邮箱",
        "imap_host": "imap.mail.yahoo.com",
        "imap_port": 993,
        "account_type": "imap",
        "note": "需在账号安全设置中生成应用密码",
    },
    "aliyun": {
        "label": "阿里邮箱",
        "imap_host": "imap.aliyun.com",
        "imap_port": 993,
        "account_type": "imap",
        "note": "使用阿里邮箱登录密码",
    },
    "custom": {
        "label": "自定义 IMAP",
        "imap_host": "",
        "imap_port": 993,
        "account_type": "imap",
        "note": "请手动填写 IMAP 服务器地址和端口",
    },
}

# provider -> 逻辑文件夹名（inbox/junkemail/deleteditems）-> 候选 IMAP 文件夹名列表
PROVIDER_FOLDER_MAP: Dict[str, Dict[str, List[str]]] = {
    "gmail": {
        "inbox": ["INBOX"],
        "junkemail": ["[Gmail]/Spam", "[Gmail]/垃圾邮件"],
        "deleteditems": ["[Gmail]/Trash", "[Gmail]/已删除邮件"],
    },
    "qq": {
        "inbox": ["INBOX"],
        "junkemail": ["Junk", "&V4NXPpCuTvY-"],
        "deleteditems": ["Deleted Messages", "&XfJT0ZABkK5O9g-"],
    },
    "163": {
        "inbox": ["INBOX"],
        "junkemail": ["&V4NXPpCuTvY-"],
        "deleteditems": ["&XfJT0ZABkK5O9g-"],
    },
    "yahoo": {
        "inbox": ["INBOX"],
        "junkemail": ["Bulk Mail"],
        "deleteditems": ["Trash"],
    },
    "_default": {
        "inbox": ["INBOX"],
        "junkemail": ["Junk", "Spam", "SPAM", "Bulk Mail"],
        "deleteditems": ["Trash", "Deleted", "Deleted Messages"],
    },
}


def get_imap_folder_candidates(provider: str, folder: str) -> List[str]:
    """
    根据 provider 和逻辑文件夹名（inbox/junkemail/deleteditems），
    返回候选 IMAP 文件夹名列表（按优先级排序）。
    不存在的 provider 退回 _default。
    """
    provider_key = (provider or "").strip() or "_default"
    folder_key = (folder or "").strip().lower() or "inbox"

    folder_map = PROVIDER_FOLDER_MAP.get(provider_key, PROVIDER_FOLDER_MAP["_default"])
    return folder_map.get(folder_key, PROVIDER_FOLDER_MAP["_default"].get(folder_key, ["INBOX"]))


def get_provider_list() -> List[Dict[str, Any]]:
    """返回供前端展示的 provider 列表（顺序固定：outlook 在前，custom 在后）"""
    order = ["outlook", "gmail", "qq", "163", "126", "yahoo", "aliyun", "custom"]
    result: List[Dict[str, Any]] = []
    for key in order:
        if key not in MAIL_PROVIDERS:
            continue
        p = MAIL_PROVIDERS[key]
        result.append(
            {
                "key": key,
                "label": p.get("label", key),
                "account_type": p.get("account_type", "imap" if key != "outlook" else "outlook"),
                "note": p.get("note", ""),
            }
        )
    return result
