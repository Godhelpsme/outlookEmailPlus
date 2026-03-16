"""
邮箱池控制器（PRD-00009 MT-1）

职责：
- 解析 HTTP 请求参数
- 调用 services/pool.py 的业务方法
- 将 service 层业务结果映射为 FD 统一响应格式
- 将 PoolServiceError 映射为统一错误响应

响应格式（FD-00009 §6）：
- 成功：{"success": true, "data": {...}}
- 失败：{"success": false, "error": "error_code", "message": "错误说明"}

HTTP 状态码映射（TD-00009 §6.3）：
- 参数错误 → 400
- 归属/凭据错误 → 403
- 状态冲突 → 409
- 业务失败（如 no_available_account） → 200 + success=false
"""

from __future__ import annotations

from flask import jsonify, request

from outlook_web.services.pool import (
    PoolServiceError,
    claim_random,
    complete_claim,
    get_pool_stats,
    release_claim,
)


def _success_response(data: dict, http_status: int = 200):
    """统一成功响应：{"success": true, "data": {...}}"""
    return jsonify({"success": True, "data": data}), http_status


def _error_response(error_code: str, message: str, http_status: int = 400):
    """统一失败响应：{"success": false, "error": "...", "message": "..."}"""
    return jsonify(
        {"success": False, "error": error_code, "message": message}
    ), http_status


def api_claim_random():
    body = request.get_json(silent=True) or {}
    caller_id = body.get("caller_id", "")
    task_id = body.get("task_id", "")
    provider = body.get("provider")

    try:
        account = claim_random(
            caller_id=caller_id,
            task_id=task_id,
            provider=provider,
        )
        return _success_response(
            {
                "account_id": account["id"],
                "email": account["email"],
                "claim_token": account["claim_token"],
                "lease_expires_at": account["lease_expires_at"],
            }
        )
    except PoolServiceError as exc:
        return _error_response(exc.error_code, str(exc), exc.http_status)


def api_claim_release():
    body = request.get_json(silent=True) or {}
    account_id = body.get("account_id")
    claim_token = body.get("claim_token", "")
    caller_id = body.get("caller_id", "")
    task_id = body.get("task_id", "")
    reason = body.get("reason")

    if account_id is None:
        return _error_response("account_id_missing", "account_id 不能为空", 400)
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return _error_response("account_id_invalid", "account_id 必须为整数", 400)

    try:
        release_claim(
            account_id=account_id,
            claim_token=claim_token,
            caller_id=caller_id,
            task_id=task_id,
            reason=reason,
        )
        return _success_response({"account_id": account_id, "pool_status": "available"})
    except PoolServiceError as exc:
        return _error_response(exc.error_code, str(exc), exc.http_status)


def api_claim_complete():
    body = request.get_json(silent=True) or {}
    account_id = body.get("account_id")
    claim_token = body.get("claim_token", "")
    caller_id = body.get("caller_id", "")
    task_id = body.get("task_id", "")
    result = body.get("result", "")
    detail = body.get("detail")

    if account_id is None:
        return _error_response("account_id_missing", "account_id 不能为空", 400)
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return _error_response("account_id_invalid", "account_id 必须为整数", 400)

    try:
        new_status = complete_claim(
            account_id=account_id,
            claim_token=claim_token,
            caller_id=caller_id,
            task_id=task_id,
            result=result,
            detail=detail,
        )
        return _success_response({"account_id": account_id, "pool_status": new_status})
    except PoolServiceError as exc:
        return _error_response(exc.error_code, str(exc), exc.http_status)


def api_pool_stats():
    try:
        stats = get_pool_stats()
        return _success_response(stats)
    except Exception as exc:
        return _error_response("internal_error", str(exc), 500)
