/**
 * Score electives against a Douyin / taste persona (EdgeOne-side, no campus I/O).
 */

export type TastePersona = {
  primary_tag?: { label?: string; key?: string; score?: number } | string;
  secondary_tags?: Array<{ label?: string } | string>;
  interest_domains?: Array<{ label?: string } | string>;
  interest_facets?: Array<{ label?: string; facet?: string } | string>;
  matching_hints?: string[];
  summary?: string;
  persona?: string;
  // Chinese field aliases from product copy
  主标签?: string;
  副标签?: string[] | string;
  领域?: string[] | string;
  子兴趣?: string[] | string;
  匹配提示?: string[] | string;
  摘要?: string;
};

type Course = Record<string, unknown>;

const BAGS: Record<string, string[]> = {
  ai_programming: [
    '人工智能', '大模型', 'ai', '编程', '软件', '算法', '数据', '计算', '智能',
    '机器学习', '区块链', '图形', '游戏', '数字图像', 'python', '开源',
  ],
  tech_devices: ['科技', '数码', '电子', '硬件', '通信', '物联网', '机器人', '工程', '创新', '创客'],
  growth_career: ['创业', '职业', '领导', '管理', '商业', '沟通', '表达', '批判', '思维', '写作', '演讲', '项目', '产品'],
  knowledge_method: ['方法', '研究', '学术', '逻辑', '科学', '统计', '心理', '认知', '学习', '教育'],
  aesthetic: ['审美', '艺术', '设计', '摄影', '影像', '视觉', '电影', '美术', '音乐', '媒体', '传播', '创意'],
  sports_health: ['体育', '运动', '跑步', '康复', '健康', '体能', '瑜伽', '球', '健身', '户外'],
  travel_media: ['旅行', '旅游', '地理', '文化', '城市', '自媒体', '新媒体', '短视频', '叙事', '纪录'],
  builder_hackathon: ['黑客', '实践', '实训', '创新', '创业', '项目', '工程', '开发', '制作', '竞赛'],
};

const DOMAIN_TO_BAG: Record<string, string> = {
  '成长/职业': 'growth_career',
  '知识方法': 'knowledge_method',
  'AI/编程': 'ai_programming',
  '科技数码': 'tech_devices',
};

function norm(text: string): string {
  return text.toLowerCase().replace(/\s+/g, '');
}

function asList(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.flatMap((item) => {
      if (typeof item === 'string') return item.split(/[、,，/|]/);
      if (item && typeof item === 'object') {
        const row = item as Record<string, unknown>;
        return [String(row.label || row.facet || row.key || '')];
      }
      return [];
    });
  }
  if (typeof value === 'string') return value.split(/[、,，/|]/);
  return [];
}

function add(weights: Map<string, number>, word: string, w: number) {
  const key = norm(word.replace(/[（(][^）)]*[）)]/g, ''));
  if (key.length < 2) return;
  weights.set(key, (weights.get(key) || 0) + w);
}

export function buildSignalWeights(persona: TastePersona): Map<string, number> {
  const weights = new Map<string, number>();
  const primary =
    typeof persona.primary_tag === 'string'
      ? persona.primary_tag
      : persona.primary_tag?.label || persona.主标签 || '';
  add(weights, primary, 2.2);

  for (const tag of [...asList(persona.secondary_tags), ...asList(persona.副标签)]) {
    add(weights, tag, 1.4);
  }
  for (const domain of [...asList(persona.interest_domains), ...asList(persona.领域)]) {
    add(weights, domain, 1.6);
    const bag = DOMAIN_TO_BAG[domain.trim()];
    if (bag) for (const kw of BAGS[bag]) add(weights, kw, 1.1);
  }
  for (const facet of [...asList(persona.interest_facets), ...asList(persona.子兴趣)]) {
    add(weights, facet, 1.8);
  }
  for (const hint of [...asList(persona.matching_hints), ...asList(persona.匹配提示)]) {
    add(weights, hint, 1.5);
  }

  const blob = norm(`${persona.summary || ''} ${persona.摘要 || ''} ${persona.persona || ''}`);
  for (const bag of Object.values(BAGS)) {
    for (const kw of bag) {
      if (blob.includes(norm(kw))) add(weights, kw, 0.9);
    }
  }

  const p = norm(primary);
  if (p.includes('builder') || p.includes('探索')) {
    for (const kw of BAGS.builder_hackathon) add(weights, kw, 0.8);
    for (const kw of BAGS.ai_programming) add(weights, kw, 0.7);
  }
  return weights;
}

