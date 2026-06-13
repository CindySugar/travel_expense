# Agent Guide

本文件给后续接手本项目的 agent 使用，记录当前项目结构、运行方式和注意事项。

## 项目概况

- 工作区路径：`D:\trae_projects\django`
- 后端：Django，目录 `backend/`
- 前端：Vue + Vite，目录 `frontend/`
- Python 虚拟环境：`.venv/`
- 后端数据库：SQLite，文件 `backend/db.sqlite3`
- 项目依赖：
  - Python: `requirements.txt`
  - Node: `frontend/package.json`

## 启动方式

后端 Django：

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

前端 Vue/Vite：

```powershell
cd frontend
npm run dev -- --host 127.0.0.1
```

常用访问地址：

- 前端：http://127.0.0.1:5173/
- Django 管理后台：http://127.0.0.1:8000/admin/login/

## 管理员账号

本地开发可使用 Django 管理员账号 `admin`。密码属于本地凭据，不写入仓库；需要时用下面命令在本机重置。

## 常用命令

Django 检查：

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
```

Django 迁移：

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
```

创建或重置管理员密码，将 `<local-dev-password>` 替换为本机临时密码，不要提交真实密码：

```powershell
.\.venv\Scripts\python.exe backend\manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); u, _ = User.objects.get_or_create(username='admin'); u.is_staff=True; u.is_superuser=True; u.set_password('<local-dev-password>'); u.save()"
```

前端构建：

```powershell
cd frontend
npm run build
```

## 已知配置

- Django 语言：`zh-hans`
- Django 时区：`Asia/Shanghai`
- 已安装并启用：`simpleui`
- 后台应用配置在 `backend/config/settings.py`
- URL 配置在 `backend/config/urls.py`

## 协作与执行注意事项

- 所有 Python 操作默认使用 `.venv`，不要直接使用系统 Python。
- 后端命令从项目根目录运行，路径写作 `backend\manage.py`。
- 前端命令在 `frontend/` 目录运行。
- 本地开发端口默认：
  - Django: `8000`
  - Vite: `5173`
- 启动服务前可检查端口：

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8000,5173 }
```

- 后台服务日志建议写入 `.logs/`，避免散落到项目根目录。
- 管理员密码和 `DJANGO_SECRET_KEY` 只通过本地环境或运维密钥管理提供，不写入仓库。

## Golutra 工作区注意事项

- 当前结构化 `workspacePath` 使用：`D:/trae_projects/django`
- 每次按需加载项目技能前，先运行：

```powershell
golutra-cli skills --workspace D:/trae_projects/django
```

- owner 日常入口：COO 私聊 `01KTXHP04B9YBVGYBMKGR8NA1F`
- 公司总控：`01KTXHP03W67ERF9QAPK3Y5723`
- 默认大群 `django` 只作兜底上下文，不作为持续工作流频道。
- ????? Git ??????????????????????
