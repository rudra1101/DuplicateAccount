export type ChatRole =
  | "user"
  | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: Date;
}

export interface ChatHistoryMessage {
  role: ChatRole;
  content: string;
}

export interface ToolInvocation {
  name: string;
  arguments: Record<string, unknown>;
  result: unknown;
}

export interface AIResponse {
  conversationId: string;
  message: string;
  model: string;
  toolsUsed: ToolInvocation[];
}