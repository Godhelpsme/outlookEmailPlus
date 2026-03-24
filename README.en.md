# Outlook Email Plus

[中文 README](./README.md)

OutlookMail Plus is a mailbox manager built for individuals and teams that work heavily with registration flows.

Unlike general-purpose email clients, it focuses on **registration and verification** workflows and is deeply optimized around getting those flows done quickly.

### Why OutlookMail Plus

- **Built for registration workflows**: it removes unnecessary steps as much as possible. You can copy mailbox addresses with one click; after sending a verification email on a signup page, you can return to the manager, click "Verification Code", fetch the latest email, and quickly extract the code or verification link with regex.
- **Lighter and more focused**: non-core features such as sending mail are intentionally left out, so the interface stays cleaner and every design choice is centered on completing registration tasks.
- **Broader import compatibility**: it supports mainstream mailbox providers such as Gmail, QQ, and 163, as well as custom IMAP servers. Self-hosted mailboxes also work. Built-in temp mailboxes help reduce privacy exposure.
- **Automation-friendly**: it exposes APIs for batch registration workflows, including mailbox claiming, verification-code retrieval, and mailbox release.
- **Third-party notifications**: third-party notification channels are supported. Telegram is already integrated, and important mailboxes can push alerts automatically.

In short, OutlookMail Plus is a mailbox manager designed specifically for registration workflows.

## Demo Site

Demo site: https://gbcoinystsyz.ap-southeast-1.clawcloudrun.com  
Login password: 12345678

There are 10 mailbox accounts provided for demonstration. Please do not delete them individually. Their content is periodically restored or reloaded. Do not treat them as your own accounts.

The demo covers most major features in this project, except email push. Telegram push is not enabled there because it requires additional configuration.

## UI Preview

The repository already includes some screenshots, and more can be added later.

![Dashboard](img/仪表盘.png)
![Mailbox View](img/邮箱界面.png)
![Verification Code Extraction](img/提取验证码.png)
![Settings](img/设置界面.png)

## Recent Updates

Highlights include:

- current stable version: `v1.9.2`
- a new compact mailbox mode for higher-density account operations with synchronized selection state
- a lightweight remark-edit flow that updates remarks through a dedicated `PATCH` endpoint without touching credentials
- richer temp-mail rendering with support for `cid:` inline images, data URLs, and remote image URLs
- more accurate refresh-failure suggestions that branch by Outlook OAuth vs. IMAP account type
- broader bilingual UI and more complete i18n coverage
- unified notification dispatch for business email notifications and Telegram delivery
- stronger external API controls with single-key, multi-key, allowlist, rate-limit, and dangerous-endpoint disable support
- mail-pool integrations consolidated under `/api/external/pool/*`
- removal of the old anonymous `/api/pool/*` endpoints
- a new demo-site guard that can prevent login password changes from the Settings page

## Core Capabilities

- Multi-mailbox management
  Supports Outlook OAuth, regular IMAP mailboxes, and GPTMail temp mailboxes
- Bulk import and organization
  Supports bulk import, tags, search, groups, and export
- Mail reading and extraction
  Supports verification-code extraction, link extraction, and raw message viewing
- Mail pool orchestration
  Supports claiming, releasing, completing, cooldown recovery, and stale-claim recycling
- Controlled external APIs
  Supports `X-API-Key` authentication, multiple consumer keys, mailbox scope restrictions, IP allowlists, and rate limits
- Notification delivery
  Supports business email notifications, Telegram push, and test sending
- Demo-site protection
  Supports locking the login-password change entry through environment variables so visitors cannot change the backend password from Settings

## Project Layout

```text
outlook_web/          Main Flask application (controllers / routes / services / repositories)
templates/            Page templates
static/               Frontend scripts and styles
data/                 SQLite data and runtime files
tests/                Automated tests
web_outlook_app.py    Backward-compatible entrypoint
```

## Quick Start

### Docker Deployment

```bash
docker pull guangshanshui/outlook-email-plus:v1.9.2
docker pull guangshanshui/outlook-email-plus:latest

docker run -d \
  --name outlook-email-plus \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -e SECRET_KEY=your-secret-key-here \
  -e LOGIN_PASSWORD=your-login-password \
  -e ALLOW_LOGIN_PASSWORD_CHANGE=false \
  guangshanshui/outlook-email-plus:v1.9.2
```

