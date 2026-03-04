# DEVLOG（发布记录）

## v1.4.0（2026-03-04）

### 新增功能
- **🔄 账号导入导出无缝迁移（PRD-00006）**：实现"导出→不修改→直接导回来"的一键无缝迁移
  - **🔍 智能识别（混合导入）模式**：在导入界面选择"智能识别"即可自动逐行判断账号类型（Outlook OAuth / 标准 IMAP / 自定义 IMAP / GPTMail 临时邮箱），支持混合格式文件一次性导入
  - **📧 域名自动推断 Provider**：2段格式（邮箱+密码）自动根据域名推断为 Gmail/QQ/163/126/Yahoo/阿里邮箱/Outlook 等，并使用对应的 IMAP 配置
  - **📁 自动按类型分组**：导入时自动创建或复用 provider 对应的分组（如 Gmail、QQ邮箱等），无需手动指定
  - **🔁 重复账号处理策略**：新增"跳过重复"和"覆盖更新"两种策略，覆盖更新仅更新凭据字段，保留备注/标签/状态
  - **🌐 兜底 IMAP 设置**：未知域名可指定备用 IMAP 服务器地址，避免导入失败
  - **📊 增强导入结果展示**：按 provider 分类统计导入/跳过/失败数量，显示自动创建的分组列表
- **📤 导出格式升级为 v2**：
  - 文件头部新增元信息注释块（导出时间、各类型账号数量、格式版本标识）
  - 新增 GPTMail 临时邮箱分段导出（仅邮箱地址），纳入全量导出
  - 导出文件名统一为 `accounts_export_YYYYMMDD_HHMMSS.txt` 带时间戳
- **🔧 新增 Repository 层能力**：
  - `get_group_by_name()`：按名称精确查找分组（不区分大小写）
  - `update_account_credentials()`：仅更新凭据字段，敏感字段自动加密

### 修复
- 无（本版本为新增功能）

### 重要变更
- **导入 API 扩展**：`POST /api/accounts` 新增 `provider="auto"` 值触发智能识别，不影响现有 provider 值的导入行为（完全向后兼容）
- **Provider 列表扩展**：`GET /api/providers` 返回列表首位新增"🔍 智能识别（混合导入）"选项
- **导出文件名变更**：从 `all_accounts_*.txt` / `selected_accounts_*.txt` 改为 `accounts_export_*.txt` / `accounts_export_selected_*.txt`
- **导出选中分组新增 GPTMail 支持**：仅当选中了"临时邮箱"系统分组时，导出文件才包含 GPTMail 分段
- **前端导入模态框新增 UI**：重复策略单选（跳过/覆盖）、兜底 IMAP 输入、智能识别模式提示

### 测试/验证
- **新增 47 个测试用例**（4 个测试文件）：覆盖域名推断、行类型识别、auto 混合导入全链路、导出 v2 格式
- **全量测试通过**：169 个测试全部通过（基线 122 + 新增 47），零回归
- **手动验收通过**：导出→导入闭环、混合格式导入、域名推断、重复策略、自动分组、向后兼容

## v1.3.0（2026-03-03）

### 新增功能
- **🎯 多邮箱统一管理系统（PRD-00005）**：在保持 Outlook 功能完全不变的前提下，支持 Gmail、QQ、163、126、Yahoo、阿里邮箱及自定义 IMAP 邮箱
  - 统一界面管理多种邮箱类型（Outlook OAuth2 + IMAP 授权码）
  - 支持 8 种邮箱提供商预设配置（自动填充 IMAP 服务器地址和端口）
  - IMAP 授权码/应用专用密码加密存储（Fernet 加密）
  - 智能文件夹映射（收件箱/垃圾邮件/已删除邮件）支持多语言和 UTF-7 编码
  - 按提供商分类导出账号（Outlook/IMAP 分组，格式清晰）
- **🔌 新增 IMAP 通用服务**：`imap_generic.py` 提供统一的 IMAP 连接、邮件列表、详情获取能力
- **📦 邮箱提供商配置系统**：`providers.py` 集中维护 8 种邮箱的 IMAP 配置与文件夹映射规则
- **🔍 验证码提取支持 IMAP**：IMAP 邮箱也可使用验证码提取功能
- **🎨 前端动态表单**：添加账号时根据选择的邮箱类型动态显示不同的输入格式提示
- **🏷️ 账号类型标识**：账号列表显示邮箱类型标签（Outlook/Gmail/QQ 等）
- **📡 新增 API 接口**：`GET /api/providers` 返回支持的邮箱提供商列表

