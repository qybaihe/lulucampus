import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import {
  asList,
  type ChannelScenePolicy,
  type MessagePayload,
  type RelationSummary,
} from "../../core/api/repositories";
import { attentionItems, pathFromAttentionLink, type AttentionItem } from "../../core/today/attention";
import { openChannelSocket, type ChannelSocketHandle } from "../../core/api/ws";
import {
  Btn,
  Card,
  Icon,
  LargeTitle,
  NavBar,
  Row,
  Screen,
  Scroll,
  StateView,
  Sticker,
} from "../../components/ui/primitives";

/** MSG · 消息（Tab 根）。数据源与 iOS 一致：搭子关系列表。 */
export function MessagesScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [items, setItems] = useState<RelationSummary[]>([]);
  const [attention, setAttention] = useState<AttentionItem[]>([]);
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      const [raw, summary] = await Promise.all([
        repos.relations.list(),
        repos.today.summary().catch(() => null),
      ]);
      setItems(asList(raw));
      setAttention(attentionItems(summary?.pending));
      setPhase("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  return (
    <Screen id="screen-MSG-messages">
      <Scroll>
        <LargeTitle title="消息与搭子" />
        {phase === "loading" ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}
        {phase === "failed" ? (
          <Card>
            <StateView
              kind="network"
              message={error ?? undefined}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : null}
        {phase === "loaded" && items.length === 0 && attention.length === 0 ? (
          <Card>
            <StateView kind="empty" message="只有已成局的人会出现在这里。" />
          </Card>
        ) : null}
        {phase === "loaded" && attention.length > 0 ? (
          <>
            <div className="t-t3 mt-3">需要你处理</div>
            <Card tight className="mt-2" data-od-id="messages-attention">
              {attention.map((item) => (
                <Row
                  key={item.id}
                  title={item.title}
                  sub={item.badge}
                  onClick={() => {
                    const path = pathFromAttentionLink(item.deepLink);
                    if (path) nav(path);
                  }}
                />
              ))}
            </Card>
          </>
        ) : null}
        {phase === "loaded" && items.length > 0 ? (
          <Card tight>
            {items.map((item) => (
              <Row
                key={item.id}
                icon={<Sticker name="chat-bubble.png" size="st-24" />}
                title={item.participants
                  .map((p) => p.display_name ?? "同学")
                  .join(" · ")}
                sub={
                  item.experiences?.length
                    ? `共同完成 · ${item.experiences[0].gathering_type}`
                    : "搭子关系"
                }
                onClick={() => {
                  if (item.channel_id) {
                    nav(`/channel/${item.channel_id}`, {
                      state: { title: "搭子会话" },
                    });
                  } else nav("/relations");
                }}
              />
            ))}
          </Card>
        ) : null}
        {phase === "loaded" ? (
          <div className="mt-2">
            <Btn kind="ghost" to="/relations">
              查看全部搭子关系
            </Btn>
          </div>
        ) : null}
      </Scroll>
    </Screen>
  );
}

/* ---------- E14 局内群聊（对齐 iOS ChannelView） ---------- */

