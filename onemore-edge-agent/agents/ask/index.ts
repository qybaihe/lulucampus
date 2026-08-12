/**
 * iOS / headless API — POST /ask
 *
 * Same campus orchestrator as /chat, intended for native clients.
 * No browser UI required: call this route with JSON + SSE.
 */

import { createLogger } from '../_logger';
import { handleCampusAgentRequest } from '../_runAgent';

const logger = createLogger('ask');

export async function onRequest(context: any) {
  return handleCampusAgentRequest(context, logger);
}
