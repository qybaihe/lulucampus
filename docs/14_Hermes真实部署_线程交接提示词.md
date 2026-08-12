# 14 · Hermes 真实部署 · 线程交接提示词

> 用途：把本文件**整段复制**给负责部署的 Agent / 线程，让其在现有服务器上把 Hermes 从 `fake` 切成可被 Web + iOS 真实调用的独立校园执行能力。  
> 日期：2026-08-12  
> 仓库：`/Users/baihe/Documents/compusone`  
> 服务器：`ubuntu@42.194.219.172`（密钥本地路径见下）

---

## 0. 给部署线程的任务陈述（请严格按此执行）

你的任务不是继续做产品功能，而是：

**在已上线的 ONE MORE（噜噜成局）后端上，把 Hermes 从 `fake` 升级为 `real`，使 Web 与 iOS 都能通过现有 FastAPI 契约真实调用校园能力；并确保每个用户的校园凭据独立加密、独立挂载、互不串仓。**

验收目标（全部达成才算完成）：

1. `ONEMORE_HERMES_MODE=real`，`/health/ready` 返回 `hermes_mode: real` 且 `hermes_cli: ok`
2. Web（`http://42.194.219.172/onemore/`）走 `/auth/scan` 能拿到**真实企业微信二维码**（非 DEMO SVG），扫码后可 redeem token
3. 同一用户后续调用课表/场馆等动作时，走真实 `sysu-anything` CLI，且使用该用户私有 vault
4. 用户 A 的 session 文件绝不能被用户 B 的执行挂载到；撤销授权会清对应加密会话文件
5. 手机号注册账号与校园扫码账号可共存；校园能力以「完成统一身份扫码 + 授权 grant」为前提
6. **不得破坏**服务器上已有其他服务（nginx 现有站点、其它 docker 容器、`/opt/AnythingSYSU` 本体）

非目标（本次不要做）：

- 不要重做 EdgeOne Agent（那是对话层，不执行校园动作）
- 不要把 Hermes 改成「每人常驻进程」
- 不要在生产开 `ONEMORE_DEV_AUTH_ENABLED=true`
- 不要改手机号注册/登录已上线契约（除非为绑定校园身份必须的最小改动）
- 不要 `push --force`、不要改 git config、不要提交 `/opt/onemore/.env`

---

## 1. 产品与架构背景（必读）

### 1.1 产品

「噜噜成局 / ONE MORE」：校园成局 + Hermes 校园行动代理。  
业务后端：FastAPI（包名 `onemore`）。  
客户端：Web（`web/`）与 iOS（`ios/`）共用同一套 HTTP 契约。

### 1.2 Hermes 是什么 / 不是什么

详见仓库 `docs/03_行动代理与Hermes设计.md`。摘要：

- Hermes = **每个用户私有的校园执行器语义**（查课表、订场、预约…）
- 部署形态 = **共享执行池 + 每用户 Vault（加密状态仓）**，不是每人一个常驻进程
- 阿凑/成局业务永远拿不到凭证，只能提交 Action Schema

### 1.3 与 EdgeOne Agent 的边界（不要混淆）

| | Hermes（本任务） | EdgeOne Agent（`onemore-edge-agent/`） |
|---|---|---|
| 职责 | 真实校园登录与动作执行 | LLM 对话编排 |
| 是否持有校园 cookie | 是（每用户 vault） | 否（最多本轮 ephemeral 提示） |
| 订场/拉课表 | 服务端真实执行 | 只返回「请 iOS 本地执行」计划 |
| 本次是否部署 | **要** | 不要 |

### 1.4 凭据独立管理（必须保持）

实现已在代码里：

- `onemore/hermes/vault.py`：`VaultManager`
  - 每用户目录：`{vault_root}/u_{user_id}/`
  - 会话文件加密为 `*.enc`（Fernet，密钥来自 `ONEMORE_VAULT_MASTER_KEY`）
  - 执行时 `mounted(user_id)`：解密到临时目录 → CLI `--state-dir` → 结束后再加密写回
  - 按 grant 清理：`FILES_BY_GRANT`（撤销 `timetable` / `agent_booking` 等会删对应 session 文件）