function shortTime(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** 认证图片：/media/images/{id} 需要 Authorization，<img src> 带不了 header。 */
function AuthImage({
  url,
  caption,
}: {
  url: string;
  caption?: string | null;
}) {
  const { client, baseURL } = useApp();
  const [state, setState] = useState<
    { kind: "loading" } | { kind: "loaded"; objectURL: string } | { kind: "failed" }
  >({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let objectURL: string | null = null;
    setState({ kind: "loading" });
    (async () => {
      try {
        const absolute = url.startsWith("http")
          ? url
          : `${baseURL.replace(/\/$/, "")}${url.startsWith("/") ? url : `/${url}`}`;
        const res = await fetch(absolute, {
          headers: {
            Accept: "image/jpeg,image/png,image/heic,image/heif",
            ...client.authHeaders(),
          },
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const blob = await res.blob();
        if (cancelled) return;
        objectURL = URL.createObjectURL(blob);
        setState({ kind: "loaded", objectURL });
      } catch {
        if (!cancelled) setState({ kind: "failed" });
      }
    })();
    return () => {
      cancelled = true;
      if (objectURL) URL.revokeObjectURL(objectURL);
    };
  }, [url, attempt, client, baseURL]);

  if (state.kind === "loaded") {
    return (
      <span>
        <img className="bubble-img" src={state.objectURL} alt="聊天图片" />
        {caption && caption !== "图片" ? (
          <span className="t-cap" style={{ display: "block", marginTop: 4 }}>
            {caption}
          </span>
        ) : null}
      </span>
    );
  }
  if (state.kind === "failed") {
    return (
      <span className="bubble-img-fallback">
        <span>图片暂不可查看</span>
        <button
          type="button"
          className="om-btn ghost sm"
          onClick={() => setAttempt((n) => n + 1)}
        >
          重试图片
        </button>
      </span>
    );
  }
  return <span className="bubble-img-fallback">…</span>;
}

function SystemGatheringCard({ content }: { content: string }) {
  const lines = content.split("\n").filter((l) => l.trim());
  const title = lines[0] ?? "成局卡";
  const rest = lines.slice(1);
  return (
    <div className="sys-gathering-card" data-od-id="channel-system-gathering-card">
      <div className="sys-title">{title}</div>
      {rest.map((line, i) => (
        <div key={i} className="sys-line">
          {line}
        </div>
      ))}
      <div className="sys-foot">以上是系统整理的事实摘要 · 接下来交给你们</div>
    </div>
  );
}

function MessageBubble({
  message,
  isMe,
}: {
  message: MessagePayload;
  isMe: boolean;
}) {
  if (message.sender_type === "system") {
    return <SystemGatheringCard content={message.content ?? "成局卡"} />;
  }
  const isAzou = message.sender_type === "azou";
  const senderLabel = isMe
    ? null
    : isAzou
      ? "噜噜"
      : message.sender_display_name || "同学";
  return (
    <div className={`bubble-group ${isMe ? "me" : ""}`}>
      {senderLabel ? <span className="bubble-sender">{senderLabel}</span> : null}
      <div className={`bubble ${isMe ? "me" : isAzou ? "azou" : ""}`}>
        {message.content_type === "image" && message.image ? (
          <AuthImage url={message.image.url} caption={message.image.caption} />
        ) : message.content_type === "location" && message.location ? (
          <span className="flex" style={{ gap: 6, alignItems: "center" }}>
            <Icon name="pin" size={16} />
            {message.location.label}
          </span>
        ) : (
          message.content ?? ""
        )}
      </div>
      <span className="bubble-time">{shortTime(message.sent_at)}</span>
    </div>
  );
}

export function ChannelScreen() {
  const { channelId } = useParams();
  const location = useLocation();
  const channelTitle =
    (location.state as { title?: string } | null)?.title ?? "局内群聊";
  const { repos, client, session, baseURL } = useApp();
  const [messages, setMessages] = useState<MessagePayload[]>([]);
  const [policy, setPolicy] = useState<ChannelScenePolicy | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [permissionNotice, setPermissionNotice] = useState(false);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const socketRef = useRef<ChannelSocketHandle | null>(null);
  const listEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const policyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const appendUnique = (incoming: MessagePayload) => {
    setMessages((prev) =>
      prev.some((m) => m.id === incoming.id) ? prev : [...prev, incoming],
    );
  };

  async function connect() {
    if (!channelId) return;
    setLoading(true);
    try {
      const [scenePolicy, raw] = await Promise.all([
        repos.channels.scenePolicy(channelId),
        repos.channels.messages(channelId),
      ]);
      setPolicy(scenePolicy);
      setMessages(asList(raw));
      setError(null);
      schedulePolicyBoundary(scenePolicy);
      if (scenePolicy.live_connection_enabled) {
        socketRef.current?.close();
        socketRef.current = openChannelSocket({
          apiBaseURL: baseURL,
          channelId,
          token: client.authToken(),
          handlers: {
            onMessage: appendUnique,
            onSessionExpired: () => {
              session.markExpired();
            },
          },
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  /** next_change_at 到期 +250ms 自动刷新场景（对齐 iOS schedulePolicyBoundary）。 */
  function schedulePolicyBoundary(scenePolicy: ChannelScenePolicy) {
    if (policyTimerRef.current) clearTimeout(policyTimerRef.current);
    if (!scenePolicy.next_change_at) return;
    const delay = new Date(scenePolicy.next_change_at).getTime() - Date.now() + 250;
    if (Number.isNaN(delay) || delay <= 0) return;
    policyTimerRef.current = setTimeout(() => void refreshPolicy(), delay);
  }

  async function refreshPolicy() {
    socketRef.current?.close();
    socketRef.current = null;
    await connect();
  }

  useEffect(() => {
    void connect();
    void repos.profile
      .me()
      .then((me) => setCurrentUserId(me.user_id ?? null))
      .catch(() => setCurrentUserId(null));
    return () => {
      socketRef.current?.close();
      socketRef.current = null;
      if (policyTimerRef.current) clearTimeout(policyTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelId, repos]);

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  const sendingEnabled = policy?.sending_enabled !== false;

  async function sendDraft() {
    if (!channelId || sending) return;
    const value = draft.trim();
    if (!value) return;
    setSending(true);
    try {
      // 同时兼容中文品牌称呼与旧的 ASCII handle。
      if (value.includes("@噜噜") || value.toLowerCase().includes("@lulu")) {
        const result = await repos.channels.mentionAzou(channelId, value);
        appendUnique(result.message);
      } else {
        const sent = await repos.channels.send(
          channelId,
          { content: value, content_type: "text" },
          `text-message-${crypto.randomUUID()}`,
        );
        appendUnique(sent);
      }
      setDraft("");
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "发送失败");
    } finally {
      setSending(false);
    }
  }

  async function sendImage(file: File) {
    if (!channelId || sending) return;
    setSending(true);
    try {
      const dims = await imageDimensions(file).catch(() => null);
      const asset = await repos.media.uploadImage(file, {
        filename: file.name || "web-photo.jpg",
        contentType: file.type || "image/jpeg",
        width: dims?.width,
        height: dims?.height,
      });
      const sent = await repos.channels.send(
        channelId,
        { content_type: "image", image: { media_id: asset.media_id, caption: "图片" } },
        `image-message-${crypto.randomUUID()}`,
      );
      appendUnique(sent);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "图片上传失败");
    } finally {
      setSending(false);
    }
  }

  function sendLocation() {
    if (!channelId || sending) return;
    if (!("geolocation" in navigator)) {
      setPermissionNotice(true);
      return;
    }
    setSending(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        void (async () => {
          try {
            const sent = await repos.channels.send(
              channelId,
              {
                content_type: "location",
                location: {
                  latitude: pos.coords.latitude,
                  longitude: pos.coords.longitude,
                  label: "我发送的位置",
                  address: null,
                },
              },
              `location-${crypto.randomUUID()}`,
            );
            appendUnique(sent);
            setError(null);
          } catch (e) {
            setError(e instanceof Error ? e.message : "发送失败");
          } finally {
            setSending(false);
          }
        })();
      },
      () => {
        setSending(false);
        setPermissionNotice(true);
      },
      { maximumAge: 30_000, timeout: 10_000 },
    );
  }

  const nextChangeLabel = useMemo(
    () => shortTime(policy?.next_change_at),
    [policy?.next_change_at],
  );

  return (
    <Screen id="screen-E14-channel">
      <NavBar title={channelTitle} backTo="/messages" />
      <Scroll padBottom={false}>
        {error ? (
          <Card>
            <StateView
              kind="network"
              message={error}
              actionTitle="重试"
              onAction={() => void refreshPolicy()}
            />
          </Card>
        ) : null}

        {policy && !sendingEnabled ? (
          <div className="chat-muted-card" data-od-id="scene-sensitive-muted">
            <div className="t-t3">现场禁言</div>
            <div className="t-foot mt-1">
              {policy.reason ?? "此场景现场不提供连接"}
            </div>
            {nextChangeLabel ? (
              <div className="t-cap mt-1">结束后 {nextChangeLabel} 可继续复盘</div>
            ) : null}
            <Btn kind="ghost" sm onClick={() => void refreshPolicy()}>
              刷新场景状态
            </Btn>
          </div>
        ) : null}

        {loading ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}

        <div className="chat-list" style={{ paddingBottom: 110 }}>
          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              isMe={m.sender_type === "human" && m.sender_id === currentUserId}
            />
          ))}
          {!loading && messages.length === 0 ? (
            <div className="bubble-sys">还没有消息。打个招呼吧。</div>
          ) : null}
          <div ref={listEndRef} />
        </div>

        {permissionNotice ? (
          <Card data-od-id="permission-recovery-notice">
            <div className="t-t3">权限未开启</div>
            <div className="t-foot mt-1">
              本次操作已停止；可稍后重试，或到系统设置恢复权限。
            </div>
            <Btn kind="text" onClick={() => setPermissionNotice(false)}>
              知道了
            </Btn>
          </Card>
        ) : null}
      </Scroll>

      {sendingEnabled ? (
        <div className="chat-input">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            style={{ display: "none" }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void sendImage(file);
            }}
          />
          <button
            type="button"
            className="nav-back"
            aria-label="发送图片"
            disabled={sending}
            onClick={() => fileInputRef.current?.click()}
          >
            <Icon name="share" size={18} />
          </button>
          <button
            type="button"
            className="nav-back"
            aria-label="发送一次位置"
            disabled={sending}
            onClick={() => sendLocation()}
          >
            <Icon name="pin" size={18} />
          </button>
          <input
            className="om-input"
            placeholder="说点什么…"
            value={draft}
            data-od-id="channel-message-input"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void sendDraft();
            }}
          />
          <button
            type="button"
            className="nav-back"
            aria-label="发送消息"
            style={{ opacity: !draft.trim() || sending ? 0.45 : 1 }}
            disabled={!draft.trim() || sending}
            onClick={() => void sendDraft()}
          >
            <Icon name="arrow" size={18} />
          </button>
        </div>
      ) : null}
    </Screen>
  );
}

async function imageDimensions(
  file: File,
): Promise<{ width: number; height: number }> {
  const bitmap = await createImageBitmap(file);
  const dims = { width: bitmap.width, height: bitmap.height };
  bitmap.close();
  return dims;
}
