# Outlook Email Plus

一个面向注册、验证、批量维护场景的邮箱聚合 Web 工具。它把 Outlook OAuth 邮箱、IMAP 邮箱、GPTMail 临时邮箱、验证码提取、邮件通知、对外开放接口和邮箱池调度整合到同一套界面里。

[English](./README.en.md)

## 这是什么

这个项目不是单纯的“收件箱查看器”。

它更适合下面这些场景：

- 集中维护多种类型的邮箱账号
- 自动读取注册验证码、验证链接和通知邮件
- 把邮箱作为资源池对接外部注册机或自动化脚本
- 搭建一个受控的演示站点，给其他人使用但不暴露高风险配置

## 最近更新

当前 README 已按最近几轮功能更新同步调整，重点包括：

- 中英双语界面与更完整的 i18n 覆盖
- 统一通知分发能力：邮件通知与 Telegram 推送共存
- 受控外部接口增强：单 Key、多 Key、白名单、限流、危险端点禁用
- 邮箱池外部集成统一收敛到 `/api/external/pool/*`
- 旧匿名 `/api/pool/*` 端点已移除
- 新增演示站点保护开关：可禁止在设置页修改登录密码

## 核心能力

- 多邮箱账号管理
  支持 Outlook OAuth、普通 IMAP 邮箱和 GPTMail 临时邮箱
- 批量导入与分组整理
  支持批量导入、标签、搜索、分组、导出
- 邮件读取与提取
  支持验证码、链接、原文内容读取
- 邮箱池调度
  支持可领取、释放、完成、冷却恢复、过期回收等状态流转
- 受控对外接口
  支持 `X-API-Key` 鉴权、多调用方 Key 管理、邮箱范围授权、IP 白名单和速率限制
- 通知能力
  支持业务邮件通知、Telegram 推送和测试发送
- 演示站点保护
  可通过环境变量锁定登录密码修改入口，避免访客在设置页改后台密码

## 项目结构

```text
outlook_web/          Flask 应用主体（controllers / routes / services / repositories）
templates/            页面模板
static/               前端脚本与样式
data/                 SQLite 数据与运行时文件
tests/                自动化测试
web_outlook_app.py    兼容入口
```

## 快速开始

### Docker 部署

```bash
docker pull ghcr.io/zeropointsix/outlook-email-plus:latest

docker run -d \
  --name outlook-email-plus \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -e SECRET_KEY=your-secret-key-here \
  -e LOGIN_PASSWORD=your-login-password \
  -e ALLOW_LOGIN_PASSWORD_CHANGE=false \
  ghcr.io/zeropointsix/outlook-email-plus:latest
```

说明：

- 建议始终挂载 `data/`，避免数据库与运行数据丢失
- `SECRET_KEY` 必须稳定且足够强
- 演示站点建议显式设置 `ALLOW_LOGIN_PASSWORD_CHANGE=false`

### 本地运行

```bash
python -m venv .venv
pip install -r requirements.txt
python web_outlook_app.py
```

### 运行测试

```bash
python -m unittest discover -s tests -v
```

## 常用环境变量

- `SECRET_KEY`
  会话与敏感字段加密密钥，必须配置
- `LOGIN_PASSWORD`
  初始后台登录密码，首次启动后会写入数据库并哈希存储
- `ALLOW_LOGIN_PASSWORD_CHANGE`
  是否允许在设置页修改登录密码。演示站点建议设为 `false`
- `DATABASE_PATH`
  SQLite 数据库路径，默认 `data/outlook_accounts.db`
- `PORT` / `HOST`
  Web 服务监听地址
- `SCHEDULER_AUTOSTART`
  是否自动启动后台调度器
- `OAUTH_CLIENT_ID`
  Outlook OAuth 应用 ID
- `OAUTH_REDIRECT_URI`
  Outlook OAuth 回调地址
- `GPTMAIL_BASE_URL`
  GPTMail 服务地址
