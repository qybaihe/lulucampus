/**
 * Elective course search — shared by Agent tools and /v1 cloud functions.
 *
 * Live "选课系统可选课" is not yet wrapped in sysu-anything as a first-class
 * command. Until then:
 * 1) Prefer client-attached localContext.electiveCatalog (iOS sync)
 * 2) Fall back to DEMO_ELECTIVES for EdgeOne demos
 * 3) plan_campus_action can still ask iOS to run `jwxt training-program`
 */

export type ElectiveCourse = {
  code: string;
  title: string;
  category: string; // 通识 / 专业选修 / 跨专业 / 体育 等
  credits: number;
  campus?: string;
  college?: string;
  capacity?: number;
  /** Already selected count when known (capacity - remaining) */
  selected?: number;
  remaining?: number;
  weekday?: string;
  time?: string;
  teacher?: string;
  tags?: string[];
  selectable?: boolean;
};

export const DEMO_ELECTIVES: ElectiveCourse[] = [
  {
    code: 'GE2101',
    title: '批判性思维与表达',
    category: '通识选修',
    credits: 2,
    campus: '珠海校区',
    college: '通识教育部',
    capacity: 120,
    remaining: 18,
    weekday: '周二',
    time: '19:00-20:40',
    teacher: '李老师',
    tags: ['写作', '表达'],
    selectable: true,
  },
  {
    code: 'CS3208',
    title: '移动应用开发',
    category: '专业选修',
    credits: 3,
    campus: '珠海校区',
    college: '计算机学院',
    capacity: 80,
    remaining: 6,
    weekday: '周四',
    time: '14:00-16:35',
    teacher: '王老师',
    tags: ['iOS', 'Swift', '工程实践'],
    selectable: true,
  },
  {
    code: 'ART1102',
    title: '摄影基础',
    category: '通识选修',
    credits: 2,
    campus: '南校园',
    college: '传播与设计学院',
    capacity: 40,
    remaining: 0,
    weekday: '周六',
    time: '09:00-11:30',
    teacher: '陈老师',
    tags: ['艺术', '实践'],
    selectable: false,
  },
  {
    code: 'PE1205',
    title: '羽毛球（提高）',
    category: '体育选修',
    credits: 1,
    campus: '珠海校区',
    college: '体育部',
    capacity: 30,
    remaining: 4,
    weekday: '周三',
    time: '16:20-17:50',
    teacher: '赵老师',
    tags: ['体育', '羽毛球'],
    selectable: true,
  },
  {
    code: 'ECO2301',
    title: '行为经济学导论',
    category: '跨专业选修',
    credits: 2,
    campus: '南校园',
    college: '岭南学院',
    capacity: 60,
    remaining: 22,
    weekday: '周一',
    time: '18:30-20:10',
    teacher: '周老师',
    tags: ['经济', '社科'],
    selectable: true,
  },
  {
    code: 'AI4002',
    title: '大模型应用实践',
    category: '专业选修',
    credits: 2,
    campus: '珠海校区',
    college: '计算机学院',
    capacity: 50,
    remaining: 11,
    weekday: '周五',
    time: '14:00-15:40',
    teacher: '刘老师',
    tags: ['AI', 'Agent', '工程'],
    selectable: true,
  },
];

export type ElectiveSearchQuery = {
  keyword?: string | null;
  category?: string | null;
  campus?: string | null;
  onlySelectable?: boolean;
  minCredits?: number | null;
  maxCredits?: number | null;
  limit?: number;
};

function normalizeElective(row: Record<string, unknown>): ElectiveCourse | null {
  const code = typeof row.code === 'string' ? row.code : null;
  const title = typeof row.title === 'string' ? row.title : null;
  if (!code || !title) return null;
  const creditsRaw = row.credits;
  const credits =
    typeof creditsRaw === 'number'
      ? creditsRaw
      : typeof creditsRaw === 'string'
        ? Number(creditsRaw)
        : 0;
  return {
    code,
    title,
    category: typeof row.category === 'string' ? row.category : '选修',
    credits: Number.isFinite(credits) ? credits : 0,
    campus: typeof row.campus === 'string' ? row.campus : undefined,
    college: typeof row.college === 'string' ? row.college : undefined,
    capacity: typeof row.capacity === 'number' ? row.capacity : undefined,
    remaining: typeof row.remaining === 'number' ? row.remaining : undefined,
    weekday: typeof row.weekday === 'string' ? row.weekday : undefined,
    time: typeof row.time === 'string' ? row.time : undefined,
    teacher: typeof row.teacher === 'string' ? row.teacher : undefined,
    tags: Array.isArray(row.tags)
      ? row.tags.filter((t): t is string => typeof t === 'string')
      : undefined,
    selectable: typeof row.selectable === 'boolean' ? row.selectable : true,
  };
}

export function parseElectiveCatalog(value: unknown): ElectiveCourse[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) =>
      item && typeof item === 'object'
        ? normalizeElective(item as Record<string, unknown>)
        : null,
    )
    .filter((item): item is ElectiveCourse => item !== null);
}

export function searchElectives(
  catalog: ElectiveCourse[],
  query: ElectiveSearchQuery,
): {
  source: 'client_catalog' | 'demo_catalog';
  total: number;
  matched: number;
  items: ElectiveCourse[];
} {
  const source = catalog.length > 0 ? 'client_catalog' : 'demo_catalog';
  const pool = catalog.length > 0 ? catalog : DEMO_ELECTIVES;
  const keyword = (query.keyword ?? '').trim().toLowerCase();
  const category = (query.category ?? '').trim().toLowerCase();
  const campus = (query.campus ?? '').trim().toLowerCase();
  const limit = Math.min(Math.max(query.limit ?? 20, 1), 50);

  const filtered = pool.filter((course) => {
    if (query.onlySelectable && course.selectable === false) return false;
    if (query.minCredits != null && course.credits < query.minCredits) return false;
    if (query.maxCredits != null && course.credits > query.maxCredits) return false;
    if (category && !course.category.toLowerCase().includes(category)) return false;
    if (campus && !(course.campus ?? '').toLowerCase().includes(campus)) return false;
    if (keyword) {
      const hay = [
        course.code,
        course.title,
        course.category,
        course.college ?? '',
        course.teacher ?? '',
        ...(course.tags ?? []),
      ]
        .join(' ')
        .toLowerCase();
      if (!hay.includes(keyword)) return false;
    }
    return true;
  });

  return {
    source,
    total: pool.length,
    matched: filtered.length,
    items: filtered.slice(0, limit),
  };
}
