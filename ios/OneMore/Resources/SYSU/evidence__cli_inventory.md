# SysU Anything CLI 盘点（南校园优先版）

- 采集日期：2026-08-11
- 可执行文件：`/Users/baihe/.local/bin/sysu-anything`
- 本地项目：`/Users/baihe/Documents/AnythingSYSU`
- 原始只读证据目录：`/Users/baihe/Documents/compusone/data/reference/sysu/evidence/raw`
- 原则：仅把清洗后的静态字段写入正式数据集；登录检查不写入姓名、学号、余额、课表、Token、Cookie、Session。

## 已执行命令与结果

| 命令 | 结果 | 正式资产用途 |
|---|---|---|
| `sysu-anything bus --bus 1 --json` | 工作日6条线路、61个发车时刻 | 写入广州校区班车静态表 |
| `sysu-anything bus --bus 0 --json` | 节假日4条线路、8个发车时刻 | 写入广州校区班车静态表 |
| `sysu-anything qg routes` | 返回珠海/南/东校园键与珠海站点键 | 写入岐关静态字典 |
| `sysu-anything qg list --today --all --json` | 返回站点名称、地址、坐标与路线证据 | 只写入站点与路线键，不写入日期级动态字段 |
| `sysu-anything usc apps --json` | 返回课室、学生活动中心、会议场所3类应用 | 写入来源盘点 |
| `sysu-anything usc schema classroom --json` | 返回课室字段定义 | 写入来源盘点，不构造动态课室 |
| `sysu-anything usc schema activity --json` | 返回活动场地字段定义 | 写入来源盘点 |
| `sysu-anything usc schema meeting --json` | 返回会议场所字段定义 | 写入来源盘点 |
| `sysu-anything usc reserve-config --json` | 返回预约配置元数据 | 写入来源盘点，不写入预约结果 |
| `sysu-anything usc activity rooms --json` | 返回结果仅见东校园/深圳场地 | 南校园活动场地记录留缺口 |
| `sysu-anything usc meeting campuses --json` | 返回5个系统校区名 | 交叉核验五校园 ID |
| `sysu-anything usc classroom campuses --json` | 返回5个系统校区名/参数 | 交叉核验五校园 ID |
| `sysu-anything usc meeting venues --campus 南校园 --json` | 返回空列表 | 不自行构造南校园动态会议场地 |
| `sysu-anything usc classroom rooms --campus 南校园 --date 2026-08-11 --section-start 1 --section-end 2 --json` | 返回 `CODE_ERROR` | 不自行构造南校园动态课室 |
| `sysu-anything jwxt status` | 登录状态正常；状态字段显示2025-2026第2学期第3周 | 只记录为缺口，不写入个人课表 |
| `sysu-anything jwxt section-times --school-year 2026-1 --json` | 返回11节标准节次，和USC节次时间一致 | 写入节次表 |
| `sysu-anything gym profile` | 当前请求链失败 | 只记录体育官网静态场馆，缺少实时参数 ID |
| `sysu-anything gym venue-types --json` | 当前请求链失败 | 不写入动态场地类型 |
| `sysu-anything libic whoami` | 站点启动响应非JSON/请求失败 | 不写入图书馆房间参数 |
| `sysu-anything libic room-types --json` | 站点启动响应非JSON/请求失败 | 只保留图书馆建筑与官方服务信息 |

## 原始文件

正式包只引用以下原始证据文件的采集结论，不把原始动态字段导入静态资产：

- `bus_workday.json`
- `bus_holiday.json`
- `qg_routes.txt`
- `qg_today_all.json`
- `usc_apps.txt`
- `usc_schema_classroom.txt`
- `usc_schema_activity.txt`
- `usc_schema_meeting.txt`
- `usc_reserve_config.txt`
- `usc_activity_rooms.txt`
- `usc_meeting_campuses.txt`
- `usc_classroom_campuses.txt`
- `usc_meeting_venues_south.txt`
- `usc_classroom_rooms_south.txt`
- `jwxt_section_times_fall_2026.txt`

原始文件位于 `/Users/baihe/Documents/compusone/data/reference/sysu/evidence/raw`，仅作为证据留存；服务端导入时只读取正式 JSON/CSV 数据集。
