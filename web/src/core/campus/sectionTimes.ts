/** 2026 秋学期标准节次，对齐 iOS section_times_2026_fall.json。 */
export const SECTION_TIMES: Record<number, [string, string]> = {
  1: ["08:00", "08:45"],
  2: ["08:55", "09:40"],
  3: ["10:10", "10:55"],
  4: ["11:05", "11:50"],
  5: ["14:20", "15:05"],
  6: ["15:15", "16:00"],
  7: ["16:30", "17:15"],
  8: ["17:25", "18:10"],
  9: ["19:00", "19:45"],
  10: ["19:55", "20:40"],
  11: ["20:50", "21:35"],
};

export function sectionTime(number: number): [string, string] | undefined {
  return SECTION_TIMES[number];
}
