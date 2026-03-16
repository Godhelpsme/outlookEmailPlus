from __future__ import annotations

from flask import Blueprint

from outlook_web.controllers import pool as pool_controller


def create_blueprint() -> Blueprint:
    bp = Blueprint("pool", __name__)
    bp.add_url_rule(
        "/api/pool/claim-random",
        view_func=pool_controller.api_claim_random,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/api/pool/claim-release",
        view_func=pool_controller.api_claim_release,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/api/pool/claim-complete",
        view_func=pool_controller.api_claim_complete,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/api/pool/stats",
        view_func=pool_controller.api_pool_stats,
        methods=["GET"],
    )
    return bp
