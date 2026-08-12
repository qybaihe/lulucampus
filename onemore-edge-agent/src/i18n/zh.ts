const zh = {
  // Header
  "app.title": "OneMore Campus Orchestrator",
  "app.subtitle": "EdgeOne 只编排 · 凭证与课表留在客户端",

  // Empty state
  "empty.title": "校园编排沙箱",
  "empty.hint": "我会根据你附带的课表/任务做排程与任务草稿；真实校园动作由 iOS 执行。试试：根据明天课表帮我排自习和健身。",
  "empty.features": "Client credentials · Local timetable · Edge orchestration",

  // Chat input
  "chat.placeholder": "例如：根据课表帮我排明天晚上的健身和作业…",
  "chat.hint": "凭证不落盘 · EdgeOne Makers Agent · 演示",

  // Preset questions
  "preset.1": "根据我附带的课表，帮我排明天的自习和健身空档。",
  "preset.2": "帮我查珠海校区还能选的 AI / 移动开发相关选修课。",

  // Tool indicators
  "tool.timetable": "课表",
  "tool.tasks": "任务",
  "tool.schedule": "排程",
  "tool.draft": "草稿",
  "tool.electives": "选修",
  "tool.campus": "校园",
  "tool.weather": "天气",
  "tool.clothing": "穿搭",
  "tool.translate": "翻译",
  "tool.statistics": "统计",

  // Status & errors
  "status.error": "请求失败，请检查后端服务是否正常运行。",
  "status.stopped": "⏹ *已停止生成*",
  "status.backendError": "后端中止请求失败，服务器可能仍在运行。",

  // Debug panel
  "debug.title": "传输流",
  "debug.events": "事件",
  "debug.clear": "清除",
  "debug.empty": "等待 SSE 事件...",
  "debug.emptyHint": "发送消息后，所有原始后端数据将在此处显示。",

  // Conversation sidebar
  "sidebar.label": "会话列表",
  "sidebar.title": "会话",
  "sidebar.newChat": "新建聊天",
  "sidebar.loading": "正在加载会话...",
  "sidebar.loadMore": "加载更多",
  "sidebar.loadingMore": "加载中...",
  "sidebar.emptyTitle": "暂无会话",
  "sidebar.emptyHint": "点击「新建聊天」开始第一段对话。",
  "sidebar.delete": "删除会话",
  "sidebar.deleteConfirm": "确定要永久删除这个会话吗？此操作不可恢复。",

  // Aria labels (button hover/screen-reader)
  "aria.send": "发送",
  "aria.clearHistory": "清除历史",
  "aria.stopGeneration": "停止生成",

  // Language toggle
  "lang.switch": "English",

  // ─── Floating bottom-right action badges ─────────────────────────────
  "floatingLink.deploy": "一键部署",
  "floatingLink.github": "GitHub",
} as const;

export default zh;
