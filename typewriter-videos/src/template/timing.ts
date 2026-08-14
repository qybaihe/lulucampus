export type TypewriterLine = {
  text: string;
  role: "title" | "body";
};

export type TypewriterClipProps = {
  background: string;
  lines: TypewriterLine[];
  logoSrc: string;
  wordmark: string;
  showLogo: boolean;
  targetSeconds: number;
};

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;
export const TARGET_SECONDS = 4;
export const TARGET_FRAMES = TARGET_SECONDS * FPS;
export const FADE_IN = 8;
export const FADE_OUT = 10;
export const START_DELAY = 6;
export const LINE_PAUSE = 4;
export const HOLD_MIN = 16;
export const MIN_FRAMES_PER_CHAR = 2;
export const MAX_FRAMES_PER_CHAR = 3;
export const TYPING_GAIN = 10 ** (-24 / 20);

export type TimingPlan = {
  framesPerChar: number;
  starts: number[];
  typingEnd: number;
  durationInFrames: number;
};

export const charCount = (lines: TypewriterLine[]) =>
  lines.reduce((sum, line) => sum + Array.from(line.text).length, 0);

export const planTiming = (
  lines: TypewriterLine[],
  targetSeconds = TARGET_SECONDS,
): TimingPlan => {
  const targetFrames = Math.round(targetSeconds * FPS);
  const chars = Math.max(charCount(lines), 1);
  const pauses = Math.max(0, lines.length - 1) * LINE_PAUSE;
  const fitsThree =
    START_DELAY + chars * MAX_FRAMES_PER_CHAR + pauses + HOLD_MIN <=
    targetFrames;
  const framesPerChar = fitsThree ? MAX_FRAMES_PER_CHAR : MIN_FRAMES_PER_CHAR;

  const starts: number[] = [];
  let cursor = START_DELAY;
  for (const [index, line] of lines.entries()) {
    starts.push(cursor);
    cursor += Array.from(line.text).length * framesPerChar;
    if (index < lines.length - 1) {
      cursor += LINE_PAUSE;
    }
  }

  const typingEnd = cursor;
  const durationInFrames = Math.max(targetFrames, typingEnd + HOLD_MIN);

  return { framesPerChar, starts, typingEnd, durationInFrames };
};