- 登录编排：`onemore/hermes/login.py` → `sysu-anything auth workwechat --state-dir …`
- 动作执行：`onemore/hermes/executor.py` → `subprocess.run([sysu_cli, …])`，fake/real 由 `hermes_mode` 开关

能力清单：`onemore/hermes/capabilities.json`（timetable / gym / libic / explore / matrix / transit…）

---

## 2. 当前线上状态（部署前事实）

### 2.1 访问与登录

| 项 | 值 |
|---|---|
| SSH | `ssh -i /Users/baihe/Downloads/baihe.pem ubuntu@42.194.219.172` |
| Web | `http://42.194.219.172/onemore/` |
| API（外网） | `http://42.194.219.172/onemore/api/`（nginx 剥掉前缀反代到本机 18100） |
| API（本机） | `127.0.0.1:18100` |
| 代码部署目录 | `/opt/onemore/` |
| 前端静态 | `/opt/onemore/web-dist/` |
| Compose | `/opt/onemore/docker-compose.prod.yml` |
| 密钥文件 | `/opt/onemore/.env`（chmod 600，**勿提交 git**） |

已上线能力：

- 手机号注册/登录：`POST /auth/register`、`POST /auth/login`（无短信验证）
- 扫码登录契约仍在：`POST /auth/session` → poll → redeem（但当前 fake，二维码是 DEMO SVG）
- Postgres / Redis / Celery worker+beat 已跑通

### 2.2 容器现状（关键缺口）

```
onemore-api-1        127.0.0.1:18100->8000  healthy
onemore-worker-1 / beat / postgres / redis  运行中
```

当前环境（摘要）：

- `ONEMORE_HERMES_MODE=fake` ← **必须改**
- `ONEMORE_VAULT_MASTER_KEY` 已存在
- volume `onemore_vault-data` 已挂到 `/app/vaults`
- **容器内没有 Node、没有 sysu-anything、没有 Playwright/Chromium**
- 主机上已有完整 CLI：`/opt/AnythingSYSU`（`node bin/sysu-anything.js` 可用）
- 主机 Playwright 缓存：`~ubuntu/.cache/ms-playwright`（含 `chromium-1228`）
- 主机资源紧张：约 **3.6Gi RAM，可用 ~1.5Gi**；磁盘 `/` 约 69G 用了 51G

### 2.3 本地开发对照

- 本机 CLI：`/Users/baihe/.local/bin/sysu-anything` → `Documents/AnythingSYSU`
- 本机开发常开 `HERMES_MODE=real`；线上被故意设成 fake 以便先上业务

### 2.4 安全组 / 端口约束

- 公网新端口不一定放行；现有方案是 **nginx :80 路径前缀** `/onemore/`
- API 只绑 `127.0.0.1:18100`，不要改成 `0.0.0.0` 裸奔
- 不要占用 3000/3001/8000/8088 等已被其它服务使用的端口

---

## 3. 目标架构（推荐落地形态）

```
浏览器 / iOS
    │  HTTPS or HTTP
    ▼
nginx :80  /onemore/api/  ──►  onemore-api:18100
                              │
                              ├─ identity: /auth/session…（real login orchestrator）
                              ├─ actions / schedule / campus… → ExecutorPool
                              │
                              ▼
                         Celery worker（生产里登录任务走 celery）
                              │
                              ▼
                    subprocess: sysu-anything …
                              │  --state-dir <tmp mount of user vault>
                              ▼
                    Vault volume（每用户 u_{id}/*.enc）
```

约束：

1. **API 与 worker 都必须能执行 CLI**（登录编排在 production 走 Celery：`onemore.identity.login`；开发态才 BackgroundTasks）
2. Vault volume 必须同时挂到 `api` 与 `worker`
3. Chromium 内存贵：限制并发（已有 `executor_global_slots` / per-user rate limit；部署时 concurrency 宁小勿大）
4. 优先「把主机已有 `/opt/AnythingSYSU` + Playwright 缓存挂进容器」或「做独立 hermes-runtime sidecar」；避免在容器里重新下载整个 Chromium（慢且占盘）

---

## 4. 推荐实施步骤（可调整，但验收不变）

### Step A · 设计部署方式（先选一种，写进回复）

