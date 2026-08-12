import {
  Btn,
  Card,
  NavBar,
  Screen,
  Scroll,
  Section,
  StateView,
} from "../../components/ui/primitives";

const STATES = [
  "loading",
  "empty",
  "network",
  "offline",
  "denied",
  "expired",
  "duplicate",
  "stale",
] as const;

export function StatesLibraryScreen() {
  return (
    <Screen id="runtime-state-library">
      <NavBar title="状态规范" backTo="/me/account" />
      <Scroll>
        <Section title="G5 · 八种全局状态" />
        {STATES.map((k) => (
          <Card key={k} className="mb-3">
            <div className="t-cap mb-2 mono">{k}</div>
            <StateView kind={k} />
          </Card>
        ))}
        <Btn kind="ghost" to="/me">
          返回我
        </Btn>
      </Scroll>
    </Screen>
  );
}

export function PermissionNoticeScreen() {
  return (
    <Screen id="permission-recovery-notice">
      <NavBar title="系统权限" backTo="/today" />
      <Scroll>
        <Card>
          <StateView
            kind="denied"
            actionTitle="去系统设置开启"
            onAction={() => {
              /* web: cannot open OS settings; honest degrade */
            }}
          />
        </Card>
      </Scroll>
    </Screen>
  );
}
