"""tests/test_v191_compact_mode_frontend_contract.py — TDD-00011 前端 RED 契约测试

目标：
1. 固定账号管理简洁模式的前端挂载点与状态约定
2. 让模式切换、状态共享、单行标签适配层的缺口直接暴露
3. 避免后续把简洁模式继续堆回 groups.js / main.js 的旧结构里
"""

from __future__ import annotations

import unittest

from tests._import_app import import_web_app_module


class V191CompactModeFrontendContractTests(unittest.TestCase):
    """TDD-00011 §6 前端 RED 契约测试"""

    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def _login(self, client, password: str = "testpass123"):
        resp = client.post("/login", json={"password": password})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json() or {}
        self.assertEqual(data.get("success"), True)

    def _get_text(self, client, path: str) -> str:
        resp = client.get(path)
        try:
            return resp.data.decode("utf-8")
        finally:
            resp.close()

    def test_t_fe_001_index_html_contains_mailbox_view_mode_switcher(self):
        client = self.app.test_client()
        self._login(client)
        index_html = self._get_text(client, "/")

        self.assertIn(
            "标准模式",
            index_html,
            "TDD-00011 要求账号管理页存在“标准模式”入口",
        )
        self.assertIn(
            "简洁模式",
            index_html,
            "TDD-00011 要求账号管理页存在“简洁模式”入口",
        )

    def test_t_fe_002_frontend_exposes_mailbox_view_mode_state(self):
        client = self.app.test_client()
        main_js = self._get_text(client, "/static/js/main.js")
        accounts_js = self._get_text(client, "/static/js/features/accounts.js")
        groups_js = self._get_text(client, "/static/js/features/groups.js")
        combined = "\n".join([main_js, accounts_js, groups_js])

        self.assertIn(
            "mailboxViewMode",
            combined,
            "TDD-00011 要求前端存在 mailboxViewMode 页面级状态",
        )

    def test_t_fe_003_compact_mode_module_exists(self):
        client = self.app.test_client()
        resp = client.get("/static/js/features/mailbox_compact.js")

        try:
            self.assertEqual(
                resp.status_code,
                200,
                "TDD-00011 要求新增 static/js/features/mailbox_compact.js 作为简洁模式独立渲染模块",
            )
        finally:
            resp.close()

    def test_t_fe_004_compact_mode_module_exposes_key_render_functions(self):
        client = self.app.test_client()
        module_js = self._get_text(client, "/static/js/features/mailbox_compact.js")

        for symbol in [
            "renderCompactGroupStrip",
            "renderCompactAccountList",
            "switchMailboxViewMode",
        ]:
            self.assertIn(
                symbol,
                module_js,
                f"TDD-00011 要求简洁模式模块暴露 `{symbol}`",
            )

    def test_t_fe_004a_compact_mode_switch_makes_compact_layout_visible(self):
        client = self.app.test_client()
        module_js = self._get_text(client, "/static/js/features/mailbox_compact.js")

        self.assertIn(
            "compactLayout.style.display = mailboxViewMode === 'compact' ? 'block' : 'none';",
            module_js,
            "简洁模式切换时必须显式显示 mailboxCompactLayout，不能继续落回 CSS 默认隐藏态",
        )

    def test_t_fe_005_frontend_keeps_single_selected_account_ids_source(self):
        client = self.app.test_client()
        main_js = self._get_text(client, "/static/js/main.js")
        self.assertIn("let selectedAccountIds = new Set();", main_js)

        compact_js = self._get_text(client, "/static/js/features/mailbox_compact.js")
        self.assertNotIn(
            "let compactSelectedAccountIds",
            compact_js,
            "TDD-00011 要求简洁模式复用 selectedAccountIds，而不是维护第二份选择集合",
        )

    def test_t_fe_006_single_row_tagging_supports_scoped_account_ids_without_clearing_global_selection(self):
        client = self.app.test_client()
        main_js = self._get_text(client, "/static/js/main.js")
        compact_js = self._get_text(client, "/static/js/features/mailbox_compact.js")
        combined = "\n".join([main_js, compact_js])

        self.assertIn(
            "scopedAccountIds",
            combined,
            "TDD-00011 要求单行打标签通过 scopedAccountIds 适配层接入",
        )

        self.assertNotIn(
            "selectedAccountIds.clear()",
            compact_js,
            "TDD-00011 要求单行打标签不清空全局 selectedAccountIds",
        )

    def test_t_fe_007_compact_mode_uses_accounts_summary_fields_for_rendering(self):
        client = self.app.test_client()
        compact_js = self._get_text(client, "/static/js/features/mailbox_compact.js")

        for field in [
            "latest_email_subject",
            "latest_email_from",
            "latest_email_folder",
            "latest_email_received_at",
            "latest_verification_code",
        ]:
            self.assertIn(
                field,
                compact_js,
                f"TDD-00011 要求简洁模式列表渲染使用 `{field}`",
            )

    def test_t_fe_008_compact_mode_does_not_depend_on_right_detail_panel(self):
        client = self.app.test_client()
        compact_js = self._get_text(client, "/static/js/features/mailbox_compact.js")

        self.assertNotIn(
            "emailDetailSection",
            compact_js,
            "TDD-00011 要求简洁模式不依赖右侧详情区完成主操作",
        )
        self.assertNotIn(
            "document.getElementById('emailDetail')",
            compact_js,
            "TDD-00011 要求简洁模式列表渲染不耦合右侧邮件详情 DOM",
        )

    def test_t_fe_009_add_account_refreshes_groups_and_compact_list_after_import(self):
        client = self.app.test_client()
        accounts_js = self._get_text(client, "/static/js/features/accounts.js")

        self.assertIn(
            "refreshMailboxAfterImport",
            accounts_js,
            "导入账号成功后应走统一刷新链路，避免简洁模式漏渲染",
        )
        self.assertIn(
            "await loadGroups();",
            accounts_js,
            "导入账号成功后应先刷新分组状态",
        )
        self.assertIn(
            "await selectGroup(importedGroupId);",
            accounts_js,
            "导入到其他分组后应切换并触发该分组的账号渲染",
        )

    def test_t_fe_010_verification_copy_lock_is_per_account_not_global(self):
        client = self.app.test_client()
        groups_js = self._get_text(client, "/static/js/features/groups.js")

        self.assertIn(
            "const verificationCopyInFlight = new Set();",
            groups_js,
            "验证码提取应改为按账号维度去重，允许不同账号并发执行",
        )
        self.assertIn(
            "verificationCopyInFlight.has(requestKey)",
            groups_js,
            "验证码提取应仅拦截同一账号的重复点击",
        )
        self.assertNotIn(
            "let copyVerificationInProgress = false;",
            groups_js,
            "旧的全局单锁会阻塞不同账号并发提取，必须移除",
        )

    def test_t_fe_011_compact_actions_do_not_render_extra_copy_menu_items(self):
        client = self.app.test_client()
        compact_js = self._get_text(client, "/static/js/features/mailbox_compact.js")

        self.assertNotIn(
            """<button class="menu-item" onclick="event.preventDefault(); event.stopPropagation(); closeCompactMenu(this); copyEmail('${escapeJs(account.email)}')">""",
            compact_js,
            "简洁模式应直接点击邮箱复制，不再渲染额外的复制邮箱菜单项",
        )
        self.assertNotIn(
            """<button class="menu-item" onclick="event.preventDefault(); event.stopPropagation(); closeCompactMenu(this); copyCompactVerification(getCompactAccountById(${account.id}), this)">""",
            compact_js,
            "简洁模式应直接点击验证码复制，不再渲染额外的复制验证码菜单项",
        )


if __name__ == "__main__":
    unittest.main()
