/* 差一个 · ONE MORE — 屏幕定义 3/3
   M · 我（10）  O · 主理人（4）  G · 全局与跨阶段（5）  MSG · 消息列表 */

defineScreens([
/* ================= MSG · 消息（Tab 根） ================= */
{
  id: "MSG", tab: "msg",
  large: "消息",
  largeSub: "只有已成局的人会出现在这里",
  body: `
    <div class="om-card tight" data-go="E14" style="cursor:pointer">
      ${P.row({ icon: P.stickerImg("trophy.png", "st-24"), title: "数学建模国赛冲刺", sub: "「模拟赛定在下周六下午怎么样？」", go: "E14", right: `<span class="t-foot">14:02</span>` })}
      ${P.row({ icon: P.stickerImg("books-stack.png", "st-24"), title: "操作系统考前冲刺", sub: "「研讨间 4C 已订好 · Lulu 已退场」", go: "E14", right: `<span class="t-foot">昨天</span>` })}
    </div>
    ${P.note("没有陌生人私聊，没有群二维码，没有已读回执。局结束 7 天后，群聊自动归档为只读。", "chat-bubble.png")}`,
},

/* ================= M · 我 ================= */
{
  id: "M1", tab: "me",
  large: "我",
  body: `
    <div class="om-card">
      <div class="flex">
        ${luluHTML("home.idle", "lulu-avatar")}
        <div class="grow">
          <div class="t-t3">阿哲</div>
          <div class="t-foot mt-1">电子信息与工程学院 · 2023 级</div>
        </div>
        <button class="om-btn ghost sm" data-go="M3">T2</button>
      </div>
      <div class="divider"></div>
      <div class="between">
        <span class="t-foot">信任等级 T2 · 可发起公开局</span>
        <button class="more t-foot" data-go="M3" style="font-weight:600">进度 →</button>
      </div>
      <div class="om-progress mt-2"><i style="width:46%"></i></div>
      <div class="t-cap mt-2">等级只有你自己看得见。它解锁能力，不是身份标识。</div>
    </div>

    ${P.section("我的")}
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("round-table.png", "st-24"), title: "我的局", sub: "3 个进行中", go: "E1" })}
      ${P.row({ icon: P.stickerImg("badge.png", "st-24"), title: "搭子关系", sub: "2 段共同经历", go: "E15" })}
      ${P.row({ icon: P.stickerImg("certificate.png", "st-24"), title: "主理人控制台", sub: "你管理的 1 个官方局", go: "O1" })}
    </div>

    ${P.section("设置")}
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("nameplate-blank.png", "st-24"), title: "画像编辑", sub: "能力标签与可用时间", go: "M2" })}
      ${P.row({ icon: P.stickerImg("access-card.png", "st-24"), title: "授权管理", sub: "已授权 3 项", go: "M4" })}
      ${P.row({ icon: icon("shield", 20), title: "隐私与安全", sub: "社交开关 · 可见性", go: "M5" })}
      ${P.row({ icon: P.stickerImg("chair-empty.png", "st-24"), title: "匹配偏好", sub: "规模 · 距离 · 时段", go: "M6" })}
      ${P.row({ icon: icon("bell", 20), title: "通知与日历", sub: "推送 · 日历同步", go: "M7" })}
      ${P.row({ icon: icon("exit", 20), title: "黑名单", sub: "已拉黑 0 人", go: "M8" })}
      ${P.row({ icon: P.stickerImg("envelope.png", "st-24"), title: "信任申诉", sub: "对等级判定提出异议", go: "M9" })}
      ${P.row({ icon: icon("gear", 20), title: "账号与数据", sub: "导出 · 注销", go: "M10" })}
    </div>`,
},
{
  id: "M2",
  nav: P.nav("画像编辑", { back: "tab:me" }),
  body: `
    ${P.section("能力标签")}
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("algorithm-gear.png", "st-24"), title: "算法", sub: "来源：已修《数据结构与算法》", right: `<span class="om-chip solid">课程</span>` })}
      ${P.row({ icon: P.stickerImg("backend-server.png", "st-24"), title: "后端", sub: "来源：已修《操作系统》《数据库系统》", right: `<span class="om-chip solid">课程</span>` })}
      ${P.row({ icon: P.stickerImg("design-palette.png", "st-24"), title: "设计", sub: "来源：你自己添加", right: `<span class="om-chip">自述</span>` })}
    </div>
    ${P.btn("添加自述标签", "ghost", "", "data-toast=\"自述标签会明确标注来源（演示）\"")}
    ${P.section("可用时间")}
    <div class="om-card tight">
      <div class="flex wrap">
        ${P.chip("周二 19:00–21:30", "soft")}${P.chip("周三 14:00–17:00", "soft")}${P.chip("周五 16:00 后", "soft")}${P.chip("周末全天", "soft")}
      </div>
      <div class="t-foot mt-3">来自课表空档。课表变了这里会自动更新。</div>
    </div>
    ${P.note("课程来源的标签不可删除（它们是事实）；自述标签随时可以删，并始终标明「自述」。", "nameplate-blank.png")}`,
},
{
  id: "M3",
  nav: P.nav("信任进度", { back: "tab:me" }),
  body: `
    <div class="center mt-3">${luluHTML("home.reply", "lulu-header")}</div>
    <div class="t-t1 center mt-2">你在 T2</div>
    <div class="t-foot center mt-1">这一级解锁：发起公开局 · 加入有门槛的局</div>
    <div class="om-card mt-4">
      <div class="between mb-2"><span class="t-foot">距 T3</span><span class="mono t-foot">还差 2 次成局</span></div>
      <div class="om-progress"><i style="width:46%"></i></div>
      <div class="om-timeline mt-4">
        <div class="tl-item done"><b>T1 · 已认证</b><div class="t-foot">校园工具全开 · 可加入公开局</div></div>
        <div class="tl-item done"><b>T2 · 可发起</b><div class="t-foot">完成 1 次成局达成 · 可发起公开局</div></div>
        <div class="tl-item now"><b>T3 · 可代理</b><div class="t-foot">再完成 2 次成局 · 解锁代理预约更高额度</div></div>
        <div class="tl-item"><b>T4 · 主理人候选</b><div class="t-foot">可申请运营官方局</div></div>
      </div>
    </div>
    ${P.note("等级只解锁能力，不是身份标识。没有排行榜，别人看不到你的等级，你也看不到别人的。", "access-card.png")}
    <button class="om-btn text mt-2" data-go="M9">对判定有异议？信任申诉 →</button>`,
},
{
  id: "M4",
  nav: P.nav("授权管理", { back: "tab:me" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("books-stack.png", "st-24"), title: "课表", sub: "用于寻找空档 · 授权于 8 月 1 日", right: P.switch(true) })}
      ${P.row({ icon: P.stickerImg("notebook-open.png", "st-24"), title: "培养方案", sub: "用于能力标签 · 授权于 8 月 1 日", right: P.switch(true) })}
      ${P.row({ icon: P.stickerImg("desk-calendar.png", "st-24"), title: "选课记录", sub: "未授权", right: P.switch(false) })}
      ${P.row({ icon: P.stickerImg("approval-stamp.png", "st-24"), title: "代理执行", sub: "每次执行前仍需你确认 · 授权于 8 月 1 日", right: P.switch(true) })}
    </div>
    ${P.note("撤回立即生效，且不删除历史：已经订好的场、写好的日历保持原样，只是以后不再代办。", "access-card.png")}`,
},
{
  id: "M5",
  nav: P.nav("隐私与安全", { back: "tab:me" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("chat-bubble.png", "st-24"), title: "社交能力", sub: "公开局 · 群聊 · 搭子关系", right: P.switch(true) })}
      ${P.row({ icon: icon("pin", 20), title: "默认公共场所", sub: "新局默认勾选", right: P.switch(true) })}
      ${P.row({ icon: icon("clock", 20), title: "局不晚于 22:00", sub: "新局默认勾选", right: P.switch(true) })}
    </div>
    ${P.section("永远关闭的")}
    <div class="om-card tight">
      ${P.row({ icon: icon("shield", 20), title: "双向确认前匿名", sub: "系统级规则，不可关闭", right: `<span class="om-chip solid">锁定</span>` })}
      ${P.row({ icon: icon("shield", 20), title: "已读回执 / 在线状态", sub: "产品不提供，不是设置项", right: `<span class="om-chip solid">不存在</span>` })}
      ${P.row({ icon: icon("shield", 20), title: "陌生人私聊", sub: "产品不提供，不是设置项", right: `<span class="om-chip solid">不存在</span>` })}
    </div>`,
},
{
  id: "M6",
  nav: P.nav("匹配偏好", { back: "tab:me" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("round-table.png", "st-24"), title: "局的规模", sub: "2–6 人", right: `<span class="om-chip">可调</span>` })}
      ${P.row({ icon: icon("pin", 20), title: "校区范围", sub: "东校园优先 · 可接受南校园", right: `<span class="om-chip">可调</span>` })}
      ${P.row({ icon: icon("clock", 20), title: "偏好时段", sub: "工作日晚 · 周末下午", right: `<span class="om-chip">可调</span>` })}
      ${P.row({ icon: P.stickerImg("hourglass.png", "st-24"), title: "招募时长", sub: "默认 48 小时", right: `<span class="om-chip">可调</span>` })}
    </div>
    ${P.note("偏好只影响「推给你什么局」，不影响别人能不能看到你发起的局。", "chair-empty.png")}`,
},
{
  id: "M7",
  nav: P.nav("通知与日历", { back: "tab:me" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: icon("bell", 20), title: "凑齐提醒", sub: "局满员时推送", right: P.switch(true) })}
      ${P.row({ icon: icon("bell", 20), title: "待确认提醒", sub: "有人等你表态时推送", right: P.switch(true) })}
      ${P.row({ icon: icon("bell", 20), title: "场景建议", sub: "如「图书馆今晚空着」· 每天最多 1 条", right: P.switch(true) })}
      ${P.row({ icon: P.stickerImg("desk-calendar.png", "st-24"), title: "日历同步", sub: "成局后自动写入系统日历", right: P.switch(true) })}
    </div>
    ${P.note("没有「好友动态」类推送，没有红点养成。通知只在你需要行动时出现。", "alarm-clock.png")}`,
},
{
  id: "M8",
  nav: P.nav("黑名单", { back: "tab:me" }),
  body: `
    ${P.stateView("empty")}
    <div class="t-foot center">被拉黑的人不会再出现在你的任何局里。<br>对方不会知道自己被拉黑。</div>`,
},
{
  id: "M9",
  nav: P.nav("信任申诉", { back: "M3" }),
  body: `
    <div class="om-card">
      <div class="t-t3">对哪次判定有异议？</div>
      <div class="t-foot mt-1">申诉由真人复核，3 个工作日内回复</div>
      <div class="divider"></div>
      ${P.row({ icon: P.stickerImg("table-tennis.png", "st-24"), title: "7 月 30 日 · 乒乓球双打", sub: "判定：临近开始退出 · 你认为：场馆临时关闭", right: `<span class="om-chip gap">可申诉</span>` })}
    </div>
    <textarea class="om-input mt-3" placeholder="补充事实经过（可选）。复核只看事实记录，不看任何人的评价。"></textarea>`,
  footer: P.btn("提交申诉", "primary", "", "data-toast=\"已提交 · 复核结果会通知你（演示）\""),
},
{
  id: "M10",
  nav: P.nav("账号与数据", { back: "tab:me" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("envelope.png", "st-24"), title: "导出我的数据", sub: "画像 · 局记录 · 共同经历 · JSON 格式", go: "", right: `<span class="chevron">›</span>` })}
      ${P.row({ icon: P.stickerImg("certificate.png", "st-24"), title: "界面状态规范", sub: "加载 / 空 / 错误等八种全局状态", go: "G5", right: `<span class="chevron">›</span>` })}
    </div>
    <div class="om-card tight">
      ${P.row({ icon: icon("exit", 20), title: "注销账号", sub: "删除全部数据 · 进行中的局会交接或解散", go: "", right: `<span class="chevron">›</span>` })}
    </div>
    ${P.note("注销前会逐项告诉你：哪些数据被删除、哪些已成局的事实记录会以匿名形式保留（场地预约凭证等学校要求的存根）。", "access-card.png")}`,
},

/* ================= O · 主理人 ================= */
{
  id: "O1",
  nav: P.nav("主理人控制台", { back: "tab:me" }),
  body: `
    <div class="om-card">
      <div class="between">
        <div class="flex">${P.stickerImg("certificate.png", "st-44")}
          <div><div class="t-t3">羽毛球协会 · 周五夜场</div><div class="t-foot">官方局 · 每周五 19:00</div></div>
        </div>
        <span class="om-chip solid">进行中</span>
      </div>
      <div class="between mt-3">
        ${P.seatStrip([
          { role: "场 1", state: "filled", sticker: "badminton.png" },
          { role: "场 2", state: "filled", sticker: "badminton.png" },
          { role: "场 3", state: "gap", sticker: "badminton.png" },
          { role: "场 4", state: "gap", sticker: "badminton.png" },
        ])}
        ${P.gapBadge(2, "本周缺")}
      </div>
      <div class="flex mt-3">
        ${P.btn("报名看板", "ghost sm", "O3")}
        ${P.btn("分享缺口卡", "ghost sm", "G2")}
      </div>
    </div>
    ${P.btn("创建官方局", "primary", "O2")}
    <div class="mt-2">${P.btn("从模板复用", "ghost", "O4")}</div>`,
},
{
  id: "O2",
  nav: P.nav("创建官方局", { back: "O1" }),
  body: `
    <div class="om-card">
      <div class="t-foot mb-2">局名称</div>
      <input class="om-input" value="羽毛球协会 · 周五夜场">
      <div class="t-foot mb-2 mt-4">时间与地点</div>
      <input class="om-input" value="每周五 19:00–21:00 · 体育馆 2F">
      <div class="t-foot mb-2 mt-4">席位与角色</div>
      <div class="flex wrap">${P.chip("场 1 · 双打 ×4", "solid")}${P.chip("场 2 · 双打 ×4", "solid")}${P.chip("场 3 · 双打 ×4", "gap")}${P.chip("场 4 · 双打 ×4", "gap")}</div>
      <div class="t-foot mb-2 mt-4">官方标识</div>
      ${P.row({ icon: P.stickerImg("approval-stamp.png", "st-24"), title: "显示「官方局」标", sub: "需社团指导教师确认 · 已确认", right: `<span class="om-chip solid">已核验</span>` })}
    </div>
    ${P.note("官方局同样遵守匿名招募规则：满员前你也看不到报名者是谁。", "access-card.png")}`,
  footer: P.btn("发布官方局", "primary", "O3"),
},
{
  id: "O3",
  nav: P.nav("报名与到场看板", { back: "O1" }),
  body: `
    <div class="om-card">
      <div class="t-t3">本周五 · 8 月 15 日</div>
      <div class="gap-hero mt-3"><span class="n">14</span><span class="of">/ 16 席已确认</span></div>
      <div class="om-progress mt-3"><i style="width:87%"></i></div>
      <div class="t-foot mt-2">满员前不显示报名者身份 · 仅按席位统计</div>
    </div>
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("badminton.png", "st-24"), title: "场 1 · 双打", sub: "4 / 4 · 已满", right: `<span class="om-chip solid">满</span>` })}
      ${P.row({ icon: P.stickerImg("badminton.png", "st-24"), title: "场 2 · 双打", sub: "4 / 4 · 已满", right: `<span class="om-chip solid">满</span>` })}
      ${P.row({ icon: P.stickerImg("badminton.png", "st-24"), title: "场 3 · 双打", sub: "3 / 4", right: `<span class="om-chip gap">缺 1</span>` })}
      ${P.row({ icon: P.stickerImg("badminton.png", "st-24"), title: "场 4 · 双打", sub: "3 / 4", right: `<span class="om-chip gap">缺 1</span>` })}
    </div>
    ${P.section("到场核验（开场后）")}
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("qr-plaque-blank.png", "st-24"), title: "扫码到场", sub: "成员到场扫场地码 · 只记录「到了 / 没到」", right: `<span class="om-chip">周五启用</span>` })}
    </div>`,
},
{
  id: "O4",
  nav: P.nav("官方局模板", { back: "O1" }),
  body: `
    <div class="om-card tight">
      ${P.row({ icon: P.stickerImg("badminton.png", "st-24"), title: "周五夜场 · 4 片场", sub: "使用 12 次 · 最近：8 月 8 日", right: P.btn("复用", "ghost sm", "O2") })}
      ${P.row({ icon: P.stickerImg("trophy.png", "st-24"), title: "新生杯 · 选拔赛", sub: "使用 2 次 · 最近：5 月 17 日", right: P.btn("复用", "ghost sm", "O2") })}
      ${P.row({ icon: P.stickerImg("poster-blank.png", "st-24"), title: "协会招新体验场", sub: "使用 1 次 · 最近：3 月 2 日", right: P.btn("复用", "ghost sm", "O2") })}
    </div>
    ${P.note("模板保存的是局的结构（时间、地点、席位、规则），不保存任何参与者信息。", "certificate.png")}`,
},

/* ================= G · 全局与跨阶段 ================= */
{
  id: "G1",
  sheet: `<div class="om-sheet">
    <div class="sheet-grab"></div>
    <div class="center">${luluHTML("home.listening", "lulu-confirm")}</div>
    <div class="t-t3 center mt-2">Hermes</div>
    <div class="chat-list mt-3">
      <div class="bubble me">今晚图书馆哪层还有研讨间？</div>
      <div class="bubble">4 楼研讨间 4C 今晚 19:00–21:30 空闲，正好覆盖你的空档。要看预约预览吗？</div>
    </div>
    <div class="flex mt-3">
      <input class="om-input" placeholder="继续问…" style="min-height:44px">
      <button class="nav-back" style="width:44px;height:44px" aria-label="语音">${icon("mic", 18)}</button>
    </div>
    <div class="flex mt-3">
      ${P.btn("看预约预览", "primary sm", "B11")}
      ${P.btn("关闭", "text sm", "__back")}
    </div>
  </div>`,
  body: `<div style="opacity:0.35;pointer-events:none">${P.section("下方页面保持不动")}${P.card(P.row({ icon: P.stickerImg("books-stack.png", "st-24"), title: "Hermes 以浮层唤起", sub: "不打断当前页面，关掉就回到原处" }))}</div>`,
},
{
  id: "G2",
  nav: P.nav("缺口卡分享", { back: "__back" }),
  body: `
    <div class="om-card mt-3" style="padding:0;overflow:hidden">
      <div style="background:var(--ink);padding:24px 20px;color:var(--paper)">
        <div class="flex" style="justify-content:space-between">
          <span class="mono" style="font-size:11px;letter-spacing:0.14em">ONE MORE · 差一个</span>
          <span style="font-size:11px;color:var(--sage)">中山大学</span>
        </div>
        <div class="mt-4" style="font-size:26px;font-weight:800;line-height:1.25">周五晚篮球 4v4<br>还差 <span style="background:var(--yolk);color:var(--ink);padding:0 10px;border-radius:8px">2</span> 个后卫</div>
        <div class="mt-3" style="font-size:13px;color:var(--sage)">周五 19:00 · 东校园室外场 3 号场</div>
      </div>
      <div style="padding:16px 20px" class="between">
        ${P.seatStrip([
          { role: "前锋", state: "filled", sticker: "basketball.png" },
          { role: "中锋", state: "filled", sticker: "basketball.png" },
          { role: "后卫", state: "gap", sticker: "basketball.png" },
          { role: "后卫", state: "gap", sticker: "basketball.png" },
        ])}
        <span class="t-cap">长按识别小程序码加入</span>
      </div>
    </div>
    ${P.note("缺口卡只含：什么事、什么时候、缺什么角色。不含发起人身份，点进来的人先认证再看局。", "qr-plaque-blank.png")}`,
  footer: `${P.btn("发到微信群", "primary", "", "data-toast=\"已生成图片（演示）\"")}
    <div class="mt-2">${P.btn("复制链接", "ghost", "", "data-toast=\"链接已复制（演示）\"")}</div>`,
},
{
  id: "G3",
  nav: "",
  body: `
    <div class="center mt-6">${luluHTML("core.care", "lulu-empty")}</div>
    <div class="t-t1 center mt-4">登录状态失效了</div>
    <div class="t-call muted center mt-2" style="max-width:280px;margin-left:auto;margin-right:auto">
      出于安全考虑需要重新认证。<br>扫一下就好——<b>你刚才在看的局会原地等你</b>。
    </div>
    <div class="qr-box mt-5">
      <svg viewBox="0 0 21 21" fill="var(--ink)"><path d="M0 0h7v7H0zM2 2v3h3V2zM14 0h7v7h-7zM16 2v3h3V2zM0 14h7v7H0zM2 16v3h3v-3zM9 0h3v3H9zM9 5h2v2H9zM14 9h3v2h-3zM18 9h3v3h-3zM9 9h2v3H9zM12 10h2v2h-2zM9 14h3v2H9zM13 13h2v2h-2zM16 14h2v2h-2zM19 14h2v2h-2zM14 17h3v2h-3zM18 18h3v3h-3zM9 18h2v3H9zM12 19h2v2h-2z"/></svg>
    </div>`,
  footer: `${P.btn("已完成扫码，回到刚才的局", "primary", "C2")}
    <div class="t-cap center mt-2">恢复后回到：公开局详情 · 周五晚篮球</div>`,
},
{
  id: "G4",
  nav: P.nav("已结束", { back: "E1" }),
  body: `
    <div class="center mt-5">${luluHTML("exit.bow", "lulu-empty")}</div>
    <div class="t-t1 center mt-4">这个局安静地结束了</div>
    <div class="t-call muted center mt-3" style="max-width:290px;margin-left:auto;margin-right:auto">
      「上周乒乓球双打」到截止时间没有凑齐。<br>没有人被拒绝，也没有人知道你开过口。<br>它就这样结束了，像没发生过一样。
    </div>
    <div class="om-card mt-6">
      ${P.row({ icon: P.stickerImg("hourglass.png", "st-24"), title: "记录", sub: "只在你的「已结束」里保留 30 天，之后彻底删除" })}
      ${P.row({ icon: icon("shield", 20), title: "其他人看到的", sub: "什么都没有。没有通知，没有归因" })}
    </div>`,
  footer: `${P.btn("换个时间再试一次", "primary", "D1")}
    <div class="mt-2">${P.btn("好的", "text", "E1")}</div>`,
},
{
  id: "G5",
  nav: P.nav("状态规范", { back: "M10" }),
  large: "八种全局状态",
  largeSub: "一套系统，所有页面共用 · 不各写各的",
  body: `
    ${P.section("1 · 加载")}
    <div class="om-card">${P.stateView("loading")}</div>
    ${P.section("2 · 空")}
    <div class="om-card">${P.stateView("empty")}</div>
    ${P.section("3 · 网络错误")}
    <div class="om-card">${P.stateView("network")}</div>
    ${P.section("4 · 离线")}
    <div class="om-card">${P.stateView("offline")}</div>
    ${P.section("5 · 权限拒绝")}
    <div class="om-card">${P.stateView("denied")}</div>
    ${P.section("6 · 会话失效")}
    <div class="om-card">${P.stateView("expired")}</div>
    ${P.section("7 · 重复点击")}
    <div class="om-card">${P.stateView("duplicate")}</div>
    ${P.section("8 · 数据过期")}
    <div class="om-card">${P.stateView("stale")}</div>
    ${P.note("统一规则：Lulu 在异常态永远用「关切」或「在想」；文案先说影响、再给动作；动作按钮最多一个主按钮。红色不出现在任何状态里。", "chat-bubble.png")}`,
},
]);
