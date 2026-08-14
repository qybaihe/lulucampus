# 噜噜自进化画像

课表和抖音，是目前最无感、也最准的冷启动方式。  
但画像的最终形态不该停在「导入那天」。

一个人是什么样的人，更取决于他在平台上的每一次真实行为：  
**找什么样的搭子，参加什么样的比赛，把哪些局真正打完。**

这套自进化模型放在主仓库分支 `feat/lulu-portrait-evolve`，目录是 `lulu-portrait-evolve/`。主站里已有雏形，但上线后学习回写不能稳定触发，所以没有直接推给用户。这里用事件源把学习路径写死：来一条行为，就校准一次；同一条事件重放，不会把画像抖成另一张脸。先在分支里长稳，再接回主站。

## 为什么最有效的信息渠道是「平台行为」

| 渠道 | 无感 | 准 | 会过时 |
|---|---|---|---|
| 用户自填标签 | 低 | 低（我希望别人怎么看我） | 会 |
| 教务课表 / 培养方案 | 高 | 高（学校记录，不可自我美化） | 慢 |
| 抖音兴趣画像 | 高 | 高（口味快照） | 会 |
| **每一次找搭子、参赛、成局** | **最高** | **最高（他正在过的日子）** | **不会** |

冷启动仍然用前两行：零填表，Day 1 就能匹配。  
自进化吃的是第四行——行为会覆盖过时的口味，但**不会擦掉**已验证的课表事实。

于是画像变成一件会呼吸的东西：用得越久，越像这个人。

## 三层，而不是一张会互相覆盖的表

```
academic   课表 / 培养方案     半衰期 365 天   只可加强，不可被行为抹掉
taste      抖音兴趣快照        半衰期 180 天   先验，不锁死主标签
lived      找搭子 / 参赛 / 成局 半衰期  60 天   真正的自进化层
```

派生主标签时按 `0.25 / 0.30 / 0.45` 混合三层。  
行为权重最高，所以「去年喜欢的视频」敌不过「这个月连续打完的两场比赛」。

找队友时**自己站的位置**写入 `roles_offered`，**缺的位置**只写入 `roles_sought`。  
「我做后端，缺前端和产品」不会把前端算成她会的技能——互补比自述更能说明这个人。

## 稳定触发契约

主站雏形不稳定，通常死在四件事上。这里逐条钉死：

1. **事件源，不靠巡检。** 学习发生在 `ingest` 同步路径，不依赖「有时会跑、有时不会」的定时任务。
2. **`event_id` 幂等。** 重试、重复投递、客户端连点，都不会把同一场球打成两场人格。
3. **主标签带滞回。** 挑战者必须高出当前值 `0.06` 才允许翻转，避免卡片在两个标签之间闪。
4. **lived 与 academic 隔离。** 课表重跑、抖音重导，都不得清空行为层；画像是投影，事件日志永远可以整段回放。
5. **有意义才对外发射。** 分数变化小于 `0.01` 且主标签没变时，不发 `portrait.updated`。

## 事件与证据强度

| 事件 | 强度 | 它在说什么 |
|---|---|---|
| `browse_competition` | 0.08 | 看过，几乎是噪声 |
| `post_intent` / `seek_teammate` | 0.35–0.40 | 他想干什么、想找谁 |
| `join_team` / `join_competition` | 0.55 | 愿意把自己押进去 |
| `complete_gathering` | 0.80 | 这件事真实发生过 |
| `recur_gathering` | 1.00 | 同一桌人愿意再来 —— 最强身份信号 |
| `late_exit` | 0.20（负向） | 只收缩场景，不改写这个人是谁 |

更新是饱和型 EMA：越接近 1 越难再涨，时间按半衰期衰减。不调用大模型，离线可复现。

## 快速开始

```bash
cd lulu-portrait-evolve
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
portrait-evolve replay fixtures/linyuan_timeline.json
```

林予安这条时间线：课表 + 抖音冷启动 → 智能应用开发大赛组队（自己后端/数据，缺前端/产品）→ 英东羽毛球成局并复局 → 数模再找建模和论文。回放后你会看到主标签仍落在探索型 Builder / AI 实践派附近，但 `health_sports`、`roles_sought` 和「真正打完的局」已经是行为写出来的，不是导入那天填的。

## 当作独立服务

```bash
pip install -e ".[api]"
portrait-evolve serve --port 8787
```

```
POST /v1/events
POST /v1/replay
GET  /v1/portraits/{user_id}
GET  /v1/portraits/{user_id}/explain
GET  /health
```

主站 `lulucampus` 继续负责教务和抖音冷启动；本系统只吃行为事件，吐出永不过时的 lived 层。用 HTTP 或事件总线接回去即可，不必把学习逻辑再嵌进业务库。

## 库用法

```python
from portrait_evolve import BehaviorEvent, PortraitStore

store = PortraitStore("portraits.db")
store.ingest(BehaviorEvent.from_dict({
    "event_id": "intent-1",
    "user_id": "u_demo_1",
    "type": "post_intent",
    "occurred_at": "2026-08-03T10:15:00+08:00",
    "scene": "比赛组队",
    "mode": "complementary",
    "competition": "智能应用开发大赛",
    "roles_offered": ["backend"],
    "roles_sought": ["frontend"],
    "text": "我做后端，缺前端",
}))
print(store.get("u_demo_1").public_view())
```

## 和噜噜成局的关系

这不是另一套社交产品。它是从成局产品里拆出的画像进化内核：

- 词汇表对齐主站：`explorer_builder`、`ai_programming`、`backend`、比赛组队 / 运动搭子。
- 伦理边界对齐主站：只用「修过什么 / 做过什么」，不用「修得怎么样」。
- 演示人物对齐主站剧组：`fixtures/linyuan_timeline.json` 就是林予安。

主站可以继续把冷启动做稳；自进化在这里单独长，长稳了再接回去。
