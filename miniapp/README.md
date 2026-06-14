# 旅行账本微信小程序

这是根据根目录 `miniapp-prd.md` 生成的 uni-app 微信小程序端骨架，复用现有 Django API。

## 开发运行

```powershell
cd miniapp
npm install
npm run dev:mp-weixin
```

然后用微信开发者工具打开 `miniapp/dist/dev/mp-weixin`。

## 后端配置

本地开发默认 API 地址是 `http://127.0.0.1:8000`，可在登录页输入框里临时修改。

真实微信登录需要在后端配置：

```powershell
$env:WECHAT_APPID="your-appid"
$env:WECHAT_APPSECRET="your-secret"
python .\backend\manage.py runserver 127.0.0.1:8000
```

Django `DEBUG=True` 时可使用 `mock:<任意标识>` 模拟微信登录，便于本地联调。

## 首版页面

- 微信登录：`pages/login/index`
- 我的出行：`pages/trips/index`
- 创建/编辑出行：`pages/trips/edit`
- 出行详情：`pages/trips/detail`
- 新增账单：`pages/expenses/edit`
