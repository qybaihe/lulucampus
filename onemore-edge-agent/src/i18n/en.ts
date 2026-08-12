const en = {
  // Header
  "app.title": "OneMore Campus Orchestrator",
  "app.subtitle": "EdgeOne orchestrates · credentials stay on device",

  // Empty state
  "empty.title": "Campus orchestration sandbox",
  "empty.hint": "I schedule around the timetable/tasks you attach; real campus actions stay on iOS. Try: arrange study and gym around tomorrow's classes.",
  "empty.features": "Client credentials · Local timetable · Edge orchestration",

  // Chat input
  "chat.placeholder": "e.g. Arrange gym and homework around my timetable…",
  "chat.hint": "Secrets stay on client · EdgeOne Makers Agent · Demo",

  // Preset questions
  "preset.1": "Using my attached timetable, find free slots for study and gym tomorrow.",
  "preset.2": "Turn homework and gym into task drafts I can save locally.",

  // Tool indicators
  "tool.timetable": "Timetable",
  "tool.tasks": "Tasks",
  "tool.schedule": "Schedule",
  "tool.draft": "Draft",
  "tool.electives": "Electives",
  "tool.campus": "Campus",
  "tool.weather": "Weather",
  "tool.clothing": "Clothing",
  "tool.translate": "Translate",
  "tool.statistics": "Statistics",

  // Status & errors
  "status.error": "Request failed. Please check if the backend service is running.",
  "status.stopped": "⏹ *Generation stopped*",
  "status.backendError": "Backend abort request failed. The server may still be running.",

  // Debug panel
  "debug.title": "Trace",
  "debug.events": "events",
  "debug.clear": "Clear",
  "debug.empty": "Waiting for SSE events...",
  "debug.emptyHint": "After sending a message, all raw backend data will be displayed here.",

  // Conversation sidebar
  "sidebar.label": "Conversation list",
  "sidebar.title": "Chats",
  "sidebar.newChat": "New chat",
  "sidebar.loading": "Loading conversations...",
  "sidebar.loadMore": "Load more",
  "sidebar.loadingMore": "Loading...",
  "sidebar.emptyTitle": "No conversations yet",
  "sidebar.emptyHint": "Click \"New chat\" to start your first conversation.",
  "sidebar.delete": "Delete conversation",
  "sidebar.deleteConfirm": "Permanently delete this conversation? This cannot be undone.",

  // Aria labels (button hover/screen-reader)
  "aria.send": "Send",
  "aria.clearHistory": "Clear history",
  "aria.stopGeneration": "Stop generation",

  // Language toggle
  "lang.switch": "中文",

  // ─── Floating bottom-right action badges ─────────────────────────────
  "floatingLink.deploy": "Deploy",
  "floatingLink.github": "GitHub",
} as const;

export default en;
