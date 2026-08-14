import {
  CalculateMetadataFunction,
  Composition,
  Sequence,
} from "remotion";
import { BlackHold } from "./BlackHold";
import { clip01, clip02, clip03, clip04, clip05, clip06, clip07 } from "./clips";
import { TypewriterClip } from "./TypewriterClip";
import {
  FPS,
  HEIGHT,
  TypewriterClipProps,
  WIDTH,
  planTiming,
} from "./timing";

const calculateTypewriterMetadata: CalculateMetadataFunction<
  TypewriterClipProps
> = ({ props }) => {
  const plan = planTiming(props.lines, props.targetSeconds);
  return {
    durationInFrames: plan.durationInFrames,
    fps: FPS,
    width: WIDTH,
    height: HEIGHT,
  };
};

const registerClip = (id: string, props: TypewriterClipProps) => {
  const plan = planTiming(props.lines, props.targetSeconds);
  return (
    <Composition
      id={id}
      component={TypewriterClip}
      durationInFrames={plan.durationInFrames}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={props}
      calculateMetadata={calculateTypewriterMetadata}
    />
  );
};

export const TemplateCompositions: React.FC = () => {
  const clip01Plan = planTiming(clip01.lines, clip01.targetSeconds);
  const clip02Plan = planTiming(clip02.lines, clip02.targetSeconds);

  return (
    <>
      {registerClip("Typewriter01", clip01)}
      {registerClip("Typewriter02", clip02)}
      {registerClip("Typewriter03", clip03)}
      {registerClip("Typewriter04", clip04)}
      {registerClip("Typewriter05", clip05)}
      {registerClip("Typewriter06", clip06)}
      {registerClip("Typewriter07", clip07)}
      <Composition
        id="BlackHold12"
        component={BlackHold}
        durationInFrames={12}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="BlackHold24"
        component={BlackHold}
        durationInFrames={24}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="BlackHold30"
        component={BlackHold}
        durationInFrames={30}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Reel01"
        component={Reel01}
        durationInFrames={clip01Plan.durationInFrames + 24}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Reel02"
        component={Reel02}
        durationInFrames={
          clip01Plan.durationInFrames + 24 + clip02Plan.durationInFrames
        }
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
    </>
  );
};

const Reel01: React.FC = () => {
  const plan = planTiming(clip01.lines, clip01.targetSeconds);

  return (
    <>
      <Sequence durationInFrames={plan.durationInFrames}>
        <TypewriterClip {...clip01} />
      </Sequence>
      <Sequence from={plan.durationInFrames} durationInFrames={24}>
        <BlackHold />
      </Sequence>
    </>
  );
};

const Reel02: React.FC = () => {
  const first = planTiming(clip01.lines, clip01.targetSeconds);
  const second = planTiming(clip02.lines, clip02.targetSeconds);
  const secondFrom = first.durationInFrames + 24;

  return (
    <>
      <Sequence durationInFrames={first.durationInFrames}>
        <TypewriterClip {...clip01} />
      </Sequence>
      <Sequence from={first.durationInFrames} durationInFrames={24}>
        <BlackHold />
      </Sequence>
      <Sequence from={secondFrom} durationInFrames={second.durationInFrames}>
        <TypewriterClip {...clip02} />
      </Sequence>
    </>
  );
};
