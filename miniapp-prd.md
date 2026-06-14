# 微信小程序改造需求文档草案

## 1. 项目建议与目标

将当前“朋友结伴出游记账管理网站”改造成微信小程序，首版采用 **uni-app + Vue** 开发小程序端，继续复用现有 Django 后端核心业务能力。

首版目标：

- 用户通过微信进入小程序并登录。
- 用户可创建出行、添加成员、记录账单、查看分摊汇总和结算建议。
- 小程序端完整迁移现有 Web 端核心功能，不做票据 OCR、真实支付、好友系统、多币种汇率等扩展。
- 微信账号与现有账号体系暂时独立，不做旧账号绑定。

推荐路线：

- 前端：新增 uni-app 小程序端，而不是直接改造当前 Vue + Vite Web 端。
- 后端：保留 Django 业务模型和 API，新增微信登录接口与小程序请求适配。
- 当前 Web 端可保留，作为管理/演示端继续使用。

## 2. 当前项目现状

现有项目结构：

- 后端：Django 5，业务集中在 `backend/trips`。
- 前端：Vue 3 + Vite，核心页面集中在单个 `frontend/src/App.vue`。
- 认证：当前使用 Django session 登录。
- API：当前为手写 JSON API，接口已覆盖注册、登录、出行、成员、账单、汇总、结算。
- 数据模型：已有 `Trip`、`TripMember`、`Expense`、`ExpenseSplit`、`Settlement`。
- 验证：已有 `backend/verify_travel_api.py` 用于验证核心账单和结算流程。

迁移前建议先处理：

