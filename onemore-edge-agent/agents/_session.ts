/**
 * Request-scoped campus session.
 *
 * Design rule (iOS owns secrets):
 * - Credentials and user data arrive ONLY in the current request body.
 * - Never write them to context.store / KV / Blob / logs.
 * - Tools close over this object for one agent run, then it is GC'd.
 */

import type { ElectiveCourse } from './_electives';
import { parseElectiveCatalog } from './_electives';

export type CampusCredentials = {
  /** Opaque CAS / shared cookie jar (sysu-anything session.json shape OK) */
  session?: Record<string, unknown>;
  jwxtSession?: Record<string, unknown>;
  libicSession?: Record<string, unknown>;
  gymSession?: Record<string, unknown>;
  gymAuth?: Record<string, unknown>;
};

export type CourseBlock = {
  id?: string;
  title: string;
  start: string; // ISO or HH:mm
  end: string;
  location?: string;
  day?: string; // YYYY-MM-DD or weekday label
};

export type LocalTask = {
  id?: string;
  title: string;
  due?: string;
  status?: 'todo' | 'doing' | 'done';
  notes?: string;
};

export type LocalContext = {
  /** Client-synced timetable occurrences for planning */
  timetable?: CourseBlock[];
  /** Client-local tasks the agent may rearrange / extend */
  tasks?: LocalTask[];
  /** Optional elective catalog synced by iOS (preferred over demo catalog) */
  electiveCatalog?: ElectiveCourse[];
  /** Douyin / taste persona for elective matching */
  tastePersona?: Record<string, unknown>;
  /** Preferred study / booking windows, e.g. ["18:00-20:00"] */
  preferredWindows?: string[];
  /** Campus label for wording, e.g. 珠海校区 / 南校园 */
  campusHint?: string;
  timezone?: string;
};

export type RequestSession = {
  credentials: CampusCredentials;
  local: LocalContext;
  hasLiveCampus: boolean;
};

function asObject(value: unknown): Record<string, unknown> | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
  return value as Record<string, unknown>;
}

function asCourseBlocks(value: unknown): CourseBlock[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (!item || typeof item !== 'object') return null;
      const row = item as Record<string, unknown>;
      const title = typeof row.title === 'string' ? row.title : null;
      const start = typeof row.start === 'string' ? row.start : null;
      const end = typeof row.end === 'string' ? row.end : null;
      if (!title || !start || !end) return null;
      return {
        id: typeof row.id === 'string' ? row.id : undefined,
        title,
        start,
        end,
        location: typeof row.location === 'string' ? row.location : undefined,
        day: typeof row.day === 'string' ? row.day : undefined,
      } satisfies CourseBlock;
    })
    .filter((item): item is CourseBlock => item !== null);
}

function asTasks(value: unknown): LocalTask[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (!item || typeof item !== 'object') return null;
      const row = item as Record<string, unknown>;
      const title = typeof row.title === 'string' ? row.title : null;
      if (!title) return null;
      const status = row.status;
      return {
        id: typeof row.id === 'string' ? row.id : undefined,
        title,
        due: typeof row.due === 'string' ? row.due : undefined,
        status:
          status === 'todo' || status === 'doing' || status === 'done' ? status : 'todo',
        notes: typeof row.notes === 'string' ? row.notes : undefined,
      } satisfies LocalTask;
    })
    .filter((item): item is LocalTask => item !== null);
}

export function parseRequestSession(body: Record<string, unknown>): RequestSession {
  const credentialsRaw = asObject(body.credentials) ?? {};
  const localRaw = asObject(body.localContext) ?? asObject(body.local_context) ?? {};

  const credentials: CampusCredentials = {
    session: asObject(credentialsRaw.session),
    jwxtSession: asObject(credentialsRaw.jwxtSession ?? credentialsRaw.jwxt_session),
    libicSession: asObject(credentialsRaw.libicSession ?? credentialsRaw.libic_session),
    gymSession: asObject(credentialsRaw.gymSession ?? credentialsRaw.gym_session),
    gymAuth: asObject(credentialsRaw.gymAuth ?? credentialsRaw.gym_auth),
  };

  const preferred = localRaw.preferredWindows ?? localRaw.preferred_windows;
  const local: LocalContext = {
    timetable: asCourseBlocks(localRaw.timetable),
    tasks: asTasks(localRaw.tasks),
    electiveCatalog: parseElectiveCatalog(
      localRaw.electiveCatalog ?? localRaw.elective_catalog,
    ),
    tastePersona:
      asObject(localRaw.tastePersona) ??
      asObject(localRaw.taste_persona) ??
      asObject(localRaw.persona) ??
      asObject(body.tastePersona) ??
      asObject(body.taste_persona),
    preferredWindows: Array.isArray(preferred)
      ? preferred.filter((item): item is string => typeof item === 'string')
      : undefined,
    campusHint:
      typeof localRaw.campusHint === 'string'
        ? localRaw.campusHint
        : typeof localRaw.campus_hint === 'string'
          ? localRaw.campus_hint
          : undefined,
    timezone: typeof localRaw.timezone === 'string' ? localRaw.timezone : 'Asia/Shanghai',
  };

  const hasLiveCampus = Boolean(
    credentials.session ||
      credentials.jwxtSession ||
      credentials.gymSession ||
      credentials.gymAuth,
  );

  return { credentials, local, hasLiveCampus };
}

/** Safe summary for prompts — never include cookie / token material. */
export function sessionCapabilitySummary(session: RequestSession): string {
  const creds: string[] = [];
  if (session.credentials.session) creds.push('cas_session');
  if (session.credentials.jwxtSession) creds.push('jwxt');
  if (session.credentials.libicSession) creds.push('libic');
  if (session.credentials.gymSession || session.credentials.gymAuth) creds.push('gym');
  return [
    `live_campus_credentials=${session.hasLiveCampus ? 'present_ephemeral' : 'absent'}`,
    `credential_kinds=${creds.join(',') || 'none'}`,
    `timetable_blocks=${session.local.timetable?.length ?? 0}`,
    `local_tasks=${session.local.tasks?.length ?? 0}`,
    `elective_catalog=${session.local.electiveCatalog?.length ?? 0}`,
    `campus_hint=${session.local.campusHint ?? 'unspecified'}`,
  ].join('; ');
}
