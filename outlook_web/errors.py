from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, Optional

from flask import current_app, g

_FALLBACK_LOGGER = logging.getLogger("outlook_web.errors")
if not _FALLBACK_LOGGER.handlers:
    _FALLBACK_LOGGER.addHandler(logging.NullHandler())
_FALLBACK_LOGGER.propagate = False


def generate_trace_id() -> str:
    return uuid.uuid4().hex


def sanitize_error_details(details: Optional[str]) -> str:
    if not details:
        return ""
    sanitized = details
    patterns = [
        (r"(?i)(bearer\s+)[A-Za-z0-9\-._~\+/]+=*", r"\1***"),
        (
            r"(?i)(refresh_token|access_token|token|password|passwd|secret)\s*[:=]\s*\"?[A-Za-z0-9\-._~\+/]+=*\"?",
            r"\1=***",
        ),
        (r"(?i)(\"refresh_token\"\s*:\s*\")[^\"]+(\"?)", r"\1***\2"),
        (r"(?i)(\"access_token\"\s*:\s*\")[^\"]+(\"?)", r"\1***\2"),
        (r"(?i)(\"password\"\s*:\s*\")[^\"]+(\"?)", r"\1***\2"),
        (r"(?i)(client_secret|refresh_token|access_token)=[^&\s]+", r"\1=***"),
    ]
    for pattern, repl in patterns:
        sanitized = re.sub(pattern, repl, sanitized)
    return sanitized


def build_error_payload(
    code: str,
    message: str,
    err_type: str = "Error",
    status: int = 500,
    details: Any = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(message, str):
        message = str(message)
    sanitized_message = sanitize_error_details(message) if message else ""

    if details is not None and not isinstance(details, str):
        try:
            details = json.dumps(details, ensure_ascii=False)
        except Exception:
            details = str(details)
    sanitized_details = sanitize_error_details(details) if details else ""

    request_trace_id = None
    try:
        request_trace_id = getattr(g, "trace_id", None)
    except Exception:
        request_trace_id = None

    trace_id_value = trace_id or request_trace_id or generate_trace_id()
    payload = {
        "code": code,
        "message": sanitized_message or "请求失败",
        "type": err_type,
        "status": status,
        "details": sanitized_details,
        "trace_id": trace_id_value,
    }

    # 根据状态码选择日志级别：
    # - 5xx: ERROR（服务端错误）
    # - 4xx: WARNING（客户端错误，如验证失败、权限不足等，属于正常业务流程）
    # - 其他: INFO
    log_level = logging.ERROR if status >= 500 else (logging.WARNING if status >= 400 else logging.INFO)

    try:
        current_app.logger.log(
            log_level,
            "trace_id=%s code=%s status=%s type=%s details=%s",
            trace_id_value,
            code,
            status,
            err_type,
            sanitized_details,
        )
    except Exception:
        try:
            _FALLBACK_LOGGER.log(
                log_level,
                "trace_id=%s code=%s status=%s type=%s details=%s",
                trace_id_value,
                code,
                status,
                err_type,
                sanitized_details,
            )
        except Exception:
            pass

    return payload