function enrichCompetition(course: Course) {
  const capacity = typeof course.capacity === 'number' ? course.capacity : undefined;
  const remaining = typeof course.remaining === 'number' ? course.remaining : undefined;
  let selected =
    typeof course.selected === 'number'
      ? course.selected
      : capacity !== undefined && remaining !== undefined
        ? Math.max(0, capacity - remaining)
        : undefined;

  const fillRate =
    capacity !== undefined && capacity > 0 && selected !== undefined
      ? Math.round(Math.min(1, Math.max(0, selected / capacity)) * 10000) / 10000
      : undefined;

  let competition_level = 'unknown';
  let competition_label = '名额未知';
  if (fillRate === undefined) {
    // keep unknown
  } else if (fillRate >= 1 || (remaining !== undefined && remaining <= 0)) {
    competition_level = 'full';
    competition_label = '已满';
  } else if (fillRate >= 0.85) {
    competition_level = 'high';
    competition_label = '竞争激烈';
  } else if (fillRate >= 0.55) {
    competition_level = 'medium';
    competition_label = '中等竞争';
  } else if (fillRate >= 0.2) {
    competition_level = 'low';
    competition_label = '竞争温和';
  } else {
    competition_level = 'empty';
    competition_label = '几乎没人选';
  }

  return {
    selected,
    capacity,
    remaining,
    fill_rate: fillRate,
    competition_level,
    competition_label,
  };
}

export function matchElectivesToPersona(
  persona: TastePersona,
  courses: Course[],
  opts?: { limit?: number; minScore?: number },
) {
  const limit = opts?.limit ?? 12;
  const minScore = opts?.minScore ?? 1.2;
  const signals = buildSignalWeights(persona);
  const ranked: Array<
    Course & {
      match_score: number;
      match_reasons: string[];
      selected?: number;
      fill_rate?: number;
      competition_level: string;
      competition_label: string;
    }
  > = [];

  for (const course of courses) {
    const hay = norm(
      ['code', 'title', 'category', 'college', 'campus', 'teacher', 'time']
        .map((k) => String(course[k] || ''))
        .join(' ') +
        ' ' +
        (Array.isArray(course.tags) ? course.tags.join(' ') : ''),
    );
    let score = 0;
    const reasons: string[] = [];
    const sorted = [...signals.entries()].sort((a, b) => b[1] - a[1]);
    for (const [token, weight] of sorted) {
      if (hay.includes(token)) {
        score += weight;
        if (reasons.length < 4) reasons.push(token);
      }
    }
    const competition = enrichCompetition(course);
    if (typeof competition.remaining === 'number' && competition.remaining > 0) score += 0.15;
    if (typeof competition.fill_rate === 'number') {
      if (competition.fill_rate >= 0.95) score -= 0.35;
      else if (competition.fill_rate >= 0.85) score -= 0.15;
      else if (competition.fill_rate >= 0.15 && competition.fill_rate <= 0.7) score += 0.05;
    }
    if (course.selectable === true) score += 0.1;
    const category = String(course.category || '');
    if (category.includes('公选') || category.includes('通识')) score += 0.2;
    if (score < minScore) continue;
    ranked.push({
      ...course,
      selected: competition.selected,
      fill_rate: competition.fill_rate,
      competition_level: competition.competition_level,
      competition_label: competition.competition_label,
      match_score: Math.round(score * 1000) / 1000,
      match_reasons: reasons,
    });
  }

  ranked.sort((a, b) => {
    if (b.match_score !== a.match_score) return b.match_score - a.match_score;
    const ra = typeof a.remaining === 'number' ? a.remaining : -1;
    const rb = typeof b.remaining === 'number' ? b.remaining : -1;
    if (rb !== ra) return rb - ra;
    return String(a.code || '').localeCompare(String(b.code || ''));
  });

  const competition_summary: Record<string, number> = {};
  for (const row of ranked) {
    competition_summary[row.competition_level] =
      (competition_summary[row.competition_level] || 0) + 1;
  }

  return {
    ok: true,
    source: 'taste_elective_match',
    persona_signals: signals.size,
    courses_scored: courses.length,
    matched: ranked.length,
    competition_summary,
    items: ranked.slice(0, limit),
  };
}
