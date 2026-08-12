export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  /**
   * True while the assistant is actively producing this message
   * (between the first text_delta and the final done/error event).
   * Drives the in-bubble blinking caret to give the user feedback
   * that more content is still streaming. Cleared once done/error fires.
   */
  streaming?: boolean;
}

export interface ToolLampState {
  id: string;
  label: string;
  icon: string;
  active: boolean;
  animKey: number;   // Incremented on each activation to remount and replay animation
}

/**
 * Lightweight summary of a conversation, returned by /conversations.
 * Used to render the left sidebar — does NOT contain full message content.
 */
export interface ConversationSummary {
  id: string;
  title: string;
  preview?: string;
  lastMessageAt?: number;
  createdAt?: number;
  userId?: string;
  messageCount?: number;
}

export interface ListConversationsParams {
  userId: string;
  limit?: number;
  order?: 'asc' | 'desc';
  after?: string;
  before?: string;
}

export interface ListConversationsResponse {
  conversations: ConversationSummary[];
  nextCursor?: string;
  previousCursor?: string;
}

/** Client-owned snapshot attached to each /chat turn (never stored by EdgeOne as secrets). */
export interface CourseBlockPayload {
  id?: string;
  title: string;
  start: string;
  end: string;
  location?: string;
  day?: string;
}

export interface LocalTaskPayload {
  id?: string;
  title: string;
  due?: string;
  status?: 'todo' | 'doing' | 'done';
  notes?: string;
}

export interface LocalContextPayload {
  timetable?: CourseBlockPayload[];
  tasks?: LocalTaskPayload[];
  electiveCatalog?: Array<{
    code: string;
    title: string;
    category: string;
    credits: number;
    campus?: string;
    college?: string;
    capacity?: number;
    remaining?: number;
    weekday?: string;
    time?: string;
    teacher?: string;
    tags?: string[];
    selectable?: boolean;
  }>;
  preferredWindows?: string[];
  campusHint?: string;
  timezone?: string;
}

/** Ephemeral credentials for one turn only — iOS Keychain export shape. */
export interface CampusCredentialsPayload {
  session?: Record<string, unknown>;
  jwxtSession?: Record<string, unknown>;
  libicSession?: Record<string, unknown>;
  gymSession?: Record<string, unknown>;
  gymAuth?: Record<string, unknown>;
}
