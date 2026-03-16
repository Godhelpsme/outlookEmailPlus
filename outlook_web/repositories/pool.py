from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import sqlite3


RESULT_TO_POOL_STATUS: Dict[str, str] = {
    "success": "used",
    "verification_timeout": "cooldown",
    "provider_blocked": "frozen",
    "credential_invalid": "retired",
    "network_error": "available",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def claim_atomic(
    conn: sqlite3.Connection,
    caller_id: str,
    task_id: str,
    lease_seconds: int,
    provider: Optional[str] = None,
    group_id: Optional[int] = None,
    tags: Optional[List[str]] = None,
    exclude_recent_minutes: Optional[int] = None,
) -> Optional[dict]:
    sql = """
        SELECT a.* FROM accounts a
        WHERE a.pool_status = 'available'
        AND a.status = 'active'
    """
    params: list = []

    if provider:
        sql += " AND a.provider = ?"
        params.append(provider)

    if group_id is not None:
        sql += " AND a.group_id = ?"
        params.append(group_id)

    if tags:
        for tag_name in tags:
            sql += """
                AND EXISTS (
                    SELECT 1 FROM account_tags at2
                    JOIN tags t2 ON at2.tag_id = t2.id
                    WHERE at2.account_id = a.id AND t2.name = ?
                )
            """
            params.append(tag_name)

    if exclude_recent_minutes and exclude_recent_minutes > 0:
        cutoff = (
            _utcnow() - timedelta(minutes=exclude_recent_minutes)
        ).isoformat() + "Z"
        sql += " AND (a.last_claimed_at IS NULL OR a.last_claimed_at < ?)"
        params.append(cutoff)

    sql += " ORDER BY RANDOM() LIMIT 1"

    conn.execute("BEGIN IMMEDIATE")
    account = conn.execute(sql, params).fetchone()

    if account is None:
        conn.execute("ROLLBACK")
        return None

    now_str = _utcnow().isoformat() + "Z"
    lease_expires_at_str = (
        _utcnow() + timedelta(seconds=lease_seconds)
    ).isoformat() + "Z"
    token = "clm_" + secrets.token_urlsafe(9)

    conn.execute(
        """
        UPDATE accounts SET
            pool_status = 'claimed',
            claimed_by = ?,
            claimed_at = ?,
            lease_expires_at = ?,
            claim_token = ?,
            last_claimed_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            f"{caller_id}:{task_id}",
            now_str,
            lease_expires_at_str,
            token,
            now_str,
            now_str,
            account["id"],
        ),
    )
    conn.execute(
        """
        INSERT INTO account_claim_logs
            (account_id, claim_token, caller_id, task_id, action, result, detail, created_at)
        VALUES (?, ?, ?, ?, 'claim', NULL, NULL, ?)
        """,
        (account["id"], token, caller_id, task_id, now_str),
    )
    conn.execute("COMMIT")
    return dict(account) | {
        "claim_token": token,
        "lease_expires_at": lease_expires_at_str,
    }


def release(
    conn: sqlite3.Connection,
    account_id: int,
    claim_token: str,
    caller_id: str,
    task_id: str,
    reason: Optional[str],
) -> None:
    now_str = _utcnow().isoformat() + "Z"
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        """
        UPDATE accounts SET
            pool_status = 'available',
            claimed_by = NULL,
            claimed_at = NULL,
            lease_expires_at = NULL,
            claim_token = NULL,
            updated_at = ?
        WHERE id = ?
        """,
        (now_str, account_id),
    )
    conn.execute(
        """
        INSERT INTO account_claim_logs
            (account_id, claim_token, caller_id, task_id, action, result, detail, created_at)
        VALUES (?, ?, ?, ?, 'release', 'manual_release', ?, ?)
        """,
        (account_id, claim_token, caller_id, task_id, reason, now_str),
    )
    conn.execute("COMMIT")


def complete(
    conn: sqlite3.Connection,
    account_id: int,
    claim_token: str,
    caller_id: str,
    task_id: str,
    result: str,
    detail: Optional[str],
) -> str:
    new_pool_status = RESULT_TO_POOL_STATUS[result]
    is_success = result == "success"
    now_str = _utcnow().isoformat() + "Z"

    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        """
        UPDATE accounts SET
            pool_status = ?,
            claimed_by = NULL,
            claimed_at = NULL,
            lease_expires_at = NULL,
            claim_token = NULL,
            last_result = ?,
            last_result_detail = ?,
            success_count = success_count + ?,
            fail_count = fail_count + ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            new_pool_status,
            result,
            detail,
            1 if is_success else 0,
            0 if is_success else 1,
            now_str,
            account_id,
        ),
    )
    conn.execute(
        """
        INSERT INTO account_claim_logs
            (account_id, claim_token, caller_id, task_id, action, result, detail, created_at)
        VALUES (?, ?, ?, ?, 'complete', ?, ?, ?)
        """,
        (account_id, claim_token, caller_id, task_id, result, detail, now_str),
    )
    conn.execute("COMMIT")
    return new_pool_status


def expire_stale_claims(conn: sqlite3.Connection) -> int:
    now_str = _utcnow().isoformat() + "Z"
    expired = conn.execute(
        """
        SELECT id, claim_token, claimed_by FROM accounts
        WHERE pool_status = 'claimed' AND lease_expires_at < ?
        """,
        (now_str,),
    ).fetchall()

    for account in expired:
        parts = (account["claimed_by"] or ":").split(":", 1)
        caller_id = parts[0]
        task_id = parts[1] if len(parts) > 1 else ""

        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE accounts SET
                pool_status = 'cooldown',
                claimed_by = NULL,
                claimed_at = NULL,
                lease_expires_at = NULL,
                claim_token = NULL,
                fail_count = fail_count + 1,
                last_result = 'lease_expired',
                updated_at = ?
            WHERE id = ?
            """,
            (now_str, account["id"]),
        )
        conn.execute(
            """
            INSERT INTO account_claim_logs
                (account_id, claim_token, caller_id, task_id, action, result, detail, created_at)
            VALUES (?, ?, ?, ?, 'expire', 'lease_expired', 'lease timeout, auto moved to cooldown', ?)
            """,
            (account["id"], account["claim_token"], caller_id, task_id, now_str),
        )
        conn.execute("COMMIT")

    return len(expired)


def recover_cooldown(conn: sqlite3.Connection, cooldown_seconds: int) -> int:
    cutoff_str = (_utcnow() - timedelta(seconds=cooldown_seconds)).isoformat() + "Z"
    now_str = _utcnow().isoformat() + "Z"
    cursor = conn.execute(
        """
        UPDATE accounts SET pool_status = 'available', updated_at = ?
        WHERE pool_status = 'cooldown' AND updated_at < ?
        """,
        (now_str, cutoff_str),
    )
    conn.commit()
    return cursor.rowcount


def get_stats(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT pool_status, COUNT(*) as cnt FROM accounts
        GROUP BY pool_status
        """
    ).fetchall()
    pool_counts: dict = {
        "available": 0,
        "claimed": 0,
        "used": 0,
        "cooldown": 0,
        "frozen": 0,
        "retired": 0,
        "not_in_pool": 0,
    }
    for row in rows:
        key = row["pool_status"] if row["pool_status"] is not None else "not_in_pool"
        if key in pool_counts:
            pool_counts[key] = row["cnt"]

    return {"pool_counts": pool_counts}
