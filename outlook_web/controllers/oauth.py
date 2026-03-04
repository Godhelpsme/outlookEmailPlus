from __future__ import annotations

import urllib.parse
from typing import Any

import requests
from flask import jsonify, request

from outlook_web import config
from outlook_web.audit import log_audit
from outlook_web.security.auth import (
    check_export_verify_token,
    consume_export_verify_token,
    login_required,
)

# OAuth 配置
OAUTH_SCOPES = [
    "offline_access",
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]


# ==================== OAuth API ====================


@login_required
def api_get_oauth_auth_url() -> Any:
    """生成 OAuth 授权 URL"""
    oauth_client_id = config.get_oauth_client_id()
    oauth_redirect_uri = config.get_oauth_redirect_uri()

    base_auth_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    params = {
        "client_id": oauth_client_id,
        "response_type": "code",
        "redirect_uri": oauth_redirect_uri,
        "response_mode": "query",
        "scope": " ".join(OAUTH_SCOPES),
        "state": "12345",
    }
    auth_url = f"{base_auth_url}?{urllib.parse.urlencode(params)}"

    return jsonify(
        {
            "success": True,
            "auth_url": auth_url,
            "client_id": oauth_client_id,
            "redirect_uri": oauth_redirect_uri,
        }
    )


@login_required
def api_exchange_oauth_token() -> Any:
    """使用授权码换取 Refresh Token"""
    oauth_client_id = config.get_oauth_client_id()
    oauth_redirect_uri = config.get_oauth_redirect_uri()

    data = request.json
    redirected_url = data.get("redirected_url", "").strip()
    verify_token = data.get("verify_token")

    if not redirected_url:
        return jsonify({"success": False, "error": "请提供授权后的完整 URL"})

    # 从 URL 中提取 code
    try:
        parsed_url = urllib.parse.urlparse(redirected_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        auth_code = query_params["code"][0]
    except (KeyError, IndexError):
        return jsonify({"success": False, "error": "无法从 URL 中提取授权码，请检查 URL 是否正确"})

    # 二次验证（敏感信息：refresh_token 不默认明文返回）
    ok, error_message = check_export_verify_token(verify_token)
    if not ok:
        return (
            jsonify({"success": False, "error": error_message, "need_verify": True}),
            401,
        )

    # 使用 Code 换取 Token (Public Client 不需要 client_secret)
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    token_data = {
        "client_id": oauth_client_id,
        "code": auth_code,
        "redirect_uri": oauth_redirect_uri,
        "grant_type": "authorization_code",
        "scope": " ".join(OAUTH_SCOPES),
    }

    try:
        response = requests.post(token_url, data=token_data, timeout=30)
    except Exception as e:
        return jsonify({"success": False, "error": f"请求失败: {str(e)}"})

    if response.status_code == 200:
        tokens = response.json()
        refresh_token = tokens.get("refresh_token")

        if not refresh_token:
            return jsonify({"success": False, "error": "未能获取 Refresh Token"})

        # 成功后再消费一次性验证 token（避免失败时消耗 token）
        ok, error_message = consume_export_verify_token(verify_token)
        if not ok:
            return (
                jsonify({"success": False, "error": error_message, "need_verify": True}),
                401,
            )

        log_audit("oauth_exchange", "oauth", None, "换取 Refresh Token 成功（已二次验证）")

        return jsonify(
            {
                "success": True,
                "refresh_token": refresh_token,
                "client_id": oauth_client_id,
                "token_type": tokens.get("token_type"),
                "expires_in": tokens.get("expires_in"),
                "scope": tokens.get("scope"),
            }
        )
    else:
        error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        error_msg = error_data.get("error_description", response.text)
        return jsonify({"success": False, "error": f"获取令牌失败: {error_msg}"})
