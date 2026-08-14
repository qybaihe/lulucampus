import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import {
  asList,
  gatheringStatusName,
  type ChannelHeader,
  type ChannelScenePolicy,
  type Gathering,
  type MessagePayload,
  type RelationSummary,
} from "../../core/api/repositories";
import { openChannelSocket, type ChannelSocketHandle } from "../../core/api/ws";
import {
  attentionItems,
  pathFromAttentionLink,
} from "../../core/today/attention";
import {
  Btn,
  Card,
  Chip,
  Icon,
  LuluMark,
  LuluSeatStrip,
  NavBar,
  PageHeader,
  Row,
  Screen,
  Scroll,
  Section,
  StateView,
  Sticker,
} from "../../components/ui/primitives";
import { relativeTimeLabel } from "../profile/notificationInbox";

const ONGOING_STATUSES = new Set([
  "Pooling",
  "Tentative",
  "Confirmed",
  "Previewed",
  "Executed",
  "Active",
]);

function needsMyConfirmation(item: Gathering): boolean {
  return (
    String(item.status) === "Tentative" && item.my_confirmation !== "confirmed"
  );
}

function ongoingGatherings(items: Gathering[]): Gathering[] {
  const now = Date.now();
  const seen = new Set<string>();
  return items
    .filter((item) => {
      if (!ONGOING_STATUSES.has(String(item.status))) return false;
      const end = item.end_at ?? item.ends_at;
      if (end) {
        const t = new Date(end).getTime();
        if (!Number.isNaN(t) && t < now - 2 * 3600 * 1000) return false;
      }
      const start = item.start_at ?? item.starts_at;
      const slot = start
        ? String(Math.floor(new Date(start).getTime() / 1800000))
        : "-";
      const key = `${item.title ?? ""}|${item.status}|${slot}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .sort((a, b) => {
      const aNeed = needsMyConfirmation(a);
      const bNeed = needsMyConfirmation(b);
      if (aNeed !== bNeed) return aNeed ? -1 : 1;
      const at = new Date(a.start_at ?? a.starts_at ?? "").getTime();
      const bt = new Date(b.start_at ?? b.starts_at ?? "").getTime();
      return (Number.isNaN(at) ? Infinity : at) - (Number.isNaN(bt) ? Infinity : bt);
    });
}

function ongoingStatusLabel(item: Gathering): string {
  if (needsMyConfirmation(item)) return "待你确认";
  const target = item.target_size ?? 0;
  const filled = Math.min(
    item.member_count ?? item.confirmed_count ?? item.filled_count ?? 0,
    target || Infinity,
  );
  const status = String(item.status);
  if (status === "Pooling") return `还差 ${Math.max(0, target - filled)} 人`;
  if (status === "Tentative") return "等大家确认";
  if (status === "Confirmed" || status === "Previewed") return "已成局";
  if (status === "Executed" || status === "Active") return "进行中";
  return gatheringStatusName(item.status);
}

function shortStartLabel(iso?: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const now = new Date();
  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
  const tomorrow = new Date(now);
  tomorrow.setDate(now.getDate() + 1);
  const time = date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  if (sameDay(date, now)) return `今天 ${time}`;
  if (sameDay(date, tomorrow)) return `明天 ${time}`;
  return date.toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function partnerChannelSubline(item: RelationSummary): string {
  const preview = item.last_message?.content?.trim();
  if (preview) return preview;
  const parts: string[] = [];
  if ((item.times_together ?? 0) > 0) parts.push(`一起 ${item.times_together} 次`);
  const recent = item.experiences?.[0]?.gathering_type;
  if (recent) parts.push(`上次${recent}`);
  if (parts.length === 0) parts.push("打个招呼吧");
  return parts.join(" · ");
}

/** MSG · 消息（Tab 根）：待办 + 进行中的局 + 搭子频道。 */
export function MessagesScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const location = useLocation();
  const [items, setItems] = useState<RelationSummary[]>([]);
  const [ongoing, setOngoing] = useState<Gathering[]>([]);
  const [attention, setAttention] = useState<
    ReturnType<typeof attentionItems>
  >([]);
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      const [rawRelations, mine, summary] = await Promise.all([
        repos.relations.list(),
        repos.gatherings.mine().catch(() => [] as Gathering[]),
        repos.today.summary().catch(() => null),
      ]);
      setItems(asList(rawRelations));
      setOngoing(ongoingGatherings(asList(mine)));
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
  }, [repos, location.key]);

  const empty =
    phase === "loaded" &&
    items.length === 0 &&
    ongoing.length === 0 &&
    attention.length === 0;

  return (
    <Screen id="screen-MSG-messages">
      <Scroll>
        <PageHeader title="消息与搭子" clip="home.listening" />
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
        {empty ? (
          <>
            <Card>
              <div className="center">
                <LuluMark placement="confirm" clip="home.listening" />
                <div className="t-t3 mt-3">这里还很安静</div>
                <div className="t-cap mt-1">
                  成局后的对话会出现在下面。正在进行的局还是上面那些卡片。
                </div>
              </div>
            </Card>
            <div className="mt-2">
              <Btn kind="primary" to="/intent">
                去差一个，说一句
              </Btn>
            </div>
          </>
        ) : null}
        {phase === "loaded" && attention.length > 0 ? (
          <>
            <Section title="需要你处理" />
            <Card tight data-od-id="messages-attention">
              {attention.map((item) => (
                <Row
                  key={item.id}
                  icon={<Sticker name="alarm-clock.png" size="st-24" />}
                  title={item.title}
                  right={
                    item.badge ? <Chip kind="gap">{item.badge}</Chip> : undefined
                  }
                  onClick={() => {
                    const path = pathFromAttentionLink(item.deepLink);
                    if (path) nav(path);
                  }}
                />
              ))}
            </Card>
          </>
        ) : null}
        {phase === "loaded" && ongoing.length > 0 ? (
          <>
            <Section title="正在进行" />
            <div className="ongoing-strip" data-od-id="messages-ongoing-strip">
              {ongoing.map((item) => {
                const needsMe = needsMyConfirmation(item);
                const target = item.target_size ?? 0;
                const filled = Math.min(
                  item.member_count ??
                    item.confirmed_count ??
                    item.filled_count ??
                    0,
                  target || Infinity,
                );
                const start = shortStartLabel(item.start_at ?? item.starts_at);
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`ongoing-card ${needsMe ? "needs-me" : ""}`}
                    onClick={() => nav(`/gathering/${item.id}`)}
                  >
                    <Chip kind={needsMe ? "gap" : "soft"}>
                      {ongoingStatusLabel(item)}
                    </Chip>
                    <div className="ongoing-card-title">{item.title ?? "未命名局"}</div>
                    {String(item.status) === "Pooling" && target > 0 ? (
                      <LuluSeatStrip filled={filled} total={Math.min(target, 8)} />
                    ) : start ? (
                      <div className="t-cap mt-1">{start}</div>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </>
        ) : null}
        {phase === "loaded" && items.length > 0 ? (
          <>
            <Section title="对话" />
            <Card tight data-od-id="messages-chat-list">
              {items.map((item) => {
                const title =
                  item.peer_display_name ??
                  item.participants
                    .map((p) => p.display_name ?? "同学")
                    .join(" · ");
                const latest =
                  item.last_message?.sent_at ?? item.latest_experience_at ?? null;
                return (
                  <Row
                    key={item.id}
                    icon={<Sticker name="chat-bubble.png" size="st-44" />}
                    title={title}
                    sub={partnerChannelSubline(item)}
                    right={
                      <span className="flex" style={{ flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                        {item.is_fixed_partner && item.partner_title ? (
                          <Chip kind="gap">{item.partner_title}</Chip>
                        ) : null}
                        {latest ? (
                          <span className="t-cap">{relativeTimeLabel(latest)}</span>
                        ) : null}
                      </span>
                    }
                    onClick={() => {
                      if (item.channel_id) {
                        nav(`/channel/${item.channel_id}`, {
                          state: { title: title || "对话" },
                        });
                      } else nav("/relations");
                    }}
                  />
                );
              })}
            </Card>
          </>
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
  const optimisticTitle =
    (location.state as { title?: string } | null)?.title ?? "对话";
  const { repos, client, session, baseURL } = useApp();
  const [header, setHeader] = useState<ChannelHeader | null>(null);
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
  const pullGen = useRef(0);

  const appendUnique = (incoming: MessagePayload) => {
    setMessages((prev) =>
      prev.some((m) => m.id === incoming.id) ? prev : [...prev, incoming],
    );
  };

  async function connect() {
    if (!channelId) return;
    const gen = ++pullGen.current;
    setLoading(true);
    try {
      const [scenePolicy, raw, channelHeader] = await Promise.all([
        repos.channels.scenePolicy(channelId),
        repos.channels.messages(channelId),
        repos.channels.header(channelId).catch(() => null),
      ]);
      if (gen !== pullGen.current) return;
      setPolicy(scenePolicy);
      setMessages(asList(raw));
      setHeader(channelHeader);
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
      if (gen !== pullGen.current) return;
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      if (gen === pullGen.current) setLoading(false);
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
      pullGen.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelId, repos]);

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  const sendingEnabled = policy?.sending_enabled !== false;

  async function pullCastReplies() {
    if (!channelId) return;
    const gen = ++pullGen.current;
    for (const delay of [5000, 7000, 10000]) {
      await new Promise((resolve) => setTimeout(resolve, delay));
      if (gen !== pullGen.current) return;
      try {
        const latest = asList(await repos.channels.messages(channelId));
        for (const item of latest) appendUnique(item);
      } catch {
        /* keep current list */
      }
    }
  }

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
      void pullCastReplies();
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

  const channelTitle = header?.title ?? optimisticTitle;
  const nextChangeLabel = useMemo(
    () => shortTime(policy?.next_change_at),
    [policy?.next_change_at],
  );

  const sharedTarget = header?.relation_id
    ? `/relation/${header.relation_id}`
    : header?.gathering_id
      ? `/gathering/${header.gathering_id}`
      : null;

  return (
    <Screen id="screen-E14-channel">
      <NavBar title={channelTitle} backTo="/messages" />
      {header?.subtitle ? (
        sharedTarget ? (
          <Link
            className="chat-shared-strip"
            to={sharedTarget}
            data-od-id="channel-shared-history"
          >
            <span>{header.subtitle}</span>
            <span className="chat-shared-link">共同经历 ›</span>
          </Link>
        ) : (
          <div className="chat-shared-strip">{header.subtitle}</div>
        )
      ) : null}
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
            placeholder="消息（无已读/在线/输入中）"
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
