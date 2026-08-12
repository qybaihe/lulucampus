import { useEffect, useRef } from "react";
import luluWave from "./assets/lulu-wave.png";

const LULU_ATLAS = {
  "home.listening": "/assets/lulu/LuluHomeListeningAtlas.png",
  "home.thinking": "/assets/lulu/LuluHomeThinkingAtlas.png",
  "core.care": "/assets/lulu/LuluCoreStatesAtlas.png",
  "core.celebrate": "/assets/lulu/LuluCoreStatesAtlas.png",
} as const;

export type LuluClip = keyof typeof LULU_ATLAS;

const LULU_CLIPS: Record<
  LuluClip,
  { loop: boolean; poster: number; frames: ReadonlyArray<readonly [number, number]> }
> = {
  "home.listening": { loop: true, poster: 0, frames: [[0, 360], [1, 320], [2, 180], [1, 320]] },
  "home.thinking": { loop: true, poster: 0, frames: [[0, 460], [1, 420], [2, 170], [3, 430]] },
  "core.care": { loop: true, poster: 2, frames: [[2, 600], [3, 420], [2, 600], [3, 420]] },
  "core.celebrate": { loop: false, poster: 1, frames: [[0, 260], [1, 300], [2, 260], [3, 560]] },
};

function cellPos(cell: number): string {
  return `${(cell % 2) * 100}% ${Math.floor(cell / 2) * 100}%`;
}

const REDUCED =
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function LuluSprite({ clip, size = 120 }: { clip: LuluClip; size?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const conf = LULU_CLIPS[clip];

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
        if (conf.loop) i = 0;
        else {
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
  return (
    <div className="lulu-wrap">
      <div
        ref={ref}
        className="lulu"
        role="img"
        aria-label="噜噜"
        style={{
          width: size,
          height: size,
          backgroundImage: `url('${LULU_ATLAS[clip]}')`,
          backgroundPosition: cellPos(poster),
          backgroundSize: "200% 200%",
        }}
      />
    </div>
  );
}

export function LuluStill({ size = 72 }: { clip?: LuluClip; size?: number }) {
  return (
    <img
      className="lulu-still"
      src={luluWave}
      width={size}
      height={size}
      alt="噜噜"
      draggable={false}
      decoding="sync"
    />
  );
}
