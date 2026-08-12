/**
 * POST /v1/electives/match — score electives against a Douyin / taste persona (no LLM).
 *
 * Body:
 *   localContext.tastePersona + localContext.electiveCatalog
 *   OR top-level persona + catalog
 *   limit / min_score optional
 */

import { createLogger } from '../../../_logger';
import { parseElectiveCatalog } from '../../../_electives';
import { matchElectivesToPersona } from '../../../../agents/_tasteMatch';

const logger = createLogger('v1-electives-match');
const JSON_HEADERS = { 'Content-Type': 'application/json; charset=UTF-8' } as const;

function asObject(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

export async function onRequestPost(context: any): Promise<Response> {
  let body: Record<string, unknown> = {};
  try {
    body = (await context.request.json()) as Record<string, unknown>;
  } catch {
    body = {};
  }

  const local =
    asObject(body.localContext) ?? asObject(body.local_context) ?? {};
  const persona =
    asObject(local.tastePersona) ??
    asObject(local.taste_persona) ??
    asObject(local.persona) ??
    asObject(body.tastePersona) ??
    asObject(body.taste_persona) ??
    asObject(body.persona);

  if (!persona) {
    return new Response(
      JSON.stringify({
        ok: false,
        reason: 'missing_taste_persona',
        next: 'Pass localContext.tastePersona (Douyin profile fields).',
      }),
      { status: 400, headers: JSON_HEADERS },
    );
  }

  const catalog = parseElectiveCatalog(
    local.electiveCatalog ?? local.elective_catalog ?? body.catalog,
  );
  if (catalog.length === 0) {
    return new Response(
      JSON.stringify({
        ok: false,
        reason: 'empty_catalog',
        next: 'Pass localContext.electiveCatalog from JWXT course-selection list.',
      }),
      { status: 400, headers: JSON_HEADERS },
    );
  }

  const limit = typeof body.limit === 'number' ? body.limit : 12;
  const minScore =
    typeof body.min_score === 'number'
      ? body.min_score
      : typeof body.minScore === 'number'
        ? body.minScore
        : 1.2;

  const result = matchElectivesToPersona(persona, catalog as Record<string, unknown>[], {
    limit,
    minScore,
  });

  logger.log(
    `[electives/match] scored=${result.courses_scored} matched=${result.matched}`,
  );
  return new Response(
    JSON.stringify({
      ok: true,
      catalog_source: 'client_catalog',
      ...result,
    }),
    { status: 200, headers: JSON_HEADERS },
  );
}
