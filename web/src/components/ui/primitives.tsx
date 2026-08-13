import type { ReactNode, ButtonHTMLAttributes, CSSProperties } from "react";
import { Link } from "react-router-dom";
import { assetURL } from "../../core/assets";
import { LuluSprite, type LuluClip } from "../lulu/LuluSprite";

const ST = assetURL("/assets/stickers/");

export function Sticker({
  name,
  size = 24,
  className = "",
}: {
  name: string;
  size?: number | "st-20" | "st-24" | "st-32" | "st-44" | "st-56" | "st-72";
  className?: string;
}) {
  const cls =
    typeof size === "string"
      ? `sticker ${size} ${className}`
      : `sticker ${className}`;
  const style =
    typeof size === "number"
      ? ({ width: size, height: size } as CSSProperties)
      : undefined;
  return (
    <img
      className={cls}
      src={`${ST}${name}`}
      alt=""
      style={style}
      draggable={false}
    />
  );
}

/** 水豚噜噜（帧动画版，对齐 iOS LuluView）。placement 决定尺寸，clip 决定动作。 */
export function LuluMark({
  placement = "empty",
  clip,
  caption,
}: {
  placement?: "hero" | "header" | "empty" | "confirm" | "avatar";
  clip?: LuluClip;
  caption?: string;
}) {
  const resolvedClip: LuluClip =
    clip ?? (placement === "confirm" ? "home.thinking" : "home.idle");
  return (
    <div className="lulu-wrap">
      <div className={`lulu lulu-${placement}`}>
        <LuluSprite
          clip={resolvedClip}
          size="100%"
          round={placement === "avatar"}
          bare
        />
      </div>
      {caption ? <div className="lulu-cap">{caption}</div> : null}
    </div>
  );
}

export function NavBar({
  title,
  backTo,
  right,
}: {
  title: string;
  backTo?: string;
  right?: ReactNode;
}) {
  return (
    <div className="om-nav">
      {backTo ? (
        <Link className="nav-back" to={backTo} aria-label="返回">
          <Icon name="back" size={18} />
        </Link>
      ) : (
        <span style={{ width: 36 }} />
      )}
      <div className="nav-title">{title}</div>
      <div className="nav-right">{right}</div>
    </div>
  );
}

export function LargeTitle({ title, sub }: { title: string; sub?: string }) {
  return (
    <>
      <div className="om-large-title">{title}</div>
      {sub ? <div className="om-large-sub">{sub}</div> : null}
    </>
  );
}

/** 稀疏确认页公式：上标题 → 中间大噜噜 → 底部选项（对齐 iOS OMStage） */
/** 稀疏确认页：上标题、中噜噜（或自定义 hero）、下操作区。 */
export function Stage({
  title,
  subtitle,
  clip = "home.reply",
  hero,
  children,
}: {
  title?: string;
  subtitle?: string;
  clip?: LuluClip;
  hero?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        minHeight: 0,
        padding: "12px 20px 28px",
      }}
    >
      {title ? (
        <div className="t-t2 center" style={{ marginTop: 8 }}>
          {title}
        </div>
      ) : null}
      {subtitle ? (
        <div
          className="t-foot muted center mt-1"
          style={{ maxWidth: 280, margin: "6px auto 0" }}
        >
          {subtitle}
        </div>
      ) : null}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: 220,
          padding: "12px 0",
        }}
      >
        {hero ?? <LuluMark placement="hero" clip={clip} />}
      </div>
      {children}
    </div>
  );
}

export function Section({
  title,
  more,
}: {
  title: string;
  more?: { label: string; to: string };
}) {
  return (
    <div className="om-section">
      <span>{title}</span>
      {more ? (
        <Link className="more" to={more.to}>
          {more.label}
        </Link>
      ) : null}
    </div>
  );
}

