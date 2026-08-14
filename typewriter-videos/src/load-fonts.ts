import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

const family = "PingFang SC";

loadFont({
  family,
  url: staticFile("fonts/PingFangSC-Light.ttf"),
  weight: "300",
});

loadFont({
  family,
  url: staticFile("fonts/PingFangSC-Regular.ttf"),
  weight: "400",
});

loadFont({
  family,
  url: staticFile("fonts/PingFangSC-Medium.ttf"),
  weight: "500",
});

export const pingFangFamily = family;