候选 A1（推荐先试）：在现有 `api`/`worker` 镜像上增加 Node + 挂载主机 CLI 与 Playwright 缓存  

- 挂载示例方向：
  - `/opt/AnythingSYSU` → 只读
  - `ONEMORE_SYSU_CLI=/opt/AnythingSYSU/bin/sysu-anything.js`（或包装脚本 `#!/usr/bin/env node`）
  - Playwright browsers path 指向已有缓存（注意容器用户权限：ubuntu vs root）

候选 A2：新增独立服务 `hermes-runner`（主机 systemd 或单独容器），API 只发任务；**若走这条，需改代码加远程执行通道——默认不要选，除非 A1 证实不可行**。

候选 A3：在主机用 systemd 跑 uvicorn+celery（非 docker）以便直接用主机 Node/Playwright——可行但会偏离当前 compose；仅当 docker 挂载权限死锁时再用。

**默认指令：优先 A1，最小改动打通 real。**

### Step B · 改 compose / 镜像 / 环境

需要新增或确认的环境变量（写入 `/opt/onemore/.env`，不要回传密钥明文到聊天）：

```bash
ONEMORE_HERMES_MODE=real
ONEMORE_SYSU_CLI=/绝对路径/到/sysu-anything
ONEMORE_VAULT_ROOT=/app/vaults          # 已与 volume 对齐则可不动
ONEMORE_VAULT_MASTER_KEY=...           # 已有，勿轮换除非你能接受全部用户重扫码
ONEMORE_EXECUTOR_GLOBAL_SLOTS=2        # 小机器建议调低
ONEMORE_EXECUTOR_PER_USER_PER_MINUTE=10
ONEMORE_EXECUTOR_LOGIN_TIMEOUT_SECONDS=200
ONEMORE_DEV_AUTH_ENABLED=false         # 保持 false
```

`docker-compose.prod.yml` 注意：

- `api` 与 `worker` 都要：CLI 可见、vault volume、必要时 `shm_size`（Chromium 常用 `shm_size: "256mb"` 或更大）
- worker concurrency 建议先 `1` 或 `2`，避免多 Chromium 把 3.6G 打爆
- beat 不需要 CLI（可不挂浏览器）

重建策略：

- 本地曾因服务器拉 PyPI 慢，用 `Dockerfile.prod` + 本机 `linux/amd64` 构建后 `docker load`；可复用该路径
- 镜像名现状：`onemore-api:prod`

### Step C · 连通性自检（容器内）

在 `api` 或 `worker` 容器内执行：

```bash
node -v
$ONEMORE_SYSU_CLI --help
# 不要求已登录成功，但命令必须能启动；Playwright 浏览器路径必须可找
```

然后：

```bash
curl -s http://127.0.0.1:18100/health/ready
# 期望 hermes_mode=real, hermes_cli=ok, database=ok, redis=ok
```

### Step D · 真实登录冒烟（Web）

1. 打开 `http://42.194.219.172/onemore/auth/scan`
2. 生成二维码：响应里的 `qr_image_data_url` 必须是真实 PNG/JPEG data URL，**不能**再是内含 `DEMO QR` 的 SVG
3. 用企业微信扫码完成一次
4. redeem 得到 `om1.` access_token
5. `GET /auth/me` 有身份事实；vault 下出现该 `u_{user_id}` 的 `*.enc`

### Step E · 真实动作冒烟

在已授权 `timetable` 的用户上：

- 触发课表刷新（Web 设置授权或调用 `/schedule/refresh`）
- 确认 worker 日志出现真实 CLI 调用且非 fake payload

可选：`gym.available` / `libic.available`（需对应授权与会话健康）

### Step F · 凭据隔离抽检

1. 两个不同校园账号各扫码一次 → 两个 vault 目录
2. 撤销某一 grant → 对应 `*.enc` 被删（见 `VaultManager.set_grant`）
3. 确认执行日志里 `--state-dir` 指向临时目录且结束后清理

### Step G · 客户端对齐

- Web：扫码页已接 `/auth/session`；切 real 后无需改契约，但要回归「开发环境完成扫码」按钮在生产不可用（`dev_auth` false）
- iOS：同样契约；部署后用 TestFlight/真机对同一 API base 回归 RealLoginView
- API base：生产 Web 已是相对路径 `/onemore/api`；iOS 需指向 `http://42.194.219.172/onemore/api`（或后续域名）

