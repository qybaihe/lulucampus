import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { pingFangFamily } from "../load-fonts";
import { BrandLogo } from "./BrandLogo";
import {
  FADE_IN,
  FADE_OUT,
  TYPING_GAIN,
  TypewriterClipProps,
  TypewriterLine,
  planTiming,
} from "./timing";

const TITLE_SIZE = 88;
const BODY_SIZE = 42;

export const TypewriterClip: React.FC<TypewriterClipProps> = ({
  background,
  lines,
  logoSrc,
  wordmark,
  showLogo,
  targetSeconds,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const plan = planTiming(lines, targetSeconds);
  const activeIndex = activeLineIndex(plan.starts, frame);
  const fadeIn = interpolate(frame, [0, FADE_IN], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - FADE_OUT, durationInFrames - 1],
    [1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    },
  );
  const sceneOpacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill style={{ backgroundColor: background }}>
      {lines.map((line, index) => {
        const start = plan.starts[index];
        const duration = Array.from(line.text).length * plan.framesPerChar;

        return (
          <Sequence
            key={`${line.text}-${index}`}
            from={start}
            durationInFrames={duration}
            layout="none"
          >
            <Audio
              src={staticFile("sfx/text-typing-keyboard.mp3")}
              volume={TYPING_GAIN}
            />
          </Sequence>
        );
      })}

      <AbsoluteFill
        style={{
          opacity: sceneOpacity,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "80px 72px",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            width: "100%",
          }}
        >
          {showLogo ? (
            <BrandLogo src={logoSrc} wordmark={wordmark} opacity={1} />
          ) : null}
          {lines.map((line, index) => (
            <TypewriterLineView
              key={`${line.role}-${line.text}`}
              line={line}
              frame={frame}
              start={plan.starts[index]}
              framesPerChar={plan.framesPerChar}
              isActive={activeIndex === index}
              isFirstBody={
                line.role === "body" &&
                lines.findIndex((item) => item.role === "body") === index
              }
            />
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const TypewriterLineView: React.FC<{
  line: TypewriterLine;
  frame: number;
  start: number;
  framesPerChar: number;
  isActive: boolean;
  isFirstBody: boolean;
}> = ({ line, frame, start, framesPerChar, isActive, isFirstBody }) => {
  const chars = Array.from(line.text);
  const typed =
    frame < start
      ? 0
      : Math.min(chars.length, Math.floor((frame - start) / framesPerChar) + 1);
  const stillTyping = isActive && typed < chars.length;
  const cursorOpacity = stillTyping ? 1 : isActive ? (frame % 12 < 7 ? 1 : 0) : 0;
  const isTitle = line.role === "title";
  const visibleChars = chars.slice(0, typed);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: isTitle ? 106 : 60,
        marginTop: isTitle ? 0 : isFirstBody ? 36 : 18,
        color: isTitle ? "#F7F7F7" : "#C9C9C9",
        fontFamily: pingFangFamily,
        fontSize: isTitle ? TITLE_SIZE : BODY_SIZE,
        fontWeight: isTitle ? 500 : 300,
        lineHeight: isTitle ? 1.2 : 1.45,
        whiteSpace: "nowrap",
      }}
    >
      {visibleChars.length === 0 ? (
        <span
          style={{
            position: "relative",
            display: "inline-block",
            width: 3,
            height: "0.86em",
          }}
        >
          <Cursor opacity={cursorOpacity} flush />
        </span>
      ) : (
        visibleChars.map((char, index) => {
          const appearAt = start + index * framesPerChar;
          const opacity = interpolate(frame, [appearAt, appearAt + 2], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          });

          return (
            <span
              key={`${char}-${index}`}
              style={{
                position: "relative",
                display: "inline-block",
                opacity,
                marginRight:
                  index === visibleChars.length - 1
                    ? 0
                    : isTitle
                      ? "0.1em"
                      : "0.06em",
              }}
            >
              {char}
              {index === visibleChars.length - 1 ? (
                <Cursor opacity={cursorOpacity} />
              ) : null}
            </span>
          );
        })
      )}
    </div>
  );
};

const Cursor: React.FC<{ opacity: number; flush?: boolean }> = ({
  opacity,
  flush,
}) => {
  return (
    <span
      style={{
        position: "absolute",
        left: flush ? "50%" : "100%",
        top: "50%",
        width: 3,
        height: "0.86em",
        marginLeft: flush ? 0 : 6,
        backgroundColor: "#F7F7F7",
        borderRadius: 1,
        opacity,
        translate: flush ? "-50% -50%" : "0px -50%",
      }}
    />
  );
};

const activeLineIndex = (starts: number[], frame: number) => {
  let active = 0;
  for (const [index, start] of starts.entries()) {
    if (frame >= start) {
      active = index;
    }
  }
  return active;
};