- 统一中文文案和文档编码，当前 README、MVP 文档、部分前后端中文字符串存在乱码风险。
- 将 API 错误信息、状态文案整理成稳定中文，方便小程序复用。
- 明确生产环境域名、HTTPS、微信小程序合法请求域名配置。实施时参考微信官方文档：[网络能力](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)、[wx.login](https://developers.weixin.qq.com/miniprogram/dev/api/open-api/login/wx.login.html)、[code2Session](https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html)。

## 3. 小程序功能需求

### 3.1 登录与用户

- 用户首次进入小程序时，使用微信登录。
- 小程序调用 `wx.login` 获取 `code`，发送给 Django 后端。
- 后端通过微信 `code2Session` 换取 `openid`，创建或读取独立微信用户。
- 首版不要求绑定现有账号密码用户。
- 登录成功后，小程序本地保存后端返回的登录凭证或会话标识。

### 3.2 首页：我的出行

- 展示当前微信用户创建或参与的出行列表。
- 每个出行卡片展示：
  - 出行名称
  - 地点
  - 日期范围
  - 成员数
  - 账单数
  - 总金额
  - 状态：草稿、未出发、进行中、已结束
- 支持创建新出行。
- 支持进入出行详情。

### 3.3 出行详情

详情页包含四个核心区域：

- 概览：总花费、人均花费、成员数、账单数。
- 成员：成员列表、添加临时成员、删除未产生账单关联的成员。
- 账单：账单列表、添加账单、删除账单。
- 结算：成员汇总、应收/应补金额、结算建议、标记结清。

### 3.4 出行管理

- 创建出行字段：
  - 名称，必填
  - 地点
  - 开始日期
  - 结束日期
  - 币种，默认 CNY
  - 备注
- 编辑出行字段同创建字段。
- 删除出行时二次确认，删除后同步删除相关账单和结算记录。

### 3.5 成员管理

- 默认创建者自动成为出行成员。
- 支持添加临时昵称成员。
- 首版不强制同行人注册或微信登录。
- 已参与付款或分摊的成员不能删除。
- 出行创建者拥有成员管理权限。

### 3.6 账单记录

- 添加账单字段：
  - 金额，必填且大于 0
  - 付款人，必选
  - 消费日期，默认今天
  - 分类，默认“其他”
  - 说明
  - 参与分摊成员，至少选择 1 人
- 首版使用平均分摊。
- 删除账单后自动刷新汇总和结算建议。
- 首版可以不做账单编辑；如保留现有 Web 能力，则小程序也可加入编辑入口。

### 3.7 汇总与结算

- 展示总花费、人均花费。
- 展示每个成员：
  - 已付款金额
  - 应分摊金额
  - 净额
  - 应收/应补/已平
- 自动生成结算建议：
  - 应补成员向应收成员转账。
  - 支持标记某条结算已结清或未结清。
- 首版不接入微信支付真实转账。

## 4. 后端改造需求

### 4.1 新增微信登录能力

新增接口：

- `POST /api/auth/wechat-login/`

请求示例：

```json
{
  "code": "wx.login 返回的 code"
}
```

返回示例：

```json
{
  "ok": true,
  "user": {
    "id": 1,
    "username": "wx_xxx"
  },
  "token": "server-issued-token"
}
```

后端行为：

- 使用 `APPID`、`APPSECRET` 调用微信 `code2Session`。
- 根据 `openid` 查询或创建本地用户。
- 建议新增 `WechatProfile` 或等价模型保存：
  - `user`
  - `openid`
  - `session_key`，如存储需加密或谨慎处理
  - `created_at`
  - `updated_at`
- 首版不处理 unionid。
- 首版不绑定旧账号密码用户。

### 4.2 小程序认证方式

建议从当前 session 认证调整为 token 认证，原因是小程序端管理 cookie/session 不如 Web 自然。

实现要求：

- 后端登录成功后签发服务端 token。
- 小程序后续请求通过 header 携带，例如：
  - `Authorization: Bearer <token>`
- 后端保留 Web session 登录能力，避免破坏当前 Web 端。
- `api_login_required` 需要同时识别 session 用户和 token 用户。

### 4.3 API 复用

优先复用现有接口：

- `GET /api/trips/`
- `POST /api/trips/`
- `GET /api/trips/{id}/`
- `PATCH /api/trips/{id}/`
- `DELETE /api/trips/{id}/`
- `GET /api/trips/{id}/members/`
- `POST /api/trips/{id}/members/`
- `DELETE /api/members/{id}/`
- `GET /api/trips/{id}/expenses/`
- `POST /api/trips/{id}/expenses/`
- `DELETE /api/expenses/{id}/`
- `GET /api/trips/{id}/summary/`
- `GET /api/trips/{id}/settlements/`
- `PATCH /api/settlements/{id}/`

可选补充：

- `PATCH /api/expenses/{id}/` 给小程序账单编辑使用。
- `GET /api/bootstrap/` 一次返回用户和出行列表，减少小程序首屏请求数。

## 5. 小程序端页面与交互

建议新增 `miniprogram/` 或 `app/miniapp/` 目录作为 uni-app 工程。

页面结构：

- `pages/login/index`：微信登录页。
- `pages/trips/index`：我的出行列表。
- `pages/trips/edit`：创建/编辑出行。
- `pages/trips/detail`：出行详情，使用分段区域展示概览、成员、账单、结算。
- `pages/expenses/edit`：新增/编辑账单。

交互要求：

- 所有提交按钮需要 loading 状态。
- 所有删除行为需要确认弹窗。
- 金额输入使用数字键盘。
- 日期使用小程序日期选择器。
- 网络错误统一 toast 或顶部提示。
- 未登录或 token 失效时自动回到登录页。
- 空列表需要友好空状态。

## 6. 非功能需求

- 请求域名必须配置为 HTTPS 合法域名。
- 后端生产环境关闭 `DEBUG`，配置 `ALLOWED_HOSTS`。
- 微信 `APPSECRET` 只能放服务端环境变量。
- 金额继续使用 Decimal，避免 float。
- 小程序端展示金额统一保留 2 位小数。
- API 返回结构保持 `{ ok: true/false }` 风格，减少前端适配成本。
- 权限规则保持现状：出行创建者可管理出行、成员、账单、结算；参与成员可查看。

## 7. 验收标准

首版验收：

- 用户可通过微信登录进入小程序。
- 首次微信登录会自动创建独立本地用户。
- 用户可创建出行，并在列表看到该出行。
- 用户可添加至少 3 名成员。
- 用户可新增多笔账单，并选择付款人和分摊成员。
- 系统可正确计算总金额、人均金额、成员净额。
- 系统可生成结算建议。
- 用户可标记结算已完成。
- 非出行相关用户不能访问该出行数据。
- 小程序在真机或微信开发者工具中完成核心流程验证。

测试建议：

- 扩展 `verify_travel_api.py`，增加微信登录/token 请求场景。
- 保留现有分摊和结算金额校验。
- 增加权限测试：A 用户创建的出行，B 用户不可访问。
- 小程序端手动验收 3 人 5 笔账单样例流程。
- 构建检查：uni-app 能成功编译为微信小程序。

## 8. 明确不纳入首版

- 微信支付真实转账。
- 好友系统。
- 群聊或微信群邀请。
- 票据图片上传和 OCR。
- 多币种实时汇率。
- 复杂角色权限。
- 历史账号绑定。
- 公开分享账单页面。

## 9. 默认假设

- 首版选择 uni-app，而不是原生小程序或 Taro。
- 首版微信账号与现有用户名密码账号独立。
- Django 后端继续作为唯一业务服务。
- 当前 Web 端不删除，迁移期间继续保留。
- 小程序第一版以功能可用和账务准确为优先，视觉设计做轻量移动端适配。
