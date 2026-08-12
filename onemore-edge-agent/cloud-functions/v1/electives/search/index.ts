/**
 * POST /v1/electives/search — structured elective search for iOS (no LLM).
 */

import { createLogger } from '../../../_logger';
import { parseElectiveCatalog, searchElectives } from '../../../_electives';

const logger = createLogger('v1-electives-search');
const JSON_HEADERS = { 'Content-Type': 'application/json; charset=UTF-8' } as const;

export async function onRequestPost(context: any): Promise<Response> {
  let body: Record<string, unknown> = {};
  try {
    body = (await context.request.json()) as Record<string, unknown>;
  } catch {
    body = {};
  }

  const local =
    (body.localContext as Record<string, unknown> | undefined) ??
    (body.local_context as Record<string, unknown> | undefined) ??
    {};
  const catalog = parseElectiveCatalog(local.electiveCatalog ?? local.elective_catalog ?? body.catalog);
  const result = searchElectives(catalog, {
    keyword: typeof body.keyword === 'string' ? body.keyword : null,
    category: typeof body.category === 'string' ? body.category : null,
    campus: typeof body.campus === 'string' ? body.campus : null,
    onlySelectable: body.only_selectable !== false && body.onlySelectable !== false,
    minCredits: typeof body.min_credits === 'number' ? body.min_credits : null,
    maxCredits: typeof body.max_credits === 'number' ? body.max_credits : null,
    limit: typeof body.limit === 'number' ? body.limit : 20,
  });

  logger.log(`[electives] source=${result.source} matched=${result.matched}`);
  return new Response(JSON.stringify({ ok: true, ...result }), {
    status: 200,
    headers: JSON_HEADERS,
  });
}
