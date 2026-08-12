/* 差一个 · ONE MORE — iPhone 壳路由与共享组件
   路由：#/tab/<today|match|create|msg|me> 或 #/s/<节点编号>
   位置持久化：localStorage */

const SCREENS = {};
function defineScreens(list) { list.forEach(s => { SCREENS[s.id] = s; }); }

const TABS = [
  { id: "today",  label: "今天",  root: "B1",  icon: "sun" },
  { id: "match",  label: "比赛",  root: "B12", icon: "trophy" },
  { id: "create", label: "差一个", root: "D1", icon: "plus" },
  { id: "msg",    label: "消息",  root: "MSG", icon: "chat" },
  { id: "me",     label: "我",    root: "M1",  icon: "person" },
];

const ST = "assets/stickers/";

/* ---------- 图标（线性，1.6px 描边） ---------- */
const ICONS = {
  sun: '<circle cx="12" cy="12" r="4.4"/><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5 5l1.7 1.7M17.3 17.3 19 19M19 5l-1.7 1.7M6.7 17.3 5 19"/>',
  trophy: '<path d="M7 4h10v5a5 5 0 0 1-10 0V4Z"/><path d="M7 6H4.5a2.5 2.5 0 0 0 2.6 4M17 6h2.5a2.5 2.5 0 0 1-2.6 4M12 14v3.2M8.5 20h7M10 17.2h4"/>',
  plus: '<path d="M12 5.5v13M5.5 12h13"/>',
  chat: '<path d="M21 12a8 8 0 0 1-8 8c-1.3 0-2.6-.3-3.7-.8L4 20.5l1.4-4.2A8 8 0 1 1 21 12Z"/>',
  person: '<circle cx="12" cy="8.2" r="3.6"/><path d="M4.8 20a7.4 7.4 0 0 1 14.4 0"/>',
  back: '<path d="M14.5 5.5 8 12l6.5 6.5"/>',
  bell: '<path d="M6 9.5a6 6 0 0 1 12 0c0 4 1.5 5.5 1.5 5.5h-15S6 13.5 6 9.5M10.3 19a1.9 1.9 0 0 0 3.4 0"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5.2l3.4 2"/>',
  pin: '<path d="M12 21s-6.5-5.4-6.5-10.3a6.5 6.5 0 0 1 13 0C18.5 15.6 12 21 12 21Z"/><circle cx="12" cy="10.5" r="2.3"/>',
  cal: '<rect x="4" y="5.5" width="16" height="15" rx="2.5"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
  shield: '<path d="M12 3 5 5.8v5.4c0 4.3 3 7.6 7 9.3 4-1.7 7-5 7-9.3V5.8L12 3Z"/><path d="m9.2 11.8 2 2 3.6-3.8"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.4 2.4M15.6 15.6 18 18M18 6l-2.4 2.4M8.4 15.6 6 18"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  share: '<path d="M12 15V4M8 8l4-4 4 4M5 12v7a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19v-7"/>',
  flag: '<path d="M6 21V4M6 4.8C8 3.4 10 3.4 12 4.8s4 1.4 6 0v8.6c-2 1.4-4 1.4-6 0s-4-1.4-6 0"/>',
  doc: '<path d="M7 3.5h7L19 8v12.5H7V3.5Z"/><path d="M14 3.5V8h4.5M10 12.5h5M10 16h5"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.8 13.6 6a6.4 6.4 0 0 1 2.5 1.5l3.4-.4 1.5 2.6-2.5 2.3a6.6 6.6 0 0 1 0 3l2.5 2.3-1.5 2.6-3.4-.4a6.4 6.4 0 0 1-2.5 1.5L12 21.2 10.4 18a6.4 6.4 0 0 1-2.5-1.5l-3.4.4L3 14.3l2.5-2.3a6.6 6.6 0 0 1 0-3L3 6.7 4.5 4.1l3.4.4A6.4 6.4 0 0 1 10.4 3L12 2.8Z" transform="scale(0.92) translate(1,1)"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>',
  scan: '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16M4 12h16"/>',
  exit: '<path d="M14 4h5v16h-5M4 12h11M11 8l4 4-4 4"/>',
  warn: '<path d="M12 3.5 22 20H2L12 3.5Z"/><path d="M12 10v4.4M12 17.2v.3"/>',
};
function icon(name, size = 22, color = "currentColor") {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;
}

