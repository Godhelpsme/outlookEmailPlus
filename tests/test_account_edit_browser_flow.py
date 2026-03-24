import json
import re
import threading
import unittest
import uuid

from tests._import_app import clear_login_attempts, import_web_app_module

try:
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False


class _LiveServerThread(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self._server = make_server("127.0.0.1", 0, app)
        self.port = int(self._server.server_port)

    def run(self):
        self._server.serve_forever()

    def shutdown(self):
        self._server.shutdown()


@unittest.skipUnless(PLAYWRIGHT_AVAILABLE, "playwright or werkzeug is unavailable")
class AccountEditBrowserFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app
        cls._server = _LiveServerThread(cls.app)
        cls._server.start()
        cls.base_url = f"http://127.0.0.1:{cls._server.port}"
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        try:
            cls._browser.close()
        finally:
            try:
                cls._playwright.stop()
            finally:
                cls._server.shutdown()
                cls._server.join(timeout=5)

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()

    def _default_group_id(self) -> int:
        conn = self.module.create_sqlite_connection()
        try:
            row = conn.execute("SELECT id FROM groups WHERE name = '默认分组' LIMIT 1").fetchone()
            return int(row["id"]) if row else 1
        finally:
            conn.close()

    def _insert_outlook_account(self, *, remark: str):
        unique = uuid.uuid4().hex
        email_addr = f"browser_remark_{unique}@outlook.com"
        password = f"pw_{unique}"
        client_id = f"cid_{unique}"
        refresh_token = f"rt_{unique}----tail"
        group_id = self._default_group_id()

        conn = self.module.create_sqlite_connection()
        try:
            cur = conn.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, remark, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email_addr,
                    self.module.encrypt_data(password),
                    client_id,
                    self.module.encrypt_data(refresh_token),
                    "outlook",
                    "outlook",
                    group_id,
                    remark,
                    "active",
                ),
            )
            conn.commit()
            account_id = int(cur.lastrowid)
        finally:
            conn.close()

        return {
            "id": account_id,
            "email": email_addr,
            "password": password,
            "client_id": client_id,
            "refresh_token": refresh_token,
            "group_id": group_id,
            "remark": remark,
        }

    def _get_account_row(self, account_id: int):
        conn = self.module.create_sqlite_connection()
        try:
            return conn.execute("SELECT * FROM accounts WHERE id = ? LIMIT 1", (account_id,)).fetchone()
        finally:
            conn.close()

    def _decrypt_if_needed(self, value: str) -> str:
        if not value:
            return value
        try:
            return self.module.decrypt_data(value)
        except Exception:
            return value

    def test_browser_can_edit_outlook_remark_without_reentering_credentials(self):
        account = self._insert_outlook_account(remark="browser_old")
        new_remark = f"browser_new_{uuid.uuid4().hex[:8]}"

        context = self._browser.new_context(locale="zh-CN")
        page = context.new_page()
        try:
            page.goto(f"{self.base_url}/login")
            page.fill("#password", "testpass123")
            page.click("#loginBtn")
            page.wait_for_url(re.compile(r".*/$"))
            page.wait_for_load_state("networkidle")
            page.locator('.nav-item[data-page="mailbox"]').click()
            page.wait_for_load_state("networkidle")

            account_card = page.locator(".account-card").filter(has_text=account["email"]).first
            account_card.wait_for(timeout=10000)
            account_card.hover()
            account_card.locator('button[title="编辑"]').evaluate("(el) => el.click()")

            page.locator("#editAccountModal.show").wait_for(timeout=10000)
            self.assertEqual(page.input_value("#editClientId"), account["client_id"])
            self.assertEqual(page.locator("#editRefreshToken").input_value(), "")

            page.fill("#editRemark", new_remark)

            with page.expect_request(
                lambda req: req.method == "PUT" and req.url.endswith(f"/api/accounts/{account['id']}")
            ) as request_info:
                page.locator("#editAccountModal button").filter(has_text="保存").click()

            request = request_info.value
            payload = json.loads(request.post_data or "{}")
            self.assertEqual(payload.get("remark"), new_remark)
            self.assertEqual(payload.get("client_id"), "")
            self.assertEqual(payload.get("refresh_token"), "")

            page.locator("#toast-container .toast.success").filter(has_text="账号更新成功").wait_for(timeout=10000)
            page.wait_for_function("() => !document.getElementById('editAccountModal').classList.contains('show')")
            page.locator(".account-card").filter(has_text=account["email"]).filter(has_text=new_remark).first.wait_for(timeout=10000)

            row = self._get_account_row(account["id"])
            self.assertIsNotNone(row)
            self.assertEqual((row["remark"] or ""), new_remark)
            self.assertEqual(row["client_id"], account["client_id"])
            self.assertEqual(self._decrypt_if_needed(row["password"]), account["password"])
            self.assertEqual(self._decrypt_if_needed(row["refresh_token"]), account["refresh_token"])
        finally:
            context.close()
