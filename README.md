# Outlook Email Plus

一个用于统一管理 Outlook / IMAP 邮箱账号、读取邮件、提取验证码，并支持邮箱池调度的 Web 项目(or 注册机)。



## 项目优势

- 一套界面统一管理 Outlook OAuth 邮箱和 IMAP 邮箱(比如qq,gmail,163等等)，减少多套工具切换成本
- 不只是“收件箱查看器”，还覆盖验证码提取、链接提取、注册池流转这些高频自动化场景
- 支持批量导入、分组、标签、搜索，适合多账号长期维护
- 可本地快速启动，也可直接 Docker 部署，落地成本低
- 提供受控对外接口和邮箱池能力，方便和注册、验证、自动化脚本衔接

## 主要功能

- 多邮箱账号管理：支持批量导入、分组、标签、搜索
- Outlook OAuth 与 IMAP 接入：兼容多种邮箱提供商
- 邮件读取与验证码提取：支持常见注册、登录、验证场景
- 邮箱池管理：支持领取、释放、完成、状态流转
- 可选扩展能力：Telegram 推送、临时邮箱、受控对外 API

## 适用场景

- 统一维护多个 Outlook / IMAP 邮箱账号
- 批量处理注册验证码、验证链接、通知邮件
- 把邮箱账号接入邮箱池后，供外部任务领取和回收
- 在受控环境中把邮件能力提供给内部脚本或自动化系统

## 部署方式

### Docker 部署

```bash
docker pull ghcr.io/zeropointsix/outlook-email-plus:latest

docker run -d \
  --name outlook-email-plus \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -e SECRET_KEY=your-secret-key-here \
  -e LOGIN_PASSWORD=your-login-password \
  ghcr.io/zeropointsix/outlook-email-plus:latest
```

说明：

- 建议把 `data/` 挂载出来做持久化
- `SECRET_KEY` 请使用稳定且安全的值

### 本地部署

```bash
python -m venv .venv
pip install -r requirements.txt
python start.py
```

常用环境变量：

- `SECRET_KEY`：会话与敏感字段加密密钥
- `LOGIN_PASSWORD`：后台登录密码
- `DATABASE_PATH`：SQLite 数据库路径
- `OAUTH_CLIENT_ID`：Outlook OAuth 应用 ID
- `OAUTH_REDIRECT_URI`：Outlook OAuth 回调地址

## 界面预览

![仪表盘](img/仪表盘.png)
![邮箱界面](img/邮箱界面.png)
![提取验证码](img/提取验证码.png)
![设置界面](img/设置界面.png)

## 项目文档

- [注册与邮箱池接口文档](./注册与邮箱池接口文档.md)

如果你需要接入注册机之类的批量工作，请直接看上面的文档

## 感谢

本项目基于以下开源技术和服务能力构建：

- Flask
- SQLite
- Microsoft Graph API
- IMAP
- APScheduler

同时感谢以下参考项目提供的思路与启发：

- [assast/outlookEmail](https://github.com/assast/outlookEmail)
- [gblaowang-i/MailAggregator_Pro](https://github.com/gblaowang-i/MailAggregator_Pro)

## 许可证

Apache License 2.0
