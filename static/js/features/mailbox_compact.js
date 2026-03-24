        function getCompactVisibleAccounts() {
            return Array.isArray(accountsCache[currentGroupId]) ? accountsCache[currentGroupId] : [];
        }

        function getCompactAccountById(accountId) {
            return getCompactVisibleAccounts().find(account => account.id === accountId) || null;
        }

        function closeCompactMenu(element) {
            const details = element && typeof element.closest === 'function' ? element.closest('details') : null;
            if (details) {
                details.removeAttribute('open');
            }
        }

        function translateCompactText(text) {
            return typeof translateAppTextLocal === 'function' ? translateAppTextLocal(text) : text;
        }

        function formatCompactSelectedCount(count) {
            if (typeof formatSelectedItemsLabel === 'function') {
                return formatSelectedItemsLabel(count);
            }
            return getUiLanguage() === 'en' ? `${count} selected` : `已选 ${count} 项`;
        }

        function formatCompactAccountCount(count) {
            const safeCount = Number(count || 0);
            if (getUiLanguage() === 'en') {
                return `${safeCount} account${safeCount === 1 ? '' : 's'}`;
            }
            return `${safeCount} 个账号`;
        }

        function renderCompactLoadingState(message = '加载中…') {
            const container = document.getElementById('compactAccountList');
            if (!container) return;
            container.innerHTML = `
                <div class="loading-overlay compact-state-block">
                    <span class="spinner"></span> ${escapeHtml(translateCompactText(message))}
                </div>
            `;
        }

        function renderCompactErrorState(message = '加载失败，请重试') {
            const container = document.getElementById('compactAccountList');
            if (!container) return;
            container.innerHTML = `
                <div class="empty-state compact-state-block">
                    <span class="empty-icon">⚠️</span>
                    <p>${escapeHtml(translateCompactText(message))}</p>
                </div>
            `;
        }

        function switchMailboxViewMode(mode) {
            mailboxViewMode = mode === 'compact' ? 'compact' : 'standard';
            localStorage.setItem('ol_mailbox_view_mode', mailboxViewMode);

            const standardLayout = document.getElementById('mailboxStandardLayout');
            const compactLayout = document.getElementById('mailboxCompactLayout');

            if (standardLayout) {
                standardLayout.style.display = mailboxViewMode === 'standard' ? '' : 'none';
            }
            if (compactLayout) {
                compactLayout.style.display = mailboxViewMode === 'compact' ? 'block' : 'none';
            }
            if (currentPage === 'mailbox' && typeof updateTopbar === 'function') {
                updateTopbar('mailbox');
            }

            if (currentGroupId && Array.isArray(accountsCache[currentGroupId])) {
                renderAccountList(accountsCache[currentGroupId]);
            }
            renderCompactGroupStrip(groups, currentGroupId);
            renderCompactAccountList(getCompactVisibleAccounts());
            updateBatchActionBar();
            updateSelectAllCheckbox();
        }

        function renderCompactGroupStrip(groupItems, activeGroupId) {
            const container = document.getElementById('compactGroupStrip');
            const summary = document.getElementById('compactModeSummary');
            if (!container) return;

            const visibleGroups = (groupItems || []).filter(group => !isTempMailboxGroup(group));
            if (visibleGroups.length === 0) {
                container.innerHTML = `<div class="compact-empty-inline">${escapeHtml(translateCompactText('暂无分组'))}</div>`;
                if (summary) {
                    summary.textContent = translateCompactText('暂无可用分组');
                }
                return;
            }

            const currentGroup = visibleGroups.find(group => group.id === activeGroupId) || visibleGroups[0];
            if (summary && currentGroup) {
                const selectedCount = selectedAccountIds.size > 0 ? ` · ${formatCompactSelectedCount(selectedAccountIds.size)}` : '';
                summary.textContent = `${formatGroupDisplayName(currentGroup.name)} · ${formatCompactAccountCount(currentGroup.account_count)}${selectedCount}`;
            }

            container.innerHTML = visibleGroups.map(group => `
                <button
                    class="group-chip ${group.id === activeGroupId ? 'active' : ''}"
                    onclick="selectGroup(${group.id})"
                >
                    <span>
                        <span class="group-chip-name">${escapeHtml(formatGroupDisplayName(group.name))}</span>
                        <span class="group-chip-meta">${escapeHtml(formatGroupDescription(group.description, '未填写说明'))} · ${escapeHtml(formatCompactAccountCount(group.account_count))}</span>
                    </span>
                </button>
            `).join('');
        }

        function syncCompactSelectionState(accountId, checked) {
            handleAccountSelectionChange(accountId, checked);
            renderCompactGroupStrip(groups, currentGroupId);
        }

        async function copyCompactVerification(account, buttonElement) {
            if (!account) {
                showToast(translateCompactText('未找到账号摘要'), 'error');
                return;
            }

            if (account.latest_verification_code) {
                try {
                    await copyToClipboard(account.latest_verification_code);
                    showToast(
                        getUiLanguage() === 'en'
                            ? `Copied: ${account.latest_verification_code}`
                            : `已复制: ${account.latest_verification_code}`,
                        'success'
                    );
                    return;
                } catch (error) {
                    showToast(translateCompactText('复制验证码失败'), 'error');
                    return;
                }
            }

            if (buttonElement) {
                copyVerificationInfo(account.email, buttonElement);
            }
        }

        function openCompactSingleTagModal(accountId) {
            showBatchTagModal('add', { scopedAccountIds: [accountId] });
        }

        function openCompactSingleMoveGroupModal(accountId) {
            showBatchMoveGroupModal({ scopedAccountIds: [accountId] });
        }

        async function refreshCompactAccount(accountId, buttonElement) {
            const account = getCompactAccountById(accountId);
            if (!account) {
                showToast(translateCompactText('未找到账号'), 'error');
                return;
            }

            const originalText = buttonElement ? buttonElement.textContent : '';
            if (buttonElement) {
                buttonElement.disabled = true;
                buttonElement.textContent = translateCompactText('拉取中...');
            }

            try {
                const requests = [
                    fetch(`/api/emails/${encodeURIComponent(account.email)}?folder=inbox&skip=0&top=10`),
                    fetch(`/api/emails/${encodeURIComponent(account.email)}?folder=junkemail&skip=0&top=10`)
                ];
                const results = await Promise.allSettled(requests);
                let hasSuccess = false;
                for (const result of results) {
                    if (result.status !== 'fulfilled' || !result.value.ok) {
                        continue;
                    }
                    const payload = await result.value.json();
                    if (!payload.success) {
                        continue;
                    }
                    hasSuccess = true;
                    if (typeof syncAccountSummaryToAccountCache === 'function' && payload.account_summary) {
                        syncAccountSummaryToAccountCache(account.email, payload.account_summary);
                    }
                }
                if (!hasSuccess) {
                    throw new Error('refresh_failed');
                }
                const hasPartialFailure = results.some(result => result.status === 'rejected' || (result.status === 'fulfilled' && !result.value.ok));
                showToast(
                    translateCompactText(hasPartialFailure ? '部分拉取完成，账号摘要已刷新' : '账号摘要已刷新'),
                    'success'
                );
            } catch (error) {
                showToast(translateCompactText('刷新账号摘要失败'), 'error');
            } finally {
                if (buttonElement) {
                    buttonElement.disabled = false;
                    buttonElement.textContent = originalText || translateCompactText('拉取');
                }
            }
        }

        function renderCompactAccountList(accounts) {
            const container = document.getElementById('compactAccountList');
            if (!container) return;

            if (!accounts || accounts.length === 0) {
                container.innerHTML = `
                    <div class="empty-state-lite compact-state-block">
                        ${escapeHtml(translateCompactText('当前分组暂无账号'))}
                    </div>
                `;
                updateSelectAllCheckbox();
                updateBatchActionBar();
                return;
            }

            container.innerHTML = (accounts || []).map(account => {
                const latestEmailSubject = account.latest_email_subject || translateCompactText('暂无邮件');
                const latestEmailFrom = account.latest_email_from || translateCompactText('未知发件人');
                const latestEmailFolder = account.latest_email_folder || '';
                const latestEmailReceivedAt = account.latest_email_received_at || '';
                const latestVerificationCode = account.latest_verification_code || '';
                const isChecked = selectedAccountIds.has(account.id);
                const tagHtml = (account.tags || []).map(tag => `
                    <span class="tag-chip">${escapeHtml(tag.name)}</span>
                `).join('');
                const providerText = (account.provider || account.account_type || 'outlook').toUpperCase();
                const statusText = formatAccountStatusLabel(account.status);
                const latestEmailMeta = [
                    latestEmailFrom || translateCompactText('未知发件人'),
                    latestEmailFolder || '',
                    latestEmailReceivedAt || ''
                ].filter(Boolean).join(' · ');

                return `
                    <div class="mail-row ${isChecked ? 'is-selected' : ''}">
                        <div class="select-cell" data-label="${escapeHtml(translateCompactText('选择'))}">
                            <input
                                type="checkbox"
                                class="account-select-checkbox"
                                value="${account.id}"
                                ${isChecked ? 'checked' : ''}
                                onchange="syncCompactSelectionState(${account.id}, this.checked)"
                            >
                        </div>
                        <div class="mail-card" data-label="${escapeHtml(translateCompactText('邮箱'))}">
                            <button
                                class="mail-card-button"
                                onclick="copyEmail('${escapeJs(account.email)}')"
                                title="${escapeHtml(translateCompactText('点击复制邮箱地址'))}"
                            >
                                <span class="mail-address">${escapeHtml(account.email || '')}</span>
                                <div class="mail-meta" title="${escapeHtml(`${providerText} · ${statusText}`)}">
                                    ${escapeHtml(providerText)} · ${escapeHtml(statusText)}
                                </div>
                            </button>
                        </div>
                        <div class="mail-code" data-label="${escapeHtml(translateCompactText('验证码'))}">
                            <button
                                class="code-button ${latestVerificationCode ? '' : 'empty'}"
                                onclick="copyCompactVerification(getCompactAccountById(${account.id}), this)"
                                title="${escapeHtml(translateCompactText(latestVerificationCode ? '复制当前摘要验证码' : '无摘要码时兜底提取验证码'))}"
                            >${escapeHtml(latestVerificationCode || translateCompactText('暂无'))}</button>
                        </div>
                        <div class="mail-snippet" data-label="${escapeHtml(translateCompactText('最新邮件'))}">
                            <div class="snippet-subject" title="${escapeHtml(latestEmailSubject)}">${escapeHtml(latestEmailSubject)}</div>
                            <div class="snippet-meta" title="${escapeHtml(latestEmailMeta)}">${escapeHtml(latestEmailMeta || translateCompactText('暂无邮件摘要'))}</div>
                        </div>
                        <div data-label="${escapeHtml(translateCompactText('标签'))}">
                            <div class="tag-list">
                                ${tagHtml || `<span class="tag-chip muted">${escapeHtml(translateCompactText('暂无标签'))}</span>`}
                            </div>
                        </div>
                        <div class="action-cell" data-label="${escapeHtml(translateCompactText('操作'))}">
                            <div class="compact-actions">
                                <button class="pull-button" onclick="refreshCompactAccount(${account.id}, this)">${escapeHtml(translateCompactText('拉取'))}</button>
                                <details class="action-menu">
                                    <summary class="menu-button" aria-label="${escapeHtml(translateCompactText('更多操作'))}" title="${escapeHtml(translateCompactText('更多操作'))}">⋯</summary>
                                    <div class="menu-panel">
                                        <button class="menu-item" onclick="event.preventDefault(); event.stopPropagation(); closeCompactMenu(this); showAccountRemarkModal(${account.id}, '${escapeJs(account.email)}', '${escapeJs(account.remark || '')}', ${account.group_id || 'null'})">${escapeHtml(translateCompactText('编辑备注'))}</button>
                                        <button class="menu-item" onclick="event.preventDefault(); event.stopPropagation(); closeCompactMenu(this); openCompactSingleTagModal(${account.id})">${escapeHtml(translateCompactText('打标签'))}</button>
                                        <button class="menu-item" onclick="event.preventDefault(); event.stopPropagation(); closeCompactMenu(this); openCompactSingleMoveGroupModal(${account.id})">${escapeHtml(translateCompactText('移动分组'))}</button>
                                        <button class="menu-item danger" onclick="event.preventDefault(); event.stopPropagation(); closeCompactMenu(this); deleteAccount(${account.id}, '${escapeJs(account.email)}')">${escapeHtml(translateCompactText('删除账号'))}</button>
                                    </div>
                                </details>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            updateSelectAllCheckbox();
            updateBatchActionBar();
        }

        window.addEventListener('ui-language-changed', () => {
            renderCompactGroupStrip(groups, currentGroupId);
            renderCompactAccountList(getCompactVisibleAccounts());
        });