### 修复
- **数据库迁移安全性**：Schema v2 → v3 升级，新增 `account_type`、`provider`、`imap_host`、`imap_port`、`imap_password` 字段，保持向后兼容
- **定时刷新任务过滤**：调度器只刷新 Outlook 账号，避免对 IMAP 账号执行无效的 Token 刷新操作
- **IMAP 删除保护**：IMAP 邮箱禁止远程删除操作，返回友好提示信息

### 重要变更
- **数据库 Schema 升级至 v3**：accounts 表新增 5 个字段支持多邮箱类型
- **账号导入格式扩展**：
  - Outlook（保持不变）：`email----password----client_id----refresh_token`
  - IMAP 预设提供商：`email----授权码----provider`
  - IMAP 自定义：`email----密码----custom----imap_host----imap_port`
- **邮件 API 路由分发**：根据 `account_type` 自动路由到 Graph API 或 IMAP 服务
- **敏感数据加密扩展**：`imap_password` 纳入加密迁移逻辑
- **架构文档完善**：新增 AGENTS.md、PRD/FD/TDD/TEST 完整文档体系

### 测试/验证
- **新增 355 行多邮箱测试**：`test_multi_mailbox.py` 覆盖 Schema v3、IMAP 导入、邮件获取、验证码提取、删除保护等核心场景
- **回归测试通过**：所有现有 Outlook 功能保持不变，Graph API → IMAP XOAUTH2 回退路径正常
- **数据库迁移验证**：v2 → v3 升级幂等性、加密字段迁移、旧数据兼容性验证通过
- **IMAP 连接测试**：Gmail/QQ/163 文件夹映射、UTF-7 编码、授权码认证验证通过

## v1.2.1（2026-03-02）

### 新增功能
- **智能 SECRET_KEY 管理系统**：自动初始化、持久化保存、重启保护，彻底解决数据丢失问题
  - 首次启动自动生成 SECRET_KEY 并保存到 .env 文件
  - 重启时使用现有 SECRET_KEY，不再重新生成
  - 添加清晰的警告提示，提醒用户备份 .env 文件
- **README 界面截图展示**：添加仪表盘、邮箱界面、验证码提取、设置界面 4 张最新截图

### 修复
- **🔥 严重 Bug 修复**：修复 SECRET_KEY 每次重启都重新生成导致数据库加密数据无法解密的问题
  - 问题表现：重启后提示"邮箱不存在"、"Failed to decrypt data"错误
  - 根本原因：SECRET_KEY 变更导致 Fernet 加密密钥改变，无法解密旧数据
  - 解决方案：start.py 添加智能环境初始化，确保 SECRET_KEY 持久化
- **自动环境配置**：如果 .env 文件不存在，自动从 .env.example 创建
- **智能密钥检测**：只在 SECRET_KEY 为占位符（your-secret-key-here）时生成新密钥

### 重要变更
- **start.py 重构**：添加 `ensure_env_file()` 智能环境初始化函数
  - 自动检查并创建 .env 文件
  - 智能判断是否需要生成新的 SECRET_KEY
  - 显示友好的提示信息（首次生成 vs 使用现有）
- **截图更新**：清理 12 张旧截图，更新为 4 张最新界面截图
- **用户体验改进**：添加 SECRET_KEY 重要性说明和备份建议

### 测试/验证
- `python -m pytest tests/ --tb=short -q`：114 个测试全部通过
- **SECRET_KEY 持久性验证**：
  - 首次启动：自动生成并保存 SECRET_KEY
  - 重启验证：SECRET_KEY 保持不变（980bb366e44920382e395a3116de578b...）
  - 多次重启：密钥始终一致，数据正常解密
- **数据加密解密验证**：
  - 清空数据库后重新启动：使用相同 SECRET_KEY
  - 导入新账号：数据正常加密存储
  - 重启后读取：数据正常解密，无错误

## v1.2.0（2026-03-01）

### 新增功能
- **UI 全局美化重设计**：从白底黑字四栏布局全面升级为现代国风设计系统（砖红 #B85C38 + 翠绿 #3A7D44 + 琥珀金 #C8963E），支持浅色/深色主题切换
- **侧边栏导航系统**：全新侧边栏支持折叠/展开，包含仪表盘、邮箱管理、临时邮箱、审计日志、刷新日志、系统设置等导航项
- **设置页面内嵌显示**：系统设置从弹窗模式改为页面内嵌直接渲染，无需额外点击
- **审计日志 & 刷新日志页面**：新增独立页面加载函数，进入即自动拉取数据
- **临时邮箱增强**：卡片新增验证码提取按钮、邮箱地址点击复制、顶栏邮箱名称可复制
- **账号头像多彩系统**：8 组渐变色按索引分配，告别单调统一颜色
- **GitHub 仓库链接**：侧边栏底部新增 GitHub 仓库快速入口
- **代码质量工具链**：新增 `pyproject.toml` 统一 black/isort 配置（line-length=127）

