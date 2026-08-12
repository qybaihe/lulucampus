/* 差一个 · ONE MORE — Lulu 动效播放器
   数据源：assets/lulu/lulu-motion.v1.json（与 iOS 工程共用契约）
   图集：2×2，单元格 627×627，锚点 (0.5, 0.941)
   reduced-motion → poster-frame（静帧） */

const LULU_ATLAS = {
  "home.idle":        "assets/lulu/LuluHomeIdleAtlas.png",
  "home.listening":   "assets/lulu/LuluHomeListeningAtlas.png",
  "home.thinking":    "assets/lulu/LuluHomeThinkingAtlas.png",
  "home.reply":       "assets/lulu/LuluHomeReplyAtlas.png",
  "core.care":        "assets/lulu/LuluCoreStatesAtlas.png",
  "core.celebrate":   "assets/lulu/LuluCoreStatesAtlas.png",
  "intent.card":      "assets/lulu/LuluIntentCardAtlas.png",
  "pool.waiting":     "assets/lulu/LuluPoolWaitingAtlas.png",
  "confirm.gather":   "assets/lulu/LuluConfirmGatherAtlas.png",
  "action.preview":   "assets/lulu/LuluActionPreviewAtlas.png",
  "action.executing": "assets/lulu/LuluActionExecutingAtlas.png",
  "exit.bow":         "assets/lulu/LuluExitBowAtlas.png",
};

/* 帧序列（cell 序号 0-3，按图集 2×2 从左到右、从上到下） */
const LULU_CLIPS = {
  "home.idle":        { loop: true,  poster: 0, frames: [[0,900],[1,300],[2,180],[3,650]] },
  "home.listening":   { loop: true,  poster: 0, frames: [[0,360],[1,320],[2,180],[1,320]] },
  "home.thinking":    { loop: true,  poster: 0, frames: [[0,460],[1,420],[2,170],[3,430]] },
  "home.reply":       { loop: true,  poster: 1, frames: [[0,260],[1,240],[2,220],[3,240]] },
  "core.care":        { loop: true,  poster: 2, frames: [[2,600],[3,420],[2,600],[3,420]] },
  "core.celebrate":   { loop: false, poster: 1, frames: [[0,260],[1,300],[2,260],[3,560]] },
  "intent.card":      { loop: false, poster: 2, frames: [[0,260],[1,260],[2,520],[3,420]] },
  "pool.waiting":     { loop: true,  poster: 0, frames: [[0,520],[1,420],[2,420],[3,320]] },
  "confirm.gather":   { loop: false, poster: 3, frames: [[0,300],[1,300],[2,300],[3,560]] },
  "action.preview":   { loop: false, poster: 2, frames: [[0,260],[1,240],[2,520],[3,320]] },
  "action.executing": { loop: true,  poster: 0, frames: [[0,180],[1,180],[2,180],[3,180]] },
  "exit.bow":         { loop: false, poster: 3, frames: [[0,360],[1,300],[2,420],[3,720]] },
};

const LULU_CELL = 627;
const _luluPlayers = new Set();
const _reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function luluHTML(clip, sizeCls, caption) {
  const c = LULU_CLIPS[clip] || LULU_CLIPS["home.idle"];
  const poster = _reducedMotion ? c.poster : c.frames[0][0];
  const pos = _cellPos(poster);
  return `<div class="lulu-wrap">
    <div class="lulu ${sizeCls}" data-lulu="${clip}"
      style="background-image:url('${LULU_ATLAS[clip]}');background-position:${pos};background-size:200% 200%;"></div>
    ${caption ? `<div class="lulu-cap">${caption}</div>` : ""}
  </div>`;
}

function _cellPos(cell) {
  const col = cell % 2, row = Math.floor(cell / 2);
  return `${col * 100}% ${row * 100}%`;
}

function luluBoot(root) {
  _luluPlayers.forEach(p => p.stop());
  _luluPlayers.clear();
  root.querySelectorAll("[data-lulu]").forEach(el => {
    const clip = el.dataset.lulu;
    const c = LULU_CLIPS[clip];
    if (!c || _reducedMotion) return;
    let i = 0, timer = null, stopped = false;
    const step = () => {
      if (stopped || !el.isConnected) { stopped = true; return; }
      const [cell, dur] = c.frames[i];
      el.style.backgroundPosition = _cellPos(cell);
      i++;
      if (i >= c.frames.length) {
        if (c.loop) { i = 0; }
        else { el.style.backgroundPosition = _cellPos(c.poster); stopped = true; return; }
      }
      timer = setTimeout(step, dur);
    };
    timer = setTimeout(step, 60);
    _luluPlayers.add({ stop() { stopped = true; clearTimeout(timer); } });
  });
}
