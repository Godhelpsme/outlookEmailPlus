# Outlook Email Plus

Outlook Email Plus is a mailbox aggregation web app for registration, verification, and multi-account automation workflows. It brings Outlook OAuth mailboxes, IMAP mailboxes, GPTMail temp mailboxes, verification-code extraction, notifications, controlled external APIs, and mail-pool orchestration into one interface.

[中文 README](./README.md) | [English README](./README.en.md)

## What This Project Is

This is not just an inbox viewer.

It is better suited for workflows such as:

- maintaining large sets of mailboxes in one place
- reading registration codes, verification links, and notification emails automatically
- exposing mailbox resources to workers through a controlled mail pool
- running a public demo site without exposing high-risk settings to visitors

## Recent Updates

This README has been refreshed to match the latest functional changes, including:

- broader bilingual UI and i18n coverage
- unified notification dispatch for business email notifications and Telegram delivery
- hardened external API controls with single-key, multi-key, IP allowlists, rate limits, and risky-endpoint guards
- mail-pool integrations consolidated under `/api/external/pool/*`
- removal of the old anonymous `/api/pool/*` endpoints
- a new demo-site guard that can disable login password changes from Settings

## Core Capabilities

- Multi-mailbox management
  Supports Outlook OAuth, regular IMAP mailboxes, and GPTMail temp mailboxes
- Bulk import and organization
  Supports import, groups, tags, search, and export
- Mail reading and extraction
  Extract verification codes, links, and raw message content
- Mail pool orchestration
  Supports claim, release, complete, cooldown recovery, and stale-claim cleanup
- Controlled external APIs
  Supports `X-API-Key`, multiple consumer keys, scoped mailbox access, IP allowlists, and rate limiting
- Notification delivery
  Supports business email notifications, Telegram push, and test delivery from Settings
- Demo-site protection
  Lets you lock login-password changes at the site level with an environment variable

## Project Layout

```text
outlook_web/          Main Flask application (controllers / routes / services / repositories)
templates/            HTML templates
static/               Frontend scripts and styles
data/                 SQLite data and runtime files
tests/                Automated tests
web_outlook_app.py    Backward-compatible entrypoint
```

## Quick Start

### Docker

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

Notes:

- Always mount `data/` if you want persistent runtime data
- `SECRET_KEY` must be stable and strong
- For demo sites, explicitly set `ALLOW_LOGIN_PASSWORD_CHANGE=false`

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
  Required session and secret-encryption key
- `LOGIN_PASSWORD`
  Initial admin login password; it is stored in the database as a hash after initialization
- `ALLOW_LOGIN_PASSWORD_CHANGE`
  Whether the login password can be changed in Settings. Set this to `false` for demo sites
- `DATABASE_PATH`
  SQLite path, default `data/outlook_accounts.db`
- `PORT` / `HOST`
  Web bind address
- `SCHEDULER_AUTOSTART`
  Whether background scheduler jobs start automatically
- `OAUTH_CLIENT_ID`
  Outlook OAuth app ID
- `OAUTH_REDIRECT_URI`
  Outlook OAuth callback URL
- `GPTMAIL_BASE_URL`
  GPTMail service base URL
- `GPTMAIL_API_KEY`
  GPTMail API key for temp-mail features

## Notification Channels

### Email Notifications

If you want business email notifications, configure a dedicated SMTP service. This channel is independent from Telegram and GPTMail.

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

Important behavior:

- the Settings page follows a save-first-then-test flow
- the test endpoint does not read temporary form values
- the system only uses the persisted `email_notification_recipient`

### Telegram Delivery

The Settings page supports:

- `telegram_bot_token`
- `telegram_chat_id`
- `telegram_poll_interval`

In the current version, Telegram delivery and business email notifications are both handled through the unified notification-dispatch flow.

## External API and Mail Pool Integration

If you need to connect this project to registration workers or other automation systems, the recommended integration path is the controlled external API:

- path prefix: `/api/external/*`
- auth header: `X-API-Key`
- mail-pool endpoints: `/api/external/pool/*`

Current external API controls include:

- single-key authentication
- multi-key configuration
- mailbox scoping per consumer
- public-mode allowlists and rate limits
- optional disabling of raw-content and long-poll style risky endpoints

Notes:

- the old anonymous `/api/pool/*` endpoints are gone
- for production, enable controlled public mode and configure IP allowlists

## Demo Site Recommendation

If you want to expose a demo site to other users, start with at least this:

```env
LOGIN_PASSWORD=your-strong-password
ALLOW_LOGIN_PASSWORD_CHANGE=false
```

This keeps the site usable while preventing visitors from changing the admin login password in Settings.

## UI Preview

The repository already includes a few screenshots, and you can add more later as the UI evolves.

![Dashboard](img/仪表盘.png)
![Mailbox View](img/邮箱界面.png)
![Verification Code Extraction](img/提取验证码.png)
![Settings](img/设置界面.png)

## Project Documentation

- [Documentation Index](./docs/INDEX.md)
- [Registration Worker and Mail Pool API](./docs/API/registration-mail-pool-api.en.md)
- [中文注册与邮箱池接口文档](./docs/API/注册与邮箱池接口文档.md)

If you are integrating workers or batch workflows, start with the external API and mail-pool docs.

## Acknowledgements

This project builds on:

- Flask
- SQLite
- Microsoft Graph API
- IMAP
- APScheduler

It also draws inspiration from:

- [assast/outlookEmail](https://github.com/assast/outlookEmail)
- [gblaowang-i/MailAggregator_Pro](https://github.com/gblaowang-i/MailAggregator_Pro)

## License

Apache License 2.0
