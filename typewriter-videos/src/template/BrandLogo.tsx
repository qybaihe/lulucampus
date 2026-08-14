import {
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { pingFangFamily } from "../load-fonts";

export const BrandLogo: React.FC<{
  src: string;
  wordmark: string;
  opacity: number;
}> = ({ src, wordmark, opacity }) => {
  const frame = useCurrentFrame();
  const intro = interpolate(frame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        marginBottom: 18,
        opacity: opacity * intro,
        scale: interpolate(frame, [0, 12], [0.94, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
          output: "perceptual-scale",
        }),
      }}
    >
      <div
        style={{
          width: 220,
          height: 220,
          borderRadius: 52,
          overflow: "hidden",
        }}
      >
        <Img
          src={staticFile(src)}
          style={{ width: 220, height: 220, objectFit: "cover" }}
        />
      </div>
      <div
        style={{
          fontFamily: pingFangFamily,
          fontWeight: 300,
          fontSize: 34,
          letterSpacing: "0.32em",
          color: "#E8E8E8",
          paddingLeft: "0.32em",
        }}
      >
        {wordmark}
      </div>
    </div>
  );
};
