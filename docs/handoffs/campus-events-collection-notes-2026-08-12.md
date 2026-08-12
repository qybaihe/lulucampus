# 校园活动采集纪要 · 2026-08-12

## 产出

| 产物 | 路径 |
|---|---|
| 活动 JSON | `data/campus-events/2026-09.json`（24 条） |
| 导入器 | `scripts/import_campus_events.py`（按 `external_key` upsert，北京时间 → naive UTC） |
| 数据库 | `onemore.db` · `external_events` |

导入命令：

```bash
.venv/bin/python3 scripts/import_campus_events.py
# 二次执行应全部 unchanged
```

## 类型分布（导入后）

| source（UI chip） | 数量 |
|---|---:|
| 其他 | 14 |
| 招聘会 | 6 |
| 宣讲会 | 2 |
| 赛事 | 2 |
| **合计** | **24** |

## 来源列表与收录标准

### 1. career.sysu.edu.cn（sysu-anything CLI，公开页）

| external_key | 标题摘要 | 时间（北京） | 依据 |
|---|---|---|---|
| `career:teachin:174843` | 多益网络秋招在线宣讲 | 2026-08-13 19:30–20:10 | `sysu-anything career teachin detail --id 174843` |
| `career:teachin:174845` | 新东方深圳空宣 | 2026-08-18 18:30–20:30 | 同上 174845 |
| `career:jobfair:49316` | 线上就业/实习双选会 | 至 2026-09-10 | jobfair detail（仍在进行） |
| `career:jobfair:49341` | 万企进校园大型双选会 | 2026-09-15 14:30–17:00 | 东校园篮球场 |
| `career:jobfair:49343` | 医职由我医学类巡回招聘会 | 2026-09-19 14:00–17:00 | 北校园篮球场 |
| `career:jobfair:49342` | 重点行业专场（珠海） | 2026-09-21 14:30–17:00 | 珠海教学楼架空层 |
| `career:jobfair:49344` | 重点行业专场（深圳） | 2026-09-29 14:30–17:00 | 深圳西教学楼南侧架空层 |
| `career:jobfair:49345` | 医科高层次人才专场 | 2026-10-29 14:30–17:30 | 北校园篮球场 |

### 2. 学院 / 研究生院官网

| external_key | 依据 URL |
|---|---|
| `math:contest:nmc-2026-gd` | https://math.sysu.edu.cn/article/3910（9/10 18:00–9/13 20:00，报名截止 9/1） |
| `official:contest:cpipc-2026` | https://graduate.sysu.edu.cn/article/603（时间以研创网为准 → `starts_at` 留空） |

### 3. 官方校历

| external_key | 依据 |
|---|---|
| 本科/研究生新生报到、非新生注册、正式上课、校庆日 | https://www.sysu.edu.cn/index/xl.htm + `data/reference/sysu/academic_calendar_2026_2027.json`（verified 2026-08-11） |

### 4. 博物馆（校史馆）官网

| external_key | 依据 URL | 说明 |
|---|---|---|
| `museum:exhibition:pangxunqin-2026` | https://bwgxsg.sysu.edu.cn/zh-hans/article/608 | 临时展，仍在「临时展览」列表；`starts_at` 留空 |
| `museum:exhibition:ruins-guangzhou` | https://bwgxsg.sysu.edu.cn/zh-hans/article/587 | 临时展；有延期公告 |
| `museum:on-show:*`（7 条基本展陈） | article/146–147, 581, 583–586 | 常设展陈；时间待官方确认（开放时段见开放指南） |

## 收录标准执行情况

- **只收录可核验来源**：每条均有 `official_url`（校历条目指向校历页 + details.source_refs）。
- **未编造**时间/地点；宣讲会/招聘会字段与 career 详情一致。
- **类型词表**：仅用 宣讲会 / 招聘会 / 赛事 / 其他。
- **付费商业中介讲座**：未收录。
- **用户发布通道**：未模拟；导入走 DB upsert，不走 `POST /events`。
- **演示数据**：导入时删除 `demo-teachin-1` / `demo-seminar-1`（example.edu.cn 假链接）。

## 未收录及原因

| 候选 | 原因 |
|---|---|
| career 列表中 5–7 月宣讲会/招聘会 | 时间已过（< 2026-08-12） |
| 管理学院 / 岭南学院首页讲座 | 均为 2026-06，已过期 |
| 深圳校区「博学大讲堂」等微信预告 | 页面无明确 8–10 月场次时间，历史预告居多 |
| 百团大战 / 社团招新 / 迎新晚会 | 2026 迎新季正式通知尚未在可抓取官网发布（暑假中） |
| explore seminar CLI | 接口 403，无可用数据 |
| 中国国际大学生创新大赛校内选拔（cse article/3534） | 报名截止已在 5–6 月，非当前可参与窗口 |
| 全国性竞赛 leads（data/competitions） | 多数非中大官方落地时间/地点，且缺本校可核验排期 |
| 博物馆微信推文正文 | 反爬验证页，未用未验证内容写字段 |

## 数量说明

目标 20–40 条，本批 **24 条**。  
2026-08-12 处于暑假尾声，**秋招与迎新季大量讲座/招新/百团信息尚未挂网**；当前可核验主力是就业系统已发布的 8–10 月招聘活动 + 校历节点 + 博物馆在展。后续可每周重跑 career CLI 增量导入。

## 验证

- `pytest tests/test_public_event_contract.py -q` → 通过
- 二次 `import_campus_events.py` → `unchanged=24`
- `GET http://127.0.0.1:8000/events` → 24 条；`starts_at` 带 `Z`；类型 chip 为中文词表
- 列表排序：`starts_at ASC NULLS LAST`（`onemore/modules/campus/service.py`），有时间的活动在前
- iOS 模拟器截图：
  - `artifacts/campus-events/B7-campus-events-sorted.png`（`-ProductionScreenID B7`）
  - 卡片可见：类型 chip（招聘会/宣讲会/其他/赛事）、标题、时间、地点

## 建议的后续增量

1. 每周 `sysu-anything career teachin list --limit 50` + `jobfair list`，只收新 ID。
2. 9 月开学后抓取团委/学生会公众号百团大战、学院迎新讲座。
3. 博物馆「讲座沙龙」新预告（当前列表多为 5–6 月已办）。
