# API 文档

## 对外开放 API

本文档对应当前项目已实现的 `/api/external/*` 只读接口。

适用范围：

- 本地化部署
- 单实例
- 单可信调用方
- 内网或受控访问环境

当前版本不建议直接公网暴露。原因见：

- `docs/BUG/BUG-00013-对外开放API公网暴露风险与可用性缺口.md`

如需机器可读规范，可同时参考：

- `docs/FD/OPENAPI-00008-对外验证码与邮件读取开放API.yaml`

## 一、接口创建结论

### 1.1 当前已创建的接口

当前 P0 范围内，对外功能接口已经落地，不再需要新增同类查询接口：

| 分类 | 方法 | 路径 | 状态 | 说明 |
|------|------|------|------|------|
| Messages | `GET` | `/api/external/messages` | 已创建 | 获取邮件列表 |
| Messages | `GET` | `/api/external/messages/latest` | 已创建 | 获取最新匹配邮件 |
| Messages | `GET` | `/api/external/messages/{message_id}` | 已创建 | 获取邮件详情 |
| Messages | `GET` | `/api/external/messages/{message_id}/raw` | 已创建 | 获取邮件 RAW 内容 |
| Verification | `GET` | `/api/external/verification-code` | 已创建 | 提取最新验证码 |
| Verification | `GET` | `/api/external/verification-link` | 已创建 | 提取最新验证链接 |
| Verification | `GET` | `/api/external/wait-message` | 已创建 | 等待新邮件到达（支持 sync/async） |
| Verification | `GET` | `/api/external/probe/<probe_id>` | 已创建（v1.2） | 查询异步探测状态 |
| System | `GET` | `/api/external/health` | 已创建 | 外部健康检查 |
| System | `GET` | `/api/external/capabilities` | 已创建 | 查询开放能力 |
| System | `GET` | `/api/external/account-status` | 已创建 | 查询邮箱账号状态 |

### 1.2 配套但不是新建开放接口的后台接口

以下接口用于管理员配置 `external_api_key`，属于现有后台接口扩展，不属于开放接口本身：

| 方法 | 路径 | 登录要求 | 说明 |
|------|------|----------|------|
| `GET` | `/api/settings` | 需要后台登录 | 返回 `external_api_key_set`、`external_api_key_masked` |
| `PUT` | `/api/settings` | 需要后台登录 | 保存或清空 `external_api_key` |

### 1.3 当前不建议继续新增的接口

P0 阶段不建议再新增以下业务接口：

- 邮件删除、标记已读、移动邮件等写接口
- 附件下载、附件元数据开放接口
- Webhook / 回调通知接口
- 多调用方 API Key 管理接口

原因是当前目标是“受控私有接入闭环”，不是开放平台化扩张。

### 1.4 后续阶段可能补充的能力

后续如果进入 P1/P2，可优先补的是能力控制，而不是继续堆新路径：

| 阶段 | 类型 | 是否已定义为独立接口 | 说明 |
|------|------|----------------------|------|
| P1 | 公网模式、IP 白名单、限流 | 已实现（v1.1） | 安全守卫层 `external_api_guard.py` |
| P1 | 高风险接口禁用（raw/wait-message） | 已实现（v1.1） | 设置页可动态开关 |
| P2 | `wait-message` 异步探测解耦 | 已实现（v1.2） | `mode=async` + `/api/external/probe/<id>` |
| P2 | 多 API Key / 范围授权 | 否 | 优先落在设置与鉴权模型，不急于新增公开路径 |

结论：

- **当前需要创建的核心开放接口：无。**
- **当前需要补齐的是正式接口文档与后续阶段边界说明。**

## 二、通用规则

### 2.1 Base URL

本地开发：

```text
http://localhost:5000
```

生产部署：

```text
https://your-domain.example.com
```

### 2.2 鉴权方式

所有 `/api/external/*` 接口统一使用请求头：

```http
X-API-Key: your-api-key
```

限制：

- 仅支持 Header 中的 `X-API-Key`
- 不支持 query 参数中的 `api_key`
- 未配置 `external_api_key` 时，统一返回 `403 API_KEY_NOT_CONFIGURED`

