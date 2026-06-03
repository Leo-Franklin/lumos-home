# 用户注册登录与密码重置设计

**日期**：2026-05-22
**状态**：已批准

---

## 1. 概述

将当前单管理员账户（环境变量配置）扩展为完整的多用户认证系统，支持邮箱注册、邮箱验证、登录（Remember Me）、忘记密码/重置密码。

### 核心需求

- 用户通过邮箱 + 密码注册，系统发送验证链接
- 注册后邮箱需验证才可登录
- 支持"记住我"（30 天有效期）
- 忘记密码时通过邮件重置（15 分钟有效）

### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 邮件服务 | Resend | 免费 100 封/天，API 友好，开发者默认域名可用 |
| Token 存储 | SQLite 数据库 | 现有架构，复用 aiosqlite，无需额外服务 |
| 密码哈希 | bcrypt（已存在） | passlib 已集成 |
| JWT | HS256（已存在） | auth.py 已实现 |

---

## 2. 数据模型

### 2.1 User 表（替代环境变量单管理员）

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 0,   -- 邮箱验证后才可登录
    is_superuser BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

**迁移说明**：
- 首次启动时，如果 `users` 表为空，自动从环境变量 `ADMIN_USERNAME`/`ADMIN_PASSWORD` 创建一个 superuser（向后兼容）
- 后续新建用户一律通过注册流程

### 2.2 EmailVerificationToken 表

```sql
CREATE TABLE email_verification_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL
);
```

- Token 有效期：24 小时
- 用户点击验证链接后，删除 Token，置 `is_active = 1`

### 2.3 PasswordResetToken 表

```sql
CREATE TABLE password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL
);
```

- Token 有效期：15 分钟
- 使用后立即删除

---

## 3. API 设计

### 3.1 注册

**POST `/api/v1/auth/register`**

Request：
```json
{
    "email": "user@example.com",
    "password": "StrongPass123!"
}
```

Response（201）：
```json
{
    "message": "Verification email sent. Please check your inbox.",
    "email": "user@example.com"
}
```

**业务逻辑**：
1. 验证邮箱格式、密码强度（至少 8 字符）
2. 检查邮箱是否已注册
3. bcrypt 哈希密码
4. 创建 User（`is_active=0`）
5. 生成 24 小时有效的验证 Token（UUID）
6. 发送验证邮件（Resend）

### 3.2 邮箱验证

**POST `/api/v1/auth/verify-email`**

Request：
```json
{
    "token": "550e8400-e29b-41d4-a716-446655440000"
}
```

Response（200）：
```json
{
    "message": "Email verified. You can now login."
}
```

**业务逻辑**：
1. 查找 Token，未过期则继续
2. 找到对应 User，置 `is_active = 1`
3. 删除 Token
4. 返回成功

### 3.3 登录

**POST `/api/v1/auth/login`**

Request：
```json
{
    "email": "user@example.com",
    "password": "StrongPass123!",
    "remember_me": true
}
```

Response（200）：
```json
{
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 2592000  -- 30 days if remember_me=true, else 86400 (24h)
}
```

**业务逻辑**：
1. 查找 User（按 email）
2. 验证 `is_active == 1`，否则拒绝（提示去验证邮箱）
3. bcrypt 验证密码
4. JWT 签发：`expires_hours = 720`（30 天）如果 `remember_me=true`，否则 `24`
5. 返回 Token

### 3.4 忘记密码 - 请求重置

**POST `/api/v1/auth/forgot-password`**

Request：
```json
{
    "email": "user@example.com"
}
```

Response（200）：
```json
{
    "message": "If that email exists, a reset link has been sent."
}
```

**业务逻辑**：
1. 根据 email 查找 User（不论是否存在，均返回相同消息，防止用户枚举）
2. 如果存在，生成 15 分钟有效的 PasswordResetToken
3. 发送重置邮件（内嵌链接）

### 3.5 重置密码

**POST `/api/v1/auth/reset-password`**

Request：
```json
{
    "token": "550e8400-e29b-41d4-a716-446655440000",
    "new_password": "NewStrongPass123!"
}
```

Response（200）：
```json
{
    "message": "Password reset successful. Please login with your new password."
}
```

**业务逻辑**：
1. 查找 Token，未过期则继续
2. 找到对应 User，更新 `password_hash`
3. 删除 Token
4. 返回成功

---

## 4. 邮件模板

### 4.1 邮箱验证邮件

**Subject**：`Verify your email - Smart Home`

**Body**：
```
Hi,

Please click the link below to verify your email address:

{verify_email_url}?token={token}

This link expires in 24 hours.

If you didn't create an account, please ignore this email.
```

### 4.2 密码重置邮件

**Subject**：`Reset your password - Smart Home`

**Body**：
```
Hi,

You requested a password reset. Click the link below to set a new password:

{reset_password_url}?token={token}

This link expires in 15 minutes.

If you didn't request this, please ignore this email.
```

---

## 5. 环境变量

新增以下配置项：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RESEND_API_KEY` | — | Resend API Key（必填） |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` | 发件人邮箱 |
| `APP_BASE_URL` | `http://localhost:8000` | 用于生成邮件链接，生产环境需修改 |

---

## 6. 错误处理

| 场景 | HTTP 状态码 | 错误信息 |
|------|-------------|----------|
| 邮箱已注册 | 400 | Email already registered |
| 无效 Token | 400 | Invalid or expired token |
| Token 已使用 | 400 | Token already used |
| 用户未激活 | 403 | Please verify your email first |
| 邮箱/密码错误 | 401 | Invalid email or password |
| 邮件发送失败 | 500 | Failed to send email（内部记录日志，不暴露给用户） |

---

## 7. 安全考量

1. **Token 随机性**：使用 UUID v4 作为 Token
2. **密码强度**：后端校验至少 8 字符
3. **防止用户枚举**：忘记密码接口无论账号是否存在均返回相同响应
4. **邮件链接有效期短**：验证 24 小时，重置 15 分钟
5. **Token 一次性**：使用后立即删除
6. **JWT 短期 Token**：即使 remember_me 也仅 30 天，到期需重新登录
7. **CORS**：复用现有 CORS 配置

---

## 8. 目录结构

```
app/
├── models/
│   ├── user.py              # 新增 User 模型
│   ├── verification_token.py # 新增 EmailVerificationToken 模型
│   └── password_reset_token.py # 新增 PasswordResetToken 模型
├── schemas/
│   └── auth.py              # 新增注册/登录/重置的 Pydantic Schema
├── services/
│   └── email.py             # 新增 Resend 邮件服务
├── api/
│   └── auth.py              # 新增注册/登录/验证/忘记密码/重置接口
├── auth.py                  # 复用（hash_password/verify_password/create_access_token）
├── deps.py                  # 调整（get_current_user 支持新模型）
├── config.py                # 新增 RESEND_API_KEY, RESEND_FROM_EMAIL, APP_BASE_URL
└── main.py                  # 注册新路由
```

---

## 9. 待确认事项

- [x] 邮件服务：Resend
- [x] 注册方式：邮箱 + 密码
- [x] 第三方登录：不需要
- [x] 重置链接有效期：15 分钟
- [x] Token 存储：数据库
- [x] Remember Me 有效期：30 天
- [x] 发件人域名：Resend 默认域名
- [x] 重置链接方式：邮件内嵌链接
- [x] 设计方案：方案 A（扩展现有架构）
