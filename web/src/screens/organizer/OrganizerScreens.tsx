import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import {
  asList,
  gatheringStatusName,
  type OrganizerDashboard,
  type OrganizerGatheringSummary,
  type OrganizerQuotaBatch,
  type OrganizerTemplate,
} from "../../core/api/repositories";
import {
  Btn,
  Card,
  Chip,
  Divider,
  NavBar,
  Note,
  Screen,
  Scroll,
  Section,
  StateView,
  Stepper,
  Sticker,
} from "../../components/ui/primitives";

function identityVisibilityLabel(raw?: string): string {
  switch (raw) {
    case "after_all_confirmed":
      return "全员确认后才展示身份";
    case "after_full":
      return "满员后展示身份";
    case "never":
      return "全程不展示身份";
    default:
      return "身份按确认进度展示";
  }
}

function formatStart(iso?: string | null): string {
  if (!iso) return "时间待确认";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "时间待确认";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getMonth() + 1}月${date.getDate()}日 ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toLocalInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** 逗号分隔角色 → 去重排序数组（对齐 iOS tokens）。 */
function roleTokens(text: string): string[] {
  return Array.from(
    new Set(
      text
        .split(/[,，]/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  )
    .sort()
    .slice(0, 20)
    .map((item) => item.slice(0, 64));
}

interface TemplateDraft {
  title: string;
  goal: string;
  gatheringType: string;
  campus: string;
  location: string;
  durationMinutes: number;
  minSize: number;
  targetSize: number;
}

function emptyTemplateDraft(): TemplateDraft {
  return {
    title: "",
    goal: "",
    gatheringType: "校园活动",
    campus: "东校园",
    location: "",
    durationMinutes: 120,
    minSize: 3,
    targetSize: 20,
  };
}

function draftFromTemplate(item: OrganizerTemplate): TemplateDraft {
  return {
    title: item.title ?? "",
    goal: item.goal ?? "",
    gatheringType: item.gathering_type ?? "校园活动",
    campus: item.campus ?? "",
    location: item.location ?? "",
    durationMinutes: item.duration_minutes ?? 120,
    minSize: item.min_size ?? 3,
    targetSize: item.target_size ?? 20,
  };
}

/** 模板编辑器（iOS TemplateEditor sheet 的 web 对应物，内嵌卡片呈现）。 */
function TemplateEditorCard({
  templateId,
  initial,
  saving,
  onSave,
  onCancel,
}: {
  templateId: string | null;
  initial: TemplateDraft;
  saving: boolean;
  onSave: (id: string | null, draft: TemplateDraft) => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState<TemplateDraft>(initial);
  const set = (patch: Partial<TemplateDraft>) => setDraft({ ...draft, ...patch });
  const invalid =
    draft.title.trim().length < 2 ||
    draft.goal.trim().length < 2 ||
    !draft.location.trim() ||
    draft.minSize > draft.targetSize;
  return (
    <Card className="mt-2">
      <div className="t-t3">{templateId ? "编辑模板" : "新建模板"}</div>
      <input
        className="om-input mt-2"
        placeholder="模板名称"
        value={draft.title}
        onChange={(e) => set({ title: e.target.value })}
      />
      <textarea
        className="om-input mt-2"
        placeholder="共同目标"
        value={draft.goal}
        onChange={(e) => set({ goal: e.target.value })}
      />
      <div className="flex mt-2" style={{ gap: 8 }}>
        <input
          className="om-input"
          placeholder="类型"
          value={draft.gatheringType}
          onChange={(e) => set({ gatheringType: e.target.value })}
        />
        <input
          className="om-input"
          placeholder="校区"
          value={draft.campus}
          onChange={(e) => set({ campus: e.target.value })}
        />
      </div>
      <input
        className="om-input mt-2"
        placeholder="地点"
        value={draft.location}
        onChange={(e) => set({ location: e.target.value })}
      />
      <div className="between mt-3">
        <span className="t-call">时长 · 分钟</span>
        <Stepper
          value={draft.durationMinutes}
          min={30}
          max={1440}
          step={30}
          onChange={(v) => set({ durationMinutes: v })}
        />
      </div>
      <div className="between mt-2">
        <span className="t-call">最低人数</span>
        <Stepper value={draft.minSize} min={2} max={500} onChange={(v) => set({ minSize: v })} />
      </div>
      <div className="between mt-2">
        <span className="t-call">目标人数</span>
        <Stepper
          value={draft.targetSize}
          min={2}
          max={500}
          onChange={(v) => set({ targetSize: v })}
        />
      </div>
      <div className="flex mt-3" style={{ gap: 8 }}>
        <Btn kind="primary" sm disabled={saving || invalid} onClick={() => onSave(templateId, draft)}>
          {saving ? "保存中…" : "保存"}
        </Btn>
        <Btn kind="text" sm onClick={onCancel}>
          取消
        </Btn>
      </div>
    </Card>
  );
}

/** 模板区（O1/O4 共用）：列表 + 新建/编辑/复制/停用/实例化。 */
function TemplatesSection({
  templates,
  working,
  onReload,
  onMessage,
}: {
  templates: OrganizerTemplate[];
  working: boolean;
  onReload: () => Promise<void>;
  onMessage: (text: string) => void;
}) {
  const { repos } = useApp();
  const [editor, setEditor] = useState<{ id: string | null; draft: TemplateDraft } | null>(null);
  const [saving, setSaving] = useState(false);

  async function save(id: string | null, draft: TemplateDraft) {
    if (saving) return;
    setSaving(true);
    try {
      const body = {
        title: draft.title.trim(),
        goal: draft.goal.trim(),
        gathering_type: draft.gatheringType.trim() || "校园活动",
        campus: draft.campus.trim() || null,
        location: draft.location.trim(),
        duration_minutes: draft.durationMinutes,
        min_size: draft.minSize,
        target_size: draft.targetSize,
      };
      if (id) {
        await repos.organizer.patchTemplate(id, body, crypto.randomUUID());
        onMessage("模板已更新");
      } else {
        await repos.organizer.createTemplate(body, crypto.randomUUID());
        onMessage("模板已创建");
      }
      setEditor(null);
      await onReload();
    } catch (e) {
      onMessage(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function copy(item: OrganizerTemplate) {
    try {
      await repos.organizer.copyTemplate(
        item.id,
        `${item.title ?? "模板"} · 副本`,
        crypto.randomUUID(),
      );
      onMessage("模板副本已创建");
      await onReload();
    } catch (e) {
      onMessage(e instanceof Error ? e.message : "复制失败");
    }
  }

  async function deactivate(item: OrganizerTemplate) {
    try {
      await repos.organizer.deactivateTemplate(item.id, crypto.randomUUID());
      onMessage("模板已停用");
      await onReload();
    } catch (e) {
      onMessage(e instanceof Error ? e.message : "停用失败");
    }
  }

  /** 明天实例化（对齐 iOS：start = now + 86400s）。 */
  async function instantiate(item: OrganizerTemplate) {
    try {
      await repos.organizer.instantiateTemplate(
        item.id,
        { start_at: new Date(Date.now() + 86_400_000).toISOString() },
        crypto.randomUUID(),
      );
      onMessage("已从模板生成官方局");
      await onReload();
    } catch (e) {
      onMessage(e instanceof Error ? e.message : "实例化失败");
    }
  }

  return (
    <div data-od-id="screen-O4-templates">
      <Section title="官方局模板" />
      <Btn
        kind="ghost"
        disabled={working || saving}
        onClick={() => setEditor({ id: null, draft: emptyTemplateDraft() })}
      >
        新建官方局模板
      </Btn>
      {editor && editor.id === null ? (
        <TemplateEditorCard
          key="new"
          templateId={null}
          initial={editor.draft}
          saving={saving}
          onSave={(id, draft) => void save(id, draft)}
          onCancel={() => setEditor(null)}
        />
      ) : null}
      {templates.length === 0 ? (
        <Card className="mt-2">
          <StateView kind="empty" message="暂时没有内容，有进展时会告诉你。" />
        </Card>
      ) : null}
      {templates.map((item) =>
        editor && editor.id === item.id ? (
          <TemplateEditorCard
            key={item.id}
            templateId={item.id}
            initial={editor.draft}
            saving={saving}
            onSave={(id, draft) => void save(id, draft)}
            onCancel={() => setEditor(null)}
          />
        ) : (
          <Card key={item.id} className="mt-2">
            <div className="between">
              <span className="t-t3">{item.title ?? "模板"}</span>
              <Chip kind={item.active === false ? "" : "solid"}>
                {item.active === false ? "停用" : "启用"}
              </Chip>
            </div>
            <div className="t-foot mt-1">
              {[item.gathering_type, item.location, item.duration_minutes ? `${item.duration_minutes} 分钟` : null]
                .filter(Boolean)
                .join(" · ")}
            </div>
            <div className="flex mt-3" style={{ gap: 8 }}>
              <Btn
                kind="ghost"
                sm
                onClick={() => setEditor({ id: item.id, draft: draftFromTemplate(item) })}
              >
                编辑
              </Btn>
              <Btn kind="ghost" sm disabled={working} onClick={() => void copy(item)}>
                复制
              </Btn>
              {item.active !== false ? (
                <Btn kind="text" sm disabled={working} onClick={() => void deactivate(item)}>
                  停用
                </Btn>
              ) : null}
            </div>
            <div className="mt-2">
              <Btn kind="primary" sm disabled={working} onClick={() => void instantiate(item)}>
                明天实例化
              </Btn>
            </div>
          </Card>
        ),
      )}
    </div>
  );
}

/** O1 · 校园主理人控制台（T4），对齐 iOS OrganizerView。 */
export function OrganizerScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [gatherings, setGatherings] = useState<OrganizerGatheringSummary[]>([]);
  const [templates, setTemplates] = useState<OrganizerTemplate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [gs, ts] = await Promise.all([
        repos.organizer.list(),
        repos.organizer.templates(),
      ]);
      setGatherings(asList(gs));
      setTemplates(asList(ts));
      setPhase("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
  }, [repos]);

  useEffect(() => {
    setPhase("loading");
    void load();
  }, [load]);

  return (
    <Screen id="screen-O1-organizer">
      <NavBar title="校园主理人" backTo="/me" />
      <Scroll>
        {phase === "loading" ? (
          <Card>
            <StateView kind="loading" message="噜噜正在取数，稍等一下。" />
          </Card>
        ) : null}
        {phase === "failed" ? (
          <>
            <Card>
              <StateView
                kind={
                  error && /T\d|信任|权限|主理人|FORBIDDEN/i.test(error)
                    ? "denied"
                    : "network"
                }
                message={error ?? undefined}
                actionTitle="重试"
                onAction={() => {
                  setPhase("loading");
                  void load();
                }}
              />
            </Card>
            <Card className="mt-2">
              <div className="t-t3">解锁条件</div>
              <div className="t-foot mt-2">
                达到 T4 且完成主理人认证后开放。当前不会伪造成功状态。
              </div>
            </Card>
          </>
        ) : null}
        {phase === "loaded" ? (
          <>
            <Card>
              <div className="between">
                <span className="t-t2">官方局 · {gatherings.length}</span>
                <Sticker name="clipboard-whistle.png" size="st-56" />
              </div>
            </Card>
            <div className="mt-2">
              <Btn kind="primary" to="/organizer/create">
                直接创建官方局
              </Btn>
            </div>
            {gatherings.length === 0 ? (
              <Card className="mt-2">
                <StateView kind="empty" message="暂时没有内容，有进展时会告诉你。" />
              </Card>
            ) : null}
            {gatherings.map((item) => (
              <Card key={item.id} className="mt-2">
                <div className="between">
                  <Chip kind="solid">{gatheringStatusName(item.status)}</Chip>
                  <span className="t-foot">目标 {item.target_size ?? "—"} 人</span>
                </div>
                <div className="t-t3 mt-2">{item.title ?? "官方局"}</div>
                <div className="t-call mt-1">{formatStart(item.start_at)}</div>
                <div className="flex mt-3" style={{ gap: 8 }}>
                  <Btn
                    kind="ghost"
                    sm
                    onClick={() => nav(`/organizer/gatherings/${item.id}/dashboard`)}
                  >
                    报名与到场看板
                  </Btn>
                  <Btn kind="ghost" sm onClick={() => nav(`/gathering/${item.id}`)}>
                    打开局详情
                  </Btn>
                </div>
              </Card>
            ))}
            <TemplatesSection
              templates={templates}
              working={false}
              onReload={load}
              onMessage={setMessage}
            />
          </>
        ) : null}
        {message ? (
          <Card className="mt-2">
            <div className="t-foot">{message}</div>
          </Card>
        ) : null}
      </Scroll>
    </Screen>
  );
}

interface QuotaBatchDraft {
  label: string;
  slots: number;
}

/** O2 · 创建官方局，对齐 iOS OfficialGatheringEditor。 */
export function OrganizerCreateScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  const [gatheringType, setGatheringType] = useState("校园活动");
  const [startAt, setStartAt] = useState(() => toLocalInput(new Date(Date.now() + 86_400_000)));
  const [endAt, setEndAt] = useState(() => toLocalInput(new Date(Date.now() + 86_400_000 + 7_200_000)));
  const [location, setLocation] = useState("");
  const [campus, setCampus] = useState("东校园");
  const [minSize, setMinSize] = useState(3);
  const [targetSize, setTargetSize] = useState(20);
  const [rolesText, setRolesText] = useState("");
  const [batches, setBatches] = useState<QuotaBatchDraft[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** 与 iOS invalidReason 一致的前置校验。 */
  function invalidReason(): string | null {
    if (title.trim().length < 2) return "名称至少 2 个字符";
    if (goal.trim().length < 2) return "共同目标至少 2 个字符";
    if (!location.trim()) return "请填写地点";
    if (new Date(endAt) <= new Date(startAt)) return "结束时间必须晚于开始时间";
    if (new Date(startAt) <= new Date()) return "开始时间必须晚于当前时间";
    if (minSize > targetSize) return "最低人数不能超过目标人数";
    if (batches.reduce((sum, b) => sum + b.slots, 0) > targetSize) {
      return "分批名额合计不能超过目标人数";
    }
    if (batches.some((b) => !b.label.trim())) return "批次名称不能为空";
    return null;
  }

  async function create() {
    if (busy || invalidReason()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await repos.organizer.create(
        {
          title: title.trim(),
          goal: goal.trim(),
          gathering_type: gatheringType.trim() || "校园活动",
          start_at: new Date(startAt).toISOString(),
          end_at: new Date(endAt).toISOString(),
          location: location.trim(),
          campus: campus.trim() || null,
          min_size: minSize,
          target_size: targetSize,
          required_roles: roleTokens(rolesText),
          quota_batches: batches.map((b) => ({ label: b.label.trim(), slots: b.slots })),
        },
        crypto.randomUUID(),
      );
      nav(`/organizer/gatherings/${created.id}/dashboard`, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setBusy(false);
    }
  }

  const reason = invalidReason();

  return (
    <Screen id="screen-O2-create-official">
      <NavBar title="创建官方局" backTo="/organizer" />
      <Scroll>
        <Section title="共同目标" />
        <Card>
          <input
            className="om-input"
            placeholder="官方局名称"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            data-od-id="organizer-create-title"
          />
          <textarea
            className="om-input mt-2"
            placeholder="要共同完成什么"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
          />
          <input
            className="om-input mt-2"
            placeholder="类型"
            value={gatheringType}
            onChange={(e) => setGatheringType(e.target.value)}
          />
        </Card>
        <Section title="时间与地点" />
        <Card>
          <label className="t-cap" style={{ display: "block" }}>
            开始
            <input
              type="datetime-local"
              className="om-input mt-1"
              value={startAt}
              onChange={(e) => setStartAt(e.target.value)}
            />
          </label>
          <label className="t-cap mt-2" style={{ display: "block" }}>
            结束
            <input
              type="datetime-local"
              className="om-input mt-1"
              value={endAt}
              min={startAt}
              onChange={(e) => setEndAt(e.target.value)}
            />
          </label>
          <div className="flex mt-3" style={{ gap: 8 }}>
            <input
              className="om-input"
              placeholder="地点"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
            <input
              className="om-input"
              placeholder="校区"
              value={campus}
              onChange={(e) => setCampus(e.target.value)}
            />
          </div>
        </Card>
        <Section title="规模" />
        <Card>
          <div className="between">
            <span className="t-call">最低人数</span>
            <Stepper value={minSize} min={2} max={500} onChange={setMinSize} />
          </div>
          <div className="between mt-2">
            <span className="t-call">目标人数</span>
            <Stepper value={targetSize} min={2} max={500} onChange={setTargetSize} />
          </div>
          <Divider />
          <input
            className="om-input"
            placeholder="所需角色（逗号分隔）"
            value={rolesText}
            onChange={(e) => setRolesText(e.target.value)}
          />
        </Card>
        <Section title="分批名额" />
        <Card>
          {batches.map((batch, index) => (
            <div key={index} className={index > 0 ? "mt-3" : undefined}>
              <input
                className="om-input"
                placeholder="批次名称"
                value={batch.label}
                onChange={(e) =>
                  setBatches(batches.map((b, i) => (i === index ? { ...b, label: e.target.value } : b)))
                }
              />
              <div className="between mt-2">
                <span className="t-call">名额</span>
                <span className="flex" style={{ alignItems: "center", gap: 8 }}>
                  <Stepper
                    value={batch.slots}
                    min={1}
                    max={500}
                    onChange={(v) =>
                      setBatches(batches.map((b, i) => (i === index ? { ...b, slots: v } : b)))
                    }
                  />
                  <Btn
                    kind="text"
                    sm
                    onClick={() => setBatches(batches.filter((_, i) => i !== index))}
                  >
                    删除
                  </Btn>
                </span>
              </div>
            </div>
          ))}
          <div className="mt-2">
            <Btn
              kind="ghost"
              sm
              disabled={batches.length >= 20}
              onClick={() => setBatches([...batches, { label: "公开名额", slots: 1 }])}
            >
              添加名额批次
            </Btn>
          </div>
        </Card>
        {reason ? <Note sticker="hourglass.png">{reason}</Note> : null}
        {error ? (
          <Card className="mt-2">
            <StateView kind="network" message={error} />
          </Card>
        ) : null}
        <div className="mt-3">
          <Btn kind="primary" disabled={busy || reason != null} onClick={() => void create()}>
            {busy ? "创建中…" : "创建"}
          </Btn>
        </div>
      </Scroll>
    </Screen>
  );
}

/** O3 · 报名与到场看板，对齐 iOS OrganizerDashboardView。 */
export function OrganizerDashboardScreen() {
  const { gatheringId } = useParams();
  const { repos } = useApp();
  const [data, setData] = useState<OrganizerDashboard | null>(null);
  const [title, setTitle] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!gatheringId) return;
    try {
      setData(await repos.organizer.dashboard(gatheringId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }, [gatheringId, repos]);

  useEffect(() => {
    void load();
    if (!gatheringId) return;
    // 看板标题来自主理人局列表（dashboard view 本身不含 title）
    void repos.organizer
      .list()
      .then((raw) => {
        const found = asList(raw).find((g) => g.id === gatheringId);
        if (found?.title) setTitle(found.title);
      })
      .catch(() => undefined);
  }, [gatheringId, repos, load]);

  async function mutate(success: string, operation: () => Promise<unknown>) {
    if (working) return;
    setWorking(true);
    setMessage(null);
    try {
      await operation();
      await load();
      setMessage(success);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "操作失败");
    } finally {
      setWorking(false);
    }
  }

  const attendanceOpen = ["Executed", "Active", "Completed"].includes(data?.status ?? "");

  return (
    <Screen id="screen-O3-organizer-dashboard">
      <NavBar title={title ?? "报名与到场"} backTo="/organizer" />
      <Scroll>
        {error ? (
          <Card>
            <StateView kind="network" message={error} actionTitle="重试" onAction={() => void load()} />
          </Card>
        ) : data == null ? (
          <Card>
            <StateView kind="loading" message="噜噜正在取数，稍等一下。" />
          </Card>
        ) : (
          <>
            <Card>
              <Chip kind="solid">{gatheringStatusName(data.status)}</Chip>
              <div className="flex mt-3" style={{ justifyContent: "space-around" }}>
                <Metric label="报名" value={data.registered_count} />
                <Metric label="确认" value={data.confirmed_count} />
                <Metric label="到场" value={data.attended_count} />
                <Metric label="目标" value={data.target_size} />
              </div>
              <div className="t-cap mt-2">{identityVisibilityLabel(data.identity_visibility)}</div>
            </Card>

            {(data.quota_batches ?? []).length > 0 ? (
              <Card className="mt-2">
                <div className="t-t3">名额批次</div>
                {(data.quota_batches ?? []).map((batch: OrganizerQuotaBatch, i: number) => (
                  <div key={i} className="between mt-2">
                    <span className="t-call">{batch.label}</span>
                    <span className="t-call mono">{batch.slots}</span>
                  </div>
                ))}
              </Card>
            ) : null}

            {data.status === "Pooling" ? (
              <div className="mt-2">
                <Btn
                  kind="primary"
                  disabled={working}
                  onClick={() =>
                    void mutate("报名已关闭，进入成员分别确认阶段", () =>
                      repos.organizer.closeRegistration(gatheringId!, crypto.randomUUID()),
                    )
                  }
                >
                  关闭报名并发起分别确认
                </Btn>
              </div>
            ) : data.status === "Confirmed" ? (
              <div className="mt-2">
                <Btn
                  kind="primary"
                  disabled={working}
                  onClick={() =>
                    void mutate("全员确认已验证，官方局已正式成局", () =>
                      repos.organizer.finalize(gatheringId!, crypto.randomUUID()),
                    )
                  }
                >
                  验证全员确认并正式成局
                </Btn>
              </div>
            ) : data.status === "Tentative" ? (
              <div className="mt-2">
                <Btn kind="ghost" disabled>
                  等待所有成员分别确认（{data.confirmed_count ?? 0} / {data.registered_count ?? 0} 已确认）
                </Btn>
              </div>
            ) : (
              <Card className="mt-2">
                <div className="t-foot">生命周期操作已完成或当前状态不接受变更。</div>
              </Card>
            )}

            <Card className="mt-2">
              <div className="t-t3">参与者与到场</div>
              {(data.participants ?? []).length === 0 ? (
                <div className="t-foot mt-2">暂无参与者</div>
              ) : null}
              {(data.participants ?? []).map((p) => (
                <div key={p.user_id}>
                  <div className="between mt-2">
                    <span>
                      <div className="t-call" style={{ fontWeight: 600 }}>
                        {p.display_name ?? "已确认成员"}
                      </div>
                      <div className="t-foot">{p.confirmation_status ?? ""}</div>
                    </span>
                    {p.attended ? (
                      <span className="t-foot" style={{ fontWeight: 700 }}>
                        ✓ 已到场
                      </span>
                    ) : (
                      <Btn
                        kind="ghost"
                        sm
                        disabled={working || !attendanceOpen}
                        onClick={() =>
                          void mutate("到场事实已登记", () =>
                            repos.organizer.markAttendance(
                              gatheringId!,
                              p.user_id,
                              crypto.randomUUID(),
                            ),
                          )
                        }
                      >
                        登记到场
                      </Btn>
                    )}
                  </div>
                  <Divider />
                </div>
              ))}
              {!attendanceOpen ? (
                <div className="t-cap mt-1">到场登记在正式成局后开放；服务端仍会校验时间窗口。</div>
              ) : null}
            </Card>
          </>
        )}
        {message ? (
          <Card className="mt-2">
            <div className="t-foot">{message}</div>
          </Card>
        ) : null}
      </Scroll>
    </Screen>
  );
}

function Metric({ label, value }: { label: string; value?: number }) {
  return (
    <span className="center" style={{ display: "inline-flex", flexDirection: "column", gap: 3 }}>
      <span className="t-t3 mono" style={{ fontWeight: 700 }}>
        {value ?? "—"}
      </span>
      <span className="t-cap">{label}</span>
    </span>
  );
}

/** O4 · 官方局模板（独立路由；与 O1 模板区共用同一组件）。 */
export function OrganizerTemplatesScreen() {
  const { repos } = useApp();
  const [templates, setTemplates] = useState<OrganizerTemplate[]>([]);
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setTemplates(asList(await repos.organizer.templates()));
      setPhase("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
  }, [repos]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Screen id="screen-O4-templates">
      <NavBar title="官方局模板" backTo="/organizer" />
      <Scroll>
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
              onAction={() => {
                setPhase("loading");
                void load();
              }}
            />
          </Card>
        ) : null}
        {phase === "loaded" ? (
          <TemplatesSection
            templates={templates}
            working={false}
            onReload={load}
            onMessage={setMessage}
          />
        ) : null}
        {message ? (
          <Card className="mt-2">
            <div className="t-foot">{message}</div>
          </Card>
        ) : null}
        <Note>T4 验证后可用 · 模板可复制、停用与一键实例化。</Note>
      </Scroll>
    </Screen>
  );
}
