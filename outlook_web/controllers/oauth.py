from __future__ import annotations

import urllib.parse
import secrets
from typing import Any

import requests
from flask import jsonify, render_template, request, session, url_for

from outlook_web import config
from outlook_web.audit import log_audit
from outlook_web.errors import build_error_response, build_export_verify_failure_response
from outlook_web.security.auth import (
    check_export_verify_token_bound,
    consume_export_verify_token,
    get_client_ip,
    get_user_agent,
    login_required,
)

# OAuth 配置
OAUTH_SCOPES = [
    "offline_access",
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]
OAUTH_STATE_SESSION_KEY = "outlook_oauth_state"
MAX_PENDING_OAUTH_STATES = 5


# ==================== OAuth API ====================


def _resolve_oauth_redirect_uri() -> str:
    callback_url = url_for("oauth.oauth_callback_page", _external=True)
    return config.get_oauth_redirect_uri(callback_url)


def _validate_oauth_config(oauth_client_id: str, oauth_redirect_uri: str):
    if not oauth_client_id:
        return build_error_response(
            "OAUTH_CONFIG_INVALID",
            "OAuth client_id 未配置，请先设置 OAUTH_CLIENT_ID",
            message_en="OAuth client_id is not configured. Set OAUTH_CLIENT_ID first",
            status=500,
        )

    parsed_uri = urllib.parse.urlparse(oauth_redirect_uri)
    if parsed_uri.scheme not in {"http", "https"} or not parsed_uri.netloc:
        return build_error_response(
            "OAUTH_CONFIG_INVALID",
            "OAuth redirect_uri 配置无效，请设置完整的 http(s) 地址",
            message_en="OAuth redirect_uri is invalid. Use a full http(s) URL",
            status=500,
        )

    return None


def _build_redirect_uri_warning(oauth_redirect_uri: str) -> str:
    current_origin = request.host_url.rstrip("/")
    parsed_redirect = urllib.parse.urlparse(oauth_redirect_uri)
    redirect_origin = f"{parsed_redirect.scheme}://{parsed_redirect.netloc}".rstrip("/")
    if redirect_origin == current_origin:
        return ""
    return (
        f"当前系统使用的 redirect_uri 是 {oauth_redirect_uri}。如果你现在通过 {current_origin} 访问本系统，"
        "请在 Azure 应用中注册该 redirect_uri，或把 OAUTH_REDIRECT_URI 改成当前部署地址下的 /oauth/callback。"
    )


def _normalize_callback_base(callback_value: str) -> str:
    parsed = urllib.parse.urlparse(callback_value or "")
    if parsed.scheme and parsed.netloc:
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    return ""


def _looks_like_invalid_code(error_name: str, error_description: str) -> bool:
    normalized = f"{error_name} {error_description}".lower()
    keywords = [
        "invalid_grant",
        "authorization code",
        "input parameter 'code'",
        "provided value for the input parameter 'code' is not valid",
        "code has expired",
        "code was already redeemed",
    ]
    return any(keyword in normalized for keyword in keywords)


def _looks_like_invalid_client_config(error_name: str, error_description: str) -> bool:
    normalized = f"{error_name} {error_description}".lower()
    keywords = [
        "invalid_client",
        "unauthorized_client",
        "application with identifier",
        "aadsts700016",
        "aadsts7000218",
        "public client",
    ]
    return any(keyword in normalized for keyword in keywords)


def _parse_oauth_callback_input(redirected_url: str) -> tuple[str, dict[str, list[str]], str]:
    candidate = (redirected_url or "").strip()
    if not candidate:
        return "", {}, ""

    if candidate.startswith("?"):
        candidate = candidate[1:]

    if "://" not in candidate and ("code=" in candidate or "error=" in candidate):
        return "", urllib.parse.parse_qs(candidate), candidate

    parsed_url = urllib.parse.urlparse(candidate)
    return parsed_url.geturl(), urllib.parse.parse_qs(parsed_url.query), parsed_url.geturl()


def _get_pending_oauth_states() -> list[str]:
    raw_states = session.get(OAUTH_STATE_SESSION_KEY)
    if isinstance(raw_states, list):
        return [str(item).strip() for item in raw_states if str(item or "").strip()]
    if isinstance(raw_states, str) and raw_states.strip():
        return [raw_states.strip()]
    return []


def _store_pending_oauth_states(states: list[str]) -> None:
    session[OAUTH_STATE_SESSION_KEY] = states
    session.modified = True


