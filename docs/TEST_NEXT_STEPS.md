# ONE MORE · 发布外部配置清单

本地 Definition of Done 只在独立 `Fidelity major = 0` 与 `Testing P0/P1 = 0` 后关闭。本文件不承载客户端遗留功能；仅列真实账号、域名、设备和凭证才能完成的生产配置，以及不阻断发布的像素级精修。

## 1. Apple 签名与上架

- 在 CI/Release 注入 Apple Development Team、App Store Connect App ID、分发证书与 provisioning profile；Release Bundle ID 已固定为 `com.onemore.campus`。
- 为 Push Notifications、Associated Domains、日历、语音、照片和位置能力生成正式 profile/usage 配置。
- 在真实 iPhone 做 Archive → 安装 → 前后台 → 权限拒绝/恢复 → 真机推送验收；Simulator 证据不替代 App Store 签名验收。

## 2. 生产 HTTPS/WSS

- 将 `/Users/baihe/Documents/compusone/ios/Config/Release.xcconfig` 的 `https://api.onemore.example`、`wss://api.onemore.example` 槽替换为正式域名。
- 部署与 SHA-256 `a05a6dcae7f75f69ea109ef40b5d8dc4cda624f4aa0493ef93f5344951ab9abd` 的冻结 OpenAPI（118 paths / 204 schemas）一致的 FastAPI 版本。
- 在 staging 使用正式 Bearer 身份复跑 15 项 live smoke；生产不启用 `DEV_AUTH`，不注入 `X-User-ID`。
- 配置 TLS、CORS、限流、PostgreSQL、Redis、Celery、监控、备份与日志保留。

## 3. APNs 与 Universal Link

- 服务端注入 APNs provider key/team/topic，验证 device token 所有权、轮换/注销与 E3/E5/E6/E7/E14/E16/G3/M3 payload。
- 在正式域名发布 `apple-app-site-association`，替换 `ASSOCIATED_DOMAIN` 槽。
- 用未登录、登录过期、已登录三种真机状态验证原始 deep-link 目标保存与认证后恢复。

## 4. 企业微信真实上游

- 注入 Corp ID、Agent/App ID、回调域、secret 与二维码上游，替换本地 fake 扫码认证 provider。
- 验证二维码过期、取消、单次兑换、防跨设备领取、授权撤回、账号切换与 deep-link 恢复；FastAPI/iOS 已保留相同异步 session 契约。

## 5. 非阻断视觉精修

当前 Gate 只要求 screenshot-level major 为 0。若继续精修，按 `/Users/baihe/Documents/compusone/ios/FIDELITY_NEXT_STEPS.md` 处理小尺寸粉发女孩可辨识面积、glass 透明度、局部卡片密度及 bottom action 的轻微纵向差。任何视觉代码改动都必须：

1. 重新构建最终 Debug app；
2. 重新捕获 36 张返回画板与 8 个状态；
3. 更新 source/binary/PNG hash manifest；
4. 重新取得独立 Fidelity Review `major = 0`；
5. 重跑受影响 UI 与 Release 审计。

## 6. 发布前复跑

```bash
cd /Users/baihe/Documents/compusone
uv run ruff check onemore tests migrations
uv run mypy onemore
uv run pytest -o addopts='' -ra
uv run alembic upgrade head
uv run python scripts/validate_competition_snapshot.py fixtures/competition_snapshot_2026-08-11_v1.1.json
uv run python scripts/validate_sysu_reference.py

cd /Users/baihe/Documents/compusone/ios
./Scripts/generate.sh
./Scripts/test.sh
python3 Scripts/audit_delivery.py
```

保持标准：后端 154+ tests、OpenAPI 118/204、赛事 24 且无 demo、iOS 72 unit / 21 UI、Fidelity major 0、Testing P0/P1 0、Release Bundle ID `com.onemore.campus` 且无 dev auth/localhost/ATS 例外/WebView/旧 IP。