- `GPTMAIL_API_KEY`
  GPTMail API Key，用于临时邮箱能力

## 通知能力说明

### 邮件通知

如果你准备启用“邮件通知”，需要额外配置 SMTP。邮件通知与 Telegram、GPTMail 是独立链路，不能互相替代。

最少需要配置：

- `EMAIL_NOTIFICATION_SMTP_HOST`
- `EMAIL_NOTIFICATION_FROM`

常见可选配置：

- `EMAIL_NOTIFICATION_SMTP_PORT`
- `EMAIL_NOTIFICATION_SMTP_USERNAME`
- `EMAIL_NOTIFICATION_SMTP_PASSWORD`
- `EMAIL_NOTIFICATION_SMTP_USE_TLS`
- `EMAIL_NOTIFICATION_SMTP_USE_SSL`
- `EMAIL_NOTIFICATION_SMTP_TIMEOUT`

示例：

```env
EMAIL_NOTIFICATION_SMTP_HOST=smtp.qq.com
EMAIL_NOTIFICATION_SMTP_PORT=465
EMAIL_NOTIFICATION_FROM=your_account@qq.com
EMAIL_NOTIFICATION_SMTP_USERNAME=your_account@qq.com
EMAIL_NOTIFICATION_SMTP_PASSWORD=your_smtp_auth_code
EMAIL_NOTIFICATION_SMTP_USE_SSL=true
EMAIL_NOTIFICATION_SMTP_USE_TLS=false
EMAIL_NOTIFICATION_SMTP_TIMEOUT=15
```

注意：

- 设置页中的测试邮件遵循“先保存，再测试”
- 测试接口不会直接读取输入框临时值
- 系统只会读取已保存的 `email_notification_recipient`

### Telegram 推送

项目支持在设置页配置：

- `telegram_bot_token`
- `telegram_chat_id`
- `telegram_poll_interval`

当前版本中，Telegram 推送与业务邮件通知已经统一接入通知分发链路。

## 外部接口与邮箱池集成

如果你要把本项目接入注册机、脚本平台或其他自动化系统，当前推荐方式是受控外部接口：

- 路径前缀：`/api/external/*`
- 鉴权头：`X-API-Key`
- 邮箱池接口：`/api/external/pool/*`

当前外部接口支持：

- 单 Key 鉴权
- 多 Key 配置
- 按调用方限制邮箱范围
- 公网模式白名单与速率限制
- 可禁用原文读取、长轮询等高风险端点

注意：

- 旧匿名 `/api/pool/*` 已移除
- 生产环境建议开启受控公网模式并配置白名单

## 演示站点建议

如果你要公开一个演示站点给其他人访问，建议至少这样配置：

```env
LOGIN_PASSWORD=your-strong-password
ALLOW_LOGIN_PASSWORD_CHANGE=false
```

这样可以达到两个目的：

- 站点仍然可以登录
- 访客无法在“系统设置”里改掉后台登录密码

## 界面预览

当前仓库已包含部分截图，后续可以继续补充更多演示图片。

![仪表盘](img/仪表盘.png)
![邮箱界面](img/邮箱界面.png)
![提取验证码](img/提取验证码.png)
![设置界面](img/设置界面.png)

## 项目文档

- [文档总索引](./docs/INDEX.md)
- [注册与邮箱池接口文档](./docs/API/注册与邮箱池接口文档.md)
- [Registration Worker and Mail Pool API](./docs/API/registration-mail-pool-api.en.md)

如果你要对接注册机或批量工作流，优先看邮箱池和外部接口文档。

## 致谢

本项目基于以下技术与服务能力构建：

- Flask
- SQLite
- Microsoft Graph API
- IMAP
- APScheduler

也参考了以下项目的思路：

- [assast/outlookEmail](https://github.com/assast/outlookEmail)
- [gblaowang-i/MailAggregator_Pro](https://github.com/gblaowang-i/MailAggregator_Pro)

## 许可证

Apache License 2.0
