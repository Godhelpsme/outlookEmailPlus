from __future__ import annotations

from flask import Blueprint

from outlook_web.controllers import oauth as oauth_controller


def create_blueprint() -> Blueprint:
    """创建 oauth Blueprint"""
    bp = Blueprint("oauth", __name__)
    bp.add_url_rule(
        "/api/oauth/auth-url",
        view_func=oauth_controller.api_get_oauth_auth_url,
        methods=["GET"],
    )
    bp.add_url_rule(
        "/api/oauth/exchange-token",
        view_func=oauth_controller.api_exchange_oauth_token,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/oauth/callback",
        view_func=oauth_controller.oauth_callback_page,
        methods=["GET"],
    )
    return bp
