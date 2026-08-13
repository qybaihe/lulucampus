import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import { FIVE_TAB_LABELS, TAB_ROOTS, type TabId } from "../../core/routing/formalNodes";
import { attentionItems } from "../../core/today/attention";
import { Icon } from "../ui/primitives";

const TAB_ORDER: TabId[] = [
  "today",
  "competitions",
  "create",
  "messages",
  "me",
];

const ICONS: Record<Exclude<TabId, "create">, string> = {
  today: "sun",
  competitions: "trophy",
  messages: "chat",
  me: "person",
};

export function TabBar() {
  const { repos, sessionState } = useApp();
  const [hasAttention, setHasAttention] = useState(false);

  useEffect(() => {
    if (sessionState.status !== "authenticated") {
      setHasAttention(false);
      return;
    }
    let cancelled = false;
    repos.today
      .summary()
      .then((summary) => {
        if (!cancelled) setHasAttention(attentionItems(summary.pending).length > 0);
      })
      .catch(() => {
        if (!cancelled) setHasAttention(false);
      });
    return () => {
      cancelled = true;
    };
  }, [repos, sessionState]);

  return (
    <nav className="tabbar" data-od-id="tabbar" aria-label="主导航">
      {TAB_ORDER.map((id) => {
        const tab = TAB_ROOTS[id];
        if (id === "create") {
          return (
            <NavLink
              key={id}
              to={tab.path}
              className={({ isActive }) =>
                `tab-item ${isActive ? "active" : ""}`
              }
              aria-label={FIVE_TAB_LABELS[2]}
              data-tab="create"
            >
              <span className="tab-create">⊕</span>
              <span className="tab-create-label">差一个</span>
              <span className="tab-dot" />
            </NavLink>
          );
        }
        return (
          <NavLink
            key={id}
            to={tab.path}
            className={({ isActive }) =>
              `tab-item ${isActive ? "active" : ""}`
            }
            data-tab={id}
            end={id === "today" || id === "me"}
          >
            <span className="tab-icon-wrap">
              <Icon name={ICONS[id]} size={24} />
              {id === "messages" && hasAttention ? (
                <span className="tab-unread" aria-label="有待处理提醒" />
              ) : null}
            </span>
            <span>{tab.label}</span>
            <span className="tab-dot" />
          </NavLink>
        );
      })}
    </nav>
  );
}

export function tabLabelsMatch(): boolean {
  return (
    FIVE_TAB_LABELS[0] === "今天" &&
    FIVE_TAB_LABELS[1] === "比赛" &&
    FIVE_TAB_LABELS[2] === "差一个" &&
    FIVE_TAB_LABELS[3] === "消息" &&
    FIVE_TAB_LABELS[4] === "我"
  );
}
