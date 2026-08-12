# 信任进度页重设计（M3）

> 日期：2026-08-12  
> 范围：`/trust/me` 契约增强 + iOS `TrustView` 主路径重做  
> 原则：等级只解锁能力；只展示本人进度；不展示技术能力键名

## 问题

旧版信任页把 `unlocks` 里的服务端能力键（`browse_open_gatherings · T1` 等）直接罗列出来，并完整展开 T0–T4 门槛卡片。用户无法回答：

1. 我离下一级还差什么？
2. 升上去能多做什么？
3. 每一级的标准在哪里查？

这与产品方案模块 D「完全透明：距下一级差距可视化」不一致。

## 产品结构

### 主路径（TrustView / M3）

| 区块 | 内容 |
|---|---|
| 当前等级 | 徽章 · 等级码 · 名称 · 一句话叙事 |
| 升到下一级 | 总进度 % + 结构化条件（进度条 / 勾选） |
| 本级已解锁 | 用户可读权益（非 capability key） |
| 下一级将解锁 | 预告权益 |
| 升级说明入口 | Sheet：完整 T0–T4 标准文档 |
| 页脚 | 隐私说明 · 申诉 · 去公开局 |

**主路径不展示**：`unlocks` 技术能力矩阵、完整五级详情墙。

### 升级文档（Sheet）

每一级固定四字段：

- `level` / `name`
- `how`：如何达到（用户可读标准）
- `benefits`：本级权益
- `is_current` / `is_reached`：仅用于本人状态标注

## 晋级条件（与 `recompute_level` 对齐）

| 当前 → 下一级 | 条件 |
|---|---|
| T0 → T1 | 统一身份认证 |
| T1 → T2 | 有效成局 ≥ 3 · 准时确认率 ≥ 80% · 近 30 天无临期爽约 · 无有效举报 |
| T2 → T3 | 有效成局 ≥ 10 · 本人发起完成 ≥ 3 · 复局 ≥ 2 · 爽约率 < 10% |
| T3 → T4 | 主理人认证（社团/院系/平台核验，不靠刷数据） |

## API：`GET /trust/me` 新增字段

在原有 `level / next_level / gaps / next_level_progress / unlocks` 上扩展：

| 字段 | 用途 |
|---|---|
| `next_level_name` | 下一级中文名 |
| `conditions[]` | 结构化条件（key/label/met/current/required/unit/detail） |
| `overall_progress` | 0–1 总进度 |
| `current_benefits[]` | 本级权益文案 |
| `next_benefits[]` | 下一级权益文案 |
| `level_guide[]` | 升级文档完整条目 |

`unlocks` **保留**供调试与服务端对照，iOS 主路径不再渲染。

## iOS 改动

- `APIModels.TrustProgress`：新增 `Condition` / `LevelGuideItem` 及上述字段
- `TrustView`：进度优先 UI；移除「服务端能力判定」与五级硬编码墙
- `TrustLevelGuideSheet`：升级说明
- `TrustRequirementView`（C3）：门槛恢复页同步展示条件进度
- 原型 `M3Screen` 与生产主路径对齐

## 验收

- [ ] M3 首屏看不到 capability 英文键
- [ ] 有下一级时可见总进度与条件列表
- [ ] 本级 / 下一级权益为中文产品文案
- [ ] 「查看升级说明」可打开 T0–T4 标准
- [ ] 他人等级仍不可见
- [ ] `pytest` 信任进度用例通过；`uv run onemore-export-openapi` 已更新
