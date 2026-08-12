/**
 * Campus orchestrator tools.
 *
 * Primary path: operate on client-supplied localContext (iOS Keychain / local DB).
 * Live campus path: only when ephemeral credentials are attached for this turn;
 * we never persist them.
 */

import { tool } from '@openai/agents';
import { z } from 'zod';
import type { CourseBlock, LocalTask, RequestSession } from './_session';
import { searchElectives } from './_electives';
import { matchElectivesToPersona } from './_tasteMatch';

function parseHm(value: string): number | null {
  const m = value.match(/(?:T|\s)?(\d{1,2}):(\d{2})/);
  if (!m) return null;
  return Number(m[1]) * 60 + Number(m[2]);
}

function formatHm(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function dayKey(block: CourseBlock): string {
  if (block.day) return block.day;
  if (block.start.includes('T')) return block.start.slice(0, 10);
  return 'unspecified-day';
}

function findGaps(
  blocks: CourseBlock[],
  windowStart = 8 * 60,
  windowEnd = 22 * 60,
  minGap = 60,
): Array<{ day: string; start: string; end: string; minutes: number }> {
  const byDay = new Map<string, Array<{ start: number; end: number; title: string }>>();
  for (const block of blocks) {
    const start = parseHm(block.start);
    const end = parseHm(block.end);
    if (start === null || end === null || end <= start) continue;
    const key = dayKey(block);
    const list = byDay.get(key) ?? [];
    list.push({ start, end, title: block.title });
    byDay.set(key, list);
  }

  const gaps: Array<{ day: string; start: string; end: string; minutes: number }> = [];
  for (const [day, items] of byDay) {
    const sorted = [...items].sort((a, b) => a.start - b.start);
    let cursor = windowStart;
    for (const item of sorted) {
      if (item.start - cursor >= minGap) {
        gaps.push({
          day,
          start: formatHm(cursor),
          end: formatHm(item.start),
          minutes: item.start - cursor,
        });
      }
      cursor = Math.max(cursor, item.end);
    }
    if (windowEnd - cursor >= minGap) {
      gaps.push({
        day,
        start: formatHm(cursor),
        end: formatHm(windowEnd),
        minutes: windowEnd - cursor,
      });
    }
  }
  return gaps.sort((a, b) => b.minutes - a.minutes);
}

export function createTools(session: RequestSession) {
  const getLocalTimetable = tool({
    name: 'get_local_timetable',
    description:
      'Read the timetable snapshot the iOS client attached for this turn. ' +
      'Use this before proposing a schedule. Does not call campus servers.',
    parameters: z.object({}),
    execute: async () => {
      const timetable = session.local.timetable ?? [];
      return JSON.stringify({
        source: 'client_localContext',
        count: timetable.length,
        campusHint: session.local.campusHint ?? null,
        blocks: timetable,
      });
    },
  });

  const proposeSchedule = tool({
    name: 'propose_schedule',
    description:
      'Arrange free time around the client timetable and optional preferred windows. ' +
      'Returns concrete gaps and suggested focus / booking slots for the user to confirm on iOS.',
    parameters: z.object({
      goal: z
        .string()
        .describe('What the user wants to fit in, e.g. 自习、健身、写作业'),
      min_minutes: z
        .number()
        .min(30)
        .max(240)
        .default(60)
        .describe('Minimum free block length in minutes'),
    }),
    execute: async ({ goal, min_minutes }) => {
      const timetable = session.local.timetable ?? [];
      const gaps = findGaps(timetable, 8 * 60, 22 * 60, min_minutes);
      const preferred = session.local.preferredWindows ?? [];
      const preferredHits = gaps.filter((gap) =>
        preferred.some((window) => {
          const [a, b] = window.split('-');
          if (!a || !b) return false;
          return gap.start >= a.trim() && gap.end <= b.trim();
        }),
      );

      const picks = (preferredHits.length ? preferredHits : gaps).slice(0, 5).map((gap, index) => ({
        rank: index + 1,
        day: gap.day,
        start: gap.start,
        end: gap.end,
        minutes: gap.minutes,
        suggestion: `${goal} @ ${gap.day} ${gap.start}-${gap.end}`,
        apply_on_client: true,
      }));

      return JSON.stringify({
        goal,
        timetable_blocks: timetable.length,
        preferred_windows: preferred,
        candidates: picks,
        note:
          picks.length === 0
            ? 'No free gaps found in the attached timetable; ask iOS for a wider date range.'
            : 'Return these candidates to the user; iOS should persist any confirmed plan locally.',
      });
    },
  });

  const draftTasks = tool({
    name: 'draft_tasks',
    description:
      'Draft or reshape local tasks. Cloud does NOT store tasks — output a mutation list ' +
      'for the iOS app to apply to its local task store.',
    parameters: z.object({
      intent: z
        .string()
        .describe('What the user asked to create or rearrange'),
      titles: z
        .array(z.string())
        .min(1)
        .max(12)
        .describe('Concrete task titles to draft'),
      due_hint: z
        .string()
        .nullable()
        .default(null)
        .describe('Optional shared due date/time hint'),
    }),
    execute: async ({ intent, titles, due_hint }) => {
      const existing = session.local.tasks ?? [];
      const create: LocalTask[] = titles.map((title, index) => ({
        id: `draft_${Date.now()}_${index}`,
        title,
        due: due_hint || undefined,
        status: 'todo',
        notes: `drafted_by_edge_agent:${intent}`,
      }));
      return JSON.stringify({
        persistence: 'client_only',
        intent,
        existing_count: existing.length,
        mutations: {
          upsert: create,
          delete_ids: [],
        },
        existing_preview: existing.slice(0, 10),
      });
    },
  });

  const listLocalTasks = tool({
    name: 'list_local_tasks',
    description: 'List tasks the client attached in localContext for this turn.',
    parameters: z.object({}),
    execute: async () => {
      const tasks = session.local.tasks ?? [];
      return JSON.stringify({
        source: 'client_localContext',
        count: tasks.length,
        tasks,
      });
    },
  });

  const searchElectivesTool = tool({
    name: 'search_electives',
    description:
      'Search elective / optional courses the student can consider. ' +
      'Uses localContext.electiveCatalog when iOS attached one; otherwise a demo catalog. ' +
      'For live JWXT training-program sync, call plan_campus_action with jwxt.training_program.',
    parameters: z.object({
      keyword: z
        .string()
        .nullable()
        .default(null)
        .describe('Free-text keyword, e.g. AI / 羽毛球 / 摄影'),
      category: z
        .string()
        .nullable()
        .default(null)
        .describe('Category filter, e.g. 通识选修 / 专业选修 / 体育选修'),
      campus: z
        .string()
        .nullable()
        .default(null)
        .describe('Campus filter, e.g. 珠海校区 / 南校园'),
      only_selectable: z
        .boolean()
        .default(true)
        .describe('If true, hide courses marked selectable=false'),
      min_credits: z.number().nullable().default(null),
      max_credits: z.number().nullable().default(null),
      limit: z.number().min(1).max(50).default(20),
    }),
    execute: async ({
      keyword,
      category,
      campus,
      only_selectable,
      min_credits,
      max_credits,
      limit,
    }) => {
      const result = searchElectives(session.local.electiveCatalog ?? [], {
        keyword,
        category,
        campus,
        onlySelectable: only_selectable,
        minCredits: min_credits,
        maxCredits: max_credits,
        limit,
      });
      return JSON.stringify({
        ...result,
        note:
          result.source === 'demo_catalog'
            ? 'Using demo elective catalog. iOS should sync real catalog into localContext.electiveCatalog.'
            : 'Using client-attached elective catalog.',
      });
    },
  });

  const matchElectivesTool = tool({
    name: 'match_electives_to_persona',
    description:
      '根据抖音/兴趣画像（localContext.tastePersona）给选修课目录打分排序，推荐适合的公选/专选。' +
      '需要客户端附带 electiveCatalog + tastePersona；不会访问校园服务器。',
    parameters: z.object({
      limit: z.number().min(1).max(30).default(10),
      min_score: z.number().min(0).max(20).default(1.2),
      prefer_public: z
        .boolean()
        .default(true)
        .describe('若为 true，优先解释公选/通识匹配；专选仍可出现在结果中'),
    }),
    execute: async ({ limit, min_score }) => {
      const persona = session.local.tastePersona;
      if (!persona) {
        return JSON.stringify({
          ok: false,
          reason: 'missing_taste_persona',
          next: '请在 localContext.tastePersona 附带抖音画像（主标签/领域/子兴趣/匹配提示）。',
        });
      }
      const catalog = session.local.electiveCatalog ?? [];
      const pool =
        catalog.length > 0
          ? catalog
          : searchElectives([], { onlySelectable: true, limit: 50 }).items;
      const result = matchElectivesToPersona(persona, pool as Record<string, unknown>[], {
        limit,
        minScore: min_score,
      });
      return JSON.stringify({
        ...result,
        catalog_source: catalog.length > 0 ? 'client_catalog' : 'demo_catalog',
        note: '匹配为启发式打分；正式选课仍由 iOS 调用 course-selection / 用户确认。',
      });
    },
  });

  const planCampusAction = tool({
    name: 'plan_campus_action',
    description:
      'Plan a campus side-effect (timetable refresh, training program, gym). ' +
      'Returns an execution plan for iOS; does not book or select courses itself.',
    parameters: z.object({
      action: z.enum([
        'timetable.today',
        'timetable.fetch_term',
        'jwxt.training_program',
        'gym.available',
        'gym.book_preview',
      ]),
      params: z
        .record(z.string(), z.union([z.string(), z.number(), z.boolean(), z.null()]))
        .default({})
        .describe('Action parameters, e.g. venue_type, date, start, end, scope'),
    }),
    execute: async ({ action, params }) => {
      const needsGym = action.startsWith('gym.');
      const hasGym = Boolean(session.credentials.gymSession || session.credentials.gymAuth);
      const hasJwxt = Boolean(session.credentials.jwxtSession || session.credentials.session);

      if (needsGym && !hasGym) {
        return JSON.stringify({
          ok: false,
          reason: 'missing_ephemeral_gym_credentials',
          next: 'Ask iOS to attach gymSession/gymAuth for one turn, or run sysu-anything gym locally.',
        });
      }
      if (
        action.startsWith('timetable.') &&
        !hasJwxt &&
        !(session.local.timetable?.length)
      ) {
        return JSON.stringify({
          ok: false,
          reason: 'missing_timetable_source',
          next: 'Attach localContext.timetable or ephemeral jwxt/session credentials.',
        });
      }
      if (action === 'jwxt.training_program' && !hasJwxt) {
        return JSON.stringify({
          ok: false,
          reason: 'missing_ephemeral_jwxt_credentials',
          next: 'Attach session/jwxtSession for one turn, or run training-program on device.',
        });
      }

      return JSON.stringify({
        ok: true,
        mode: 'client_execute',
        action,
        params,
        credentials_present_ephemeral: session.hasLiveCampus,
        ios_bridge: {
          cli_hints: {
            'timetable.today': 'sysu-anything today --json',
            'timetable.fetch_term': 'sysu-anything jwxt timetable-import --json',
            'jwxt.training_program': 'sysu-anything jwxt training-program --json',
            'gym.available':
              'sysu-anything gym available --venue-type <name> --date <YYYY-MM-DD> --json',
            'gym.book_preview':
              'sysu-anything gym book --venue-type <name> --date <d> --start <t> --end <t> --json',
          }[action],
          confirm_required: action === 'gym.book_preview',
        },
        note:
          'EdgeOne agent only orchestrates. iOS (or a one-shot sandbox bridge) performs the action with local secrets.',
      });
    },
  });

  return [
    getLocalTimetable,
    listLocalTasks,
    proposeSchedule,
    draftTasks,
    searchElectivesTool,
    matchElectivesTool,
    planCampusAction,
  ];
}
