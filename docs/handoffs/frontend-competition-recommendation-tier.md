# 前端交接 · 比赛推荐档文案（Tier A/B/C → 中文标签）

> 交接对象：iOS / 前端  
> 后端已完成：`2026-08-12`  
> 范围：仅「比赛雷达」推荐档展示与筛选，**不涉及**用户信任等级 T0–T4  
> 契约：`openapi/onemore.openapi.json`（已导出）

---

## 1. 背景（为什么改）

当前 iOS 把内部运营码直接显示成：

- 筛选：`Tier A` / `Tier B` / `Tier C`
- 卡片 / 详情：`TIER A`

用户会误以为是**比赛难度 / 含金量**，或和**信任等级**搞混。

实际含义是**运营推荐权重**（学校官方优先 vs 可核验 vs 商业补充），不是难度。

---

## 2. 后端已定稿（不要在前端另造文案表）

### 2.1 怎么存数据

| 层 | 字段 | 值 | 说明 |
|---|---|---|---|
| DB / 快照入库 | `recommendation_tier` | `A` \| `B` \| `C` | **只存稳定码**，`String(1)`，可筛选、可索引 |
| 公开 API 派生 | `recommendation_label` | 见下表 | 读路径派生，**不落库** |
| 公开 API 派生 | `recommendation_description` | 见下表 | 读路径派生，**不落库** |

单一真相源（改文案只改后端）：

```text
onemore/modules/competitions/recommendation.py
```

### 2.2 标签对照（方案一 · 冻结）

| code（筛选用） | label（展示用） | description（脚注 / 说明） |
|---|---|---|
| `A` | **优先推荐** | 学校或权威学会/行业组织官方通知，关键行动字段完整，默认优先展示。 |
| `B` | **可报名** | 官方赛项页可核验，信息仍可能变动；正常展示，临近报名可再核对。 |
| `C` | **补充参考** | 事实可核验，多为商业主办或推荐价值较弱；作补充信息，默认降权。 |

**禁止**再渲染：`Tier A`、`TIER A`、`等级A`、`A档` 等英文/内部用语。

### 2.3 接口变更

#### 列表 / 详情（既有）

```http
GET /competitions
GET /competitions/{id}
```

每个 `CompetitionView` **新增必填字段**：

```json
{
  "recommendation_tier": "A",
  "recommendation_label": "优先推荐",
  "recommendation_description": "学校或权威学会/行业组织官方通知，关键行动字段完整，默认优先展示。"
}
```

- 筛选 query **不变**：`?recommendation_tier=A|B|C`（仍传 code，不要传中文 label）
- 排序仍由服务端 `priority` 决定；前端不必按 A/B/C 再排一次

#### 新增目录（筛选 chips 优先用这个）

```http
GET /competitions/recommendation-tiers
```

响应示例：

```json
{
  "data": [
    {
      "code": "A",
      "label": "优先推荐",
      "description": "学校或权威学会/行业组织官方通知，关键行动字段完整，默认优先展示。",
      "sort_order": 0
    },
    {
      "code": "B",
      "label": "可报名",
      "description": "官方赛项页可核验，信息仍可能变动；正常展示，临近报名可再核对。",
      "sort_order": 1
    },
    {
      "code": "C",
      "label": "补充参考",
      "description": "事实可核验，多为商业主办或推荐价值较弱；作补充信息，默认降权。",
      "sort_order": 2
    }
  ]
}
```

筛选条渲染：`全部` + 按 `sort_order` 的 `label`；点选后请求 `recommendation_tier={code}`。

---

## 3. iOS 必改点（对照当前代码）

### 3.1 模型

文件：`ios/OneMore/Core/Networking/APIModels.swift` · `Competition`

在 `recommendationTier` 旁增加（snake_case JSON → camelCase）：

```swift
let recommendationTier: String          // 已有，筛选用 code
let recommendationLabel: String         // 新增，展示用
let recommendationDescription: String   // 新增，说明用
```

可选：再加目录模型

```swift
struct RecommendationTierMeta: Codable, Identifiable, Sendable {
    var id: String { code }
    let code: String
    let label: String
    let description: String
    let sortOrder: Int
}
```

Repository 增加：

```text
GET /competitions/recommendation-tiers
```

### 3.2 列表页 B12

文件：`ios/OneMore/Features/Competitions/CompetitionsView.swift`

| 现状 | 改为 |
|---|---|
| `OMSeg(... "Tier A")` | chips：`全部` / `优先推荐` / `可报名` / `补充参考`（label 来自目录或列表项映射） |
| 选中仍本地存 `"A"`/`"B"`/`"C"` | **继续**把 code 传给 `repository.list(tier:)` |
| 卡片 `OMChip("TIER \(item.recommendationTier)")` | `OMChip(item.recommendationLabel)`；A 可用现有强调样式 |
| 页脚只解释「已核验」 | 追加一句推荐档说明（可用目录 description 拼，或固定短文案） |

