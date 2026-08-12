# 校园活动采集线程 · 交接提示词

> 用途：新开一个线程，专注采集**中山大学真实校园活动**，充实 ONE MORE App 的「校园活动」列表。
> 本文档可整段作为新线程的启动提示词。今天是 2026-08-12（暑假尾声），采集目标以 **8 月下旬～10 月** 的迎新季、招新、宣讲会、讲座为主。

---

## 任务

为 ONE MORE（中大校园组局 App）的「校园活动」板块采集真实、可核验的中大校园活动，写入后端 `external_events` 表，让 App 里 活动 Tab → 校园活动 分段（B7 页面）从目前的 2 条演示数据充实到 20～40 条真实活动。

**硬要求：只收录真实存在、来源可核验的活动。宁可少，不可编。** 每条必须带来源 URL 或明确的官方出处（公众号推文标题+日期亦可）。

## 一、数据落点（契约）

表：`external_events`（定义在 `onemore/db/models.py:824`），经 `GET /events` 供 iOS 展示。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | String(36) | 留空，默认自动生成 uuid |
| `source` | String(32) | **UI 类型 chip 直接显示此值**。用词表：讲座 / 演出 / 赛事 / 社团 / 招新 / 宣讲会 / 招聘会 / 其他 |
| `external_key` | String(128) | **全局唯一**，幂等键。格式 `<来源>:<类型>:<原站ID或slug>`，如 `career:teachin:174791`、`official:lecture:2026-0901-baituan` |
| `title` | String(256) | 活动全称，不要截断 |
| `starts_at` / `ends_at` | DateTime | **存 UTC**（北京时间 −8h）。SQLite 里是无时区 naive UTC，API 层会自动补 `Z`（有契约测试守着，别存带 tz 的） |
| `location` | String(256) | 校区 + 具体地点，如「广州南校园 怀士堂」 |
| `official_url` | Text | **非空约束**。有原文链接填原文；实在没有填 `""` |
| `details` | JSON | 可放 `{"description": "…", "organizer": "校团委"}`。不要放任何个人身份信息 |

参考样例（测试里的合法插入）：`tests/test_public_event_contract.py`。

## 二、采集来源（按优先级）

### 1. sysu-anything CLI（本机已装，纯 HTTP 实时数据）

```bash
sysu-anything career teachin list --limit 30     # 宣讲会（含详情/时间/地点/报名链接）
sysu-anything career teachin detail --id <id>    # 单条详情
sysu-anything career jobfair list --limit 20     # 招聘会
sysu-anything explore seminar list               # 交叉探索平台组会/seminar
```

- career 源的 `external_key` 用 `career:teachin:<id>` / `career:jobfair:<id>`，`official_url` 填详情页 URL
- 宣讲会/招聘会 9 月秋招季大量更新，是内容主力

### 2. WebSearch 官方渠道

- 中山大学官网通知公告 / 新闻（sysu.edu.cn）
- 中山大学团委、学生会、研究生会公众号近期推文（讲座、演出、百团大战）
- 各校区（广州南/北/东、珠海、深圳）的迎新安排、新生教育周活动
- 体育馆、图书馆、博物馆（中大博物馆近期展览）开放活动

### 3. 已有本地资料

- `data/reference/sysu/` 下的校园参考包（`scripts/build_sysu_south_bundle.py` 产物）可能有场馆/组织信息可佐证 location 用词

## 三、工作流

1. **采集**：用上面来源收集活动，逐条记录：标题 / 类型 / 北京时间 / 地点 / 来源 URL / 一句话说明
2. **整理成数据文件**：写 `data/campus-events/2026-09.json`（新建目录），结构为对象数组，字段同契约表（`starts_at` 写 ISO8601 带 `+08:00`，导入器负责转 UTC）
3. **写导入器**：`scripts/import_campus_events.py`
   - 读 JSON → 按 `external_key` **upsert**（存在则更新，不存在则插入），可重复跑不产生重复
   - 北京时间 → UTC naive 转换在导入器里做
   - 用 `onemore.core.database.SessionLocal` 直接写库（参考 `tests/test_public_event_contract.py` 的插入方式）
   - **不要走 `POST /events`**——那是 T4 用户发布通道，不是批量导入通道
4. **验证**：
   - `.venv/bin/python3 -m pytest tests/test_public_event_contract.py -q` 必须通过
   - 重启后端：`pkill -f "uvicorn onemore.main" ; nohup .venv/bin/uvicorn onemore.main:app --host 127.0.0.1 --port 8000 &`
   - `curl -s http://127.0.0.1:8000/events | python3 -m json.tool | head -40` 确认新活动按时间排序出现
   - iOS 复核：模拟器启动 `-ProductionScreenID B7` 或活动 Tab（`-InitialTab competitions -ActivitySegment 校园活动`）截图确认卡片渲染正常（类型 chip、标题、时间、地点）

## 四、质量红线

- **禁止编造**：没有来源的活动一条都不要。标题、时间、地点必须与来源一致
- 时间已过（< 2026-08-12）的不要；「时间待定」的可以收，`starts_at` 留空（UI 会显示「时间待官方确认」）
- 类型用词表内的词，不要发明新类目（实在不属于任何类用「其他」）
- 不收录需要付费报名且明显商业化的活动；考研/留学中介讲座一律不收
- 用户发布通道（`POST /events`，T4 门槛、匿名展示）已上线，本线程**只导入官方/半官方活动**，不要模拟用户发布

## 五、完成的定义

- `data/campus-events/2026-09.json` 含 20～40 条真实活动，每条有来源 URL
- `scripts/import_campus_events.py` 可重复执行（幂等 upsert），跑完后 `sqlite3 onemore.db "SELECT source, COUNT(*) FROM external_events GROUP BY source;"` 可见各类型数量
- 契约测试通过；`/events` 接口返回新数据；iOS 校园活动段截图确认渲染
- 在 `docs/handoffs/` 留一份采集纪要（来源列表、收录标准执行情况、未收录的及原因）

## 六、上下文速查

- 后端模块：`onemore/modules/campus/`（api.py / service.py / schemas.py）
- iOS 展示：`ios/OneMore/Features/Today/CampusToolsViews.swift` 的 `CampusEventsContent`（活动 Tab 与 B7 共用）
- 后端运行：`.venv/bin/uvicorn onemore.main:app --host 127.0.0.1 --port 8000`
- 数据库：`onemore.db`（SQLite，工作区根目录）
