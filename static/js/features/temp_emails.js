        // ==================== 临时邮箱相关 ====================

        // 加载临时邮箱列表
        async function loadTempEmails(forceRefresh = false) {
            const container = document.getElementById('accountList');

            if (!forceRefresh && accountsCache['temp']) {
                renderTempEmailList(accountsCache['temp']);
                return;
            }

            container.innerHTML = '<div class="loading loading-small"><div class="loading-spinner"></div></div>';

            try {
                const response = await fetch('/api/temp-emails');
                const data = await response.json();

                if (data.success) {
                    accountsCache['temp'] = data.emails;
                    renderTempEmailList(data.emails);

                    const group = groups.find(g => g.name === '临时邮箱');
                    if (group) {
                        group.account_count = data.emails.length;
                        renderGroupList(groups);
                    }
                }
            } catch (error) {
                container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
            }
        }

        // 渲染临时邮箱列表
        function renderTempEmailList(emails) {
            const container = document.getElementById('accountList');

            if (emails.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">⚡</div>
                        <div class="empty-state-text">暂无临时邮箱<br>点击下方按钮生成</div>
                    </div>
                `;
                return;
            }

            container.innerHTML = emails.map(email => `
                <div class="account-item ${currentAccount === email.email ? 'active' : ''}"
                     onclick="selectTempEmail('${escapeJs(email.email)}')">
                    <div class="account-email" title="${escapeHtml(email.email)}">
                        ${escapeHtml(email.email)}
                    </div>
                    <div class="account-actions">
                        <button class="account-action-btn" onclick="event.stopPropagation(); copyEmail('${escapeJs(email.email)}')" title="复制邮箱">复制</button>
                        <button class="account-action-btn" onclick="event.stopPropagation(); clearTempEmailMessages('${escapeJs(email.email)}')" title="清空邮件">清空</button>
                        <button class="account-action-btn delete" onclick="event.stopPropagation(); deleteTempEmail('${escapeJs(email.email)}')" title="删除">删除</button>
                    </div>
                </div>
            `).join('');
        }

        // 生成临时邮箱
        async function generateTempEmail() {
            // 获取按钮并显示加载状态
            const btn = document.querySelector('.account-panel-footer .add-account-btn');
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = '⏳ 生成中...';
            btn.style.opacity = '0.7';
            btn.style.cursor = 'not-allowed';

            try {
                const response = await fetch('/api/temp-emails/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });

                const data = await response.json();

                if (data.success) {
                    showToast(`临时邮箱已生成: ${data.email}`, 'success');
                    delete accountsCache['temp'];
                    loadTempEmails(true);
                    loadGroups();
                } else {
                    // 显示详细的错误信息
                    const errorMsg = data.error || '生成临时邮箱失败';
                    if (data.error && typeof data.error === 'object') {
                        // 结构化错误对象
                        const detailedError = data.error.message || data.error.error || errorMsg;
                        showToast(detailedError, 'error', data.error);
                    } else {
                        // 字符串错误
                        showToast(errorMsg, 'error');
                    }
                }
            } catch (error) {
                showToast('生成临时邮箱失败', 'error');
            } finally {
                // 恢复按钮状态
                btn.disabled = false;
                btn.textContent = originalText;
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            }
        }

        // 选择临时邮箱
        function selectTempEmail(email) {
            currentAccount = email;
            isTempEmailGroup = true;

            document.getElementById('currentAccount').classList.add('show');
            document.getElementById('currentAccountEmail').textContent = email + ' (临时)';

            document.querySelectorAll('.account-item').forEach(item => {
                item.classList.remove('active');
                const emailEl = item.querySelector('.account-email');
                if (emailEl && emailEl.textContent.includes(email)) {
                    item.classList.add('active');
                }
            });

            // 隐藏文件夹切换按钮（临时邮箱不支持文件夹）
            const folderTabs = document.getElementById('folderTabs');
            if (folderTabs) {
                folderTabs.style.display = 'none';
            }

            document.getElementById('emailList').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📬</div>
                    <div class="empty-state-text">点击"获取邮件"按钮获取邮件</div>
                </div>
            `;

            document.getElementById('emailDetail').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📄</div>
                    <div class="empty-state-text">选择一封邮件查看详情</div>
                </div>
            `;
            document.getElementById('emailDetailToolbar').style.display = 'none';
            document.getElementById('emailCount').textContent = '';
            document.getElementById('methodTag').style.display = 'none';
        }

        // 清空临时邮箱的所有邮件
        async function clearTempEmailMessages(email) {
            if (!confirm(`确定要清空临时邮箱 ${email} 的所有邮件吗？`)) {
                return;
            }

            try {
                const response = await fetch(`/api/temp-emails/${encodeURIComponent(email)}/clear`, {
                    method: 'DELETE'
                });

                const data = await response.json();

                if (data.success) {
                    showToast('邮件已清空', 'success');

                    // 如果当前选中的就是这个邮箱，清空邮件列表
                    if (currentAccount === email) {
                        currentEmails = [];
                        document.getElementById('emailCount').textContent = '(0)';
                        document.getElementById('emailList').innerHTML = `
                            <div class="empty-state">
                                <div class="empty-state-icon">📭</div>
                                <div class="empty-state-text">收件箱为空</div>
                            </div>
                        `;
                        document.getElementById('emailDetail').innerHTML = `
                            <div class="empty-state">
                                <div class="empty-state-icon">📄</div>
                                <div class="empty-state-text">选择一封邮件查看详情</div>
                            </div>
                        `;
                        document.getElementById('emailDetailToolbar').style.display = 'none';
                    }
                } else {
                    handleApiError(data, '清空临时邮箱失败');
                }
            } catch (error) {
                showToast('清空失败', 'error');
            }
        }

        // 删除临时邮箱
        async function deleteTempEmail(email) {
            if (!confirm(`确定要删除临时邮箱 ${email} 吗？\n该邮箱的所有邮件也将被删除。`)) {
                return;
            }

            try {
                const response = await fetch(`/api/temp-emails/${encodeURIComponent(email)}`, {
                    method: 'DELETE'
                });

                const data = await response.json();

                if (data.success) {
                    showToast('临时邮箱已删除', 'success');
                    delete accountsCache['temp'];

                    if (currentAccount === email) {
                        currentAccount = null;
                        document.getElementById('currentAccount').classList.remove('show');
                        document.getElementById('emailList').innerHTML = `
                            <div class="empty-state">
                                <div class="empty-state-icon">📬</div>
                                <div class="empty-state-text">请从左侧选择一个邮箱账号</div>
                            </div>
                        `;
                        document.getElementById('emailDetail').innerHTML = `
                            <div class="empty-state">
                                <div class="empty-state-icon">📄</div>
                                <div class="empty-state-text">选择一封邮件查看详情</div>
                            </div>
                        `;
                    }

                    loadTempEmails(true);
                    loadGroups();
                } else {
                    handleApiError(data, '删除临时邮箱失败');
                }
            } catch (error) {
                showToast('删除失败', 'error');
            }
        }

        // 加载临时邮箱的邮件
        async function loadTempEmailMessages(email) {
            const container = document.getElementById('emailList');
            container.innerHTML = '<div class="loading"><div class="loading-spinner"></div></div>';

            // 禁用按钮
            const refreshBtn = document.querySelector('.refresh-btn');
            if (refreshBtn) {
                refreshBtn.disabled = true;
                refreshBtn.textContent = '获取中...';
            }

            try {
                const response = await fetch(`/api/temp-emails/${encodeURIComponent(email)}/messages`);
                const data = await response.json();

                if (data.success) {
                    currentEmails = data.emails;
                    currentMethod = 'gptmail';

                    const methodTag = document.getElementById('methodTag');
                    methodTag.textContent = 'GPTMail';
                    methodTag.style.display = 'inline';
                    methodTag.style.backgroundColor = '#00bcf2';
                    methodTag.style.color = 'white';

                    document.getElementById('emailCount').textContent = `(${data.count})`;

                    renderEmailList(data.emails);
                } else {
                    handleApiError(data, '加载临时邮件失败');
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">⚠️</div>
                            <div class="empty-state-text">${data.error && data.error.message ? data.error.message : '加载失败'}</div>
                        </div>
                    `;
                }
            } catch (error) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">⚠️</div>
                        <div class="empty-state-text">网络错误，请重试</div>
                    </div>
                `;
            } finally {
                // 启用按钮
                if (refreshBtn) {
                    refreshBtn.disabled = false;
                    refreshBtn.textContent = '获取邮件';
                }
            }
        }

        // 获取临时邮件详情
        async function getTempEmailDetail(messageId, index) {
            document.querySelectorAll('.email-item').forEach((item, i) => {
                item.classList.toggle('active', i === index);
            });

            document.getElementById('emailDetailToolbar').style.display = 'flex';

            const container = document.getElementById('emailDetail');
            container.innerHTML = '<div class="loading"><div class="loading-spinner"></div></div>';

            try {
                const response = await fetch(`/api/temp-emails/${encodeURIComponent(currentAccount)}/messages/${encodeURIComponent(messageId)}`);
                const data = await response.json();

                if (data.success) {
                    renderEmailDetail(data.email);
                } else {
                    handleApiError(data, '加载邮件详情失败');
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">⚠️</div>
                            <div class="empty-state-text">${data.error && data.error.message ? data.error.message : '加载失败'}</div>
                        </div>
                    `;
                }
            } catch (error) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">⚠️</div>
                        <div class="empty-state-text">网络错误，请重试</div>
                    </div>
                `;
            }
        }

