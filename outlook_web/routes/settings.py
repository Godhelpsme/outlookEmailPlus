from __future__ import annotations

from flask import Blueprint

from outlook_web.controllers import settings as settings_controller


def create_blueprint() -> Blueprint:
    """创建 settings Blueprint"""
    bp = Blueprint("settings", __name__)
    bp.add_url_rule(
        "/api/settings/validate-cron",
        view_func=settings_controller.api_validate_cron,
        methods=["POST"],
    )
    bp.add_url_rule("/api/settings", view_func=settings_controller.api_get_settings, methods=["GET"])
    bp.add_url_rule(
        "/api/settings",
        view_func=settings_controller.api_update_settings,
        methods=["PUT"],
    )
    return bp
