import {
  useEffect,
  useMemo,
  useRef,
} from "react";

import {
  Box,
} from "@mui/material";

import type {
  ChatMessage,
} from "../../models/chat";

import type {
  ChatFeedback,
  ChatFeedbackRating,
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

  serverMessageIdByLocalId:
    Record<string, number>;

  feedbackByMessageId:
    Record<number, ChatFeedback>;

  feedbackSavingMessageId:
    number | null;

  regenerating: boolean;

  onRegenerate:
    () => void;

  onFeedback: (
    messageId: number,
    rating: ChatFeedbackRating,
    comment: string | null,
  ) => Promise<void>;
}


const ChatMessages = ({
  messages,
  sourcesByMessageId,
  serverMessageIdByLocalId,
  feedbackByMessageId,
  feedbackSavingMessageId,
  regenerating,
  onRegenerate,
  onFeedback,
}: Props) => {
  const scrollContainerRef =
    useRef<
      HTMLDivElement | null
    >(null);

  const lastRegeneratableAssistantId =
    useMemo(() => {
      let lastUserIndex = -1;

      for (
        let index =
          messages.length - 1;
        index >= 1;
        index -= 1
      ) {
        if (
          messages[index].role
          === "user"
        ) {
          lastUserIndex = index;
          break;
        }
      }

      if (
        lastUserIndex < 0
      ) {
        return null;
      }

      for (
        let index =
          messages.length - 1;
        index > lastUserIndex;
        index -= 1
      ) {
        if (
          messages[index].role
          === "assistant"
        ) {
          return (
            messages[index].id
          );
        }
      }

      return null;
    }, [
      messages,
    ]);


  useEffect(() => {
    const container =
      scrollContainerRef.current;

    if (!container) {
      return;
    }

    requestAnimationFrame(
      () => {
        container.scrollTo({
          top:
            container.scrollHeight,
          behavior:
            "smooth",
        });
      },
    );
  }, [
    messages,
    regenerating,
  ]);


  return (
    <Box
      ref={
        scrollContainerRef
      }
      sx={{
        flex: 1,
        minHeight: 0,

        overflowY:
          "auto",

        overflowX:
          "hidden",

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
        (
          msg,
        ) => {
          const serverMessageId =
            serverMessageIdByLocalId[
              msg.id
            ];

          const feedback =
            serverMessageId
              ? feedbackByMessageId[
                  serverMessageId
                ]
              : undefined;

          return (
            <MessageBubble
              key={
                msg.id
              }
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
              serverMessageId={
                serverMessageId
              }
              feedback={
                feedback
              }
              feedbackSaving={
                Boolean(
                  serverMessageId
                  && feedbackSavingMessageId
                    === serverMessageId
                )
              }
              canRegenerate={
                msg.id
                === lastRegeneratableAssistantId
              }
              regenerating={
                regenerating
                && msg.id
                  === lastRegeneratableAssistantId
              }
              onRegenerate={
                onRegenerate
              }
              onFeedback={
                onFeedback
              }
            />
          );
        },
      )}
    </Box>
  );
};


export default ChatMessages;