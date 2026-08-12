/**
 * POST /v1/capabilities — headless discovery for iOS.
 */

import { createLogger } from '../../_logger';

const logger = createLogger('v1-capabilities');
const JSON_HEADERS = { 'Content-Type': 'application/json; charset=UTF-8' } as const;

export async function onRequestPost(context: any): Promise<Response> {
  logger.log('[capabilities] requested');
  return new Response(
    JSON.stringify({
      service: 'onemore-edge-agent',
      mode: 'api_first',
      browser_ui: 'optional_debug_only',
      endpoints: {
        ask: {
          method: 'POST',
          path: '/ask',
          contentType: 'application/json',
          response: 'text/event-stream',
          headers_required: ['Makers-Conversation-Id'],
        },
        chat: {
          method: 'POST',
          path: '/chat',
          note: 'Same agent as /ask; kept for web debug page',
        },
        electives_search: {
          method: 'POST',
          path: '/v1/electives/search',
          response: 'application/json',
          note: 'Deterministic elective search without LLM',
        },
        stop: { method: 'POST', path: '/stop' },
      },
      tools: [
        'get_local_timetable',
        'list_local_tasks',
        'propose_schedule',
        'draft_tasks',
        'search_electives',
        'plan_campus_action',
      ],
      limits: {
        secrets: 'client_ephemeral_only',
        live_course_selection_system: false,
        live_jwxt_training_program: 'via_ios_bridge',
        live_gym: 'via_ios_bridge',
        elective_search_sources: ['localContext.electiveCatalog', 'demo_catalog'],
      },
    }),
    { status: 200, headers: JSON_HEADERS },
  );
}

export async function onRequestGet(context: any): Promise<Response> {
  return onRequestPost(context);
}
