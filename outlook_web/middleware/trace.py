"""
Trace ID 中间件

功能：
- 为每个请求生成/透传 trace_id
- 在响应中添加 X-Trace-Id 头
- 将 legacy 字符串错误格式标准化为结构化错误
"""
from __future__ import annotations

import json
from typing import Any, Dict

from flask import g, request

from outlook_web.errors import build_error_payload, generate_trace_id


def ensure_trace_id():
    """为每个请求生成/透传 trace_id，便于前后端统一追踪"""
    incoming = request.headers.get('X-Trace-Id') or request.headers.get('X-Request-Id')
    if incoming:
        incoming = incoming.strip()
        g.trace_id = incoming[:64]
    else:
        g.trace_id = generate_trace_id()


def attach_trace_id_and_normalize_errors(response):
    """统一写入 X-Trace-Id，并把 legacy 的字符串错误格式标准化为结构化错误"""
    trace_id_value = None
    try:
        trace_id_value = getattr(g, 'trace_id', None)
        if trace_id_value:
            response.headers.setdefault('X-Trace-Id', trace_id_value)
    except Exception:
        trace_id_value = None

    try:
        if response.is_streamed:
            return response

        content_type = response.headers.get('Content-Type', '') or ''
        if not content_type.startswith('application/json'):
            return response

        data = response.get_json(silent=True)
        if not isinstance(data, dict):
            return response

        if data.get('success') is not False:
            return response

        # 统一补齐 trace_id/status 等字段
        if isinstance(data.get('error'), dict):
            error_obj = dict(data['error'])
            mutated = False
            if not error_obj.get('trace_id') and trace_id_value:
                error_obj['trace_id'] = trace_id_value
                mutated = True
            if not error_obj.get('status'):
                error_obj['status'] = response.status_code if response.status_code >= 400 else 400
                mutated = True
            if not error_obj.get('code'):
                error_obj['code'] = 'UNKNOWN_ERROR'
                mutated = True
            if not error_obj.get('message'):
                error_obj['message'] = '请求失败'
                mutated = True
            if mutated:
                new_data = dict(data)
                new_data['error'] = error_obj
                response.set_data(json.dumps(new_data, ensure_ascii=False))
            return response

        # legacy：error 为字符串
        if isinstance(data.get('error'), str):
            legacy_message = data.get('error') or '请求失败'
            status_for_payload = response.status_code if response.status_code >= 400 else 400
            error_payload = build_error_payload(
                code='LEGACY_ERROR',
                message=legacy_message,
                err_type='LegacyError',
                status=status_for_payload,
                details='',
                trace_id=trace_id_value
            )
            new_data = dict(data)
            new_data['error'] = error_payload
            response.set_data(json.dumps(new_data, ensure_ascii=False))
            return response
    except Exception:
        return response

    return response
