import type { ReactNode } from "react";
import {
  authorizationLine,
  type ActionCopy,
} from "../../core/campus/actionCopy";
import { Card, Chip, Progress, Sticker } from "../ui/primitives";

export function ActionReviewCard({
  copy,
  authorizedCount,
  requiredCount,
  testId,
  children,
}: {
  copy: ActionCopy;
  authorizedCount?: number;
  requiredCount?: number;
  testId?: string;
  children?: ReactNode;
}) {
  const showProgress = typeof requiredCount === "number" && requiredCount > 0;
  const chipKind =
    copy.statusLabel === "待核对"
      ? "gap"
      : copy.statusLabel === "已完成"
        ? "solid"
        : "soft";

  return (
    <Card data-od-id={testId}>
      <div className="action-review-hero">
        <div className="action-review-mark">
          <Sticker name={copy.sticker} size="st-56" />
        </div>
        <div className="grow">
          <Chip kind={chipKind}>{copy.statusLabel}</Chip>
          <div className="t-t2 mt-2">{copy.title}</div>
          {copy.headline && copy.headline !== copy.title ? (
            <div className="t-call muted mt-1">{copy.headline}</div>
          ) : null}
          {copy.timeLine ? (
            <div className="action-review-time mt-2">{copy.timeLine}</div>
          ) : null}
        </div>
      </div>
      {copy.facts.length > 0 ? (
        <>
          <div className="divider" />
          {copy.facts.map((fact) => (
            <div className="between action-review-fact" key={fact.label}>
              <span className="t-foot">{fact.label}</span>
              <span className="action-review-value">{fact.value}</span>
            </div>
          ))}
        </>
      ) : null}
      {copy.note ? <div className="t-foot mt-3">{copy.note}</div> : null}
      {showProgress ? (
        <>
          <div className="divider" />
          <div className="t-foot mb-2">
            {authorizationLine(authorizedCount ?? 0, requiredCount ?? 0)}
          </div>
          <Progress
            value={((authorizedCount ?? 0) / (requiredCount ?? 1)) * 100}
          />
        </>
      ) : null}
      {children ? (
        <>
          <div className="divider" />
          <div className="action-review-actions">{children}</div>
        </>
      ) : null}
    </Card>
  );
}
