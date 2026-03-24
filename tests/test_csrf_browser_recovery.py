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
class CsrfBrowserRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app
        cls._original_csrf_enabled = cls.app.config.get("WTF_CSRF_ENABLED")
        cls._original_csrf_check_default = cls.app.config.get("WTF_CSRF_CHECK_DEFAULT")
        cls.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=True,
            WTF_CSRF_CHECK_DEFAULT=True,
        )

        cls._server = _LiveServerThread(cls.app)
        cls._server.start()
        cls.base_url = f"http://127.0.0.1:{cls._server.port}"
        cls._playwright = sync_playwright().start()
        try:
            cls._browser = cls._playwright.chromium.launch(headless=True)
        except Exception as exc:
            cls._playwright.stop()
            cls._server.shutdown()
            cls._server.join(timeout=5)
            raise unittest.SkipTest(f"playwright chromium is unavailable: {exc}")

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
                cls.app.config.update(
                    WTF_CSRF_ENABLED=cls._original_csrf_enabled,
                    WTF_CSRF_CHECK_DEFAULT=cls._original_csrf_check_default,
                )

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()
            from outlook_web.db import get_db

            db = get_db()
            db.execute("DELETE FROM accounts WHERE email LIKE '%@csrf-browser.test'")
            db.commit()

    def _account_exists(self, email_addr: str) -> bool:
        conn = self.module.create_sqlite_connection()
        try:
            row = conn.execute("SELECT 1 FROM accounts WHERE email = ? LIMIT 1", (email_addr,)).fetchone()
            return row is not None
        finally:
            conn.close()

    def test_browser_recovers_after_stale_csrf_token_and_retries_once(self):
        unique = uuid.uuid4().hex[:10]
        email_addr = f"browser_{unique}@csrf-browser.test"
        account_line = f"{email_addr}----pwd----cid_{unique}----rt_{unique}"

        context = self._browser.new_context(locale="zh-CN")
        page = context.new_page()
        account_post_statuses = []
        csrf_token_request_count = 0

        def _collect_account_import_response(response):
            nonlocal csrf_token_request_count
            request = response.request
            if request.method == "POST" and response.url.endswith("/api/accounts"):
                account_post_statuses.append(response.status)
            if request.method == "GET" and response.url.endswith("/api/csrf-token"):
                csrf_token_request_count += 1

        page.on("response", _collect_account_import_response)

        try:
            page.goto(f"{self.base_url}/login")
            page.fill("#password", "testpass123")
            page.click("#loginBtn")
            page.wait_for_url(re.compile(r".*/$"))
            page.wait_for_load_state("networkidle")
            page.locator('.nav-item[data-page="mailbox"]').click()
            page.wait_for_load_state("networkidle")
            page.wait_for_function(
                """() => {
                    const select = document.getElementById('importGroupSelect');
                    return select && select.options.length > 0;
                }"""
            )
            account_post_statuses.clear()
            csrf_token_request_count = 0

            page.evaluate(
                """(line) => {
                    showAddAccountModal();
                    document.getElementById('accountInput').value = line;
                    const select = document.getElementById('importGroupSelect');
                    if (select && select.options.length > 0) {
                        select.value = select.options[0].value;
                    }
                    csrfToken = 'stale-csrf-token';
                    addAccount();
                }""",
                account_line,
            )

            page.locator("#toast-container .toast.success").filter(has_text="导入完成").wait_for(timeout=15000)
            page.wait_for_function(
                """(targetEmail) => {
                    const cards = Array.from(document.querySelectorAll('.account-card .account-email'));
                    return cards.some((node) => (node.textContent || '').includes(targetEmail));
                }""",
                arg=email_addr,
                timeout=15000,
            )

            self.assertEqual(account_post_statuses, [400, 200])
            self.assertEqual(csrf_token_request_count, 1)
            self.assertTrue(self._account_exists(email_addr))
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
