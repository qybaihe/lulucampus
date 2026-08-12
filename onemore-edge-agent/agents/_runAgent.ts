/**
 * Shared agent runner for /chat and /ask (iOS API).
 */

import OpenAI from 'openai';
import { run, Agent, OpenAIChatCompletionsModel, type Session } from '@openai/agents';
import { createTools } from './_tools';
import { sseResponse } from './_sse';
import { parseRequestSession, sessionCapabilitySummary } from './_session';

const DEFAULT_MODEL = '@makers/deepseek-v4-flash';

export type AgentLogger = {
  log: (...a: unknown[]) => void;
  error: (...a: unknown[]) => void;
};

export async function handleCampusAgentRequest(
  context: any,
  logger: AgentLogger,
): Promise<Response> {
  const body = (context.request.body ?? {}) as Record<string, unknown>;
  const message = typeof body.message === 'string' ? body.message : undefined;
  if (!message) {
    return new Response(JSON.stringify({ error: "'message' is required" }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const rawUserId =
    typeof body.userId === 'string'
      ? body.userId
      : typeof body.user_id === 'string'
        ? body.user_id
        : '';
  const userId = rawUserId.trim() || undefined;
  const userMsgId = typeof body.userMsgId === 'string' ? body.userMsgId : undefined;

  const conversationId: string = context.conversation_id ?? '';
  const signal: AbortSignal | undefined = context.request.signal;
  const requestSession = parseRequestSession(body);
  const capability = sessionCapabilitySummary(requestSession);

  logger.log(
    `[request] cid=${conversationId}, uid=${userId ?? '-'}, ${capability}, message="${message.slice(0, 50)}..."`,
  );

  if (userId && conversationId) {
    try {
      const appendArgs: Record<string, unknown> = {
        conversationId,
        role: 'user',
        content: message,
        userId,
      };
      if (userMsgId) appendArgs.messageId = userMsgId;
      await context.store.appendMessage(appendArgs);
    } catch (e) {
      logger.error('[agent] failed to write user index:', e);
    }
  }

  const session: Session | undefined = conversationId
    ? context.store.openaiSession(conversationId)
    : undefined;

  const env = context.env as Record<string, string | undefined>;
  const llmClient = new OpenAI({
    apiKey: env.AI_GATEWAY_API_KEY,
    baseURL: env.AI_GATEWAY_BASE_URL,
  });
  const model = new OpenAIChatCompletionsModel(
    llmClient,
    env.AI_GATEWAY_MODEL ?? DEFAULT_MODEL,
  );

  const agent = new Agent({
    name: 'OneMoreCampusOrchestrator',
    instructions:
      '你是 OneMore 的校园编排 Agent，跑在 EdgeOne Makers 上，面向 iOS API 调用。\n' +
      '分工：iOS 保管凭证与本地课表/任务/选修目录；你只编排，不持久化 Cookie/Token。\n' +
      `当前请求能力：${capability}\n` +
      '\n' +
      '工具（只能用精确名字）：\n' +
      '- `get_local_timetable` / `list_local_tasks`\n' +
      '- `propose_schedule`：围绕课表找空档\n' +
      '- `draft_tasks`：任务草稿（客户端落库）\n' +
      '- `search_electives`：查询可选选修课（客户端目录或演示目录）\n' +
      '- `match_electives_to_persona`：按抖音画像给选修课打分推荐\n' +
      '- `plan_campus_action`：规划真实校园动作（含 jwxt.training_program）\n' +
      '\n' +
      '规则：\n' +
      '- 问选修/公选/适合选什么课时：有画像用 match_electives_to_persona，否则 search_electives。\n' +
      '- 需要真实培养方案同步时用 plan_campus_action(jwxt.training_program)。\n' +
      '- 预约类必须强调用户确认；不要假装已提交。\n' +
      '- 中文简洁回答。',
    tools: createTools(requestSession),
    model,
  });

  const toSseEvent = (e: any) => {
    if (e.type === 'raw_model_stream_event' && e.data?.type === 'output_text_delta') {
      return { event: 'text_delta', data: { delta: e.data.delta as string } };
    }
    if (e.type === 'run_item_stream_event' && e.name === 'tool_called') {
      const toolName = e.item?.name ?? e.item?.rawItem?.name;
      if (toolName) return { event: 'tool_called', data: { tool: toolName } };
    }
    return null;
  };

  return sseResponse(
    async function* () {
      const result = await run(agent, message, { stream: true, signal, session });
      for await (const event of result.toStream()) {
        if (signal?.aborted) break;
        const sse = toSseEvent(event);
        if (sse) yield sse;
      }
    },
    { signal, logger },
  );
}