/* ---------- 共享片段 ---------- */
const P = {
  nav(title, opts = {}) {
    const { back = null, right = "" } = opts;
    return `<div class="om-nav">
      ${back ? `<button class="nav-back" data-go="${back}" aria-label="返回">${icon("back", 18)}</button>` : ""}
      <div class="nav-title">${title}</div>
      <div class="nav-right">${right}</div>
    </div>`;
  },
  largeTitle(t, sub) {
    return `<div class="om-large-title">${t}</div>${sub ? `<div class="om-large-sub">${sub}</div>` : ""}`;
  },
  section(t, more) {
    return `<div class="om-section"><span>${t}</span>${more ? `<button class="more" data-go="${more.go}">${more.label}</button>` : ""}</div>`;
  },
  row(o) {
    return `<button class="om-row" ${o.go ? `data-go="${o.go}"` : ""}>
      ${o.icon ? `<span class="row-icon">${o.icon}</span>` : ""}
      <span class="row-main">
        <span class="row-title">${o.title}</span>
        ${o.sub ? `<div class="row-sub">${o.sub}</div>` : ""}
      </span>
      ${o.right ? `<span class="row-right">${o.right}</span>` : ""}
      ${o.go ? `<span class="chevron">›</span>` : ""}
    </button>`;
  },
  card(inner, cls = "") { return `<div class="om-card ${cls}">${inner}</div>`; },
  btn(label, kind = "primary", go, extra = "") {
    return `<button class="om-btn ${kind}" ${go ? `data-go="${go}"` : ""} ${extra}>${label}</button>`;
  },
  chip(t, kind = "", img = "") {
    return `<span class="om-chip ${kind}">${img ? `<img src="${ST}${img}" alt="">` : ""}${t}</span>`;
  },
  gapBadge(n, label = "还缺") {
    return `<span class="gap-badge">${label} <span class="n">${n}</span> 人</span>`;
  },
  /* 圆桌席位：seats = [{role, state:'filled'|'gap', sticker}] */
  seatTable(name, seats, sticker = "round-table.png") {
    const n = seats.length;
    const R = 96, cx = 120, cy = 120;
    const dots = seats.map((s, i) => {
      const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
      return `<div class="seat ${s.state}" style="left:${x}px;top:${y}px">
        <div class="seat-dot"><img src="${ST}${s.sticker}" alt=""></div>
        <div class="seat-role">${s.state === "gap" ? "缺 · " : ""}${s.role}</div>
      </div>`;
    }).join("");
    return `<div class="seat-table" role="img" aria-label="${name}：${seats.filter(s=>s.state==="filled").length} 人已就位，缺 ${seats.filter(s=>s.state==="gap").length} 人">
      <div class="table-top"><div><img src="${ST}${sticker}" alt=""><div class="table-name">${name}</div></div></div>
      ${dots}
    </div>`;
  },
  seatStrip(seats) {
    return `<span class="seat-strip">${seats.map(s =>
      `<span class="s ${s.state}"><img src="${ST}${s.sticker}" alt="${s.role}${s.state === "gap" ? "（缺口）" : "（已就位）"}"></span>`).join("")}</span>`;
  },
  progress(a, b) {
    return `<div class="between mb-2"><span class="t-foot">已就位 <b class="mono" style="color:var(--ink)">${a}</b> / ${b}</span>${a < b ? P.gapBadge(b - a) : `<span class="om-chip solid">已满员</span>`}</div>
    <div class="om-progress"><i style="width:${(a / b) * 100}%"></i></div>`;
  },
  stateView(kind) {
    const M = {
      loading:  { clip: "home.thinking", t: "正在加载", d: "Lulu 正在取数，稍等一下。", btn: "" },
      empty:    { clip: "home.idle", t: "这里还空着", d: "暂时没有内容。有进展时，Lulu 会来告诉你。", btn: "" },
      network:  { clip: "core.care", t: "网络开了小差", d: "请求没有发出去。检查网络后再试一次，已填的内容都在。", btn: ["重新加载", "primary"] },
      offline:  { clip: "core.care", t: "当前离线", d: "你现在看到的是上次同步的内容。恢复网络后会自动更新。", btn: "" },
      denied:   { clip: "core.care", t: "这个权限还没开", d: "没有它，这部分功能用不了。你可以随时在设置里改主意。", btn: ["去系统设置开启", "primary"] },
      expired:  { clip: "core.care", t: "登录状态失效了", d: "出于安全考虑需要重新认证。用企业微信扫一下就好，进度不会丢。", btn: ["重新扫码认证", "primary"] },
      duplicate:{ clip: "home.reply", t: "已经收到啦", d: "这个操作正在处理，不用重复点。", btn: "" },
      stale:    { clip: "home.thinking", t: "内容可能不是最新", d: "这页数据更新于 12 分钟前。下拉可以刷新。", btn: ["刷新", "ghost"] },
    };
    const m = M[kind];
    return `<div class="state-view">
      ${luluHTML(m.clip, "lulu-empty")}
      <div class="sv-title">${m.t}</div>
      <div class="sv-desc">${m.d}</div>
      ${m.btn ? P.btn(m.btn[0], m.btn[1]) : ""}
    </div>`;
  },
  note(text, img = "chat-bubble.png") {
    return `<div class="om-note"><img src="${ST}${img}" alt=""><span>${text}</span></div>`;
  },
  switch(on = false) { return `<span class="om-switch ${on ? "on" : ""}"></span>`; },
  stickerImg(name, cls = "st-44") { return `<img class="sticker ${cls}" src="${ST}${name}" alt="">`; },
};

