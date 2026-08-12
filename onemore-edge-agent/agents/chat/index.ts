/**
 * Web demo chat endpoint — POST /chat
 */

import { createLogger } from '../_logger';
import { handleCampusAgentRequest } from '../_runAgent';

const logger = createLogger('chat');

export async function onRequest(context: any) {
  return handleCampusAgentRequest(context, logger);
}
