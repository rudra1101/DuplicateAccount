const API_URL =
   "http://127.0.0.1:8000/api";


export interface ChatSource {
  documentId: number | null;
  documentName: string;
  pageNumber: number | null;
  score?: number | null;
}


export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}


export interface AIResponse {
  conversationId: string;
  message: string;
  model?: string | null;
  toolsUsed?: unknown[];
  sources: ChatSource[];
}


export type ChatStreamEvent =
  | {
      type: "start";
      conversationId: string;
    }
  | {
      type: "status";
      message: string;
    }
  | {
      type: "delta";
      text: string;
    }
  | {
      type: "done";
      conversationId: string;
      messageId: number;
      model?: string | null;
      sources: ChatSource[];
      toolsUsed?: unknown[];
    }
  | {
      type: "error";
      message: string;
    };


export interface StreamAIHandlers {
  onStart?: (
    conversationId: string,
  ) => void;

  onStatus?: (
    message: string,
  ) => void;

  onDelta?: (
    text: string,
  ) => void;

  onDone?: (
    event: Extract<
      ChatStreamEvent,
      { type: "done" }
    >,
  ) => void;
}


export interface KnowledgeChunk {
  id: number;
  chunkId: string;
  chunkIndex: number;
  pageNumber: number | null;
  content: string;
  characterCount: number;
}


export interface KnowledgeDocumentDetails {
  id: number;
  name: string;
  originalFilename: string;
  contentType: string;
  status: string;
  chunkCount: number;
  characterCount: number;
  errorMessage: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  chunks: KnowledgeChunk[];
}


export interface ChatConversationSummary {
  id: string;
  title: string;
  createdAt: string | null;
  updatedAt: string | null;
}


export interface StoredChatMessage {
  id: number;
  conversationId: string;
  role: "user" | "assistant";
  content: string;
  model: string | null;
  sources: ChatSource[];
  createdAt: string | null;
}


export interface ChatConversationDetails
  extends ChatConversationSummary {
  messages: StoredChatMessage[];
}



export type ChatFeedbackRating =
  | "UP"
  | "DOWN";


export interface ChatFeedback {
  id: number;
  messageId: number;
  conversationId: string;
  rating: ChatFeedbackRating;
  comment: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}


async function parseApiResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  const contentType =
    response.headers.get("content-type") ?? "";

  let payload: any = null;

  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    const text = await response.text();
    payload = text || null;
  }

  if (!response.ok) {
    const detail =
      typeof payload === "object"
      && payload !== null
      && "detail" in payload
        ? String(payload.detail)
        : (
          typeof payload === "string"
            ? payload
            : fallbackMessage
        );

    throw new Error(
      detail || fallbackMessage,
    );
  }

  return payload as T;
}


async function ensureSuccess(
  response: Response,
  fallbackMessage: string,
): Promise<void> {
  if (response.ok) {
    return;
  }

  await parseApiResponse(
    response,
    fallbackMessage,
  );
}


export async function askAI(
  message: string,
  history: ChatHistoryMessage[] = [],
  conversationId: string | null = null,
  useReasoningModel = false,
  signal?: AbortSignal,
): Promise<AIResponse> {
  const response = await fetch(
    `${API_URL}/chat/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        conversationId,
        history,
        useReasoningModel,
      }),
      signal,
    },
  );

  const result =
    await parseApiResponse<AIResponse>(
      response,
      "Unable to contact Rudrix.",
    );

  return {
    ...result,
    sources:
      Array.isArray(result.sources)
        ? result.sources
        : [],
  };
}


export async function getKnowledgeDocument(
  documentId: number,
): Promise<KnowledgeDocumentDetails> {
  if (
    !Number.isInteger(documentId)
    || documentId <= 0
  ) {
    throw new Error(
      `Invalid knowledge document ID: ${documentId}`,
    );
  }

  const response = await fetch(
    `${API_URL}/knowledge/documents/${documentId}`,
  );

  return parseApiResponse<KnowledgeDocumentDetails>(
    response,
    "Unable to load the knowledge document.",
  );
}


export async function getChatConversations(
  limit = 50,
): Promise<ChatConversationSummary[]> {
  const safeLimit = Math.max(
    1,
    Math.min(
      Math.trunc(limit),
      100,
    ),
  );

  const response = await fetch(
    `${API_URL}/chat-history/?limit=${safeLimit}`,
  );

  return parseApiResponse<
    ChatConversationSummary[]
  >(
    response,
    "Unable to load chat history.",
  );
}


export async function getChatConversation(
  conversationId: string,
): Promise<ChatConversationDetails> {
  const normalizedId =
    conversationId.trim();

  if (!normalizedId) {
    throw new Error(
      "Conversation ID is required.",
    );
  }

  const response = await fetch(
    `${API_URL}/chat-history/${encodeURIComponent(normalizedId)}`,
  );

  return parseApiResponse<
    ChatConversationDetails
  >(
    response,
    "Unable to load the conversation.",
  );
}



export async function regenerateChatResponse(
  conversationId: string,
  useReasoningModel = false,
  signal?: AbortSignal,
): Promise<AIResponse> {
  const normalizedId =
    conversationId.trim();

  if (!normalizedId) {
    throw new Error(
      "Conversation ID is required.",
    );
  }

  const response = await fetch(
    `${API_URL}/chat-history/${encodeURIComponent(normalizedId)}/regenerate`,
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        useReasoningModel,
      }),
      signal,
    },
  );

  const result =
    await parseApiResponse<AIResponse>(
      response,
      "Unable to regenerate the response.",
    );

  return {
    ...result,
    sources:
      Array.isArray(
        result.sources,
      )
        ? result.sources
        : [],
  };
}


export async function generateChatConversationTitle(
  conversationId: string,
): Promise<ChatConversationSummary> {
  const normalizedId =
    conversationId.trim();

  if (!normalizedId) {
    throw new Error(
      "Conversation ID is required.",
    );
  }

  const response = await fetch(
    `${API_URL}/chat-history/${encodeURIComponent(normalizedId)}/generate-title`,
    {
      method: "POST",
    },
  );

  return parseApiResponse<
    ChatConversationSummary
  >(
    response,
    "Unable to generate the conversation title.",
  );
}


export async function renameChatConversation(
  conversationId: string,
  title: string,
): Promise<ChatConversationSummary> {
  const normalizedId =
    conversationId.trim();

  const normalizedTitle =
    title.trim().replace(/\s+/g, " ");

  if (!normalizedId) {
    throw new Error(
      "Conversation ID is required.",
    );
  }

  if (!normalizedTitle) {
    throw new Error(
      "Conversation title cannot be empty.",
    );
  }

  if (normalizedTitle.length > 60) {
    throw new Error(
      "Conversation title cannot exceed 60 characters.",
    );
  }

  const response = await fetch(
    `${API_URL}/chat-history/${encodeURIComponent(normalizedId)}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: normalizedTitle,
      }),
    },
  );

  return parseApiResponse<
    ChatConversationSummary
  >(
    response,
    "Unable to rename the conversation.",
  );
}