推荐页脚短文案（可直接贴）：

> 「优先推荐」来自学校或权威学会官方通知；「可报名」为官方可核验赛事；「补充参考」多为商业主办，自行判断是否适合。推荐档不是比赛难度，也不是你的信任等级。

### 3.3 详情页 B12.1

文件：`ios/OneMore/Features/Competitions/CompetitionDetailView.swift`

| 现状 | 改为 |
|---|---|
| `TIER \(item.recommendationTier) · 已核验 · 队伍 …` | `\(item.recommendationLabel) · 已核验 · 队伍 …` |
| 无解释 | 可选：在卡片或 `OMNote` 用 `item.recommendationDescription` 一行说明 |

### 3.4 其它搜索清理

全仓搜：`TIER`、`Tier`、`recommendationTier` 展示路径，确保**没有任何**用户可见的 `Tier A/B/C`。

原型画板若写死了 `Tier`，同步改成中文标签（`ScreensB` 等），避免设计回放与真机不一致。

### 3.5 测试 / UITest

若有断言文案含 `TIER` / `Tier A`，改为 `优先推荐` 等 label。  
Accessibility id 可继续用 code（如 `recommendation-tier-A`），**可见字符串必须是中文 label**。

---

## 4. 验收清单（前端完成标准）

- [ ] 列表筛选显示：`全部 | 优先推荐 | 可报名 | 补充参考`，不再出现 `Tier A/B/C`
- [ ] 点「优先推荐」请求 `GET /competitions?recommendation_tier=A`（code 正确）
- [ ] 卡片 chip 显示 `recommendation_label`，不显示 `TIER A`
- [ ] 详情副标题用 label；可选展示 description
- [ ] 页脚或空态能解释推荐档 ≠ 难度 ≠ 信任等级
- [ ] 模型能解码新字段；旧 mock 数据补齐 `recommendation_label` / `recommendation_description`
- [ ] 联调 OpenAPI：`CompetitionView` 含新字段；存在 path `/competitions/recommendation-tiers`

---

## 5. 不要做的事

1. **不要**把信任等级 T0–T4 和推荐档混在同一套 UI 文案里。  
2. **不要**前端本地硬编码另一套 A→文案映射当长期方案（可 fallback，但应以 API 字段为准）。  
3. **不要**改筛选 query 为中文；query 永远是 `A|B|C`。  
4. **不要**暗示 C 档「不能报 / 不靠谱」——C 仍是可核验可行动赛事，只是降权补充。  
5. **不要**改后端存库结构；标签已在读路径派生。

---

## 6. 参考路径

| 用途 | 路径 |
|---|---|
| 标签单一真相 | `onemore/modules/competitions/recommendation.py` |
| API | `onemore/modules/competitions/api.py` |
| View 序列化 | `onemore/modules/competitions/service.py` · `_view` |
| Schema | `onemore/modules/competitions/schemas.py` · `CompetitionView` / `RecommendationTierView` |
| 验收说明 | `docs/09_比赛雷达V1.1质量验收与入库说明.md` §3 |
| 联调摘要 | `docs/06_后端实现与前端联调.md` |
| OpenAPI | `openapi/onemore.openapi.json` |
| 后端测试 | `tests/test_competitions.py` |

---

## 7. 可直接转给前端 Agent 的执行提示词

```text
任务：按后端已定稿，把 iOS 比赛雷达的 Tier A/B/C 改成用户友好中文标签。

背景：
- recommendation_tier 存库/筛选码仍是 A|B|C，不是难度等级，也不是用户信任等级。
- 后端已在 CompetitionView 增加 recommendation_label / recommendation_description。
- 新增 GET /competitions/recommendation-tiers 返回筛选目录。
- 对照文档：docs/handoffs/frontend-competition-recommendation-tier.md

必须完成：
1. APIModels.Competition 解码 recommendationLabel、recommendationDescription。
2. CompetitionsView：筛选条改为「全部 / 优先推荐 / 可报名 / 补充参考」；请求仍传 A/B/C。
3. 列表卡片 chip、详情副标题禁止再显示 “Tier A” / “TIER A”，改用 recommendationLabel。
4. 页脚或详情加一句说明：推荐档是运营推荐权重，不是比赛难度。
5. 优先用 GET /competitions/recommendation-tiers 驱动筛选 chips；若暂不接目录接口，至少用接口下发的 label 字段，不要本地英文 Tier。
6. 全仓清理用户可见的 Tier A/B/C 文案；更新相关 UITest / mock。

验收：
- 真机/模拟器列表与详情只见中文标签。
- 筛选「优先推荐」实际请求 recommendation_tier=A。
- 解码真实 /competitions 响应不因缺字段失败。
```
