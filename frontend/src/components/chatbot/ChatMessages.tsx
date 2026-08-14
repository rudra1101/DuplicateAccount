import {
  useEffect,
  useRef,
} from "react";

import {
  Box,
} from "@mui/material";

import type {
  ChatMessage,
} from "../../models/chat";

import type {
  ChatSource,
} from "../../services/aiService";

import MessageBubble
  from "./MessageBubble";

interface Props {
  messages: ChatMessage[];

  sourcesByMessageId: Record<
    string,
    ChatSource[]
  >;
}

const ChatMessages = ({
  messages,
  sourcesByMessageId,
}: Props) => {
  const scrollContainerRef =
    useRef<HTMLDivElement | null>(
      null,
    );

  useEffect(() => {
    const container =
      scrollContainerRef.current;

    if (!container) {
      return;
    }

    requestAnimationFrame(() => {
      container.scrollTo({
        top:
          container.scrollHeight,
        behavior:
          "smooth",
      });
    });
  }, [messages]);

  return (
    <Box
      ref={scrollContainerRef}
      sx={{
        flex: 1,
        minHeight: 0,

        overflowY: "auto",
        overflowX: "hidden",

        px: 1.75,
        py: 1.5,

        bgcolor: (theme) =>
          theme.palette.mode
            === "light"
            ? "#fafafa"
            : "background.default",
      }}
    >
      {messages.map(
        (msg) => (
          <MessageBubble
            key={msg.id}
            message={
              msg.content
            }
            role={
              msg.role
            }
            sources={
              sourcesByMessageId[
                msg.id
              ] ?? []
            }
          />
        ),
      )}
    </Box>
  );
};

export default ChatMessages;