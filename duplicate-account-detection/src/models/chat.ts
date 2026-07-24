export interface ChatMessage {
    id: number;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
}

export interface AIResponse {
    message: string;
}