/* ---------- 壳与路由 ---------- */
let currentTab = "today";
let stack = [];

function tabbarHTML() {
  return `<div class="tabbar">${TABS.map(t => {
    if (t.id === "create") {
      return `<button class="tab-item" data-tab="create" aria-label="差一个">
        <span class="tab-create">⊕</span><span class="tab-create-label">差一个</span><span class="tab-dot"></span>
      </button>`;
    }
    return `<button class="tab-item ${currentTab === t.id ? "active" : ""}" data-tab="${t.id}">
      ${icon(t.icon, 24)}<span>${t.label}</span><span class="tab-dot"></span>
    </button>`;
  }).join("")}</div><div class="home-indicator"></div>`;
}

function statusbarHTML() {
  return `<div class="statusbar">
    <span class="mono" style="font-weight:700">9:41</span>
    <span class="sb-icons">
      <svg width="18" height="12" viewBox="0 0 18 12" fill="currentColor"><rect x="0" y="7" width="3" height="5" rx="1"/><rect x="5" y="5" width="3" height="7" rx="1"/><rect x="10" y="2.5" width="3" height="9.5" rx="1"/><rect x="15" y="0" width="3" height="12" rx="1"/></svg>
      <svg width="17" height="12" viewBox="0 0 17 12" fill="currentColor"><path d="M8.5 9.6a1.6 1.6 0 1 1 0 3.2 1.6 1.6 0 0 1 0-3.2ZM8.5 5.7c1.8 0 3.4.7 4.6 1.9l-1.5 1.5a4.4 4.4 0 0 0-6.2 0L3.9 7.6a6.4 6.4 0 0 1 4.6-1.9Zm0-4.2c2.9 0 5.6 1.2 7.6 3.1l-1.5 1.5A8.6 8.6 0 0 0 8.5 4a8.6 8.6 0 0 0-6.1 2.6L.9 4.6A10.7 10.7 0 0 1 8.5 1.5Z"/></svg>
      <svg width="25" height="12" viewBox="0 0 25 12" fill="none"><rect x="0.5" y="0.5" width="21" height="11" rx="3.5" stroke="currentColor" opacity="0.4"/><rect x="2" y="2" width="15" height="8" rx="2" fill="currentColor"/><path d="M23.5 4v4a2 2 0 0 0 0-4Z" fill="currentColor" opacity="0.4"/></svg>
    </span>
  </div><div class="dynamic-island"></div>`;
}

