import { useState } from "react";
import {
  Drawer,
  Box,
  CircularProgress,
} from "@mui/material";

import ChatHeader from "./ChatHeader";
import ChatMessages from "./ChatMessages";
import ChatInput from "./ChatInput";
import SuggestedPrompts from "./SuggestedPrompts";

import { ChatMessage } from "../../models/chat";
import { askAI } from "../../services/aiService";

interface Props {
  open: boolean;
  onClose: () => void;
}

const ChatBot = ({ open, onClose }: Props) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: "assistant",
      content:
        "👋 Hello! I'm IdentityAI Copilot.\n\nI can help you analyze duplicate accounts, explain AI confidence scores, generate reports, and answer IAM questions.",
      timestamp: new Date(),
    },
  ]);

  const [loading, setLoading] = useState(false);

  const sendMessage = async (text: string) => {
    const userMessage: ChatMessage = {
      id: Date.now(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    setLoading(true);

    const response = await askAI(text);

    const aiMessage: ChatMessage = {
      id: Date.now() + 1,
      role: "assistant",
      content: response.message,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, aiMessage]);

    setLoading(false);
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: 420,
          display: "flex",
          flexDirection: "column",
        },
      }}
    >
      <ChatHeader />

      <SuggestedPrompts onSelect={sendMessage} />

      <ChatMessages messages={messages} />

      {loading && (
        <Box
          display="flex"
          justifyContent="center"
          py={2}
        >
          <CircularProgress size={24} />
        </Box>
      )}

      <ChatInput onSend={sendMessage} />
    </Drawer>
  );
};

export default ChatBot;