export function Card({
  children,
  tight,
  className = "",
  onClick,
  id,
  "data-od-id": dataOdId,
}: {
  children: ReactNode;
  tight?: boolean;
  className?: string;
  onClick?: () => void;
  id?: string;
  "data-od-id"?: string;
}) {
  return (
    <div
      className={`om-card ${tight ? "tight" : ""} ${className}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      style={onClick ? { cursor: "pointer" } : undefined}
      id={id}
      data-od-id={dataOdId}
    >
      {children}
    </div>
  );
}

/** 分隔线 — OMDivider 的 web 对应物。 */
export function Divider() {
  return (
    <div
      aria-hidden
      style={{ borderTop: "1px solid var(--line)", margin: "12px 0" }}
    />
  );
}

export function Row({
  icon,
  title,
  sub,
  right,
  to,
  onClick,
}: {
  icon?: ReactNode;
  title: string;
  sub?: string;
  right?: ReactNode;
  to?: string;
  onClick?: () => void;
}) {
  const inner = (
    <>
      {icon ? <span className="row-icon">{icon}</span> : null}
      <span className="row-main">
        <span className="row-title">{title}</span>
        {sub ? <div className="row-sub">{sub}</div> : null}
      </span>
      {right ? <span className="row-right">{right}</span> : null}
      {to ? <span className="chevron">›</span> : null}
    </>
  );
  if (to) {
    return (
      <Link className="om-row" to={to}>
        {inner}
      </Link>
    );
  }
  return (
    <button type="button" className="om-row" onClick={onClick}>
      {inner}
    </button>
  );
}

export function Btn({
  children,
  kind = "primary",
  sm,
  to,
  onClick,
  disabled,
  disabledReason,
  type = "button",
  extra,
  id,
}: {
  children: ReactNode;
  kind?: "primary" | "ghost" | "dark" | "text";
  sm?: boolean;
  to?: string;
  onClick?: () => void;
  disabled?: boolean;
  /** 禁用原因（对齐 iOS OMButton.disabledReason）：设置后按钮禁用并以 title 呈现原因 */
  disabledReason?: string;
  type?: "button" | "submit";
  extra?: string;
  id?: string;
}) {
  const isDisabled = disabled || disabledReason != null;
  const cls = `om-btn ${kind}${sm ? " sm" : ""}${extra ? ` ${extra}` : ""}`;
  if (to) {
    return (
      <Link
        className={cls}
        to={to}
        aria-disabled={isDisabled}
        title={disabledReason}
        id={id}
      >
        {children}
      </Link>
    );
  }
  return (
    <button
      type={type}
      className={cls}
      onClick={onClick}
      disabled={isDisabled}
      title={disabledReason}
      id={id}
    >
      {children}
    </button>
  );
}

export function Chip({
  children,
  kind = "",
  sticker,
  onClick,
}: {
  children: ReactNode;
  kind?: string;
  sticker?: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className={`om-chip ${kind}`}
      onClick={onClick}
      style={{ cursor: onClick ? "pointer" : "default" }}
    >
      {sticker ? <Sticker name={sticker} size={14} /> : null}
      {children}
    </button>
  );
}

export function GapBadge({ n, label = "还缺" }: { n: number; label?: string }) {
  return (
    <span className="gap-badge">
      {label} <span className="n">{n}</span> 人
    </span>
  );
}

export function Progress({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="om-progress">
      <i style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Note({
  children,
  sticker = "chat-bubble.png",
}: {
  children: ReactNode;
  sticker?: string;
}) {
  return (
    <div className="om-note">
      <img src={`${ST}${sticker}`} alt="" />
      <span>{children}</span>
    </div>
  );
}

export function Switch({
  on,
  onChange,
  disabled,
}: {
  on?: boolean;
  onChange?: (next: boolean) => void;
  disabled?: boolean;
}) {
  if (!onChange) {
    return <span className={`om-switch ${on ? "on" : ""}`} />;
  }
  return (
    <button
      type="button"
      role="switch"
      aria-checked={!!on}
      disabled={disabled}
      onClick={() => onChange(!on)}
      style={{
        background: "none",
        border: "none",
        padding: 0,
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.45 : 1,
      }}
    >
      <span className={`om-switch ${on ? "on" : ""}`} />
    </button>
  );
}

/** Segmented control — web analogue of OMSeg. */
export function Seg<T extends string>({
  options,
  value,
  onChange,
  disabled,
}: {
  options: Array<{ value: T; label: string }>;
  value: T | null;
  onChange: (next: T) => void;
  disabled?: boolean;
}) {
  return (
    <div className="om-seg">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          className={value === opt.value ? "on" : ""}
          disabled={disabled}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

/** Stepper — web analogue of iOS Stepper（如「最低成局人数」2…20）。 */
export function Stepper({
  value,
  min,
  max,
  step = 1,
  onChange,
  disabled,
}: {
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (next: number) => void;
  disabled?: boolean;
}) {
  const btnStyle: CSSProperties = {
    width: 30,
    height: 30,
    borderRadius: 9,
    border: "1px solid var(--line)",
    background: "var(--card)",
    fontWeight: 800,
    fontSize: 16,
    lineHeight: 1,
    color: "var(--ink)",
    cursor: "pointer",
  };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <button
        type="button"
        style={{ ...btnStyle, opacity: disabled || value <= min ? 0.4 : 1 }}
        disabled={disabled || value <= min}
        onClick={() => onChange(Math.max(min, value - step))}
        aria-label="减少"
      >
        −
      </button>
      <span className="mono" style={{ minWidth: 22, textAlign: "center", fontWeight: 700 }}>
        {value}
      </span>
      <button
        type="button"
        style={{ ...btnStyle, opacity: disabled || value >= max ? 0.4 : 1 }}
        disabled={disabled || value >= max}
        onClick={() => onChange(Math.min(max, value + step))}
        aria-label="增加"
      >
        +
      </button>
    </span>
  );
}

export function StateView({
  kind,
  message,
  actionTitle,
  onAction,
}: {
  kind:
    | "loading"
    | "empty"
    | "network"
    | "offline"
    | "denied"
    | "expired"
    | "duplicate"
    | "stale";
  message?: string;
  actionTitle?: string;
  onAction?: () => void;
}) {
  const M: Record<string, { t: string; d: string }> = {
    loading: { t: "正在加载", d: "噜噜正在取数，稍等一下。" },
    empty: { t: "这里还空着", d: "暂时没有内容。有进展时，噜噜会来告诉你。" },
    network: {
      t: "网络开了小差",
      d: "请求没有发出去。检查网络后再试一次，已填的内容都在。",
    },
    offline: {
      t: "当前离线",
      d: "你现在看到的是上次同步的内容。恢复网络后会自动更新。",
    },
    denied: {
      t: "这个权限还没开",
      d: "没有它，这部分功能用不了。你可以随时在设置里改主意。",
    },
    expired: {
      t: "登录状态失效了",
      d: "出于安全考虑需要重新认证。用企业微信扫一下就好，进度不会丢。",
    },
    duplicate: {
      t: "已经收到啦",
      d: "这个操作正在处理，不用重复点。",
    },
    stale: {
      t: "内容可能不是最新",
      d: "这页数据更新于稍早前。下拉可以刷新。",
    },
  };
  // 对齐 iOS OMG5State.clip：loading/stale 在想，empty 待机，错误类关切，duplicate 回应
  const CLIP: Record<string, LuluClip> = {
    loading: "home.thinking",
    stale: "home.thinking",
    empty: "home.idle",
    network: "core.care",
    offline: "core.care",
    denied: "core.care",
    expired: "core.care",
    duplicate: "home.reply",
  };
  const m = M[kind];
  return (
    <div className="state-view" data-state={kind}>
      <LuluMark placement="empty" clip={CLIP[kind]} />
      <div className="sv-title">{m.t}</div>
      <div className="sv-desc">{message ?? m.d}</div>
      {actionTitle && onAction ? (
        <Btn kind="primary" onClick={onAction}>
          {actionTitle}
        </Btn>
      ) : null}
    </div>
  );
}

export function Footer({ children }: { children: ReactNode }) {
  return <div className="om-footer">{children}</div>;
}

export function Screen({
  id,
  children,
  className = "",
}: {
  /** Prefer iOS runtime accessibility identifier (e.g. screen-B1-today). */
  id: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`screen-body ${className}`}
      data-screen={id}
      data-od-id={id}
      data-accessibility-id={id}
      style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}
    >
      {children}
    </div>
  );
}

export function Scroll({
  children,
  padBottom = true,
}: {
  children: ReactNode;
  padBottom?: boolean;
}) {
  return (
    <div className="scroll" style={padBottom ? undefined : { paddingBottom: 24 }}>
      {children}
    </div>
  );
}

const ICONS: Record<string, string> = {
  sun: '<circle cx="12" cy="12" r="4.4"/><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5 5l1.7 1.7M17.3 17.3 19 19M19 5l-1.7 1.7M6.7 17.3 5 19"/>',
  trophy:
    '<path d="M7 4h10v5a5 5 0 0 1-10 0V4Z"/><path d="M7 6H4.5a2.5 2.5 0 0 0 2.6 4M17 6h2.5a2.5 2.5 0 0 1-2.6 4M12 14v3.2M8.5 20h7M10 17.2h4"/>',
  plus: '<path d="M12 5.5v13M5.5 12h13"/>',
  chat: '<path d="M21 12a8 8 0 0 1-8 8c-1.3 0-2.6-.3-3.7-.8L4 20.5l1.4-4.2A8 8 0 1 1 21 12Z"/>',
  person:
    '<circle cx="12" cy="8.2" r="3.6"/><path d="M4.8 20a7.4 7.4 0 0 1 14.4 0"/>',
  back: '<path d="M14.5 5.5 8 12l6.5 6.5"/>',
  bell: '<path d="M6 9.5a6 6 0 0 1 12 0c0 4 1.5 5.5 1.5 5.5h-15S6 13.5 6 9.5M10.3 19a1.9 1.9 0 0 0 3.4 0"/>',
  clock:
    '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5.2l3.4 2"/>',
  pin: '<path d="M12 21s-6.5-5.4-6.5-10.3a6.5 6.5 0 0 1 13 0C18.5 15.6 12 21 12 21Z"/><circle cx="12" cy="10.5" r="2.3"/>',
  shield:
    '<path d="M12 3 5 5.8v5.4c0 4.3 3 7.6 7 9.3 4-1.7 7-5 7-9.3V5.8L12 3Z"/><path d="m9.2 11.8 2 2 3.6-3.8"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.8 13.6 6a6.4 6.4 0 0 1 2.5 1.5l3.4-.4 1.5 2.6-2.5 2.3a6.6 6.6 0 0 1 0 3l2.5 2.3-1.5 2.6-3.4-.4a6.4 6.4 0 0 1-2.5 1.5L12 21.2 10.4 18a6.4 6.4 0 0 1-2.5-1.5l-3.4.4L3 14.3l2.5-2.3a6.6 6.6 0 0 1 0-3L3 6.7 4.5 4.1l3.4.4A6.4 6.4 0 0 1 10.4 3L12 2.8Z"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>',
  exit: '<path d="M14 4h5v16h-5M4 12h11M11 8l4 4-4 4"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  share:
    '<path d="M12 15V4M8 8l4-4 4 4M5 12v7a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19v-7"/>',
  warn: '<path d="M12 3.5 22 20H2L12 3.5Z"/><path d="M12 10v4.4M12 17.2v.3"/>',
  spark:
    '<path d="M12 3c.7 3.9 2.7 6 6.6 6.6-3.9.7-6 2.7-6.6 6.6-.7-3.9-2.7-6-6.6-6.6C9.3 9 11.3 6.9 12 3Z"/><path d="M18.5 14.5c.4 2 1.4 3.1 3.4 3.4-2 .4-3.1 1.4-3.4 3.4-.4-2-1.4-3.1-3.4-3.4 2-.4 3.1-1.4 3.4-3.4Z"/>',
  users:
    '<circle cx="9" cy="8.5" r="3.2"/><path d="M2.8 19.5a6.2 6.2 0 0 1 12.4 0"/><circle cx="16.8" cy="9.5" r="2.6"/><path d="M15.4 14.6a5.4 5.4 0 0 1 5.8 4.9"/>',
  eye: '<path d="M2.5 12S6 5.8 12 5.8 21.5 12 21.5 12 18 18.2 12 18.2 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="2.8"/>',
  quote:
    '<path d="M9.5 7.5c-2.6.6-4 2.4-4 5v4h4.4v-4.4H7.6c0-1.6.8-2.7 2.4-3.2l-.5-1.4ZM18 7.5c-2.6.6-4 2.4-4 5v4h4.4v-4.4h-2.3c0-1.6.8-2.7 2.4-3.2L18 7.5Z"/>',
};

export function Icon({
  name,
  size = 22,
  color = "currentColor",
}: {
  name: string;
  size?: number;
  color?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      dangerouslySetInnerHTML={{ __html: ICONS[name] || "" }}
    />
  );
}

export function SeatStrip({
  seats,
}: {
  seats: Array<{ role: string; state: "filled" | "gap"; sticker: string }>;
}) {
  return (
    <span className="seat-strip">
      {seats.map((s, i) => (
        <span key={i} className={`s ${s.state}`}>
          <img src={`${ST}${s.sticker}`} alt={s.role} />
        </span>
      ))}
    </span>
  );
}

export type BtnProps = ButtonHTMLAttributes<HTMLButtonElement>;