function renderScreen(id) {
  const s = SCREENS[id];
  if (!s) return `<div class="scroll">${P.stateView("empty")}</div>`;
  const body = typeof s.body === "function" ? s.body() : s.body;
  const showTab = s.tab !== undefined;
  if (showTab) currentTab = s.tab;
  return `${s.nav || ""}${s.large ? P.largeTitle(s.large, s.largeSub) : ""}
    <div class="scroll" data-screen="${s.id}">${body}</div>
    ${s.footer ? `<div class="om-footer ${showTab ? "" : "over-sheet"}">${s.footer}</div>` : ""}
    ${s.sheet || ""}
    ${showTab ? tabbarHTML() : `<div class="home-indicator"></div>`}`;
}

function mount() {
  const el = document.getElementById("screen-root");
  const id = stack.length ? stack[stack.length - 1] : TABS.find(t => t.id === currentTab).root;
  el.innerHTML = renderScreen(id);
  luluBoot(el);
  bind(el);
  const sc = el.querySelector(".scroll");
  if (sc) sc.scrollTop = 0;
  syncHash();
}

function bind(root) {
  root.querySelectorAll("[data-go]").forEach(b => {
    b.addEventListener("click", () => {
      const t = b.dataset.go;
      if (t === "__back") { pop(); return; }
      if (t.startsWith("tab:")) { goTab(t.slice(4)); return; }
      push(t);
    });
  });
  root.querySelectorAll("[data-tab]").forEach(b => {
    b.addEventListener("click", () => goTab(b.dataset.tab));
  });
  root.querySelectorAll("[data-toast]").forEach(b => {
    b.addEventListener("click", () => toast(b.dataset.toast));
  });
  root.querySelectorAll(".om-switch").forEach(sw => {
    sw.addEventListener("click", () => sw.classList.toggle("on"));
  });
  root.querySelectorAll("[data-seg]").forEach(seg => {
    seg.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
      seg.querySelectorAll("button").forEach(x => x.classList.remove("on"));
      b.classList.add("on");
    }));
  });
}

function push(id) { stack.push(id); mount(); }
function pop() { stack.pop(); mount(); }
function goTab(t) { currentTab = t; stack = []; mount(); }

function syncHash() {
  const id = stack.length ? stack[stack.length - 1] : null;
  const h = id ? `#/s/${id}` : `#/tab/${currentTab}`;
  history.replaceState(null, "", h);
  localStorage.setItem("onemore.pos", h);
}

function restoreFromHash() {
  const h = location.hash || localStorage.getItem("onemore.pos") || "";
  const m = h.match(/#\/s\/([\w.]+)/);
  const t = h.match(/#\/tab\/(\w+)/);
  if (m && SCREENS[m[1]]) {
    const s = SCREENS[m[1]];
    if (s.tab !== undefined) { currentTab = s.tab; stack = [m[1]]; }
    else { stack = [m[1]]; }
  } else if (t && TABS.some(x => x.id === t[1])) {
    currentTab = t[1];
  }
}

function toast(msg) {
  let el = document.querySelector(".om-toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "om-toast";
    document.getElementById("screen-root").appendChild(el);
  }
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 1800);
}

window.addEventListener("hashchange", () => { restoreFromHash(); mount(); });