def _issue_oauth_state() -> str:
    state = secrets.token_urlsafe(24)
    pending_states = [item for item in _get_pending_oauth_states() if item != state]
    pending_states.append(state)
    if len(pending_states) > MAX_PENDING_OAUTH_STATES:
        pending_states = pending_states[-MAX_PENDING_OAUTH_STATES:]
    _store_pending_oauth_states(pending_states)
    return state


def _has_expected_oauth_state(state: str) -> bool:
    candidate = str(state or "").strip()
    if not candidate:
        return False
    return any(secrets.compare_digest(candidate, item) for item in _get_pending_oauth_states())


def _consume_expected_oauth_state(state: str) -> bool:
    candidate = str(state or "").strip()
    if not candidate:
        return False

    pending_states = _get_pending_oauth_states()
    remaining_states: list[str] = []
    consumed = False
    for item in pending_states:
        if not consumed and secrets.compare_digest(candidate, item):
            consumed = True
            continue
        remaining_states.append(item)
    if consumed:
        _store_pending_oauth_states(remaining_states)
    return consumed


def oauth_callback_page() -> Any:
    """OAuth 回调页：将授权结果回传给主窗口，失败时提供手工复制兜底。"""
    return render_template("oauth_callback.html")


@login_required
def api_get_oauth_auth_url() -> Any:
    """生成 OAuth 授权 URL"""
    oauth_client_id = config.get_oauth_client_id()
    oauth_redirect_uri = _resolve_oauth_redirect_uri()

    config_error = _validate_oauth_config(oauth_client_id, oauth_redirect_uri)
    if config_error is not None:
        return config_error

    oauth_state = _issue_oauth_state()
    base_auth_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    params = {
        "client_id": oauth_client_id,
        "response_type": "code",
        "redirect_uri": oauth_redirect_uri,
        "response_mode": "query",
        "scope": " ".join(OAUTH_SCOPES),
        "state": oauth_state,
    }
    auth_url = f"{base_auth_url}?{urllib.parse.urlencode(params)}"

    return jsonify(
        {
            "success": True,
            "auth_url": auth_url,
            "client_id": oauth_client_id,
            "redirect_uri": oauth_redirect_uri,
            "redirect_uri_warning": _build_redirect_uri_warning(oauth_redirect_uri),
        }
    )