Notes:

- always mount `data/` to avoid losing the database and runtime data
- `SECRET_KEY` must stay stable and strong; a random 64-character value is recommended
- for production deployments, pin an explicit version tag such as `v1.9.2`; keep `latest` for quick evaluation

### Local Run

```bash
python -m venv .venv
pip install -r requirements.txt
python web_outlook_app.py
```

### Run Tests

```bash
python -m unittest discover -s tests -v
```

## Common Environment Variables

- `SECRET_KEY`
  Required for session security and sensitive-data encryption
- `LOGIN_PASSWORD`
  Initial backend login password; after first startup it is hashed and stored in the database
- `ALLOW_LOGIN_PASSWORD_CHANGE`
  Whether login password changes are allowed in Settings. For demo sites, set this to `false`
- `DATABASE_PATH`
  SQLite database path. Default: `data/outlook_accounts.db`
- `PORT` / `HOST`
  Web server bind address
- `SCHEDULER_AUTOSTART`
  Whether background scheduler jobs start automatically
- `OAUTH_CLIENT_ID`
  Outlook OAuth application ID
- `OAUTH_REDIRECT_URI`
  Outlook OAuth callback URL
- `GPTMAIL_BASE_URL`
  GPTMail service URL
- `GPTMAIL_API_KEY`
  GPTMail API key for temp-mail capabilities

## Notification Channels

### Email Notifications

If you want to enable business email notifications, you need to configure SMTP separately. Email notifications, Telegram, and GPTMail are independent channels and do not replace each other.

Minimum required variables:

- `EMAIL_NOTIFICATION_SMTP_HOST`
- `EMAIL_NOTIFICATION_FROM`

Common optional variables:

- `EMAIL_NOTIFICATION_SMTP_PORT`
- `EMAIL_NOTIFICATION_SMTP_USERNAME`
- `EMAIL_NOTIFICATION_SMTP_PASSWORD`
- `EMAIL_NOTIFICATION_SMTP_USE_TLS`
- `EMAIL_NOTIFICATION_SMTP_USE_SSL`
- `EMAIL_NOTIFICATION_SMTP_TIMEOUT`

Example:

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

Notes:

- the Settings page follows a save-first-then-test flow
- the test endpoint does not read temporary values from the form
- the system only uses the saved `email_notification_recipient`

### Telegram Push

The Settings page supports:

- `telegram_bot_token`
- `telegram_chat_id`
- `telegram_poll_interval`

In the current version, Telegram push and business email notifications are both handled by the unified notification-dispatch flow.

## External API and Mail Pool Integration

If you want to connect this project to registration workers, script platforms, or other automation systems, the recommended path is the controlled external API:

- path prefix: `/api/external/*`
- auth header: `X-API-Key`
- mail-pool endpoints: `/api/external/pool/*`

Current external API capabilities include:

- single-key authentication
- multi-key configuration
- mailbox scope restrictions per caller
- public-mode allowlists and rate limits
- the ability to disable risky endpoints such as raw-content reading and long polling

Notes:

- the old anonymous `/api/pool/*` endpoints have been removed
- in production, controlled public mode with allowlists is recommended

## Demo Site Recommendation

If you want to expose a demo site to other users, at minimum use:

```env
LOGIN_PASSWORD=your-strong-password
ALLOW_LOGIN_PASSWORD_CHANGE=false
```

- the site remains usable
- visitors cannot change the backend login password from Settings

## Project Documentation

- [中文注册与邮箱池接口文档](./注册与邮箱池接口文档.md)
- [Registration Worker and Mail Pool API](./registration-mail-pool-api.en.md)

If you plan to integrate registration workers or batch workflows, start with the mail-pool and external API docs.

## Acknowledgements

This project is built on:

- Flask
- SQLite
- Microsoft Graph API
- IMAP
- APScheduler

It also draws ideas from:

- [assast/outlookEmail](https://github.com/assast/outlookEmail)
- [gblaowang-i/MailAggregator_Pro](https://github.com/gblaowang-i/MailAggregator_Pro)

## License

Apache License 2.0
