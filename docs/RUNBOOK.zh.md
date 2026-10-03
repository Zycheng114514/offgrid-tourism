# 运行手册

English version: [RUNBOOK.md](RUNBOOK.md)

## 本地运行（Mac 或 Linux，Python 3.10+，无需安装任何包）

```bash
cd server
DB_PATH=../data/runtime/dev.sqlite python -m offgrid seed
LLM_PROVIDER=simulated DB_PATH=../data/runtime/dev.sqlite PORT=8790 python -m offgrid serve
```

打开 <http://127.0.0.1:8790/>（首页）、`/host`（商户端）、`/pipeline`（管道演示页）、`/app/`（游客端）。

测试（无需网络，使用模拟的模型）：

```bash
cd server && python -m unittest discover tests
```

## 把演示部署到服务器

```bash
deploy/deploy.sh <ssh-host>
```

它做什么：把代码和数据复制到服务器上的 `~/offgrid-tourism`（只复制，不会删除那里的任何内容）；首次运行时写入 `.env`（模拟的模型，模拟器网关）；首次运行时向数据库载入预置的假商户数据；在 tmux 会话 `offgrid` 中重启应用；如果没有正在运行的临时通道（Cloudflare quick tunnel），就在 tmux 会话 `tunnel` 中启动一个；打印公开 URL。

- 每次临时通道重启，公开 URL 都会变化。当前 URL：在服务器上运行 `grep trycloudflare ~/offgrid-tourism/data/runtime/tunnel.log | tail -1`。
- 服务器上的日志：`~/offgrid-tourism/data/runtime/server.log`、`tunnel.log`。
- 用全新的演示数据重新开始：`deploy/deploy.sh <ssh-host> --reset-data`（旧数据库会在服务器上保留为带时间戳的 `.bak` 副本）。

## 连接 Android 短信网关手机（D4）

由一位队友在一部装有 SIM 卡、能一直开机并保持在线的 Android 手机上操作。

1. 安装“SMS Gateway for Android”（开源，文档见 docs.sms-gate.app）。开启 **Cloud server** 模式；应用会显示用户名和密码。
2. 注册我们的 webhook（替换其中的值；可在任何一台电脑上运行）：

   ```bash
   curl -X POST -u USERNAME:PASSWORD -H "Content-Type: application/json" -d '{"url": "https://PUBLIC-URL/webhooks/sms-gate", "event": "sms:received"}' https://api.sms-gate.app/3rdparty/v1/webhooks
   ```

3. 在服务器上编辑 `~/offgrid-tourism/.env`：`SMS_GATEWAY=android`、`SMSGATE_USER`、`SMSGATE_PASSWORD`、`SMS_PUBLIC_NUMBER`（这部手机的号码）；然后再次运行 `deploy/deploy.sh <ssh-host>` 来重启。
4. 用另一部手机给这部手机发短信：`CARI makan Garoga` 应该会返回三条商户条目。

如果临时通道重启，它的 URL 会变化：用新的 URL 重新注册 webhook。

## Vercel（为不保存状态的部分提供的永久链接）

文件：`vercel.json`（把每个请求都发送到 `api/index.py`）、`api/index.py`、`server/offgrid/wsgi.py`。没有构建步骤，也没有依赖项。

在本地测试同一个应用：`cd server && PORT=8791 python -m offgrid.wsgi`，然后打开 <http://127.0.0.1:8791/>。

第一次部署（只做一次，由拥有该仓库的 GitHub 账号操作）：

1. 用 GitHub 登录 vercel.com（免费的 Hobby 方案）。
2. Add New → Project → 导入 `Zycheng114514/offgrid-tourism`。如果列表中没有这个仓库，用“Adjust GitHub App Permissions”授予 Vercel 访问该仓库的权限。
3. Framework Preset：**Other**。Root Directory、构建和输出设置、环境变量都保持为空。部署。
4. 使用 **Domains** 下的地址（例如 `offgrid-tourism.vercel.app`）；每次部署各自生成的长地址可能会要求访问者登录。

之后，每次向 `main` 上传（push）都会自动重新部署。当我们自己服务器的临时通道地址变化时，更新 `deploy/live_server_url.txt` 并上传（push），这样 Vercel 上的 `/host` 就会指向新地址。

