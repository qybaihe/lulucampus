/* 差一个 · ONE MORE — 屏幕定义 2/3
   C · 公开局与站外落地（4）  D · 意图与匹配（8）  E · 局的全生命周期（17） */

defineScreens([
/* ================= C · 公开局 ================= */
{
  id: "C1",
  nav: P.nav("公开局", { back: "tab:today" }),
  body: `
    <div class="om-seg mb-3" data-seg><button class="on">全部</button><button>运动</button><button>学业</button><button>比赛</button></div>
    <div class="om-card" data-go="C2" style="cursor:pointer">
      <div class="between">
        <div class="flex">${P.stickerImg("basketball.png", "st-44")}
          <div><div class="t-t3">周五晚篮球半场 4v4</div><div class="t-foot">周五 19:00 · 东校园室外场</div></div>
        </div>
        ${P.gapBadge(2)}
      </div>
      <div class="between mt-3">
        ${P.seatStrip([
          { role: "前锋", state: "filled", sticker: "basketball.png" },
          { role: "中锋", state: "filled", sticker: "basketball.png" },
          { role: "后卫", state: "gap", sticker: "basketball.png" },
          { role: "后卫", state: "gap", sticker: "basketball.png" },
        ])}
        <span class="t-foot">匿名招募中</span>
      </div>
    </div>
    <div class="om-card" data-go="C2" style="cursor:pointer">
      <div class="between">
        <div class="flex">${P.stickerImg("books-stack.png", "st-44")}
          <div><div class="t-t3">操作系统考前冲刺</div><div class="t-foot">周四 19:00 · 图书馆研讨间</div></div>
        </div>
        ${P.gapBadge(1)}
      </div>
      <div class="between mt-3">
        ${P.seatStrip([
          { role: "串讲", state: "filled", sticker: "books-stack.png" },
          { role: "刷题", state: "filled", sticker: "notebook-open.png" },
          { role: "答疑", state: "gap", sticker: "chat-bubble.png" },
        ])}
        <span class="t-foot">匿名招募中</span>
      </div>
    </div>
    <div class="om-card" data-go="C3" style="cursor:pointer">
      <div class="between">
        <div class="flex">${P.stickerImg("trophy.png", "st-44")}
          <div><div class="t-t3">挑战杯 · 智能硬件方向</div><div class="t-foot">赛季局 · 10 月校赛</div></div>
        </div>
        <span class="om-chip">有准入门槛</span>
      </div>
      <div class="t-foot mt-2">需要 T2 及以上 · 看看怎么达到 →</div>
    </div>
    ${P.note("这里只显示角色缺口与人数进度。不显示成员是谁，也不显示任何人的信任等级。", "access-card.png")}`,
},
{
  id: "C2",
  nav: P.nav("公开局详情", { back: "C1" }),
  body: `
    ${P.seatTable("周五晚篮球 4v4", [
      { role: "前锋", state: "filled", sticker: "basketball.png" },
      { role: "中锋", state: "filled", sticker: "basketball.png" },
      { role: "后卫", state: "gap", sticker: "basketball.png" },
      { role: "后卫", state: "gap", sticker: "basketball.png" },
    ], "basketball.png")}
    <div class="om-card tight">
      ${P.row({ icon: icon("clock", 20), title: "周五 19:00–21:00", sub: "东校园室外篮球场 3 号场" })}
      ${P.row({ icon: icon("shield", 20), title: "安全偏好", sub: "公共场所 · 双向确认后才可见身份" })}
      ${P.row({ icon: P.stickerImg("hourglass.png", "st-24"), title: "招募截止", sub: "周五 12:00 · 未满员则安静解散" })}
    </div>
    ${P.note("加入后你的身份对其他成员保持匿名，直到双方都确认成局。", "access-card.png")}`,
  footer: `${P.btn("补一个「后卫」位", "primary", "D4")}
    <div class="mt-2">${P.btn("分享给微信同学", "ghost", "G2")}</div>`,
},
{
  id: "C3",
  nav: P.nav("准入门槛", { back: "C1" }),
  body: `
    <div class="center mt-4">${luluHTML("core.care", "lulu-header")}</div>
    <div class="t-t1 center mt-3">这个局暂时进不去</div>
    <div class="t-call muted center mt-2">不是拒绝你——是这个局设了门槛，而你还差一步。</div>
    <div class="om-card mt-5">
      <div class="t-t3 mb-2">「挑战杯 · 智能硬件」要求</div>
      ${P.row({ icon: P.stickerImg("approval-stamp.png", "st-24"), title: "信任等级 T2", sub: "你当前 T1 · 完成 1 次成局即可升到 T2", right: `<span class="om-chip gap">差 1 次成局</span>` })}
      ${P.row({ icon: P.stickerImg("algorithm-gear.png", "st-24"), title: "至少 1 个相关能力标签", sub: "你已有「算法」· 已满足", right: `<span class="om-chip solid">已满足</span>` })}
    </div>
    <div class="t-call center mt-2">先去打成任何一个局，回来这扇门就开了。</div>`,
  footer: P.btn("去看看我能进的局", "primary", "C1"),
},
{
  id: "C4",
  nav: "",
  body: `
    <div class="center mt-6">${P.stickerImg("qr-plaque-blank.png", "st-96")}</div>
    <div class="t-t1 center mt-4">有人差一个你</div>
    <div class="t-call muted center mt-2">这是一张来自「差一个」的缺口卡</div>
    <div class="om-card mt-5">
      <div class="between">
        <div class="flex">${P.stickerImg("basketball.png", "st-44")}
          <div><div class="t-t3">周五晚篮球半场 4v4</div><div class="t-foot">周五 19:00 · 东校园室外场</div></div>
        </div>
        ${P.gapBadge(2)}
      </div>
      <div class="mt-3">${P.seatStrip([
        { role: "前锋", state: "filled", sticker: "basketball.png" },
        { role: "中锋", state: "filled", sticker: "basketball.png" },
        { role: "后卫", state: "gap", sticker: "basketball.png" },
        { role: "后卫", state: "gap", sticker: "basketball.png" },
      ])}</div>
    </div>
    ${P.note("你还没有登录。认证后会直接回到这个局，不用重新找链接。", "access-card.png")}`,
  footer: `${P.btn("企业微信扫码认证", "primary", "A3")}
    <div class="t-cap center mt-2">中山大学师生专属 · 认证后回到本局</div>`,
},

/* ================= D · 意图与匹配 ================= */
{
  id: "D1", tab: "create",
  body: `
    <div class="center mt-5">${luluHTML("home.listening", "lulu-hero", "我在听。说一句想做的事就行。")}</div>
    <div class="om-card mt-4" style="border-radius:var(--r-xl)">
      <textarea class="om-input" style="border:none;background:transparent" placeholder="例如：周五晚上想找人打半场篮球，缺两个后卫"></textarea>
      <div class="between mt-2">
        <span class="t-cap">不用指定找谁</span>
        <button class="nav-back" aria-label="语音输入">${icon("mic", 18)}</button>
      </div>
    </div>
    <div class="flex wrap mt-4" style="justify-content:center">
      ${P.chip("明晚研讨室赶 DDL", "soft", "books-stack.png")}
      ${P.chip("数模缺一个写作的", "soft", "trophy.png")}
      ${P.chip("周末羽毛球双打", "soft", "badminton.png")}
    </div>`,
  footer: P.btn("说完了，交给 Lulu", "primary", "D2"),
},
{
  id: "D2",
  nav: P.nav("澄清一下", { back: "D1" }),
  body: `
    <div class="center mt-3">${luluHTML("home.thinking", "lulu-header")}</div>
    <div class="chat-list mt-4">
      <div class="bubble me">周五晚上想找人打半场篮球，缺两个后卫</div>
      <div class="bubble">明白。确认两件事：<br>1. 时间定在 <b>周五 19:00–21:00</b> 可以吗？那是你和场馆都空着的时段。</div>
      <div class="bubble me">可以</div>
      <div class="bubble">2. 水平有要求吗？比如「打过全场就行」，还是不限？</div>
    </div>
    <div class="flex wrap mt-3">
      ${P.chip("不限，能跑就行", "soft")}
      ${P.chip("打过全场", "soft")}
      ${P.chip("院队水平", "soft")}
    </div>
    <div class="t-cap center mt-3">最多问两轮，问完就出意图卡</div>`,
  footer: P.btn("不限，能跑就行", "primary", "D3"),
},
{
  id: "D3",
  nav: P.nav("意图卡确认", { back: "D2" }),
  body: `
    <div class="center mt-3">${luluHTML("intent.card", "lulu-confirm")}</div>
    <div class="t-t2 center mt-2">我理解对了吗？</div>
    <div class="om-card mt-4" style="border:2px solid var(--yolk)">
      ${P.row({ icon: P.stickerImg("basketball.png", "st-24"), title: "做什么", sub: "篮球半场 4v4", go: "D3.3", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: icon("clock", 20), title: "什么时候", sub: "周五 19:00–21:00", go: "D3.2", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: P.stickerImg("round-table.png", "st-24"), title: "需要几个人", sub: "连你共 4 人", go: "D3.3", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: P.stickerImg("basketball.png", "st-24"), title: "角色缺口", sub: "后卫 × 2 · 水平不限", go: "D3.3", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: icon("shield", 20), title: "安全偏好", sub: "公共场所 · 默认", go: "D3.4", right: `<span class="chevron">›</span>` })}
    </div>
    ${P.note("确认后进入匿名招募。满员前，没有人知道你是谁。", "access-card.png")}`,
  footer: `${P.btn("确认，开始招募", "primary", "D4")}
    <div class="mt-2">${P.btn("改需要的能力", "text", "D3.1")}</div>`,
},
{
  id: "D3.1",
  nav: P.nav("能力编辑", { back: "D3" }),
  body: `
    <div class="t-foot mb-3">给这个局标注需要的能力。标签只描述「这件事需要什么」，不描述人。</div>
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("algorithm-gear.png", "st-24"), title: "算法", sub: "建模、题解、复杂度", right: P.switch(false) })}
      ${P.row({ icon: P.stickerImg("backend-server.png", "st-24"), title: "后端", sub: "服务、数据库、部署", right: P.switch(false) })}
      ${P.row({ icon: P.stickerImg("frontend-browser.png", "st-24"), title: "前端", sub: "界面、交互、小程序", right: P.switch(false) })}
      ${P.row({ icon: P.stickerImg("data-chart.png", "st-24"), title: "数据", sub: "分析、可视化、建模", right: P.switch(false) })}
      ${P.row({ icon: P.stickerImg("product-notes.png", "st-24"), title: "产品", sub: "需求、文档、路演", right: P.switch(false) })}
      ${P.row({ icon: P.stickerImg("design-palette.png", "st-24"), title: "设计", sub: "视觉、海报、PPT", right: P.switch(false) })}
    </div>`,
  footer: P.btn("保存", "primary", "D3"),
},
{
  id: "D3.2",
  nav: P.nav("空档选择", { back: "D3" }),
  body: `
    <div class="t-foot mb-3">黄色格是你的固定空档。只能在这些时间里选——这是「不打扰」的边界。</div>
    <div class="om-card tight">
      <div class="schedule-grid">
        <span></span><span class="sg-head">三</span><span class="sg-head">四</span><span class="sg-head">五</span><span class="sg-head">六</span><span class="sg-head">日</span>
        <span class="sg-time">下午</span><span class="sg-cell"></span><span class="sg-cell free">空档</span><span class="sg-cell free">空档</span><span class="sg-cell free">空档</span><span class="sg-cell free">空档</span>
        <span class="sg-time">晚上</span><span class="sg-cell"></span><span class="sg-cell"></span><span class="sg-cell free" style="border-width:2px">已选 19–21</span><span class="sg-cell free">空档</span><span class="sg-cell free">空档</span>
      </div>
    </div>
    <div class="om-card tight mt-3">
      ${P.row({ icon: icon("clock", 20), title: "周五 19:00–21:00", sub: "与场馆空闲重合", right: `<span class="om-chip gap">当前选择</span>` })}
      ${P.row({ icon: icon("clock", 20), title: "周六 15:00–17:00", sub: "场馆需现场确认", right: P.btn("换这个", "ghost sm", "D3") })}
    </div>`,
  footer: P.btn("就用周五晚上", "primary", "D3"),
},
{
  id: "D3.3",
  nav: P.nav("角色编辑", { back: "D3" }),
  body: `
    <div class="t-foot mb-3">一个局最少 2 人、最多 12 人。每个席位写清角色，别人才知道自己补的是哪。</div>
    ${P.seatTable("篮球 4v4 · 席位", [
      { role: "你 · 前锋", state: "filled", sticker: "basketball.png" },
      { role: "中锋", state: "filled", sticker: "basketball.png" },
      { role: "后卫", state: "gap", sticker: "basketball.png" },
      { role: "后卫", state: "gap", sticker: "basketball.png" },
    ], "basketball.png")}
    <div class="flex mt-2">
      ${P.btn("加一个席位", "ghost sm", "", "data-toast=\"已加到 5 席（演示）\"")}
      ${P.btn("减一个席位", "ghost sm", "", "data-toast=\"至少保留 2 席\"")}
    </div>`,
  footer: P.btn("保存席位", "primary", "D3"),
},
{
  id: "D3.4",
  nav: P.nav("安全偏好", { back: "D3" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: icon("pin", 20), title: "只在公共场所进行", sub: "体育馆、图书馆、教学楼等学校场地", right: P.switch(true) })}
      ${P.row({ icon: P.stickerImg("access-card.png", "st-24"), title: "同性别组队", sub: "仅对运动类局生效", right: P.switch(false) })}
      ${P.row({ icon: icon("clock", 20), title: "不晚于 22:00 结束", sub: "宿舍门禁前留出路程", right: P.switch(true) })}
      ${P.row({ icon: icon("shield", 20), title: "双向确认前匿名", sub: "系统默认，不可关闭", right: `<span class="om-chip solid">锁定</span>` })}
    </div>
    ${P.note("安全偏好会写进局卡，加入的人在确认前就能看到并遵守。", "access-card.png")}`,
  footer: P.btn("保存", "primary", "D3"),
},
{
  id: "D4",
  nav: P.nav("匿名池", { back: "tab:today" }),
  body: `
    <div class="center mt-4">${luluHTML("pool.waiting", "lulu-hero")}</div>
    <div class="t-t1 center mt-3">正在匿名招募</div>
    <div class="gap-hero mt-3" style="justify-content:center"><span class="n">2</span><span class="of">个后卫位还空着</span></div>
    <div class="om-card mt-5">
      <div class="between mb-2"><span class="t-foot">招募剩余时间</span><span class="mono t-t3">41:22:08</span></div>
      <div class="om-progress"><i style="width:38%"></i></div>
      <div class="divider"></div>
      ${P.row({ icon: icon("shield", 20), title: "全程匿名", sub: "满员前，没有人知道你是谁，你也不知道有谁" })}
      ${P.row({ icon: P.stickerImg("hourglass.png", "st-24"), title: "周五 12:00 截止", sub: "到点未满员，这个局会安静解散，不归因给任何人" })}
    </div>
    <div class="flex">
      ${P.btn("分享缺口卡到微信群", "ghost", "G2")}
      ${P.btn("取消招募", "text", "E12")}
    </div>`,
},

/* ================= E · 局的全生命周期 ================= */
{
  id: "E1",
  nav: P.nav("我的局", { back: "tab:today" }),
  body: `
    <div class="om-seg mb-3" data-seg><button class="on">进行中</button><button>已完成</button><button>已结束</button></div>
    <div class="om-card tight" data-go="E2" style="cursor:pointer">
      ${P.row({ icon: P.stickerImg("trophy.png", "st-24"), title: "数学建模国赛冲刺", sub: "周五 19:00 · 研讨间 4C 已订", go: "E2", right: `<span class="om-chip solid">已成局</span>` })}
      ${P.row({ icon: P.stickerImg("basketball.png", "st-24"), title: "周五晚篮球半场", sub: "匿名招募中 · 截止周五 12:00", go: "D4", right: `<span class="om-chip gap">缺 2</span>` })}
      ${P.row({ icon: P.stickerImg("books-stack.png", "st-24"), title: "操作系统考前冲刺", sub: "3 人已确认 · 等你确认", go: "E3", right: `<span class="gap-badge">差你 1 票</span>` })}
    </div>
    ${P.section("已安静结束")}
    <div class="om-card tight" data-go="G4" style="cursor:pointer">
      ${P.row({ icon: P.stickerImg("table-tennis.png", "st-24"), title: "上周乒乓球双打", sub: "未凑齐 · 已安静解散", go: "G4", right: `<span class="om-chip">已结束</span>` })}
    </div>`,
},
{
  id: "E2",
  nav: P.nav("局详情", { back: "E1", right: `<button class="nav-back" data-go="G2" aria-label="分享缺口卡">${icon("share", 17)}</button>` }),
  body: `
    ${P.seatTable("数学建模国赛冲刺", [
      { role: "建模", state: "filled", sticker: "data-chart.png" },
      { role: "编程", state: "filled", sticker: "algorithm-gear.png" },
      { role: "写作", state: "filled", sticker: "marker.png" },
    ], "trophy.png")}
    <div class="om-card tight">
      ${P.row({ icon: icon("clock", 20), title: "周五 19:00–21:30", sub: "图书馆 4F 研讨间 4C · 已订", go: "E4", right: `<span class="om-chip">改约</span>` })}
      ${P.row({ icon: P.stickerImg("round-table.png", "st-24"), title: "协作空间", sub: "时间地点 · 角色待办 · 群聊", go: "E7", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: P.stickerImg("trophy.png", "st-24"), title: "共同目标", sub: "长期局：整个赛季的训练与参赛", go: "E11", right: `<span class="chevron">›</span>` })}
    </div>
    <div class="flex">
      ${P.btn("退出这个局", "ghost sm", "E12")}
      ${P.btn("举报与拉黑", "text sm", "E13")}
    </div>`,
},
{
  id: "E3",
  nav: P.nav("多人确认", { back: "E1" }),
  body: `
    <div class="center mt-3">${luluHTML("confirm.gather", "lulu-confirm")}</div>
    <div class="t-t2 center mt-2">就差你确认了</div>
    <div class="t-foot center mt-1">操作系统考前冲刺 · 周四 19:00 · 图书馆 4C</div>
    <div class="om-card mt-4">
      ${P.progress(3, 4)}
      <div class="om-timeline mt-4">
        <div class="tl-item done"><b>3 个席位已确认</b><div class="t-foot">双向确认完成前，彼此匿名</div></div>
        <div class="tl-item now"><b>你的确认</b><div class="t-foot">截止今晚 22:00 · 剩 4 小时 12 分</div></div>
      </div>
    </div>
    ${P.note("确认即同意时间地点与安全偏好。超时未确认，席位自动让出，不会有任何人知道你被邀请过。", "hourglass.png")}`,
  footer: `${P.btn("确认加入", "primary", "E5")}
    <div class="mt-2">${P.btn("这次不参加", "text", "E1")}</div>`,
},
{
  id: "E4",
  nav: P.nav("改约协商", { back: "E2" }),
  body: `
    <div class="om-card">
      <div class="t-t3">提议改约</div>
      <div class="t-foot mt-1">当前：周五 19:00–21:30 · 图书馆 4C</div>
      <div class="divider"></div>
      ${P.row({ icon: icon("clock", 20), title: "改为：周六 15:00–17:30", sub: "提议人：建模位成员 · 理由：周五临时有实验", right: `<span class="om-chip gap">待表态</span>` })}
    </div>
    <div class="om-card tight">
      <div class="t-t3 mb-2">表态情况</div>
      ${P.row({ icon: P.stickerImg("data-chart.png", "st-24"), title: "建模位", sub: "提议人", right: `<span class="om-chip solid">同意</span>` })}
      ${P.row({ icon: P.stickerImg("algorithm-gear.png", "st-24"), title: "编程位", sub: "1 小时前", right: `<span class="om-chip solid">同意</span>` })}
      ${P.row({ icon: P.stickerImg("marker.png", "st-24"), title: "写作位（你）", sub: "等你表态", right: `<span class="om-chip gap">待表态</span>` })}
    </div>
    <div class="flex">
      ${P.btn("同意改约", "primary", "", "data-toast=\"已同意 · 全员通过后 Lulu 会重订研讨间\"")}
      ${P.btn("保持原时间", "ghost", "", "data-toast=\"已表态 · 提议未通过，维持原安排\"")}
    </div>`,
},
{
  id: "E5",
  nav: P.nav("行动预览", { back: "E3" }),
  body: `
    <div class="center mt-3">${luluHTML("action.preview", "lulu-confirm")}</div>
    <div class="t-t2 center mt-2">授权前，最后看一遍</div>
    <div class="t-foot center mt-1">这是全流程唯一一次真实写操作</div>
    <div class="om-card mt-4" style="border:2px solid var(--ink)">
      ${P.row({ icon: P.stickerImg("seminar-room-sign.png", "st-24"), title: "预订：图书馆 4F 研讨间 4C", sub: "周四 19:00–21:30 · 6 人位" })}
      ${P.row({ icon: P.stickerImg("access-card.png", "st-24"), title: "使用账号：你本人的校园账号", sub: "占用本周研讨室额度 2.5 / 6 小时" })}
      ${P.row({ icon: P.stickerImg("desk-calendar.png", "st-24"), title: "写入 4 位成员的日历", sub: "系统日历 · 提前 15 分钟提醒 · 仅写时间地点" })}
      ${P.row({ icon: icon("shield", 20), title: "不会做的事", sub: "不代发消息 · 不代请假 · 不涉及支付" })}
    </div>
    ${P.note("授权只对这一次有效。下次行动会重新给你看预览。", "hourglass.png")}`,
  footer: `${P.btn("确认并授权执行", "primary", "E6")}
    <div class="mt-2">${P.btn("返回修改", "text", "__back")}</div>`,
},
{
  id: "E6",
  nav: P.nav("执行结果", { back: "tab:today" }),
  body: `
    <div class="center mt-5">${luluHTML("core.celebrate", "lulu-header")}</div>
    <div class="t-t1 center mt-3">订好了</div>
    <div class="om-card mt-4">
      <div class="om-timeline">
        <div class="tl-item done"><b>研讨间 4C 预订成功</b><div class="t-foot">周四 19:00–21:30 · 预约号 YJ-20814</div></div>
        <div class="tl-item done"><b>已写入 4 位成员的日历</b><div class="t-foot">提前 15 分钟提醒</div></div>
        <div class="tl-item done"><b>协作空间已开启</b><div class="t-foot">群聊已可用 · Lulu 已退场</div></div>
      </div>
    </div>
    ${P.note("如果失败：Lulu 会说明卡在哪一步、已做的部分是否回滚，并给出下一步——不会只丢一个错误码。", "chat-bubble.png")}`,
  footer: P.btn("进入协作空间", "primary", "E7"),
},
{
  id: "E7",
  nav: P.nav("协作空间", { back: "E2" }),
  body: `
    <div class="om-card" style="background:var(--gap-soft);border-color:var(--yolk)">
      <div class="flex">
        ${luluHTML("exit.bow", "lulu-confirm")}
        <div class="grow">
          <div class="t-t3">事办完了，我先走啦</div>
          <div class="t-foot mt-1">场订好了、日历写好了。接下来是你们自己的事——Lulu 已退场，这个空间里不再有 AI。</div>
        </div>
      </div>
    </div>
    <div class="om-card tight">
      ${P.row({ icon: icon("clock", 20), title: "周四 19:00–21:30", sub: "图书馆 4F 研讨间 4C · 预约号 YJ-20814" })}
      ${P.row({ icon: P.stickerImg("data-chart.png", "st-24"), title: "建模位", sub: "待办：整理近 3 年赛题类型", right: `<span class="om-chip solid">已就位</span>` })}
      ${P.row({ icon: P.stickerImg("algorithm-gear.png", "st-24"), title: "编程位", sub: "待办：搭好求解代码框架", right: `<span class="om-chip solid">已就位</span>` })}
      ${P.row({ icon: P.stickerImg("marker.png", "st-24"), title: "写作位（你）", sub: "待办：准备论文模板", right: `<span class="om-chip solid">已就位</span>` })}
    </div>`,
  footer: P.btn("进入群聊", "primary", "E14"),
},
{
  id: "E8",
  nav: P.nav("补位", { back: "E2" }),
  body: `
    <div class="center mt-3">${luluHTML("pool.waiting", "lulu-header")}</div>
    <div class="t-t2 center mt-2">有人退出，缺口重新打开</div>
    <div class="t-foot center mt-1">编程位空出来了 · 补位招募已自动重启</div>
    ${P.seatTable("数学建模国赛冲刺", [
      { role: "建模", state: "filled", sticker: "data-chart.png" },
      { role: "编程", state: "gap", sticker: "algorithm-gear.png" },
      { role: "写作", state: "filled", sticker: "marker.png" },
    ], "trophy.png")}
    ${P.note("退出不需要理由，也不会公示是谁退出。缺口重新匿名招募，和第一次一样。", "access-card.png")}`,
  footer: `${P.btn("分享补位缺口卡", "primary", "G2")}
    <div class="mt-2">${P.btn("缩小规模继续", "ghost", "", "data-toast=\"已改为 2 人局（演示）\"")}</div>`,
},
{
  id: "E9",
  nav: P.nav("完成确认", { back: "E2" }),
  body: `
    <div class="center mt-4">${luluHTML("home.reply", "lulu-header")}</div>
    <div class="t-t1 center mt-3">这次局，成了吗？</div>
    <div class="t-foot center mt-1">数学建模国赛冲刺 · 周四研讨</div>
    <div class="om-card mt-5">
      ${P.row({ icon: P.stickerImg("approval-stamp.png", "st-24"), title: "完成了", sub: "人到齐，事办完", go: "E10", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: P.stickerImg("hourglass.png", "st-24"), title: "部分完成", sub: "有人没到或提前结束", go: "E10", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: P.stickerImg("envelope.png", "st-24"), title: "没能进行", sub: "不追责，只记录事实", go: "E10", right: `<span class="chevron">›</span>` })}
    </div>
    ${P.note("完成确认只影响你自己的信任进度，不会给别人打分、写评价。", "access-card.png")}`,
},
{
  id: "E10",
  nav: P.nav("复局选择", { back: "E9" }),
  body: `
    <div class="center mt-4">${luluHTML("core.celebrate", "lulu-header")}</div>
    <div class="t-t1 center mt-3">下次呢？</div>
    <div class="om-card mt-5">
      ${P.row({ icon: P.stickerImg("round-table.png", "st-24"), title: "再来一次", sub: "原班人马，下周同一时间", go: "D3", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: P.stickerImg("chair-empty.png", "st-24"), title: "换人再来", sub: "保留局的框架，重新招募", go: "D3.3", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: P.stickerImg("certificate.png", "st-24"), title: "就到这里", sub: "归档这次局，记住一起做过事的人", go: "E15", right: `<span class="chevron">›</span>` })}
    </div>`,
},
{
  id: "E11",
  nav: P.nav("共同目标", { back: "E2" }),
  body: `
    <div class="om-card">
      <div class="flex">${P.stickerImg("trophy.png", "st-56")}
        <div><div class="t-t2">数学建模 · 整个赛季</div><div class="t-foot mt-1">长期局 · 8 月 12 日 → 9 月 7 日</div></div>
      </div>
      <div class="divider"></div>
      <div class="between mb-2"><span class="t-foot">赛季进度</span><span class="mono t-foot">第 2 / 4 阶段</span></div>
      <div class="om-progress"><i style="width:50%"></i></div>
    </div>
    <div class="om-card tight">
      <div class="om-timeline">
        <div class="tl-item done"><b>组队与分工</b><div class="t-foot">8 月 5 日完成</div></div>
        <div class="tl-item done"><b>赛题类型研讨</b><div class="t-foot">8 月 12 日 · 研讨间 4C</div></div>
        <div class="tl-item now"><b>模拟赛一次</b><div class="t-foot">8 月 24 日前 · 场地未定</div></div>
        <div class="tl-item"><b>正式参赛</b><div class="t-foot">9 月 4–7 日</div></div>
      </div>
    </div>
    ${P.btn("为「模拟赛」发起一次行动", "primary", "D1")}`,
},
{
  id: "E12",
  nav: P.nav("退出", { back: "E2" }),
  body: `
    <div class="center mt-4">${luluHTML("core.care", "lulu-header")}</div>
    <div class="t-t1 center mt-3">退出不需要理由</div>
    <div class="t-call muted center mt-2" style="max-width:280px;margin-left:auto;margin-right:auto">
      你退出后，缺口会重新匿名打开。其他成员只会看到「席位空出来了」，不会看到是谁、为什么。
    </div>
    <div class="om-card mt-5">
      ${P.row({ icon: icon("clock", 20), title: "距开始还有 26 小时", sub: "现在退出，补位时间充足" })}
      ${P.row({ icon: icon("shield", 20), title: "对信任进度的影响", sub: "24 小时内退出不记录；临近开始的退出会减缓升级，但不降级" })}
    </div>`,
  footer: `${P.btn("确认退出", "ghost", "E8")}
    <div class="mt-2">${P.btn("再想想", "primary", "__back")}</div>`,
},
{
  id: "E13",
  nav: P.nav("举报与拉黑", { back: "E2" }),
  body: `
    <div class="center mt-4">${luluHTML("core.care", "lulu-header")}</div>
    <div class="t-t1 center mt-3">安全出口一直开着</div>
    <div class="om-card mt-5">
      ${P.row({ icon: icon("flag", 20), title: "举报这个局", sub: "内容违规、虚假招募、安全问题", go: "", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: icon("flag", 20), title: "举报成员", sub: "双向确认后才可选择具体成员", go: "", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: icon("exit", 20), title: "拉黑并退出", sub: "对方不会再出现在你的任何局里", go: "M8", right: `<span class="chevron">›</span>` })}
    </div>
    ${P.note("举报由真人审核。紧急安全问题请直接联系学校保卫处 020-84110110。", "access-card.png")}`,
},
{
  id: "E14",
  nav: P.nav("数学建模国赛冲刺", { back: "tab:msg" }),
  body: `
    <div class="chat-list mt-3">
      <div class="bubble-sys">研讨间 4C 已订好 · 周四 19:00 · Lulu 已退场</div>
      <div class="bubble">论文模板我传到群文件了，用的是去年国一的格式</div>
      <div class="bubble me">收到，我今晚把摘要部分先搭起来</div>
      <div class="bubble">模拟赛定在下周六下午怎么样？我看了看大家空档都合适</div>
      <div class="bubble me">可以，周六下午我没课</div>
    </div>
    <div class="om-note mt-4"><img src="${ST}access-card.png" alt=""><span>这个群聊里没有 AI。没有已读回执，没有在线状态，没有「正在输入」。</span></div>`,
  sheet: `<div class="chat-input">
      <input class="om-input" placeholder="发消息…">
      <button class="nav-back" style="width:42px;height:42px" aria-label="发送">${icon("arrow", 17)}</button>
    </div>`,
},
{
  id: "E15",
  nav: P.nav("搭子关系", { back: "M1" }),
  body: `
    <div class="t-foot mb-3">一起做成过事的人。只记事实，不记评价。</div>
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("data-chart.png", "st-24"), title: "一起打过 2 个局", sub: "数学建模 × 2 · 最近：8 月 12 日", go: "E16", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: P.stickerImg("basketball.png", "st-24"), title: "一起打过 1 个局", sub: "篮球半场 · 最近：7 月 28 日", go: "E16", right: `<span class="chevron">›</span>` })}
    </div>
    ${P.note("没有「最常一起的人」排行，没有搭子数量统计。关系是事实记录，不是社交资本。", "access-card.png")}`,
},
{
  id: "E16",
  nav: P.nav("共同经历", { back: "E15" }),
  body: `
    <div class="t-foot mb-3">你们一起做过的事。只有事实，没有印象分。</div>
    <div class="om-card tight">
      <div class="om-timeline">
        <div class="tl-item done"><b>数学建模国赛冲刺</b><div class="t-foot">8 月 12 日 · 研讨间 4C · 已完成</div></div>
        <div class="tl-item done"><b>数学建模校内热身赛</b><div class="t-foot">6 月 20 日 · 线上 · 已完成</div></div>
      </div>
    </div>
    ${P.note("这里不会出现「靠谱」「准时」这类评价标签——共同经历只回答「一起做过什么」。", "chat-bubble.png")}`,
  footer: P.btn("解除搭子关系", "ghost", "E17"),
},
{
  id: "E17",
  nav: P.nav("解除关系", { back: "E16" }),
  body: `
    <div class="center mt-4">${luluHTML("core.care", "lulu-header")}</div>
    <div class="t-t1 center mt-3">单向解除，立即生效</div>
    <div class="t-call muted center mt-2" style="max-width:280px;margin-left:auto;margin-right:auto">
      解除后：共同经历保留事实但不再关联彼此；对方不会收到通知；你们不会再被匹配进同一个局。
    </div>
    <div class="om-card mt-5">
      ${P.row({ icon: icon("shield", 20), title: "对方看到的", sub: "什么都没有。没有通知，没有提示" })}
      ${P.row({ icon: icon("exit", 20), title: "可以恢复吗", sub: "不可以。再次成局需要重新双向确认" })}
    </div>`,
  footer: `${P.btn("确认解除", "ghost", "E15")}
    <div class="mt-2">${P.btn("再想想", "primary", "__back")}</div>`,
},
]);
