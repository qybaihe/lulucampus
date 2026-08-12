/**
 * Channel WebSocket — web analogue of iOS WebSocketClient.swift.
 *
 * - URL: {wsBase}/channels/{channelId}（wsBase 由 API baseURL 推导 http→ws）
 * - 认证：浏览器无法设自定义 header，改在 Sec-WebSocket-Protocol 提供
 *   `om-auth.<base64url(token)>`（与 `onemore.v1` 一起），token 不进 URL。
 * - 帧：裸 MessagePayload JSON（无 data/meta 信封）
 * - 去重：seen id set（消费方仍应二次去重，对齐 iOS 双层去重）
 * - 退避：min(2^retry, 20) 秒；收到消息即归零
 * - 4401：标记会话过期并终止（不再重连）
 * - 页面不可见时断开（对齐 iOS 后台断开），可见后恢复
 */

import type { MessagePayload } from "./repositories";

export type ChannelSocketState =
  | "idle"
  | "connecting"
  | "connected"
  | { waitingToRetry: number };

export interface ChannelSocketHandlers {
  onMessage: (message: MessagePayload) => void;
  onSessionExpired?: () => void;
  onStateChange?: (state: ChannelSocketState) => void;
}

export interface ChannelSocketHandle {
  close: () => void;
}

function base64Url(value: string): string {
  return btoa(value).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function websocketBaseURL(apiBaseURL: string): string {
  if (typeof import.meta !== "undefined" && import.meta.env?.VITE_WS_BASE) {
    return String(import.meta.env.VITE_WS_BASE).replace(/\/$/, "");
  }
  let base = apiBaseURL.replace(/\/$/, "");
  // Relative API base (same-origin reverse proxy) → resolve via page origin.
  if (!/^https?:\/\//i.test(base) && typeof window !== "undefined" && window.location) {
    base = window.location.origin + base;
  }
  return base.replace(/^http/, "ws");
}

export function openChannelSocket(opts: {
  apiBaseURL: string;
  channelId: string;
  token: string | null;
  handlers: ChannelSocketHandlers;
}): ChannelSocketHandle {
  const { apiBaseURL, channelId, token, handlers } = opts;
  const url = `${websocketBaseURL(apiBaseURL)}/channels/${channelId}`;
  const seen = new Set<string>();
  let socket: WebSocket | null = null;
  let retry = 0;
  let closed = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  const setState = (state: ChannelSocketState) =>
    handlers.onStateChange?.(state);

  // 无凭证：与 iOS 一致 — 结束流、不重连
  if (!token) {
    setState("idle");
    return { close: () => undefined };
  }

  const protocols = ["onemore.v1", `om-auth.${base64Url(token)}`];

  function connect() {
    if (closed || documentHidden()) return;
    setState("connecting");
    let ws: WebSocket;
    try {
      ws = new WebSocket(url, protocols);
    } catch {
      scheduleRetry();
      return;
    }
    socket = ws;

    ws.onopen = () => {
      if (ws !== socket) return;
      setState("connected");
    };

    ws.onmessage = (event) => {
      if (ws !== socket) return;
      retry = 0;
      try {
        const payload = JSON.parse(String(event.data)) as MessagePayload;
        if (payload && typeof payload.id === "string") {
          if (seen.has(payload.id)) return;
          seen.add(payload.id);
          handlers.onMessage(payload);
        }
      } catch {
        /* 非 JSON 帧忽略 */
      }
    };

    ws.onclose = (event) => {
      if (ws !== socket) return;
      socket = null;
      if (closed) return;
      if (event.code === 4401) {
        handlers.onSessionExpired?.();
        setState("idle");
        closed = true;
        return;
      }
      scheduleRetry();
    };

    ws.onerror = () => {
      /* onclose 统一处理 */
    };
  }

  function scheduleRetry() {
    if (closed) return;
    if (documentHidden()) {
      setState("idle");
      return;
    }
    retry += 1;
    setState({ waitingToRetry: retry });
    const delay = Math.min(2 ** retry, 20) * 1000;
    retryTimer = setTimeout(connect, delay);
  }

  function documentHidden(): boolean {
    return typeof document !== "undefined" && document.visibilityState === "hidden";
  }

  function onVisibility() {
    if (closed) return;
    if (documentHidden()) {
      // 对齐 iOS：后台断开，前台恢复
      if (retryTimer) clearTimeout(retryTimer);
      retryTimer = null;
      socket?.close(1000, "backgrounded");
      socket = null;
      setState("idle");
    } else if (!socket) {
      retry = 0;
      connect();
    }
  }

  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", onVisibility);
  }
  connect();

  return {
    close() {
      closed = true;
      if (retryTimer) clearTimeout(retryTimer);
      retryTimer = null;
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", onVisibility);
      }
      socket?.close(1000, "client closed");
      socket = null;
    },
  };
}
