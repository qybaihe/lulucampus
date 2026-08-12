/* 差一个 · ONE MORE — 屏幕定义 1/3
   A · 认证与初始化（8）  B · 今天与校园工具（18） */

defineScreens([
/* ================= A · 认证与初始化 ================= */
{
  id: "A1",
  nav: "",
  body: `
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:70vh">
      ${luluHTML("home.idle", "lulu-empty")}
      <div class="t-t2 mt-4">差一个</div>
      <div class="t-foot mt-1">ONE MORE · 正在为你准备</div>
      <div class="mt-6" style="width:120px"><div class="om-progress"><i style="width:64%"></i></div></div>
      <div class="t-cap mt-3">正在检查登录状态…</div>
    </div>
    <div class="om-card tight mt-4">
      <div class="t-foot center">冷启动路由：未登录 → ${` `}<b>认证说明</b> · 已登录 → <b>今天</b> · 会话失效 → <b>认证恢复</b></div>
      <div class="flex mt-3" style="justify-content:center;flex-wrap:wrap">
        ${P.btn("未登录路径", "ghost sm", "A2")}
        ${P.btn("会话失效路径", "ghost sm", "G3")}
        ${P.btn("已登录路径", "ghost sm", "tab:today")}
      </div>
    </div>`,
},
{
  id: "A2",
  body: `
    <div class="center mt-6">${luluHTML("home.reply", "lulu-hero")}</div>
    <div class="t-hero center mt-4">说一句想做的事，<br>剩下的交给 Lulu</div>
    <div class="t-call muted center mt-3" style="max-width:290px;margin-left:auto;margin-right:auto">
      想找人打比赛、凑人打球、约研讨室赶 DDL——<br>人凑齐、场订好，它就退场。
    </div>
    <div class="om-card mt-6">
      ${P.row({ icon: P.stickerImg("round-table.png", "st-24"), title: "最小单位是「一个局」", sub: "没有人物卡片，没有刷人，没有加好友" })}
      ${P.row({ icon: P.stickerImg("hourglass.png", "st-24"), title: "AI 越早退场越好", sub: "事办成就走，剩下的你们自己聊" })}
      ${P.row({ icon: P.stickerImg("approval-stamp.png", "st-24"), title: "凑不齐就安静结束", sub: "没有人知道你开过口" })}
    </div>`,
  footer: `${P.btn("用企业微信扫码认证", "primary", "A3")}
    <div class="t-cap center mt-2">仅限中山大学师生 · 全程不输入密码</div>`,
},
{
  id: "A3",
  nav: P.nav("扫码认证", { back: "A2" }),
  body: `
    <div class="center mt-4">${luluHTML("home.listening", "lulu-header", "打开企业微信，扫一扫")}</div>
    <div class="qr-box mt-4">
      <svg viewBox="0 0 21 21" fill="var(--ink)"><path d="M0 0h7v7H0zM2 2v3h3V2zM14 0h7v7h-7zM16 2v3h3V2zM0 14h7v7H0zM2 16v3h3v-3zM9 0h3v3H9zM9 5h2v2H9zM14 9h3v2h-3zM18 9h3v3h-3zM9 9h2v3H9zM12 10h2v2h-2zM9 14h3v2H9zM13 13h2v2h-2zM16 14h2v2h-2zM19 14h2v2h-2zM14 17h3v2h-3zM18 18h3v3h-3zM9 18h2v3H9zM12 19h2v2h-2z"/></svg>
    </div>
    <div class="t-foot center mt-4">企业微信 → 工作台 → 扫一扫<br>认证只确认「你是中大人」，不读取聊天</div>
    <div class="om-note mt-5"><img src="${ST}access-card.png" alt=""><span>认证信息仅来自学校统一身份平台：姓名、学号、院系、年级。我们无法也不会修改。</span></div>`,
  footer: P.btn("我已在企业微信完成扫码", "primary", "A4"),
},
{
  id: "A4",
  nav: P.nav("授权范围", { back: "A3" }),
  large: "只给你愿意给的",
  largeSub: "每一项都可以单独关闭，之后随时改",
  body: `
    <div class="om-card">
      ${P.row({ icon: P.stickerImg("books-stack.png", "st-24"), title: "课表", sub: "用来找你的真实空档", right: P.switch(true) })}
      ${P.row({ icon: P.stickerImg("notebook-open.png", "st-24"), title: "培养方案", sub: "生成能力标签的来源之一", right: P.switch(true) })}
      ${P.row({ icon: P.stickerImg("desk-calendar.png", "st-24"), title: "选课记录", sub: "辅助判断你上过哪些课", right: P.switch(false) })}
      ${P.row({ icon: P.stickerImg("approval-stamp.png", "st-24"), title: "代理执行", sub: "订场、写日历前的最后一步确认权永远在你手里", right: P.switch(true) })}
    </div>
    ${P.note("关闭某一项只会影响对应能力：例如关闭课表后，Lulu 无法自动找空档，你仍可以手动选时间。", "nameplate-blank.png")}
    <button class="om-btn text mt-3" data-go="A8">看看权限被拒绝时会怎样</button>`,
  footer: P.btn("继续", "primary", "A5"),
},
{
  id: "A5",
  nav: P.nav("画像初始化", { back: "A4" }),
  body: `
    <div class="center mt-6">${luluHTML("home.thinking", "lulu-hero", "正在读你的课表和培养方案…")}</div>
    <div class="om-card mt-6">
      <div class="om-timeline">
        <div class="tl-item done"><b>统一身份认证</b><div class="t-foot">已确认 · 电子信息与工程学院 2023 级</div></div>
        <div class="tl-item done"><b>读取课表</b><div class="t-foot">本学期 6 门课 · 识别出 9 段固定空档</div></div>
        <div class="tl-item now"><b>生成能力标签</b><div class="t-foot">正在从培养方案与选课记录提取…</div></div>
        <div class="tl-item"><b>整理可用时间</b><div class="t-foot">稍后完成</div></div>
      </div>
    </div>
    <div class="t-foot center">不用填任何表。读完会给你确认。</div>`,
},
{
  id: "A6",
  nav: P.nav("画像确认", { back: "A4" }),
  large: "确认三件事",
  largeSub: "这是 Lulu 帮你组队时唯一依据的画像",
  body: `
    ${P.section("认证事实 · 来自学校，不可改")}
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("teaching-building.png", "st-24"), title: "中山大学 · 东校园", sub: "电子信息和通信工程学院 · 2023 级本科" })}
    </div>
    ${P.section("能力标签 · 每个都有来源")}
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("algorithm-gear.png", "st-24"), title: "算法", sub: "来源：已修《数据结构与算法》92 分", right: `<span class="om-chip solid">课程</span>` })}
      ${P.row({ icon: P.stickerImg("backend-server.png", "st-24"), title: "后端", sub: "来源：已修《操作系统》《数据库系统》", right: `<span class="om-chip solid">课程</span>` })}
      ${P.row({ icon: P.stickerImg("design-palette.png", "st-24"), title: "设计", sub: "来源：你稍后可以自己加", right: `<span class="om-chip">自述</span>` })}
    </div>
    ${P.section("可用时间 · 来自课表空档")}
    <div class="om-card tight">
      <div class="flex wrap">
        ${P.chip("周二 19:00–21:30", "soft")}${P.chip("周三 14:00–17:00", "soft")}${P.chip("周五 16:00 后", "soft")}${P.chip("周末全天", "soft")}
      </div>
      <div class="t-foot mt-3">只展示「什么时候有空」，不展示忙碌原因。</div>
    </div>`,
  footer: P.btn("确认，继续", "primary", "A7"),
},
{
  id: "A7",
  nav: P.nav("社交开关", { back: "A6" }),
  body: `
    <div class="center mt-6">${luluHTML("core.care", "lulu-header")}</div>
    <div class="t-t1 center mt-4">社交能力，默认关闭</div>
    <div class="t-call muted center mt-3" style="max-width:280px;margin-left:auto;margin-right:auto">
      打开后，你发起的局可以公开招募，成局后可以和队友聊天。<br>不开，也能用全部校园工具。
    </div>
    <div class="om-card mt-6">
      ${P.row({ icon: P.stickerImg("chat-bubble.png", "st-24"), title: "开启社交能力", sub: "公开局 · 局内群聊 · 搭子关系", right: P.switch(false) })}
    </div>
    ${P.note("即使开启：双向确认前对方看不到你的真实身份；没有陌生人私聊；没有已读回执和在线状态。", "access-card.png")}`,
  footer: `${P.btn("先不开，进入 App", "ghost", "tab:today")}
    <div class="mt-2">${P.btn("开启并进入", "primary", "tab:today")}</div>`,
},
{
  id: "A8",
  nav: P.nav("系统权限", { back: "A4" }),
  body: `
    ${P.stateView("denied")}
    <div class="om-card">
      <div class="t-t3 mb-2">权限被拒后影响了什么</div>
      ${P.row({ icon: P.stickerImg("desk-calendar.png", "st-24"), title: "日历写入：未开启", sub: "订场成功后无法自动写进日历，改为手动添加" })}
      ${P.row({ icon: P.stickerImg("alarm-clock.png", "st-24"), title: "通知：未开启", sub: "凑齐、待确认不会推送，只在 App 内显示" })}
    </div>
    ${P.note("拒绝不会惩罚你：所有核心功能仍可用，只是少了自动化。恢复路径永远是这一页，不会藏在系统设置里让你找。", "chat-bubble.png")}`,
  footer: P.btn("去系统设置开启", "primary", "", "data-toast=\"已打开系统设置（演示）\""),
},

/* ================= B · 今天与校园工具 ================= */
{
  id: "B1", tab: "today",
  large: "今天",
  largeSub: "8 月 12 日 · 周三 · 东校园",
  nav: P.nav("", { right: `<button class="nav-back" data-go="G1" aria-label="问 Hermes">${icon("spark", 18)}</button>` }),
  body: `
    <div class="om-card" data-go="B10" style="cursor:pointer">
      <div class="flex">
        ${luluHTML("home.reply", "lulu-confirm")}
        <div class="grow">
          <div class="t-t3">图书馆 4 楼今晚空着</div>
          <div class="t-foot mt-1">你的《操作系统》作业周四截止，19:00–21:30 正好是你的空档。</div>
        </div>
      </div>
      <div class="flex mt-3">
        ${P.btn("一键发起研讨局", "primary sm", "B10")}
        ${P.btn("忽略", "text sm", "", "data-toast=\"已忽略，不会重复提醒\"")}
      </div>
    </div>

    ${P.section("今日日程", { label: "课表", go: "B3" })}
    <div class="om-card tight">
      ${P.row({ icon: icon("clock", 20), title: "数据结构与算法", sub: "10:00–11:40 · 教学楼 B204", go: "B3.1", right: `<span class="om-chip">1 小时后</span>` })}
      ${P.row({ icon: icon("clock", 20), title: "大学体育 · 羽毛球", sub: "16:00–17:30 · 体育馆 2 号场", go: "B3.1" })}
    </div>

    ${P.section("待确认")}
    <div class="om-card tight" data-go="E3" style="cursor:pointer">
      ${P.row({ icon: P.stickerImg("hourglass.png", "st-24"), title: "数学建模 · 还差你的确认", sub: "4 人局 · 剩 3 人已确认 · 截止今晚 22:00", go: "E3", right: `<span class="gap-badge">差你 1 票</span>` })}
    </div>

    ${P.section("校园工具")}
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("books-stack.png", "st-24"), title: "我的课表", sub: "本周 6 门课", go: "B3" })}
      ${P.row({ icon: P.stickerImg("alarm-clock.png", "st-24"), title: "作业与 DDL", sub: "2 个本周截止", go: "B4", right: `<span class="om-chip gap">1 紧急</span>` })}
      ${P.row({ icon: P.stickerImg("badminton.png", "st-24"), title: "体育场馆", sub: "羽毛球今晚有空场", go: "B5" })}
      ${P.row({ icon: P.stickerImg("seminar-room-sign.png", "st-24"), title: "研讨室", sub: "图书馆 4 楼当前空闲 3 间", go: "B6" })}
      ${P.row({ icon: P.stickerImg("poster-blank.png", "st-24"), title: "校园活动", sub: "本周 12 场", go: "B7" })}
      ${P.row({ icon: P.stickerImg("notebook-open.png", "st-24"), title: "组会与课题", sub: "周五 14:00 导师组会", go: "B8" })}
      ${P.row({ icon: P.stickerImg("school-bus.png", "st-24"), title: "班车与节次", sub: "东校园 ⇄ 南校园", go: "B9" })}
    </div>

    ${P.section("我的局", { label: "全部", go: "E1" })}
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("trophy.png", "st-24"), title: "数学建模国赛冲刺", sub: "已订研讨室 · 周五 19:00", go: "E2", right: `<span class="om-chip solid">已成局</span>` })}
      ${P.row({ icon: P.stickerImg("basketball.png", "st-24"), title: "周五晚篮球半场", sub: "匿名招募中", go: "D4", right: `<span class="om-chip gap">缺 2</span>` })}
    </div>`,
},
{
  id: "B2",
  nav: P.nav("Hermes", { back: "__back" }),
  body: `
    <div class="center mt-3">${luluHTML("home.listening", "lulu-header")}</div>
    <div class="chat-list mt-4">
      <div class="bubble me">明天下午南校园图书馆开吗？</div>
      <div class="bubble">开。明天是工作日，南校园图书馆 8:00–22:30 开放。你 14:00–17:00 没课，要帮你看看研讨室吗？</div>
      <div class="bubble me">周五晚上体育馆羽毛球还有场吗？</div>
      <div class="bubble">有。周五 19:00–21:00 还剩 2 片羽毛球场。你周五 16:00 后没课——要订的话我会先给你看预览，确认后才下单。</div>
    </div>`,
  footer: `<div class="flex">
      <input class="om-input" placeholder="问校园相关的事…" style="min-height:44px">
      <button class="nav-back" style="width:44px;height:44px" aria-label="语音输入">${icon("mic", 18)}</button>
    </div>
    <div class="t-cap center mt-2">只回答校园事实与可用性 · 不评价人</div>`,
},
{
  id: "B3",
  nav: P.nav("我的课表", { back: "tab:today" }),
  body: `
    <div class="om-seg mb-3" data-seg><button class="on">本周</button><button>下周</button><button>整学期</button></div>
    <div class="om-card tight">
      <div class="schedule-grid">
        <span></span><span class="sg-head">一</span><span class="sg-head">二</span><span class="sg-head">三</span><span class="sg-head">四</span><span class="sg-head">五</span>
        <span class="sg-time">1-2</span><span class="sg-cell"></span><span class="sg-cell has" data-go="B3.1">高等数学</span><span class="sg-cell"></span><span class="sg-cell has">大学英语</span><span class="sg-cell"></span>
        <span class="sg-time">3-4</span><span class="sg-cell has">操作系统</span><span class="sg-cell"></span><span class="sg-cell has" data-go="B3.1">数据结构</span><span class="sg-cell"></span><span class="sg-cell has">概率论</span>
        <span class="sg-time">5-6</span><span class="sg-cell free">空档</span><span class="sg-cell has">体育</span><span class="sg-cell free">空档</span><span class="sg-cell has">毛概</span><span class="sg-cell free">空档</span>
        <span class="sg-time">7-8</span><span class="sg-cell"></span><span class="sg-cell"></span><span class="sg-cell"></span><span class="sg-cell"></span><span class="sg-cell"></span>
      </div>
    </div>
    ${P.note("黄色虚线格是你的固定空档——Lulu 只在这些时间里帮你攒局。课表来自教务系统，别人看不到。", "desk-calendar.png")}`,
},
{
  id: "B3.1",
  nav: P.nav("课程详情", { back: "B3" }),
  body: `
    <div class="om-card">
      <div class="flex">${P.stickerImg("books-stack.png", "st-56")}
        <div><div class="t-t2">数据结构与算法</div><div class="t-foot mt-1">CS2101 · 3 学分 · 必修</div></div>
      </div>
      <div class="divider"></div>
      ${P.row({ icon: icon("clock", 20), title: "周三 10:00–11:40", sub: "第 1–16 周" })}
      ${P.row({ icon: icon("pin", 20), title: "东校园 教学楼 B204", sub: "距你当前位置步行约 6 分钟" })}
      ${P.row({ icon: icon("doc", 20), title: "作业 3：二叉树遍历", sub: "周四 23:59 截止", go: "B4.1", right: `<span class="om-chip gap">明天截止</span>` })}
    </div>
    ${P.note("这里不会出现同课同学名单。想找人一起复习，可以从作业详情发起一个局。", "access-card.png")}
    <div class="mt-3">${P.btn("就这门课发起复习局", "primary", "D1")}</div>`,
},
{
  id: "B4",
  nav: P.nav("作业与 DDL", { back: "tab:today" }),
  body: `
    <div class="om-card tight" style="border-color:var(--yolk);border-width:2px">
      ${P.row({ icon: P.stickerImg("alarm-clock.png", "st-24"), title: "作业 3：二叉树遍历", sub: "数据结构与算法 · 剩 31 小时", go: "B4.1", right: `<span class="om-chip gap">最紧急</span>` })}
    </div>
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("notebook-open.png", "st-24"), title: "实验报告 2", sub: "操作系统 · 剩 4 天", go: "B4.1" })}
      ${P.row({ icon: P.stickerImg("marker.png", "st-24"), title: "英语视听说 Unit 5", sub: "大学英语 · 剩 6 天", go: "B4.1" })}
    </div>
    ${P.note("按剩余时间排序，不按课程重要度打分。DDL 来自教务系统与课程群公告的公开信息。", "hourglass.png")}`,
},
{
  id: "B4.1",
  nav: P.nav("作业详情", { back: "B4" }),
  body: `
    <div class="om-card">
      <div class="t-t2">作业 3：二叉树遍历</div>
      <div class="t-foot mt-1">数据结构与算法 · 周四 23:59 截止</div>
      <div class="gap-hero mt-4"><span class="n">31</span><span class="of">小时后截止</span></div>
      <div class="divider"></div>
      <div class="t-call">实现前序 / 中序 / 后序遍历的递归与非递归版本，提交 PDF 报告与源码。占平时成绩 10%。</div>
    </div>
    <div class="om-card">
      <div class="t-t3 mb-2">你的空档里，这两段最适合</div>
      ${P.row({ icon: icon("clock", 20), title: "今晚 19:00–21:30", sub: "图书馆 4 楼研讨室当前有空", right: P.btn("发起研讨局", "primary sm", "B10") })}
      ${P.row({ icon: icon("clock", 20), title: "明天 14:00–17:00", sub: "宿舍 / 自习均可", right: P.btn("单人行动", "ghost sm", "B11") })}
    </div>`,
},
{
  id: "B5",
  nav: P.nav("体育场馆", { back: "tab:today" }),
  body: `
    <div class="cal-strip mb-3">
      <div class="cal-day"><div class="d mono">12</div><div class="w">今天</div><div class="dotline"><i></i></div></div>
      <div class="cal-day on"><div class="d mono">13</div><div class="w">周四</div><div class="dotline"><i></i><i></i></div></div>
      <div class="cal-day"><div class="d mono">14</div><div class="w">周五</div><div class="dotline"><i></i></div></div>
      <div class="cal-day"><div class="d mono">15</div><div class="w">周六</div><div class="dotline"></div></div>
      <div class="cal-day"><div class="d mono">16</div><div class="w">周日</div><div class="dotline"><i></i><i></i></div></div>
    </div>
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("badminton.png", "st-24"), title: "羽毛球馆", sub: "东校园体育馆 2F", go: "B5.1", right: `<span class="om-chip gap">今晚有空</span>` })}
      ${P.row({ icon: P.stickerImg("basketball.png", "st-24"), title: "篮球场", sub: "东校园室外场", go: "B5.1", right: `<span class="om-chip">3 片空</span>` })}
      ${P.row({ icon: P.stickerImg("table-tennis.png", "st-24"), title: "乒乓球馆", sub: "东校园体育馆 1F", go: "B5.1", right: `<span class="om-chip">已满</span>` })}
      ${P.row({ icon: P.stickerImg("football.png", "st-24"), title: "足球场", sub: "东校园真草场", go: "B5.1", right: `<span class="om-chip">1 片空</span>` })}
    </div>
    ${P.note("只显示场地有没有空，不显示「现在谁在场」。", "access-card.png")}`,
},
{
  id: "B5.1",
  nav: P.nav("羽毛球馆 · 时段", { back: "B5" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: icon("clock", 20), title: "18:00–19:00", sub: "2 号场 · 4 人半场", right: P.btn("选这个", "ghost sm", "B11") })}
      ${P.row({ icon: icon("clock", 20), title: "19:00–20:00", sub: "2 号场 · 4 人半场", right: P.btn("选这个", "ghost sm", "B11") })}
      ${P.row({ icon: icon("clock", 20), title: "20:00–21:00", sub: "5 号场 · 可包场", right: P.btn("选这个", "ghost sm", "B11") })}
    </div>
    <div class="om-card">
      <div class="flex">${luluHTML("home.reply", "lulu-confirm")}
        <div class="t-call grow">一个人订场可以直接订；<b>缺球友的话，我可以顺手帮你开个局</b>，人齐了一起订。</div>
      </div>
    </div>
    ${P.btn("差球友，开个局", "primary", "D1")}`,
},
{
  id: "B6",
  nav: P.nav("研讨室", { back: "tab:today" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("seminar-room-sign.png", "st-24"), title: "图书馆 4F · 研讨间", sub: "4–8 人 · 白板 · 插座", go: "B6.1", right: `<span class="om-chip gap">3 间空闲</span>` })}
      ${P.row({ icon: P.stickerImg("study-lamp.png", "st-24"), title: "图书馆 6F · 静音研讨间", sub: "2–4 人 · 需安静", go: "B6.1", right: `<span class="om-chip">1 间空闲</span>` })}
      ${P.row({ icon: P.stickerImg("teaching-building.png", "st-24"), title: "教学楼 C 区 · 讨论室", sub: "6–10 人 · 可投影", go: "B6.1", right: `<span class="om-chip">今晚全满</span>` })}
    </div>
    ${P.note("研讨室预约以学校图书馆系统为准。Lulu 只做代预约，且每次都会先给你看预览。", "chat-bubble.png")}`,
},
{
  id: "B6.1",
  nav: P.nav("图书馆 4F · 选时段", { back: "B6" }),
  body: `
    <div class="cal-strip mb-3">
      <div class="cal-day on"><div class="d mono">12</div><div class="w">今天</div><div class="dotline"><i></i></div></div>
      <div class="cal-day"><div class="d mono">13</div><div class="w">周四</div><div class="dotline"><i></i></div></div>
      <div class="cal-day"><div class="d mono">14</div><div class="w">周五</div><div class="dotline"></div></div>
    </div>
    <div class="om-card tight">
      ${P.row({ icon: icon("clock", 20), title: "14:00–16:00", sub: "研讨间 4B · 6 人位", right: P.btn("选", "ghost sm", "B11") })}
      ${P.row({ icon: icon("clock", 20), title: "16:00–18:00", sub: "研讨间 4A · 8 人位", right: P.btn("选", "ghost sm", "B11") })}
      ${P.row({ icon: icon("clock", 20), title: "19:00–21:30", sub: "研讨间 4C · 6 人位 · 与你的空档重合", right: `<span class="om-chip gap">推荐</span>` })}
    </div>
    ${P.btn("用 19:00–21:30 发起研讨局", "primary", "B10")}`,
},
{
  id: "B7",
  nav: P.nav("校园活动", { back: "tab:today" }),
  body: `
    ${P.note("未登录也能浏览这一页。报名才需要认证。", "poster-blank.png")}
    <div class="om-card tight mt-3">
      ${P.row({ icon: P.stickerImg("poster-blank.png", "st-24"), title: "「人工智能+X」交叉学科讲座", sub: "周四 15:00 · 南校园梁銶琚堂", go: "B7.1" })}
      ${P.row({ icon: P.stickerImg("poster-blank.png", "st-24"), title: "社团招新夜市", sub: "周五 18:30 · 东校园生活区广场", go: "B7.1" })}
      ${P.row({ icon: P.stickerImg("poster-blank.png", "st-24"), title: "校友分享：从实验室到创业", sub: "周六 10:00 · 珠海校区", go: "B7.1" })}
    </div>`,
},
{
  id: "B7.1",
  nav: P.nav("活动详情", { back: "B7" }),
  body: `
    <div class="om-card">
      <div class="center" style="background:var(--ink-06);border-radius:var(--r-md);padding:28px 0">${P.stickerImg("poster-blank.png", "st-96")}</div>
      <div class="t-t2 mt-3">「人工智能+X」交叉学科讲座</div>
      <div class="t-foot mt-1">主办：计算机学院 · 周四 15:00–17:00 · 南校园梁銶琚堂</div>
      <div class="t-call mt-3">四位来自医学、法学、材料与计算机的老师，各用 15 分钟讲一个 AI 进入自己学科的真实案例。</div>
    </div>
    ${P.btn("去不去，先放进日程看看", "primary", "", "data-toast=\"已加入今日日程（演示）\"")}
    <div class="mt-2">${P.btn("想找同去的人，开个局", "ghost", "D1")}</div>`,
},
{
  id: "B8",
  nav: P.nav("组会与课题", { back: "tab:today" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("notebook-open.png", "st-24"), title: "导师组会", sub: "周五 14:00–16:00 · 计算机学院楼 A501", right: `<span class="om-chip solid">本周</span>` })}
      ${P.row({ icon: P.stickerImg("laptop-closed.png", "st-24"), title: "课题：校园人流预测", sub: "下次汇报：文献综述部分", right: `<span class="om-chip">进行中</span>` })}
    </div>
    ${P.note("组会信息来自你主动同步的课题组日历。App 不会替你请假，也不会替你汇报。", "access-card.png")}`,
},
{
  id: "B9",
  nav: P.nav("班车与节次", { back: "tab:today" }),
  body: `
    ${P.section("校区班车")}
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("school-bus.png", "st-24"), title: "东校园 → 南校园", sub: "下一班 14:30 · 教学楼 A 区上车", right: `<span class="om-chip gap">25 分钟后</span>` })}
      ${P.row({ icon: P.stickerImg("school-bus.png", "st-24"), title: "东校园 → 珠海校区", sub: "每天 7:30 / 17:00 两班", right: `<span class="om-chip">需预约</span>` })}
    </div>
    ${P.section("上课节次")}
    <div class="om-card tight">
      ${P.row({ icon: icon("clock", 20), title: "第 1–2 节", sub: "08:00–09:40", right: `<span class="mono t-foot">08:00</span>` })}
      ${P.row({ icon: icon("clock", 20), title: "第 3–4 节", sub: "10:00–11:40", right: `<span class="mono t-foot">10:00</span>` })}
      ${P.row({ icon: icon("clock", 20), title: "第 5–6 节", sub: "14:00–15:40", right: `<span class="mono t-foot">14:00</span>` })}
      ${P.row({ icon: icon("clock", 20), title: "第 7–8 节", sub: "16:00–17:40", right: `<span class="mono t-foot">16:00</span>` })}
      ${P.row({ icon: icon("clock", 20), title: "第 9–10 节", sub: "19:00–20:40", right: `<span class="mono t-foot">19:00</span>` })}
    </div>`,
},
{
  id: "B10",
  nav: P.nav("场景触发", { back: "tab:today" }),
  body: `
    <div class="center mt-4">${luluHTML("intent.card", "lulu-hero")}</div>
    <div class="om-card mt-4">
      <div class="t-t2">图书馆 4 楼今晚空着</div>
      <div class="t-call muted mt-2">三个事实拼在一起：</div>
      <div class="om-timeline mt-3">
        <div class="tl-item done"><b>你的空档</b><div class="t-foot">今晚 19:00–21:30 没课</div></div>
        <div class="tl-item done"><b>场地空闲</b><div class="t-foot">图书馆 4F 研讨间 4C 当前可订</div></div>
        <div class="tl-item now"><b>DDL 临近</b><div class="t-foot">《操作系统》实验报告 剩 4 天</div></div>
      </div>
    </div>
    <div class="flex">
      ${P.btn("发起研讨局", "primary", "D1")}
      ${P.btn("忽略", "ghost", "tab:today")}
    </div>
    <div class="t-cap center mt-2">忽略后同类建议 3 天内不再出现</div>`,
},
{
  id: "B11",
  nav: P.nav("行动预览", { back: "__back" }),
  body: `
    <div class="center mt-3">${luluHTML("action.preview", "lulu-confirm")}</div>
    <div class="t-t2 center mt-2">确认这次单人行动</div>
    <div class="om-card mt-4">
      ${P.row({ icon: P.stickerImg("seminar-room-sign.png", "st-24"), title: "预订：图书馆 4F 研讨间 4C", sub: "今天 19:00–21:30" })}
      ${P.row({ icon: P.stickerImg("access-card.png", "st-24"), title: "使用账号：你本人校园账号", sub: "占用本周研讨室额度 2.5 / 6 小时" })}
      ${P.row({ icon: P.stickerImg("desk-calendar.png", "st-24"), title: "写入日历", sub: "系统日历 · 提前 15 分钟提醒" })}
    </div>
    ${P.note("这是唯一一次真实写操作。看清楚再授权；授权后随时可以在「我的局」里取消。", "hourglass.png")}`,
  footer: `${P.btn("确认并授权执行", "primary", "E6")}
    <div class="mt-2">${P.btn("再想想", "text", "__back")}</div>`,
},
{
  id: "B12", tab: "match",
  large: "比赛",
  largeSub: "已核验赛事 · 看出哪桌还差人",
  body: `
    <div class="om-seg mb-3" data-seg><button class="on">全部</button><button>我能上桌</button><button>还差人</button></div>

    <div class="om-card" data-go="B12.1" style="cursor:pointer">
      <div class="between">
        <div class="flex">${P.stickerImg("trophy.png", "st-44")}
          <div><div class="t-t3">全国大学生数学建模竞赛</div><div class="t-foot">9 月 4 日开赛 · 3 人队</div></div>
        </div>
        <span class="om-chip solid">已核验</span>
      </div>
      <div class="between mt-3">
        ${P.seatStrip([
          { role: "建模", state: "filled", sticker: "data-chart.png" },
          { role: "编程", state: "filled", sticker: "algorithm-gear.png" },
          { role: "写作", state: "gap", sticker: "marker.png" },
        ])}
        ${P.gapBadge(1)}
      </div>
    </div>

    <div class="om-card" data-go="B12.1" style="cursor:pointer">
      <div class="between">
        <div class="flex">${P.stickerImg("trophy.png", "st-44")}
          <div><div class="t-t3">ACM-ICPC 校队选拔</div><div class="t-foot">8 月 30 日 · 3 人队</div></div>
        </div>
        <span class="om-chip solid">已核验</span>
      </div>
      <div class="between mt-3">
        ${P.seatStrip([
          { role: "算法", state: "filled", sticker: "algorithm-gear.png" },
          { role: "算法", state: "gap", sticker: "algorithm-gear.png" },
          { role: "代码", state: "gap", sticker: "backend-server.png" },
        ])}
        ${P.gapBadge(2)}
      </div>
    </div>

    <div class="om-card" data-go="B12.1" style="cursor:pointer">
      <div class="between">
        <div class="flex">${P.stickerImg("trophy.png", "st-44")}
          <div><div class="t-t3">「挑战杯」课外学术作品赛</div><div class="t-foot">10 月校赛 · 最多 8 人</div></div>
        </div>
        <span class="om-chip solid">已核验</span>
      </div>
      <div class="between mt-3">
        ${P.seatStrip([
          { role: "产品", state: "filled", sticker: "product-notes.png" },
          { role: "设计", state: "filled", sticker: "design-palette.png" },
          { role: "前端", state: "gap", sticker: "frontend-browser.png" },
          { role: "后端", state: "gap", sticker: "backend-server.png" },
        ])}
        ${P.gapBadge(2)}
      </div>
    </div>

    ${P.note("「已核验」= 赛事信息经学校团委或学院官方渠道确认。席位只显示角色缺口，不显示已就位者是谁。", "approval-stamp.png")}`,
},
{
  id: "B12.1",
  nav: P.nav("赛事详情", { back: "tab:match" }),
  body: `
    <div class="center mt-2">${P.stickerImg("trophy.png", "st-72")}</div>
    <div class="t-t1 center mt-2">全国大学生数学建模竞赛</div>
    <div class="t-foot center">9 月 4–7 日 · 3 人一队 · 校推免加分赛事</div>

    ${P.seatTable("数模 · 这桌 2/3 已就位", [
      { role: "建模", state: "filled", sticker: "data-chart.png" },
      { role: "编程", state: "filled", sticker: "algorithm-gear.png" },
      { role: "写作", state: "gap", sticker: "marker.png" },
    ], "round-table.png")}

    <div class="om-card">
      <div class="t-t3 mb-2">这桌需要的能力</div>
      <div class="flex wrap">
        ${P.chip("数学建模", "solid", "data-chart.png")}
        ${P.chip("编程实现", "solid", "algorithm-gear.png")}
        ${P.chip("论文写作 · 缺口", "gap", "marker.png")}
      </div>
      <div class="divider"></div>
      <div class="t-t3 mb-2">你具备的</div>
      <div class="flex wrap">${P.chip("算法", "soft", "algorithm-gear.png")}${P.chip("后端", "soft", "backend-server.png")}</div>
      <div class="t-foot mt-2">你的「编程实现」与这桌已就位角色重合，可以补「写作」位以外的空缺，或自己另开一桌。</div>
    </div>

    <div class="om-card tight">
      ${P.row({ icon: icon("cal", 20), title: "赛程", sub: "9/4 20:00 发题 → 9/7 20:00 提交" })}
      ${P.row({ icon: icon("doc", 20), title: "组队规则", sub: "每队 3 人，可跨学院，不可跨校" })}
    </div>`,
  footer: `${P.btn("补上「写作」这席", "primary", "D1")}
    <div class="mt-2">${P.btn("自己另开一桌", "ghost", "D1")}</div>`,
},
]);