### 修复
- **BUG-002** 选中账号名称未在邮件栏顶部显示（`currentAccountBar` 显示逻辑修正）
- **BUG-012** 侧边栏折叠后导航图标消失（CSS 选择器排除 `.nav-icon`）
- **BUG-013** 邮箱管理页仍显示"临时邮箱"分组（`renderGroupList` 过滤）
- **BUG-014/015** 审计日志和刷新日志页面永远 loading（新增加载函数 + navigate 调用）
- **BUG-016** 设置页面从弹窗改为内嵌显示
- **BUG-018** 导入账号弹窗 textarea 尺寸优化
- **BUG-020** 临时邮箱顶栏邮箱名称不可复制
- **BUG-021** 进入邮箱管理不自动选中默认分组
- **BUG-022** 切换分组时 currentAccountBar 不重置
- **BUG-023** 收件箱/垃圾邮件 Tab 切换 active 状态不更新（`.folder-tab` → `.email-tab`）
- **BUG-024** 从临时邮箱返回邮箱管理后账号列数据残留
- **Docker CI** secrets 检测从 job-level if 改为独立 check-secrets job，修复云端构建始终跳过的问题
- **安全修复**：移除误提交的包含密钥的 `start_temp.bat`

### 重要变更
- **CI/CD 全面升级**：所有 workflow 的 `actions/checkout` 从 v4 升级至 v6
- **代码格式化**：30+ 文件 isort 导入排序修复（`--profile black`），1 文件 black 格式化
- **Dependabot 移除**：不再自动创建依赖更新 PR
- **Docker 镜像**：成功推送至 `guangshanshui/outlook-email-plus`（支持 linux/amd64 + linux/arm64）
- 新增 19 个 UI 重设计 BUG 回归测试（`test_ui_redesign_bugs.py`）

### 测试/验证
- `python -m pytest tests/ --tb=short -q`：114 个测试全部通过
- `docker build .`：本地 Docker 构建通过
- GitHub Actions：Python Tests ✅ / Code Quality ✅ / Docker Build Push ✅
- 本地服务器启动验证：`/healthz` 返回 `{"status":"ok"}`

## v1.1.1（2026-02-28）

### 新增功能
- GitHub Actions Docker 构建工作流支持推送到 Docker Hub（`guangshanshui/outlook-email-plus`），并在未配置凭据时自动跳过，避免 fork/缺失 secrets 场景构建失败。

### 修复
- README 同步更新镜像地址与仓库链接，避免用户拉取/访问到旧地址（GHCR/旧仓库）。

### 重要变更
- 容器镜像发布从 GitHub Container Registry（GHCR）切换为 Docker Hub；需要在仓库 Secrets 中配置 `DOCKERHUB_USERNAME` 与 `DOCKERHUB_TOKEN` 才会执行推送。

### 测试/验证
- `npm test`：布局系统 Jest 用例回归。
- `python -m unittest discover -s tests -v`：全量 Python 单测回归。
- `docker build .`：本地镜像构建通过（用于验证 Dockerfile 未回归）。

## v1.1.0（2026-02-27）

### 新增功能
- 新增“可调整布局系统”：支持面板拖拽调整宽度、折叠/展开指示器、布局状态持久化与版本迁移。
- 新增“恢复默认布局”入口与确认对话框，便于一键回到默认四栏布局。
- UI 导航栏展示应用版本号，便于排查问题与对齐发布版本。
- 新增布局系统测试工程（Jest）：覆盖拖拽/键盘调整、折叠/展开、状态保存/加载、窗口自适配等场景。

### 修复
- 修复窄屏下自动/手动折叠后指示器不可见、导致无法再展开的问题。
- 修复折叠后页面出现滚动条、指示器高度观感异常的问题。
- 修复“隐藏邮件列表”仅改 display 导致 Grid 仍占位的空白列问题（与布局系统联动）。

### 重要变更
- 前端布局从历史侧栏方案调整为 Grid + CSS 变量驱动的四栏式布局；折叠时通过 layout-width 变量将列宽置 0（保存宽度不丢失）。
- 新增 `layout-system-enabled` 标记类，用于与旧的窄屏侧栏样式隔离，避免样式冲突与交互回归。

### 测试/验证
- `npm test`：布局系统 Jest 覆盖单元/集成用例。
- `python -m unittest discover -s tests -v`：全量 Python 单测回归。
- 手工验证：宽屏/窄屏折叠与指示器可见性、折叠后无滚动条、重置布局可恢复默认状态。
