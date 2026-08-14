import { TARGET_SECONDS, TypewriterClipProps } from "./timing";

const brand = {
  background: "#000000",
  logoSrc: "logo/lulu-app-icon.png",
  wordmark: "噜噜成局",
  showLogo: true,
  targetSeconds: TARGET_SECONDS,
} as const;

export const clip01: TypewriterClipProps = {
  ...brand,
  lines: [
    { text: "来噜噜成局", role: "title" },
    { text: "导入你的抖音主页链接", role: "body" },
    { text: "获取你的性格画像", role: "body" },
  ],
};

export const clip02: TypewriterClipProps = {
  ...brand,
  lines: [
    { text: "来噜噜成局", role: "title" },
    { text: "根据抖音画像", role: "body" },
    { text: "推荐你喜欢的公选", role: "body" },
    { text: "找到和你选同样课的人", role: "body" },
  ],
};

export const clip03: TypewriterClipProps = {
  ...brand,
  lines: [
    { text: "来噜噜成局", role: "title" },
    { text: "活动组局找搭子", role: "body" },
    { text: "再也不尴尬", role: "body" },
  ],
};

export const clip04: TypewriterClipProps = {
  ...brand,
  lines: [
    { text: "来噜噜成局", role: "title" },
    { text: "活动人满", role: "body" },
    { text: "进入群聊", role: "body" },
    { text: "帮你想好开场白", role: "body" },
    { text: "还有共同经历的事情", role: "body" },
  ],
};

export const clip05: TypewriterClipProps = {
  ...brand,
  lines: [
    { text: "来噜噜成局", role: "title" },
    { text: "帮你在解决日常琐事的同时", role: "body" },
    { text: "找到和你有共同偏好的人", role: "body" },
  ],
};

export const clip06: TypewriterClipProps = {
  ...brand,
  lines: [
    { text: "来噜噜成局", role: "title" },
    { text: "帮你收集各大比赛信息", role: "body" },
    { text: "帮你找到比赛好队友", role: "body" },
  ],
};

export const clip07: TypewriterClipProps = {
  ...brand,
  lines: [
    { text: "来噜噜成局", role: "title" },
    { text: "噜噜在Hermes的指引下", role: "body" },
    { text: "找到了和他一起玩的人", role: "body" },
    { text: "他们同一个时间去篮球馆", role: "body" },
  ],
};
