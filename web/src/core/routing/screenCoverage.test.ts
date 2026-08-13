import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  EXTRA_COMPOSITE_NODES,
  FIVE_TAB_LABELS,
  FORMAL_NODES,
  productionWebRoutes,
  TASTE_IMPORT_ROUTE,
} from "./formalNodes";

function walk(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, acc);
    else if (p.endsWith(".tsx") || p.endsWith(".ts")) acc.push(p);
  }
  return acc;
}

describe("screen coverage vs SCREEN_MAP production surfaces", () => {
  const screensRoot = join(process.cwd(), "src/screens");
  const appTsx = readFileSync(join(process.cwd(), "src/App.tsx"), "utf8");
  const screenFiles = walk(screensRoot);
  const screenSource = screenFiles.map((f) => readFileSync(f, "utf8")).join("\n");
  const reposSource = readFileSync(
    join(process.cwd(), "src/core/api/repositories.ts"),
    "utf8",
  );
  const gatheringSource = readFileSync(
    join(process.cwd(), "src/screens/gatherings/GatheringScreens.tsx"),
    "utf8",
  );
  const organizerSource = readFileSync(
    join(process.cwd(), "src/screens/organizer/OrganizerScreens.tsx"),
    "utf8",
  );
  const relationsSource = readFileSync(
    join(process.cwd(), "src/screens/relations/RelationsScreens.tsx"),
    "utf8",
  );
  const competitionsSource = readFileSync(
    join(process.cwd(), "src/screens/competitions/CompetitionsScreens.tsx"),
    "utf8",
  );
  const todaySource = readFileSync(
    join(process.cwd(), "src/screens/today/TodayScreens.tsx"),
    "utf8",
  );

  it("ships screen modules for every Feature area", () => {
    const areas = [
      "auth",
      "today",
      "competitions",
      "intent",
      "gatherings",
      "messages",
      "profile",
      "relations",
      "organizer",
      "taste",
      "shared",
    ];
    for (const area of areas) {
      expect(
        screenFiles.some((f) => f.includes(`/screens/${area}/`)),
        `missing screens for ${area}`,
      ).toBe(true);
    }
  });

  it("registers production web routes in App.tsx", () => {
    const routes = productionWebRoutes();
    const required = [
      "/today",
      "/competitions",
      "/intent",
      "/messages",
      "/me",
      "/gatherings/open",
      "/gatherings/mine",
      "/relations",
      "/organizer",
      "/auth",
      "/auth/scan",
      "/me/taste",
      "/states",
    ];
    for (const path of required) {
      expect(appTsx.includes(`path="${path}"`), path).toBe(true);
    }
    expect(routes.some((r) => r.id === "B1")).toBe(true);
    expect(routes.some((r) => r.id === TASTE_IMPORT_ROUTE.id)).toBe(true);
    expect(EXTRA_COMPOSITE_NODES.map((n) => n.id)).toContain("MSG");
  });

  it("embeds formal a11y identifiers on shipped screens", () => {
    const must = [
      "screen-B1-today",
      "screen-B12-competitions",
      "screen-D1-intent",
      "screen-M1-profile",
      "screen-MSG-messages",
      "screen-A2-auth-intro",
      "screen-C1-public-gatherings",
      "screen-E1-my-gatherings",
      "screen-E14-channel",
      "screen-E15-relations",
      "screen-O1-organizer",
      "screen-taste-import",
      "runtime-state-library",
    ];
    for (const id of must) {
      expect(screenSource.includes(id), id).toBe(true);
    }
  });

  it("E4–E10 gathering surfaces are real UI wired to repositories, not empty divs", () => {
    const markers = [
      "gathering-reschedule-actions",
      "gathering-backfill-actions",
      "gathering-completion-actions",
      "gathering-recurrence-actions",
      "gathering-action-preview",
      "gathering-collaboration-space",
      "gathering-action-result",
    ];
    for (const m of markers) {
      expect(gatheringSource.includes(m), m).toBe(true);
      // empty self-closing placeholder pattern
      expect(
        gatheringSource.includes(`data-od-id="${m}" />`) ||
          gatheringSource.includes(`data-od-id='${m}' />`),
        `${m} must not be an empty self-closing div`,
      ).toBe(false);
    }
    // repository methods used
    for (const call of [
      "currentReschedule",
      "voteReschedule",
      "reschedule",
      "backfill",
      "claimBackfill",
      "complete",
      "recur",
      "actionCapability",
      "actions.preview",
    ]) {
      expect(
        gatheringSource.includes(call) || reposSource.includes(call),
        call,
      ).toBe(true);
    }
    expect(reposSource.includes("/gatherings/${id}/reschedule")).toBe(true);
    expect(reposSource.includes("/gatherings/${id}/backfill")).toBe(true);
    expect(reposSource.includes("/gatherings/${id}/complete")).toBe(true);
    expect(reposSource.includes("/actions/preview")).toBe(true);
  });

  it("Organizer/Relations do not dump raw JSON as the primary UI", () => {
    expect(organizerSource.includes("JSON.stringify")).toBe(false);
    expect(relationsSource.includes("JSON.stringify")).toBe(false);
    // O2 create posts to organizer
    expect(organizerSource.includes("repos.organizer.create")).toBe(true);
    expect(reposSource.includes('"/organizer/gatherings"')).toBe(true);
    // E11 shared goals cards
    expect(relationsSource.includes("shared-goal-card") || relationsSource.includes("Progress")).toBe(
      true,
    );
    expect(
      relationsSource.includes("repos.relations") &&
        relationsSource.includes(".goals"),
    ).toBe(true);
  });

  it("does not invent hard-coded competition seat business facts", () => {
    expect(competitionsSource.includes('role: "建模"')).toBe(false);
    expect(competitionsSource.includes('role: "编程"')).toBe(false);
    expect(competitionsSource.includes('role: "写作"')).toBe(false);
    expect(gatheringSource.includes('role: "A"')).toBe(false);
    expect(gatheringSource.includes("seatsFromGathering")).toBe(true);
  });

  it("Hermes and campus tools call real repository endpoints", () => {
    expect(todaySource.includes("repos.hermes.ask")).toBe(true);
    expect(reposSource.includes('"/hermes/ask"')).toBe(true);
    expect(reposSource.includes('"/hermes/peers/start"')).toBe(true);
    expect(todaySource.includes("repos.campus.assignments") || todaySource.includes("campus.assignments")).toBe(
      true,
    );
    expect(todaySource.includes("repos.campus.gymAvailable") || todaySource.includes("gymAvailable")).toBe(
      true,
    );
    expect(todaySource.includes("repos.campus.roomAvailable") || todaySource.includes("roomAvailable")).toBe(
      true,
    );
    expect(reposSource.includes('"/venues/gym/available"')).toBe(true);
    expect(reposSource.includes('"/assignments"')).toBe(true);
  });

  it("B10 SceneTrigger uses server scene_trigger and forbids hard-coded demo copy", () => {
    // Must load from summary or navigation state — not invent library-4F demo
    expect(todaySource.includes("repos.today.summary")).toBe(true);
    expect(todaySource.includes("scene_trigger")).toBe(true);
    expect(todaySource.includes("ignoreSceneTrigger") || reposSource.includes("ignoreSceneTrigger")).toBe(
      true,
    );
    expect(reposSource.includes("/today/triggers/")).toBe(true);
    // Forbidden hard-coded business demo strings from the old prototype board
    const forbidden = [
      "今晚图书馆 4F 有空档",
      "图书馆 4F 有空档",
      "与你作业 DDL 重叠",
    ];
    for (const s of forbidden) {
      expect(todaySource.includes(s), `forbidden demo string: ${s}`).toBe(false);
    }
    // Must surface server title/body fields
    expect(todaySource.includes("trigger.title") || todaySource.includes("scene_trigger.title")).toBe(
      true,
    );
    expect(todaySource.includes("trigger.body") || todaySource.includes("scene_trigger.body")).toBe(
      true,
    );
  });

  it("five-tab labels remain verbatim", () => {
    expect([...FIVE_TAB_LABELS]).toEqual(["今天", "比赛", "差一个", "消息", "我"]);
  });

  it("keeps 74 formal nodes", () => {
    expect(FORMAL_NODES).toHaveLength(74);
  });
});