export async function deleteChatConversation(
  conversationId: string,
): Promise<void> {
  const normalizedId =
    conversationId.trim();

  if (!normalizedId) {
    throw new Error(
      "Conversation ID is required.",
    );
  }

  const response = await fetch(
    `${API_URL}/chat-history/${encodeURIComponent(normalizedId)}`,
    {
      method: "DELETE",
    },
  );

  await ensureSuccess(
    response,
    "Unable to delete the conversation.",
  );
}


export async function clearChatConversations():
Promise<void> {
  const response = await fetch(
    `${API_URL}/chat-history/`,
    {
      method: "DELETE",
    },
  );

  await ensureSuccess(
    response,
    "Unable to clear chat history.",
  );
}



export async function submitChatFeedback(
  conversationId: string,
  messageId: number,
  rating: ChatFeedbackRating,
  comment: string | null = null,
): Promise<ChatFeedback> {
  const normalizedId =
    conversationId.trim();

  if (!normalizedId) {
    throw new Error(
      "Conversation ID is required.",
    );
  }

  if (
    !Number.isInteger(messageId)
    || messageId <= 0
  ) {
    throw new Error(
      "A valid chat message ID is required.",
    );
  }

  const normalizedComment =
    comment?.trim() || null;

  const response = await fetch(
    `${API_URL}/chat-feedback/`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        conversationId:
          normalizedId,
        messageId,
        rating,
        comment:
          normalizedComment,
      }),
    },
  );

  return parseApiResponse<
    ChatFeedback
  >(
    response,
    "Unable to save feedback.",
  );
}


export async function getConversationFeedback(
  conversationId: string,
): Promise<ChatFeedback[]> {
  const normalizedId =
    conversationId.trim();

  if (!normalizedId) {
    return [];
  }

  const response = await fetch(
    `${API_URL}/chat-feedback/conversation/${encodeURIComponent(normalizedId)}`,
  );

  const result =
    await parseApiResponse<
      ChatFeedback[]
    >(
      response,
      "Unable to load feedback.",
    );

  return Array.isArray(
    result,
  )
    ? result
    : [];
}



export async function streamAI(
  message: string,
  history: ChatHistoryMessage[] = [],
  conversationId: string | null = null,
  useReasoningModel = false,
  handlers: StreamAIHandlers = {},
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/chat/stream`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        message,
        conversationId,
        history,
        useReasoningModel,
      }),

      signal,
    },
  );

  if (!response.ok) {
    await parseApiResponse(
      response,
      "Unable to contact Rudrix.",
    );

    return;
  }

  if (!response.body) {
    throw new Error(
      "Streaming response body is unavailable.",
    );
  }

  const reader =
    response.body.getReader();

  const decoder =
    new TextDecoder();

  let buffer = "";

  const processLine = (
    rawLine: string,
  ) => {
    const line =
      rawLine.trim();

    if (!line) {
      return;
    }

    let event:
      ChatStreamEvent;

    try {
      event =
        JSON.parse(
          line,
        ) as ChatStreamEvent;
    } catch {
      return;
    }

    if (
      event.type
      === "start"
    ) {
      handlers.onStart?.(
        event.conversationId,
      );

      return;
    }

    if (
      event.type
      === "status"
    ) {
      handlers.onStatus?.(
        event.message,
      );

      return;
    }

    if (
      event.type
      === "delta"
    ) {
      handlers.onDelta?.(
        event.text,
      );

      return;
    }

    if (
      event.type
      === "done"
    ) {
      handlers.onDone?.(
        event,
      );

      return;
    }

    if (
      event.type
      === "error"
    ) {
      throw new Error(
        event.message
        || "Rudrix streaming request failed.",
      );
    }
  };

  while (true) {
    const {
      value,
      done,
    } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(
      value,
      {
        stream: true,
      },
    );

    const lines =
      buffer.split("\n");

    buffer =
      lines.pop()
      ?? "";

    for (
      const line of lines
    ) {
      processLine(
        line,
      );
    }
  }

  buffer += decoder.decode();

  if (
    buffer.trim()
  ) {
    processLine(
      buffer,
    );
  }
}