手机号用户路径：

- 手机号注册可先用产品；**校园能力**仍需走统一身份扫码绑定 vault
- 若产品要「手机号账号绑定校园身份」，复用现有 resume/扫码绑定逻辑，不要另造一套明文存 NetID（只用 `netid_hash`）

---

## 5. 风险与红线

| 风险 | 应对 |
|---|---|
| 内存不足导致 Chromium OOM | 降 slots/concurrency；加 `shm_size`；必要时把 worker 迁到独立小机 |
| 容器 root vs 主机缓存权限 | 统一用户或 chmod/ACL；不要世界可写密钥目录 |
| 轮换 `VAULT_MASTER_KEY` | 等于全部用户会话作废，需重扫码——默认不轮换 |
| 校园站点对云 IP 风控 | 实测扫码与 jwxt；失败时记录 error_category，不要假成功 |
| 误伤其它站点 | 只改 `/opt/onemore` 与 nginx 里 onemore 段；改 nginx 前备份 |
| 把密钥贴进 git / 聊天 | 禁止；只报告「已设置/已轮换」 |

---

## 6. 关键文件索引（仓库内）

```
docs/03_行动代理与Hermes设计.md          # 设计真相源
docs/02_后端服务开发指南.md
docs/06_后端实现与前端联调.md
onemore/hermes/login.py                  # 真实扫码编排
onemore/hermes/executor.py               # fake/real 执行池
onemore/hermes/vault.py                  # 每用户加密仓
onemore/hermes/capabilities.json         # 动作目录
onemore/modules/identity/api.py          # /auth/session*
onemore/core/config.py                   # 生产校验（real 时要求 CLI 存在）
docker-compose.prod.yml                  # 线上 compose
Dockerfile.prod                          # 当前生产镜像（无 Node）
```

服务器：

```
/opt/onemore/                 # 应用
/opt/onemore/.env             # 密钥
/opt/AnythingSYSU/            # 已有 CLI 源码与 node_modules
/opt/AnythingSYSU/bin/sysu-anything.js
~ubuntu/.cache/ms-playwright  # 浏览器缓存
/etc/nginx/sites-enabled/sysu-anything-demo-ip  # 含 /onemore/ 段（已有备份习惯）
```

---

## 7. 交付物（部署线程完成后必须回报）

1. 采用的方案（A1/A2/A3）与最终 compose/挂载摘要（无密钥）
2. `curl` `/health/ready` 全文
3. 一次真实扫码的证据：session 状态到 SUCCESS + vault 目录存在（可打码 user_id）
4. 一次真实课表或 gym/libic 调用的日志片段（证明不是 fake）
5. 并发/内存参数最终值
6. 回滚方式（如何改回 `HERMES_MODE=fake` 并重启）
7. 未解决问题列表（若校园 IP 被拦、某子系统失败等）

---

## 8. 一键上下文命令（部署线程可直接用）

```bash
# SSH
ssh -i /Users/baihe/Downloads/baihe.pem ubuntu@42.194.219.172

# 看现状
sudo docker compose -f /opt/onemore/docker-compose.prod.yml ps
sudo grep ONEMORE_HERMES_MODE /opt/onemore/.env
curl -s http://127.0.0.1:18100/health/ready
node /opt/AnythingSYSU/bin/sysu-anything.js --help | head

# 本地仓库
cd /Users/baihe/Documents/compusone
```

---

## 9. 成功判据（用户原话对齐）

> 「不能保持 fake；要确保成独立可使用的；服务器上部署上去；APP 与 Web 都能真实调用 Hermes；每个凭据独立管理。」

对应工程判据：

- [ ] real 模式健康检查通过  
- [ ] Web/iOS 共用 API 真实扫码登录成功  
- [ ] 动作走 sysu-anything，非 fake 分支  
- [ ] vault 每用户隔离 + grant 级清理仍生效  
- [ ] 现有手机号登录与其它站点服务不被破坏  

---

**开始工作吧。先汇报你选择的部署方案（A1/A2/A3）和风险，再改配置与镜像；每完成一个 Step 做一次冒烟再继续。**