### 2.2.1 P1 公网安全层（v1.1 新增）

在 API Key 鉴权之后，额外叠加以下安全控制。**仅在"公网模式"开启时生效**，默认关闭（与 P0 行为完全一致）。

| 配置项 | 键名 | 默认值 | 说明 |
|--------|------|--------|------|
| 公网模式 | `external_api_public_mode` | `false` | 开启后激活 IP 白名单、限流、功能禁用 |
| IP 白名单 | `external_api_ip_whitelist` | `[]` | JSON 数组，支持精确 IP 和 CIDR（如 `192.168.0.0/16`）；为空则不限制 |
| 限流阈值 | `external_api_rate_limit_per_minute` | `60` | 每 IP 每分钟最大请求数 |
| 禁用 raw | `external_api_disable_raw_content` | `false` | 禁止 `/messages/{id}/raw` 端点 |
| 禁用 wait-message | `external_api_disable_wait_message` | `false` | 禁止 `/wait-message` 端点 |

在设置页 → 对外开放 API → 🛡️ 公网安全配置 中可动态修改，无需重启。

### 2.3 通用成功响应

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {}
}
```

### 2.4 通用失败响应

```json
{
  "success": false,
  "code": "INVALID_PARAM",
  "message": "参数错误",
  "data": null
}
```

### 2.5 通用错误码

| 错误码 | HTTP 状态码 | 含义 |
|--------|-------------|------|
| `UNAUTHORIZED` | `401` | 未提供或提供了错误的 `X-API-Key` |
| `API_KEY_NOT_CONFIGURED` | `403` | 系统未配置对外 API Key |
| `INVALID_PARAM` | `400` | 参数不合法 |
| `ACCOUNT_NOT_FOUND` | `404` | 指定邮箱账号不存在 |
| `MAIL_NOT_FOUND` | `404` | 未找到匹配邮件 |
| `VERIFICATION_CODE_NOT_FOUND` | `404` | 未找到验证码 |
| `VERIFICATION_LINK_NOT_FOUND` | `404` | 未找到验证链接 |
| `PROXY_ERROR` | `502` | 代理连接失败 |
| `UPSTREAM_READ_FAILED` | `502` | Graph / IMAP 均读取失败 |
| `INTERNAL_ERROR` | `500` | 服务内部错误 |
| `IP_NOT_ALLOWED` | `403` | 当前 IP 不在白名单中（公网模式） |
| `FEATURE_DISABLED` | `403` | 功能在公网模式下已禁用 |
| `RATE_LIMIT_EXCEEDED` | `429` | 请求频率超限（公网模式） |

### 2.6 通用查询参数

大多数邮件类接口共用以下参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `email` | string | 是 | 无 | 目标邮箱地址 |
| `folder` | string | 否 | `inbox` | `inbox` / `junkemail` / `deleteditems` |
| `from_contains` | string | 否 | 空 | 发件人模糊匹配 |
| `subject_contains` | string | 否 | 空 | 主题模糊匹配 |
| `since_minutes` | int | 否 | 视接口而定 | 最近 N 分钟内邮件 |

分页相关参数仅 `messages` 使用：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `skip` | int | 否 | `0` | 跳过条数，必须 `>=0` |
| `top` | int | 否 | `20` | 返回条数，范围 `1-50` |

### 2.7 接口版本与兼容策略

当前对外接口未单独引入 `/v1` 前缀，当前文档默认描述的是：

- **P0 受控私有接入版本**
- 路径基线统一为 `/api/external/*`

兼容策略如下：

1. **优先字段扩展，不轻易改路径**
   - P1 / P2 优先通过新增响应字段增强能力
   - 不轻易修改现有接口 URL
2. **保持响应主结构稳定**
   - 统一保持 `success / code / message / data`
   - 调用方不应依赖未文档化的内部字段
3. **破坏性变更才进入新版本**
   - 若后续必须改变鉴权方式、主响应结构或请求语义，建议新增 `/api/external/v2/*`
4. **当前高风险接口不承诺长期不变**
   - `/api/external/wait-message`
   - `/api/external/messages/{message_id}/raw`
   - 这两个接口在进入公网模式时可能被限制、降级或替换

### 2.8 后续接口演进原则

为了避免接口碎片化，后续演进默认遵循以下原则：

1. **P1 优先增强现有接口字段，不优先新增路径**
   - `health` 增加真实探测结果
   - `capabilities` 增加当前模式与限制信息
   - `account-status` 增加探测摘要
2. **P1 的安全治理优先放在安全层，而不是业务接口层**
   - 公网模式
   - IP 白名单
   - 限流
   - 高风险接口分级
3. **P2 只有在同步模型无法满足要求时，才考虑新增异步接口**
   - `wait-message` 优先内部解耦
   - 不默认承诺新增异步公开路径

## 三、快速示例

### 3.1 健康检查

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:5000/api/external/health"
```

### 3.2 读取邮件列表

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:5000/api/external/messages?email=user@outlook.com&folder=inbox&top=10"
```

### 3.3 提取验证码

```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:5000/api/external/verification-code?email=user@outlook.com&subject_contains=verify&since_minutes=10"
```

## 四、Messages 类接口

### 4.1 `GET /api/external/messages`

用途：获取指定邮箱的邮件列表。

附加参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `skip` | int | 否 | `0` | 分页偏移 |
| `top` | int | 否 | `20` | 返回数量，范围 `1-50` |

成功响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "emails": [
      {
        "id": "msg-1",
        "email_address": "user@outlook.com",
        "from_address": "noreply@example.com",
        "subject": "Your verification code",
        "content_preview": "Your code is 123456",
        "has_html": false,
        "timestamp": 1772961600,
        "created_at": "2026-03-08T12:00:00Z",
        "is_read": false,
        "method": "Graph API"
      }
    ],
    "count": 1,
    "has_more": false
  }
}
```

### 4.2 `GET /api/external/messages/latest`

用途：获取符合筛选条件的最新一封邮件。

成功响应中的 `data` 即单条 `MessageSummary`：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "id": "msg-new",
    "email_address": "user@outlook.com",
    "from_address": "noreply@example.com",
    "subject": "Target mail",
    "content_preview": "Your code is 123456",
    "has_html": false,
    "timestamp": 1772961600,
    "created_at": "2026-03-08T12:00:00Z",
    "is_read": false,
    "method": "Graph API"
  }
}
```

### 4.3 `GET /api/external/messages/{message_id}`

用途：获取单封邮件详情。

路径参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message_id` | string | 是 | 邮件 ID |

说明：

- 该接口仍需通过 query 参数传入 `email`
- `folder` 为可选提示参数，默认 `inbox`

成功响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "id": "msg-1",
    "email_address": "user@outlook.com",
    "from_address": "noreply@example.com",
    "to_address": "user@outlook.com",
    "subject": "Your verification code",
    "content": "Your code is 123456",
    "html_content": "<p>Your code is 123456</p>",
    "raw_content": "RAW MIME CONTENT",
    "timestamp": 1772961600,
    "created_at": "2026-03-08T12:00:00Z",
    "has_html": true,
    "method": "Graph API"
  }
}
```

### 4.4 `GET /api/external/messages/{message_id}/raw`

用途：只返回邮件 RAW 内容，便于编码和解析排查。

成功响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "id": "msg-1",
    "email_address": "user@outlook.com",
    "raw_content": "MIME-Version: 1.0\r\nraw test",
    "method": "Graph API"
  }
}
```

注意：

- 该接口返回高敏感原始内容
- 当前仅建议在受控私有环境下使用
- 若未来进入公网模式，该接口应作为默认受限接口处理

> **⚠️ 安全风险说明**
>
> `/api/external/messages/{message_id}/raw` 返回未经过滤的邮件原始内容（完整 MIME 正文），可能包含敏感信息、附件二进制数据或恶意脚本。
>
> **当前版本定位**：仅面向受控私有接入场景（单实例、单可信调用方、内网部署）。
>
> **风险点**：
> - 原始内容无字段级脱敏，调用方须自行处理展示安全
> - 当前无独立的访问频率限制
> - 若部署在公网，该接口应优先禁用或加入 IP 白名单保护（P1 计划）

## 五、Verification 类接口

### 5.1 `GET /api/external/verification-code`

用途：从符合条件的最新邮件中提取验证码。

附加参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `code_length` | string | 否 | 空 | 例如 `4-8` 或 `6-6` |
| `code_regex` | string | 否 | 空 | 自定义验证码正则 |
| `code_source` | string | 否 | `all` | `subject` / `content` / `html` / `all` |

特别说明：

- 未显式传入 `since_minutes` 时，该接口默认只扫描最近 `10` 分钟的邮件

成功响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "verification_code": "123456",
    "verification_link": "",
    "links": [],
    "formatted": "123456",
    "match_source": "content",
    "confidence": "high",
    "email": "user@outlook.com",
    "matched_email_id": "msg-1",
    "from": "noreply@example.com",
    "subject": "Your verification code",
    "received_at": "2026-03-08T12:00:00Z",
    "method": "Graph API"
  }
}
```

失败场景：

- 没有命中邮件：`404 MAIL_NOT_FOUND`
- 命中邮件但未提取到验证码：`404 VERIFICATION_CODE_NOT_FOUND`

### 5.2 `GET /api/external/verification-link`

用途：从符合条件的最新邮件中提取验证链接。

特别说明：

- 未显式传入 `since_minutes` 时，该接口默认只扫描最近 `10` 分钟的邮件

成功响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "verification_code": "",
    "verification_link": "https://example.com/verify?token=abc",
    "links": [
      "https://example.com/verify?token=abc"
    ],
    "formatted": "https://example.com/verify?token=abc",
    "confidence": "high",
    "email": "user@outlook.com",
    "matched_email_id": "msg-1",
    "from": "noreply@example.com",
    "subject": "Please verify your email",
    "received_at": "2026-03-08T12:00:00Z",
    "method": "Graph API"
  }
}
```

失败场景：

- 没有命中邮件：`404 MAIL_NOT_FOUND`
- 命中邮件但未提取到验证链接：`404 VERIFICATION_LINK_NOT_FOUND`

### 5.3 `GET /api/external/wait-message`

用途：在超时时间内轮询等待符合条件的新邮件到达。

附加参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `timeout_seconds` | int | 否 | `30` | 取值范围 `1-120` |
| `poll_interval` | int | 否 | `5` | 轮询间隔，必须大于 `0` 且不超过 `timeout_seconds` |
| `mode` | string | 否 | `sync` | `sync` = 阻塞等待（P0），`async` = 创建探测任务（P2） |

#### 同步模式（`mode=sync`，默认）

行为说明：

- 只返回调用开始后到达的新邮件
- 不会立即返回历史旧邮件
- 当前实现为同步轮询，请求线程会被占用

成功响应：结构与 `GET /api/external/messages/latest` 一致

失败场景：

- 超时未命中：`404 MAIL_NOT_FOUND`
- `timeout_seconds` 超限：`400 INVALID_PARAM`

#### 异步模式（`mode=async`，v1.2 新增）

行为说明：

- 立即返回 `202` + `probe_id`，不阻塞请求线程
- 后台 worker 每 5 秒轮询一次，匹配到新邮件后写入缓存
- 调用方通过 `GET /api/external/probe/<probe_id>` 查询结果

成功响应（`202`）：

```json
{
  "success": true,
  "code": "OK",
  "data": {
    "probe_id": "abc123...",
    "status": "pending",
    "expires_at": "2026-03-11T15:00:00Z",
    "poll_url": "/api/external/probe/abc123..."
  }
}
```

> **⚠️ 安全风险说明**
>
> 同步模式下，请求线程在等待期间被独占（最长 120 秒）。
> 推荐在高并发或公网场景使用 `mode=async` 避免线程耗尽。
> 公网模式（P1）下可通过设置禁用此端点。

### 5.4 `GET /api/external/probe/<probe_id>`（v1.2 新增）

用途：查询异步探测任务的状态与结果。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `probe_id` | string (path) | 是 | 由 `wait-message?mode=async` 返回 |

探测状态：

| 状态 | 含义 |
|------|------|
| `pending` | 后台正在轮询，尚未命中 |
| `matched` | 已命中新邮件，`message` 字段包含邮件数据 |
| `timeout` | 等待超时，未匹配到邮件 |
| `error` | 轮询过程中发生错误 |

成功响应（`matched`）：

```json
{
  "success": true,
  "code": "OK",
  "data": {
    "probe_id": "abc123...",
    "email": "user@outlook.com",
    "status": "matched",
    "created_at": "...",
    "expires_at": "...",
    "message": { ... }
  }
}
```

失败场景：`404 MAIL_NOT_FOUND`（probe_id 不存在）

## 六、System 类接口

### 6.1 `GET /api/external/health`

用途：检查外部接口、服务进程和数据库是否基本可用。

成功响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "status": "ok",
    "service": "outlook-email-plus",
    "version": "0.1.0-draft",
    "server_time_utc": "2026-03-08T12:00:00Z",
    "database": "ok"
  }
}
```

注意：

- 该接口当前偏向“服务与数据库存活”
- 不代表上游 Graph / IMAP 一定真实可读

### 6.2 `GET /api/external/capabilities`

用途：返回当前实例对外开放的能力清单。

成功响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "service": "outlook-email-plus",
    "version": "0.1.0-draft",
    "features": [
      "message_list",
      "message_detail",
      "raw_content",
      "verification_code",
      "verification_link",
      "wait_message"
    ]
  }
}
```

### 6.3 `GET /api/external/account-status`

用途：检查指定邮箱账号是否存在，以及基础可读条件是否满足。

参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `email` | string | 是 | 目标邮箱地址 |

成功响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "email": "user@outlook.com",
    "exists": true,
    "account_type": "outlook",
    "provider": "outlook",
    "group_id": 1,
    "status": "active",
    "last_refresh_at": null,
    "preferred_method": "graph",
    "can_read": true
  }
}
```

注意：

- `can_read=true` 仅表示基础配置字段存在
- 不等于已经完成真实拉信探测

## 七、管理员配置接口说明

### 7.1 `GET /api/settings`

用途：管理员登录后查看当前系统设置。

与开放 API 相关的返回字段：

| 字段 | 说明 |
|------|------|
| `external_api_key_set` | 是否已配置开放 API Key |
| `external_api_key_masked` | 脱敏后的 Key 展示值 |

### 7.2 `PUT /api/settings`

用途：管理员登录后保存系统设置。

与开放 API 相关的请求字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `external_api_key` | string | 设置新的开放 API Key；传空字符串表示清空 |

说明：

- 配置写入后不会明文回显
- 实际存储会走现有敏感配置加密逻辑

## 八、接入建议

推荐接入顺序：

1. 管理员登录后台，通过 `/api/settings` 配置 `external_api_key`
2. 调用 `/api/external/health` 检查基础可用性
3. 调用 `/api/external/account-status?email=...` 确认目标邮箱存在
4. 视业务选择 `/messages`、`/verification-code`、`/verification-link`
5. 仅在受控场景下使用 `/wait-message` 与 `/raw`

## 九、已知限制

- 当前仅适合受控私有接入，不建议直接公网暴露
- 当前只有单 `external_api_key`，默认具备读取本实例全部已配置邮箱的能力边界
- `wait-message` 为同步轮询实现，不适合高并发公网场景
- `/api/external/health` 与 `/api/external/account-status` 当前仍偏轻量，不等价于真实上游探测

## 十、当前接口问题与处理口径

下面这些不是“代码 Bug 列表”，而是调用方在使用接口时必须理解的当前接口问题。

### 10.1 `message_id` 不能单独定位账号

现状：

- `GET /api/external/messages/{message_id}`
- `GET /api/external/messages/{message_id}/raw`

仍然要求同时传 `email` 查询参数。

原因：

- 当前 `message_id` 的定位仍依赖邮箱上下文
- 系统没有建立“全局 message_id 到账号”的索引层

处理口径：

- 当前保留 `?email=...` 作为必填上下文
- P0/P1 不为此单独新增查询接口
- 如未来确实需要全局消息索引，再考虑在新版本中调整

### 10.2 `health` 与 `account-status` 当前是轻量自检，不是真实探测

现状：

- `/api/external/health` 主要反映服务和数据库是否存活
- `/api/external/account-status` 主要反映账号是否存在、基础配置是否完整

问题：

- 它们不能证明 Graph / IMAP 在当前时刻一定可读

处理口径：

- 当前文档明确按“轻量自检”解释这两个接口
- P1 优先扩展字段，不优先新增同类接口

### 10.3 `/raw` 接口敏感度高

现状：

- `/api/external/messages/{message_id}/raw` 可返回原始邮件内容

问题：

- 原始内容可能包含完整 MIME、头信息、HTML 或调试用敏感内容

处理口径：

- 当前仅建议在受控私有环境下使用
- 未来进入公网模式时，该接口默认应视为受限接口

### 10.4 `wait-message` 成本高

现状：

- `/api/external/wait-message` 使用同步轮询
- 请求线程会在超时窗口内被占用

问题：

- 对单 worker 或低并发部署不友好
- 不适合作为长期公网高并发能力

处理口径：

- 当前允许在受控环境下保留
- P1 若进入公网模式，应优先禁用或限制
- P2 再考虑是否替换为异步模型

### 10.5 单 API Key 权限边界较粗

现状：

- 当前只有一个 `external_api_key`
- 默认可读取本实例全部已配置邮箱

问题：

- 不适合多调用方或复杂权限边界

处理口径：

- 当前仅按单可信调用方场景验收
- P2 再做多 API Key 和范围授权

## 十一、后续阶段接口文档预留

本节用于说明后续如果进入 P1/P2，接口文档应优先怎么演进。

### 11.1 P1：优先扩展现有接口字段

#### `GET /api/external/health`

建议后续增加但当前不承诺的字段：

| 字段 | 含义 |
|------|------|
| `upstream_probe_ok` | 上游读取链路最近一次探测是否成功 |
| `last_probe_at` | 最近一次探测时间 |
| `last_probe_error` | 最近一次探测错误摘要 |
| `public_mode` | 当前是否处于公网模式 |

#### `GET /api/external/capabilities`

建议后续增加但当前不承诺的字段：

| 字段 | 含义 |
|------|------|
| `public_mode` | 当前模式是否为公网模式 |
| `restricted_features` | 当前被限制的接口能力 |
| `rate_limit_enabled` | 是否已启用限流 |

#### `GET /api/external/account-status`

建议后续增加但当前不承诺的字段：

| 字段 | 含义 |
|------|------|
| `upstream_probe_ok` | 最近一次真实读取探测结果 |
| `probe_method` | 探测所使用的读取方式 |
| `last_probe_at` | 最近探测时间 |
| `last_probe_error` | 最近探测错误摘要 |

### 11.2 P1：优先新增控制字段，不优先新增业务路径

P1 更推荐补的是控制能力，而不是新增更多邮件接口：

- 公网模式开关
- 来源 IP 白名单
- 限流
- `/wait-message` 与 `/raw` 的接口分级

这些能力默认应体现在：

- 安全层
- 系统能力说明字段
- 部署文档

而不是优先新增新的业务 URL。

### 11.3 P2：只有在必要时才考虑新接口

如果 P2 阶段必须引入新的公开接口，建议优先满足以下条件：

1. 现有同步接口已无法满足并发或稳定性要求
2. 仅通过扩展字段无法表达新能力
3. 新接口语义清晰，且不会和现有路径混淆

当前不提前承诺新增以下路径：

- 异步等待接口
- 多调用方管理接口
- 配额管理接口

如果未来必须新增，建议进入新版本或新增专门的管理域，而不是继续把所有能力堆在 `/api/external/*` 主业务路径下。
