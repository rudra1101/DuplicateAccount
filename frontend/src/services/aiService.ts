import type {
  AIResponse,
  ChatHistoryMessage,
} from "../models/chat";

const API_URL =
  "http://127.0.0.1:8000/api";

interface ChatRequestPayload {
  message: string;
  conversationId: string | null;
  history: ChatHistoryMessage[];
  useReasoningModel: boolean;
}

interface ApiErrorResponse {
  detail?: string;
}

async function parseResponse(
  response: Response,
): Promise<AIResponse> {
  if (response.ok) {
    return response.json() as Promise<AIResponse>;
  }

  const responseText =
    await response.text();

  let errorMessage =
    "Unable to contact the AI assistant.";

  if (responseText) {
    try {
      const parsed = JSON.parse(
        responseText,
      ) as ApiErrorResponse;

      if (parsed.detail) {
        errorMessage = parsed.detail;
      }
    } catch {
      errorMessage = responseText;
    }
  }

  throw new Error(errorMessage);
}

export async function askAI(
  message: string,
  history: ChatHistoryMessage[],
  conversationId: string | null,
  useReasoningModel = false,
): Promise<AIResponse> {
  const normalizedMessage =
    message.trim();

  if (!normalizedMessage) {
    throw new Error(
      "Chat message cannot be empty.",
    );
  }

  const payload: ChatRequestPayload = {
    message: normalizedMessage,
    conversationId,
    history: history.slice(-30),
    useReasoningModel,
  };

  const response = await fetch(
    `${API_URL}/chat/`,
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  return parseResponse(response);
}