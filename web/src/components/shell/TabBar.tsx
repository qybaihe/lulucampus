import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import { assetURL } from "../../core/assets";
import { FIVE_TAB_LABELS, TAB_ROOTS, type TabId } from "../../core/routing/formalNodes";
import { attentionItems } from "../../core/today/attention";

const TAB_ORDER: TabId[] = [
  "today",
  "competitions",
  "create",
  "messages",
  "me",
];

const TAB_ASSET: Record<TabId, string> = {
  today: "tab-today",
  competitions: "tab-activity",
  create: "tab-create",
  messages: "tab-messages",
  me: "tab-profile",
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
        return (
          <NavLink
            key={id}
            to={tab.path}
            className={({ isActive }) => `tab-item ${isActive ? "active" : ""}`}
            aria-label={id === "create" ? FIVE_TAB_LABELS[2] : tab.label}
            data-tab={id}
            end={id === "today" || id === "me"}
          >
            {({ isActive }) => (
              <>
                <span className="tab-icon-wrap">
                  <img
                    src={assetURL(
                      `/assets/tab/${TAB_ASSET[id]}-${isActive ? "active" : "inactive"}.png`,
                    )}
                    alt=""
                    className={id === "create" ? "tab-png-create" : "tab-png"}
                    draggable={false}
                  />
                  {id === "messages" && hasAttention ? (
                    <span className="tab-unread" aria-label="有待处理提醒" />
                  ) : null}
                </span>
                <span className={id === "create" ? "tab-create-label" : undefined}>
                  {tab.label}
                </span>
                <span className="tab-dot" />
              </>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}

export function tabLabelsMatch(): boolean {
  return (
    FIVE_TAB_LABELS[0] === "今天" &&
    FIVE_TAB_LABELS[1] === "活动" &&
    FIVE_TAB_LABELS[2] === "差一个" &&
    FIVE_TAB_LABELS[3] === "消息" &&
    FIVE_TAB_LABELS[4] === "我"
  );
}
