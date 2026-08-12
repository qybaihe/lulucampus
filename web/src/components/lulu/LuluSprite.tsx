import { useEffect, useRef } from "react";
import { assetURL } from "../../core/assets";

/**
 * Lulu 图集播放器 — 与设计稿 export/js/lulu.js 同一契约：
 * 2×2 图集，单元格 627×627，reduced-motion 时停在 poster 帧。
 */

const LULU_ATLAS = {
  "home.idle": assetURL("/assets/lulu/LuluHomeIdleAtlas.png"),
  "home.listening": assetURL("/assets/lulu/LuluHomeListeningAtlas.png"),
  "home.thinking": assetURL("/assets/lulu/LuluHomeThinkingAtlas.png"),
  "home.reply": assetURL("/assets/lulu/LuluHomeReplyAtlas.png"),
  "core.care": assetURL("/assets/lulu/LuluCoreStatesAtlas.png"),
  "core.celebrate": assetURL("/assets/lulu/LuluCoreStatesAtlas.png"),
  "intent.card": assetURL("/assets/lulu/LuluIntentCardAtlas.png"),
  "pool.waiting": assetURL("/assets/lulu/LuluPoolWaitingAtlas.png"),
  "confirm.gather": assetURL("/assets/lulu/LuluConfirmGatherAtlas.png"),
  "action.preview": assetURL("/assets/lulu/LuluActionPreviewAtlas.png"),
  "action.executing": assetURL("/assets/lulu/LuluActionExecutingAtlas.png"),
  "exit.bow": assetURL("/assets/lulu/LuluExitBowAtlas.png"),
} as const;

export type LuluClip = keyof typeof LULU_ATLAS;

/** [cell, durationMs]，cell 按 2×2 从左到右、从上到下 0-3 */
const LULU_CLIPS: Record<
  LuluClip,
  { loop: boolean; poster: number; frames: ReadonlyArray<readonly [number, number]> }
> = {
  "home.idle": { loop: true, poster: 0, frames: [[0, 900], [1, 300], [2, 180], [3, 650]] },
  "home.listening": { loop: true, poster: 0, frames: [[0, 360], [1, 320], [2, 180], [1, 320]] },
  "home.thinking": { loop: true, poster: 0, frames: [[0, 460], [1, 420], [2, 170], [3, 430]] },
  "home.reply": { loop: true, poster: 1, frames: [[0, 260], [1, 240], [2, 220], [3, 240]] },
  "core.care": { loop: true, poster: 2, frames: [[2, 600], [3, 420], [2, 600], [3, 420]] },
  "core.celebrate": { loop: false, poster: 1, frames: [[0, 260], [1, 300], [2, 260], [3, 560]] },
  "intent.card": { loop: false, poster: 2, frames: [[0, 260], [1, 260], [2, 520], [3, 420]] },
  "pool.waiting": { loop: true, poster: 0, frames: [[0, 520], [1, 420], [2, 420], [3, 320]] },
  "confirm.gather": { loop: false, poster: 3, frames: [[0, 300], [1, 300], [2, 300], [3, 560]] },
  "action.preview": { loop: false, poster: 2, frames: [[0, 260], [1, 240], [2, 520], [3, 320]] },
  "action.executing": { loop: true, poster: 0, frames: [[0, 180], [1, 180], [2, 180], [3, 180]] },
  "exit.bow": { loop: false, poster: 3, frames: [[0, 360], [1, 300], [2, 420], [3, 720]] },
};

function cellPos(cell: number): string {
  const col = cell % 2;
  const row = Math.floor(cell / 2);
  return `${col * 100}% ${row * 100}%`;
}

const REDUCED =
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function LuluSprite({
  clip,
  size = 120,
  caption,
  round = false,
  bare = false,
}: {
  clip: LuluClip;
  /** 边长；传 `"100%"` 时填满父级（配合 LuluMark placement 尺寸） */
  size?: number | string;
  caption?: string;
  round?: boolean;
  /** 仅输出精灵节点，不包一层 lulu-wrap（给 LuluMark 用） */
  bare?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const conf = LULU_CLIPS[clip] ?? LULU_CLIPS["home.idle"];

  useEffect(() => {
    const el = ref.current;
    if (!el || REDUCED) return;
    let i = 0;
    let stopped = false;
    let timer = 0;
    const step = () => {
      if (stopped || !el.isConnected) return;
      const [cell, dur] = conf.frames[i];
      el.style.backgroundPosition = cellPos(cell);
      i += 1;
      if (i >= conf.frames.length) {
        if (conf.loop) {
          i = 0;
        } else {
          el.style.backgroundPosition = cellPos(conf.poster);
          return;
        }
      }
      timer = window.setTimeout(step, dur);
    };
    timer = window.setTimeout(step, 60);
    return () => {
      stopped = true;
      window.clearTimeout(timer);
    };
  }, [conf]);

  const poster = REDUCED ? conf.poster : conf.frames[0][0];
  const sprite = (
    <div
      ref={ref}
      className="lulu"
      role="img"
      aria-label={`噜噜 · ${clip}`}
      style={{
        width: size,
        height: size,
        backgroundImage: `url('${LULU_ATLAS[clip]}')`,
        backgroundPosition: cellPos(poster),
        backgroundSize: "200% 200%",
        borderRadius: round ? "50%" : undefined,
      }}
    />
  );
  if (bare) return sprite;
  return (
    <div className="lulu-wrap">
      {sprite}
      {caption ? <div className="lulu-cap">{caption}</div> : null}
    </div>
  );
}