@login_required
def api_exchange_oauth_token() -> Any:
    """使用授权码换取 Refresh Token"""
    oauth_client_id = config.get_oauth_client_id()
    oauth_redirect_uri = _resolve_oauth_redirect_uri()

    config_error = _validate_oauth_config(oauth_client_id, oauth_redirect_uri)
    if config_error is not None:
        return config_error

    data = request.json or {}
    redirected_url = data.get("redirected_url", "").strip()
    verify_token = data.get("verify_token")

    if not redirected_url:
        return build_error_response(
            "INVALID_PARAM",
            "请提供微软授权回跳后的完整 URL 或 query 参数",
            message_en="Provide the full OAuth callback URL or query string",
            status=400,
        )

    if not verify_token:
        return build_error_response(
            "OAUTH_VERIFY_TOKEN_REQUIRED",
            "缺少 verify_token，请先输入当前系统登录密码完成二次验证",
            message_en="verify_token is missing. Complete the local verification step first",
            status=401,
            extra={"need_verify": True},
        )

    callback_url, query_params, callback_input = _parse_oauth_callback_input(redirected_url)

    returned_state = str((query_params.get("state") or [""])[0] or "").strip()
    if not returned_state:
        return build_error_response(
            "OAUTH_STATE_INVALID",
            "授权回跳缺少 state，请重新发起微软授权",
            message_en="The OAuth callback is missing state. Start a new authorization flow",
            status=400,
            details=callback_input,
        )
    if not _get_pending_oauth_states():
        return build_error_response(
            "OAUTH_STATE_INVALID",
            "当前授权会话已失效，请重新点击“打开授权页面”发起新的微软授权",
            message_en="The OAuth authorization session expired. Start a new authorization flow",
            status=400,
            details=callback_input,
        )
    if not _has_expected_oauth_state(returned_state):
        return build_error_response(
            "OAUTH_STATE_INVALID",
            "授权结果与当前会话不匹配，请重新发起微软授权",
            message_en="The OAuth callback does not match the current session. Start a new authorization flow",
            status=400,
            details=callback_input,
        )

    error_name = (query_params.get("error") or [""])[0]
    error_description = (query_params.get("error_description") or [""])[0]
    if error_name:
        return build_error_response(
            "OAUTH_MICROSOFT_AUTH_FAILED",
            f"微软授权失败：{error_description or error_name}",
            message_en=f"Microsoft authorization failed: {error_description or error_name}",
            status=400,
            details=callback_input,
        )

    configured_base = _normalize_callback_base(oauth_redirect_uri)
    callback_base = _normalize_callback_base(callback_url)
    if callback_base and configured_base and callback_base != configured_base:
        return build_error_response(
            "OAUTH_REDIRECT_URI_MISMATCH",
            f"回跳地址与当前配置不一致。当前配置要求 {oauth_redirect_uri}，请在 Azure 应用中注册并使用这个 redirect_uri 重新授权。",
            message_en=(
                "The callback URL does not match the configured redirect_uri. "
                f"Use {oauth_redirect_uri} in Azure and retry authorization"
            ),
            status=400,
            details=f"callback_url={callback_url}",
        )

    # 从 URL 中提取 code
    try:
        auth_code = query_params["code"][0]
    except (KeyError, IndexError):
        return build_error_response(
            "OAUTH_CODE_PARSE_FAILED",
            "无法从回跳结果中提取授权码，请确认授权成功后再重试",
            message_en="Failed to extract the authorization code from the callback",
            status=400,
            details=callback_input,
        )

    client_ip = get_client_ip()
    user_agent = get_user_agent()

    # 二次验证（敏感信息：refresh_token 不默认明文返回）
    # 先校验 token 与当前客户端的绑定关系，避免绑定不匹配时先消耗微软授权码。
    ok, error_message = check_export_verify_token_bound(verify_token, client_ip, user_agent)
    if not ok:
        return build_export_verify_failure_response(error_message)

    if not _consume_expected_oauth_state(returned_state):
        return build_error_response(
            "OAUTH_STATE_INVALID",
            "当前授权会话已失效，请重新发起微软授权",
            message_en="The OAuth authorization session expired. Start a new authorization flow",
            status=400,
            details=callback_input,
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
        return build_error_response(
            "OAUTH_MICROSOFT_REQUEST_FAILED",
            f"请求微软 OAuth 服务失败：{str(e)}",
            message_en=f"Request to Microsoft OAuth failed: {str(e)}",
            status=502,
        )

    if response.status_code == 200:
        tokens = response.json()
        refresh_token = tokens.get("refresh_token")

        if not refresh_token:
            return build_error_response(
                "OAUTH_REFRESH_TOKEN_MISSING",
                "微软未返回 refresh_token，请确认 Azure 应用启用了 offline_access 并重新授权",
                message_en="Microsoft did not return a refresh token. Ensure offline_access is granted and retry",
                status=502,
            )

        # 成功后再消费一次性验证 token（避免失败时消耗 token）
        ok, error_message = consume_export_verify_token(verify_token, client_ip, user_agent)
        if not ok:
            return build_export_verify_failure_response(error_message)

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

    try:
        error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    except ValueError:
        error_data = {}
    error_name = str(error_data.get("error") or "").strip()
    error_msg = str(error_data.get("error_description") or response.text or "").strip()

    if "redirect_uri" in error_msg.lower() or "aadsts50011" in error_msg.lower():
        return build_error_response(
            "OAUTH_REDIRECT_URI_MISMATCH",
            f"微软拒绝了当前 redirect_uri。请在 Azure 应用中注册 {oauth_redirect_uri}，并确保页面使用这个地址完成授权。",
            message_en=(
                "Microsoft rejected the redirect_uri. "
                f"Register {oauth_redirect_uri} in Azure and use it for authorization"
            ),
            status=400,
            details=error_msg,
        )

    if _looks_like_invalid_code(error_name, error_msg):
        return build_error_response(
            "OAUTH_CODE_INVALID",
            "授权码无效、已过期或已被使用，请重新打开授权链接完成一次新的微软授权",
            message_en="The authorization code is invalid, expired, or already used. Start a new authorization flow",
            status=400,
            details=error_msg,
        )

    if _looks_like_invalid_client_config(error_name, error_msg):
        return build_error_response(
            "OAUTH_CONFIG_INVALID",
            "OAuth 应用配置无效，请检查 OAUTH_CLIENT_ID、应用类型和 Azure 应用授权设置",
            message_en="OAuth application configuration is invalid. Check OAUTH_CLIENT_ID, app type, and Azure consent settings",
            status=400,
            details=error_msg,
        )

    return build_error_response(
        "OAUTH_MICROSOFT_AUTH_FAILED",
        f"微软换取 Token 失败：{error_msg or response.status_code}",
        message_en=f"Microsoft token exchange failed: {error_msg or response.status_code}",
        status=502,
        details=error_msg or f"http_status={response.status_code}",
    )
