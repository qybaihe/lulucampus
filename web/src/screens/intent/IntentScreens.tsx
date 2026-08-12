import { useMemo, useState, type ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import { APIClientError } from "../../core/api/client";
import type {
  IntentCard,
  IntentCompileResult,
  IntentPublishResult,
} from "../../core/api/repositories";
import {
  Btn,
  Card,
  Chip,
  Divider,
  Icon,
  LuluMark,
  NavBar,
  Note,
  Screen,
  Scroll,
  Section,
  Seg,
  StateView,
  Stepper,
  Sticker,
  Switch,
} from "../../components/ui/primitives";

/** 后端 intensity 枚举 → 用户可读文案（对齐 iOS intensityLabel）。 */
function intensityLabel(value: string): string {
  switch (value) {
    case "light":
    case "轻松参与":
      return "轻松参与";
    case "balanced":
    case "认真参与":
      return "认真参与";
    case "focused":
    case "高强度冲刺":
      return "高强度冲刺";
    default:
      return value;
  }
}

function normalizedIntensity(value: string): string {
  switch (value) {
    case "轻松参与":
      return "light";
    case "认真参与":
      return "balanced";
    case "高强度冲刺":
      return "focused";
    default:
      return value;
  }
}

function statusName(status?: string): string {
  switch (status) {
    case "pooling":
      return "匿名池";
    case "pending_confirmation":
      return "待确认";
    case "confirmed":
      return "已确认";
    case "completed":
      return "已完成";
    default:
      return status || "匿名池";
  }
}

/** 顿号/逗号等分隔的标签串 → 数组（对齐 iOS split）。 */
function splitTags(value: string): string[] {
  return value
    .split(/[、,，/;；\n ]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

/** 摘要卡标签：过滤 taste: 内部画像标签，最多露出 6 个。 */
function displayTags(value: string): string[] {
  const visible = splitTags(value).filter((tag) => !tag.startsWith("taste:"));
  if (visible.length > 6) {
    return [...visible.slice(0, 6), `+${visible.length - 6}`];
  }
  return visible;
}

function toLocalInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function windowLabel(startISO: string, endISO: string): string {
  const start = new Date(startISO);
  const end = new Date(endISO);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return "时间待定";
  }
  const pad = (n: number) => String(n).padStart(2, "0");
  const day = `${start.getMonth() + 1}月${start.getDate()}日`;
  const range = `${pad(start.getHours())}:${pad(start.getMinutes())}–${pad(end.getHours())}:${pad(end.getMinutes())}`;
  return `${day} ${range}`;
}

/** 与 iOS isAmbiguousPublishError 对齐：网络/解码/5xx/幂等中间态视为“结果不明”。 */
function isAmbiguousPublishError(error: unknown): boolean {
  if (!(error instanceof APIClientError)) return true;
  switch (error.kind) {
    case "transport":
    case "invalidResponse":
    case "decoding":
    case "offline":
      return true;
    case "server":
      return (
        (error.status ?? 0) >= 500 ||
        ["IDEMPOTENCY_IN_PROGRESS", "IDEMPOTENCY_RESULT_PENDING", "IDEMPOTENCY_RESULT_UNKNOWN"].includes(
          error.body?.code ?? "",
        )
      );
    default:
      return false;
  }
}

interface EditorState {
  goal: string;
  moodNote: string;
  capabilitiesText: string;
  rolesText: string;
  campus: string;
  intensity: string;
  socialMode: string;
  sameGenderOnly: boolean;
  minimumSize: number;
  targetSize: number;
  startAt: string; // datetime-local
  endAt: string;
}

function editorFromCard(card: IntentCard, prev?: EditorState): EditorState {
  const window = card.available_windows?.[0];
  const start = window?.start_at ? new Date(window.start_at) : new Date(Date.now() + 86_400_000);
  const end = window?.end_at ? new Date(window.end_at) : new Date(Date.now() + 93_600_000);
  return {
    goal: card.goal ?? "",
    moodNote: card.mood_note ?? prev?.moodNote ?? "",
    capabilitiesText: (card.capabilities ?? []).map((c) => c.key).join("、"),
    rolesText: (card.required_roles ?? []).join("、"),
    campus: card.campus ?? "",
    intensity: normalizedIntensity(card.intensity ?? "balanced"),
    socialMode: card.social_mode ?? "after_full",
    sameGenderOnly: card.same_gender_only ?? false,
    minimumSize: card.min_size ?? card.minimum_size ?? 2,
    targetSize: card.target_size ?? 3,
    startAt: toLocalInput(start),
    endAt: toLocalInput(end),
  };
}

type Phase =
  | { kind: "editing" }
  | { kind: "compiling" }
  | {
      kind: "clarifying";
      card: IntentCard;
      questions: NonNullable<IntentCompileResult["questions"]>;
      round: number;
      maxRounds: number;
    }
  | { kind: "preview"; card: IntentCard }
  | { kind: "publishing"; card: IntentCard }
  | { kind: "published"; result: IntentPublishResult }
  | { kind: "failed"; message: string };

/** D1–D4 · 差一个（一句话 → 澄清 → 意图卡 → 发布入池），对齐 iOS IntentComposerView。 */
export function IntentComposerScreen() {
  const { repos } = useApp();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const competitionId = params.get("competition");
  const [text, setText] = useState("");
  const [moodNote, setMoodNote] = useState("");
  const [clarifyAnswer, setClarifyAnswer] = useState("");
  const [clarifyStart, setClarifyStart] = useState(() => toLocalInput(new Date(Date.now() + 86_400_000)));
  const [clarifyEnd, setClarifyEnd] = useState(() => toLocalInput(new Date(Date.now() + 93_600_000)));
  const [phase, setPhase] = useState<Phase>({ kind: "editing" });
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [fineTuning, setFineTuning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [pendingPublishKey, setPendingPublishKey] = useState<string | null>(null);

  const presets = useMemo(
    () => [
      { label: "明晚研讨室赶 DDL", sticker: "books-stack.png" },
      { label: "数模缺一个写作的", sticker: "trophy.png" },
      { label: "周末羽毛球双打", sticker: "badminton.png" },
    ],
    [],
  );

  async function compile(round = 0, answers: Record<string, string> = {}) {
    const value = text.trim();
    if (!value) return;
    setPhase({ kind: "compiling" });
    setOperationError(null);
    try {
      const mood = moodNote.trim();
      const result = await repos.intent.compile({
        text: value,
        mood_note: mood || undefined,
        competition_id: competitionId,
        clarification_round: round,
        answers,
      });
      const maxRounds = result.max_rounds ?? 2;
      if (result.needs_clarification && round < maxRounds && result.card) {
        setClarifyAnswer("");
        setPhase({
          kind: "clarifying",
          card: result.card,
          questions: result.questions ?? [],
          round,
          maxRounds,
        });
      } else if (result.card) {
        setEditor(editorFromCard(result.card));
        setPhase({ kind: "preview", card: result.card });
      } else {
        setPhase({ kind: "failed", message: "编译结果缺少意图卡" });
      }
    } catch (e) {
      setPhase({ kind: "failed", message: e instanceof Error ? e.message : "编译失败" });
    }
  }

  function answerClarification(
    questions: NonNullable<IntentCompileResult["questions"]>,
    round: number,
  ) {
    const answers: Record<string, string> = {};
    for (const q of questions) {
      const key = String(q.key ?? q.id ?? "answer");
      if (key === "availability") {
        answers[key] = `${new Date(clarifyStart).toISOString()}|${new Date(clarifyEnd).toISOString()}`;
      } else {
        const value = clarifyAnswer.trim();
        if (value) answers[key] = value;
      }
    }
    if (Object.keys(answers).length !== questions.length) {
      setOperationError("请完成这一轮的所有澄清项");
      return;
    }
    void compile(Math.min(round + 1, 2), answers);
  }

  /** PATCH 保存微调（对齐 iOS save：保留能力 source，校验人数/时间）。 */
  async function save(card: IntentCard): Promise<IntentCard | null> {
    if (!editor || !card.id || saving) return null;
    if (editor.minimumSize > editor.targetSize) {
      setOperationError("最低人数不能超过目标人数");
      return null;
    }
    if (new Date(editor.endAt) <= new Date(editor.startAt)) {
      setOperationError("结束时间必须晚于开始时间");
      return null;
    }
    setSaving(true);
    try {
      const existing = new Map((card.capabilities ?? []).map((c) => [c.key, c.source]));
      const capabilities = splitTags(editor.capabilitiesText).map((key) => ({
        key,
        source: existing.get(key) ?? "self_reported",
      }));
      const mood = editor.moodNote.trim();
      const updated = await repos.intent.patch(card.id, {
        gathering_type: card.gathering_type,
        goal: editor.goal,
        mood_note: mood || null,
        capabilities,
        required_roles: splitTags(editor.rolesText),
        intensity: editor.intensity,
        available_windows: [
          {
            start_at: new Date(editor.startAt).toISOString(),
            end_at: new Date(editor.endAt).toISOString(),
            stability: 1,
          },
        ],
        campus: editor.campus.trim() || null,
        min_size: editor.minimumSize,
        target_size: editor.targetSize,
        social_mode: editor.socialMode,
        same_gender_only: editor.sameGenderOnly,
        expires_at: card.expires_at ?? undefined,
      });
      setEditor(editorFromCard(updated, editor));
      setPhase({ kind: "preview", card: updated });
      setOperationError(null);
      return updated;
    } catch (e) {
      setOperationError(e instanceof Error ? e.message : "保存失败");
      return null;
    } finally {
      setSaving(false);
    }
  }

  /** 发布（对齐 iOS publish：先保存，再发布；结果不明时查 publication 恢复）。 */
  async function publish(card: IntentCard) {
    const key = pendingPublishKey ?? `web-publish-${crypto.randomUUID()}`;
    setPendingPublishKey(key);
    const recovering = pendingPublishKey != null;
    if (recovering && card.id) {
      try {
        const recovered = await repos.intent.publication(card.id);
        setPhase({ kind: "published", result: recovered });
        setPendingPublishKey(null);
        setOperationError("发布结果已从服务端恢复。");
        return;
      } catch (e) {
        if (!(e instanceof APIClientError && e.status === 404)) {
          setOperationError(
            `正在向服务端核对上次发布结果，请保持网络后重试：${e instanceof Error ? e.message : e}`,
          );
          return;
        }
        // 404 = 上次操作确定无结果，继续走保存 + 发布
      }
    }
    const updated = await save(card);
    if (!updated?.id) return;
    setPhase({ kind: "publishing", card: updated });
    try {
      const result = await repos.intent.publish({ card_id: updated.id }, key);
      setPhase({ kind: "published", result });
      setOperationError(null);
      setPendingPublishKey(null);
    } catch (e) {
      if (isAmbiguousPublishError(e)) {
        try {
          const recovered = await repos.intent.publication(updated.id);
          setPhase({ kind: "published", result: recovered });
          setPendingPublishKey(null);
          setOperationError("发布结果已从服务端恢复。");
        } catch {
          setPhase({ kind: "preview", card: updated });
          setOperationError("发布响应未确认，已保留同一操作标识；重试时会先核对服务端结果。");
        }
        return;
      }
      setPhase({ kind: "preview", card: updated });
      setOperationError(e instanceof Error ? e.message : "发布失败");
      setPendingPublishKey(null);
    }
  }

  async function withdraw(card: IntentCard) {
    if (!card.id || saving) return;
    setSaving(true);
    try {
      await repos.intent.remove(card.id, crypto.randomUUID());
      setPhase({ kind: "editing" });
      setOperationError(null);
    } catch (e) {
      setOperationError(e instanceof Error ? e.message : "撤回失败");
    } finally {
      setSaving(false);
    }
  }

  const inputPanel = (
    <Card className="mt-4">
      <textarea
        className="om-input"
        style={{ border: "none", background: "transparent", minHeight: 108 }}
        placeholder="例如：周六晚上珠海校区，差一个会打双打的同学"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Divider />
      <div className="flex" style={{ alignItems: "center", gap: 8 }}>
        <span style={{ color: "var(--yolk-border)" }}>
          <Icon name="quote" size={14} />
        </span>
        <input
          className="om-input"
          style={{ border: "none", background: "transparent", flex: 1 }}
          placeholder="一句话心情（可选）"
          value={moodNote}
          maxLength={60}
          onChange={(e) => setMoodNote(e.target.value)}
        />
      </div>
    </Card>
  );

  function summaryCard(card: IntentCard, state: EditorState) {
    const capabilityChips = displayTags(state.capabilitiesText);
    const roleChips = displayTags(state.rolesText);
    return (
      <Card id="intent-summary-card">
        <div className="flex" style={{ gap: 6 }}>
          <Chip kind="gap">{card.gathering_type ?? "局"}</Chip>
          <Chip kind="soft">匿名意图卡</Chip>
        </div>
        <div className="t-t3 mt-3" style={{ fontWeight: 700 }}>
          {state.goal || card.goal}
        </div>
        {state.moodNote.trim() ? (
          <div className="t-foot mt-2" style={{ fontStyle: "italic" }}>
            “{state.moodNote.trim()}”
          </div>
        ) : null}
        <Divider />
        <div className="stack" style={{ gap: 9 }}>
          <FactRow icon="clock" text={windowLabel(state.startAt, state.endAt)} />
          <FactRow icon="pin" text={state.campus || "校区待定"} />
          <FactRow
            icon="users"
            text={
              state.minimumSize === state.targetSize
                ? `${state.targetSize} 人 · ${intensityLabel(state.intensity)}`
                : `${state.minimumSize}–${state.targetSize} 人 · ${intensityLabel(state.intensity)}`
            }
          />
          <FactRow
            icon="eye"
            text={state.socialMode === "after_full" ? "满员确认后互见身份" : "最低人数确认后互见身份"}
          />
          {state.sameGenderOnly ? <FactRow icon="shield" text="只匹配同性成员" /> : null}
        </div>
        {capabilityChips.length || roleChips.length ? (
          <>
            <Divider />
            {capabilityChips.length ? (
              <ChipsRow title="我能带来" items={capabilityChips} />
            ) : null}
            {roleChips.length ? (
              <div className={capabilityChips.length ? "mt-2" : undefined}>
                <ChipsRow title="还需要" items={roleChips} />
              </div>
            ) : null}
          </>
        ) : null}
      </Card>
    );
  }

  function fineTuneEditors(card: IntentCard, state: EditorState) {
    const set = (patch: Partial<EditorState>) => setEditor({ ...state, ...patch });
    return (
      <>
        <Card className="mt-2" id="intent-capabilities-editor">
          <div className="t-t3">内容</div>
          <textarea
            className="om-input mt-2"
            placeholder="目标"
            value={state.goal}
            onChange={(e) => set({ goal: e.target.value })}
          />
          <input
            className="om-input mt-2"
            placeholder="一句话心情（匿名可见，可留空）"
            value={state.moodNote}
            maxLength={60}
            onChange={(e) => set({ moodNote: e.target.value })}
          />
          <input
            className="om-input mt-2"
            placeholder="我的能力标签（顿号分隔）"
            value={state.capabilitiesText}
            onChange={(e) => set({ capabilitiesText: e.target.value })}
          />
          <input
            className="om-input mt-2"
            placeholder="所需角色（顿号分隔）"
            value={state.rolesText}
            onChange={(e) => set({ rolesText: e.target.value })}
          />
        </Card>
        <Card className="mt-2" id="intent-availability-editor">
          <div className="t-t3">时间与校区</div>
          <input
            className="om-input mt-2"
            placeholder="校区"
            value={state.campus}
            onChange={(e) => set({ campus: e.target.value })}
          />
          <label className="t-cap mt-2" style={{ display: "block" }}>
            开始
            <input
              type="datetime-local"
              className="om-input mt-1"
              value={state.startAt}
              onChange={(e) => set({ startAt: e.target.value })}
            />
          </label>
          <label className="t-cap mt-2" style={{ display: "block" }}>
            结束
            <input
              type="datetime-local"
              className="om-input mt-1"
              value={state.endAt}
              min={state.startAt}
              onChange={(e) => set({ endAt: e.target.value })}
            />
          </label>
        </Card>
        <Card className="mt-2" id="intent-roles-editor">
          <div className="t-t3">人数与投入</div>
          <div className="between mt-2">
            <span className="t-call">最低人数</span>
            <Stepper
              value={state.minimumSize}
              min={2}
              max={20}
              onChange={(v) => set({ minimumSize: v })}
            />
          </div>
          <div className="between mt-2">
            <span className="t-call">目标人数</span>
            <Stepper
              value={state.targetSize}
              min={2}
              max={20}
              onChange={(v) => set({ targetSize: v })}
            />
          </div>
          <div className="mt-2">
            <Seg
              options={["light", "balanced", "focused"].map((v) => ({
                value: v,
                label: intensityLabel(v),
              }))}
              value={state.intensity}
              onChange={(v) => set({ intensity: v })}
            />
          </div>
        </Card>
        <Card className="mt-2" id="intent-safety-editor">
          <div className="t-t3">身份安全</div>
          <div className="mt-2">
            <Seg
              options={[
                { value: "after_full", label: "满员确认后" },
                { value: "after_confirmed", label: "最低人数确认后" },
              ]}
              value={state.socialMode}
              onChange={(v) => set({ socialMode: v })}
            />
          </div>
          <div className="between mt-3">
            <span className="t-t3">本次只匹配同性成员</span>
            <Switch
              on={state.sameGenderOnly}
              onChange={(v) => set({ sameGenderOnly: v })}
            />
          </div>
        </Card>
        <Btn kind="ghost" sm onClick={() => void save(card)} disabled={saving}>
          {saving ? "保存中…" : "保存调整"}
        </Btn>
      </>
    );
  }

  function editorView(card: IntentCard, publishing: boolean) {
    if (!editor) return null;
    return (
      <div id="screen-D3-intent-editor">
        <Section title="噜噜整理好了，确认一下" />
        {summaryCard(card, editor)}
        <button
          type="button"
          className="nav-back mt-1"
          style={{ width: "100%", height: 40 }}
          onClick={() => setFineTuning((v) => !v)}
        >
          <span className="t-foot" style={{ fontWeight: 600 }}>
            {fineTuning ? "收起调整 ▲" : "调整细节 ▼"}
          </span>
        </button>
        {fineTuning ? fineTuneEditors(card, editor) : null}
        <div className="mt-3">
          <Btn
            kind="primary"
            onClick={() => void publish(card)}
            disabled={saving || publishing}
          >
            {publishing ? "发布中…" : "开始找人"}
          </Btn>
        </div>
        <div className="t-cap center mt-2">
          发布后进入匿名池；找齐并确认前，不会透露任何人的身份。
        </div>
        <Btn kind="text" sm onClick={() => void withdraw(card)} disabled={saving}>
          撤回这张卡
        </Btn>
      </div>
    );
  }

  let content: ReactNode = null;
  if (phase.kind === "editing") {
    content = (
      <>
        <div className="mt-3">
          <Btn kind="primary" onClick={() => void compile()} disabled={!text.trim()}>
            整理成意图卡
          </Btn>
        </div>
        {text.trim() ? (
          <div className="t-cap center mt-2">
            噜噜会整理成一张匿名意图卡，确认后才开始找人。
          </div>
        ) : null}
        <div
          className="flex wrap mt-5"
          style={{ justifyContent: "center", gap: 8, rowGap: 10 }}
        >
          {presets.map((p) => (
            <Chip key={p.label} kind="soft" sticker={p.sticker} onClick={() => setText(p.label)}>
              {p.label}
            </Chip>
          ))}
        </div>
        {competitionId ? <Note sticker="trophy.png">已绑定赛事 {competitionId}</Note> : null}
        {!competitionId ? (
          <div className="mt-3">
            <Btn kind="text" sm to="/gatherings/initiate" id="intent-direct-initiate">
              熟练了？直接发起具体局
            </Btn>
          </div>
        ) : null}
        {/* 对齐 iOS：噜噜站在输入区下方的留白处（home.idle） */}
        <div className="center" style={{ marginTop: 28, marginBottom: 8 }}>
          <LuluMark placement="empty" clip="home.idle" />
        </div>
      </>
    );
  } else if (phase.kind === "compiling") {
    content = (
      <Card className="mt-3">
        <div className="center">
          <LuluMark placement="confirm" clip="home.thinking" />
          <div className="t-t3 mt-3">噜噜正在理解…</div>
          <div className="t-foot mt-1">正在整理成一张匿名意图卡</div>
        </div>
      </Card>
    );
  } else if (phase.kind === "clarifying") {
    content = (
      <div id="screen-D2-clarification">
        <Card className="mt-3">
          <Chip kind="gap">
            澄清 {phase.round + 1} / {phase.maxRounds}
          </Chip>
          {phase.questions.map((q) => {
            const key = String(q.key ?? q.id ?? "answer");
            return (
              <div key={key}>
                <div className="t-t3 mt-3">{q.prompt ?? "再确认一件事"}</div>
                {key === "availability" ? (
                  <>
                    <label className="t-cap mt-2" style={{ display: "block" }}>
                      开始
                      <input
                        type="datetime-local"
                        className="om-input mt-1"
                        value={clarifyStart}
                        onChange={(e) => setClarifyStart(e.target.value)}
                      />
                    </label>
                    <label className="t-cap mt-2" style={{ display: "block" }}>
                      结束
                      <input
                        type="datetime-local"
                        className="om-input mt-1"
                        value={clarifyEnd}
                        min={clarifyStart}
                        onChange={(e) => setClarifyEnd(e.target.value)}
                      />
                    </label>
                  </>
                ) : (
                  <input
                    className="om-input mt-2"
                    placeholder="例如：前端、产品"
                    value={clarifyAnswer}
                    onChange={(e) => setClarifyAnswer(e.target.value)}
                  />
                )}
              </div>
            );
          })}
        </Card>
        <div className="mt-2">
          <Btn
            kind="primary"
            onClick={() => answerClarification(phase.questions, phase.round)}
            id="intent-clarification-continue"
          >
            继续
          </Btn>
        </div>
      </div>
    );
  } else if (phase.kind === "preview" || phase.kind === "publishing") {
    content = editorView(phase.card, phase.kind === "publishing");
  } else if (phase.kind === "published") {
    content = (
      <>
        <Card className="mt-3">
          <div className="flex" style={{ alignItems: "center", gap: 10 }}>
            <Sticker name="hourglass.png" size="st-44" />
            <span className="t-t3">已进入{statusName(phase.result.status)}</span>
          </div>
        </Card>
        <div className="mt-2">
          <Btn
            kind="primary"
            id="intent-view-gathering"
            onClick={() => {
              if (phase.result.gathering_id) {
                navigate(`/gathering/${phase.result.gathering_id}`);
              } else {
                navigate("/gatherings/mine");
              }
            }}
          >
            查看招募状态
          </Btn>
        </div>
      </>
    );
  } else if (phase.kind === "failed") {
    content = (
      <Card className="mt-3">
        <StateView
          kind="network"
          message={phase.message}
          actionTitle="重新编辑"
          onAction={() => setPhase({ kind: "editing" })}
        />
      </Card>
    );
  }

  return (
    <Screen id="screen-D1-intent">
      <NavBar
        title={competitionId ? "赛事组队" : "差一个，就说一句"}
        backTo={competitionId ? "/competitions" : undefined}
      />
      <Scroll>
        {phase.kind === "editing" || phase.kind === "clarifying" ? inputPanel : null}
        {content}
        {operationError ? (
          <Card className="mt-3">
            <StateView kind="network" message={operationError} />
          </Card>
        ) : null}
      </Scroll>
    </Screen>
  );
}

function FactRow({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="flex" style={{ alignItems: "baseline", gap: 9 }}>
      <span style={{ width: 18, color: "var(--yolk-border)" }}>
        <Icon name={icon} size={13} />
      </span>
      <span className="t-body">{text}</span>
    </div>
  );
}

function ChipsRow({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="stack" style={{ gap: 6 }}>
      <span className="t-cap">{title}</span>
      <div className="flex wrap" style={{ gap: 6 }}>
        {items.map((item) => (
          <Chip key={item} kind="soft">
            {item}
          </Chip>
        ))}
      </div>
    </div>
  );
}

/**
 * D3.1–D3.4 独立路由：iOS 中它们是编辑器内的分区（非独立页面），
 * web 保留路由节点，进入时引导回编辑器主流程。
 */
function EditorSectionRedirect({ id, title }: { id: string; title: string }) {
  return (
    <Screen id={id}>
      <NavBar title={title} backTo="/intent" />
      <Scroll>
        <Note>此分区已并入意图卡编辑器，请从「差一个」的意图卡中「调整细节」进入。</Note>
        <Btn kind="primary" to="/intent">
          回到意图卡
        </Btn>
      </Scroll>
    </Screen>
  );
}

export function IntentCapabilitiesScreen() {
  return <EditorSectionRedirect id="intent-capabilities-editor" title="能力编辑" />;
}

export function IntentAvailabilityScreen() {
  return <EditorSectionRedirect id="intent-availability-editor" title="空档选择" />;
}

export function IntentRolesScreen() {
  return <EditorSectionRedirect id="intent-roles-editor" title="角色编辑" />;
}

export function IntentSafetyScreen() {
  return <EditorSectionRedirect id="intent-safety-editor" title="安全偏好" />;
}
