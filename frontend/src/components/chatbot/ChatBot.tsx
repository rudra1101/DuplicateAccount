import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Alert,
  Box,
  CircularProgress,
  Drawer,
} from "@mui/material";

import ChatHeader
  from "./ChatHeader";
import ChatHistoryPanel
  from "./ChatHistoryPanel";
import ChatInput
  from "./ChatInput";
import ChatMessages
  from "./ChatMessages";
import SuggestedPrompts
  from "./SuggestedPrompts";

import type {
  ChatHistoryMessage,
  ChatMessage,
} from "../../models/chat";

import {
  askAI,
  clearChatConversations,
  deleteChatConversation,
  getChatConversation,
  getChatConversations,
  renameChatConversation,
} from "../../services/aiService";

import type {
  ChatConversationSummary,
  ChatSource,
  StoredChatMessage,
} from "../../services/aiService";


interface Props {
  open: boolean;
  onClose: () => void;
}


function createMessageId(): string {
  return `${Date.now()}-${Math.random()
    .toString(36)
    .slice(2)}`;
}


function createWelcomeMessage():
ChatMessage {
  return {
    id: createMessageId(),

    role: "assistant",

    content:
      "👋 Hello! I'm Rudrix.\n\n"
      + "I can help you analyze duplicate accounts, "
      + "explain confidence scores, review scan results, "
      + "and answer IAM-related questions.",

    timestamp:
      new Date(),
  };
}


function stripStructuredSourceFooter(
  message: string,
  sources: ChatSource[],
): string {
  if (!sources.length) {
    return message;
  }

  return message
    .trim()
    .replace(
      /\n{1,3}Sources?:\s*[\s\S]*$/i,
      "",
    )
    .trim();
}


function storedMessageToChatMessage(
  message: StoredChatMessage,
): ChatMessage {
  const sources =
    Array.isArray(
      message.sources,
    )
      ? message.sources
      : [];

  return {
    id:
      `stored-${message.id}`,

    role:
      message.role === "user"
        ? "user"
        : "assistant",

    content:
      stripStructuredSourceFooter(
        message.content,
        sources,
      ),

    timestamp:
      message.createdAt
        ? new Date(
          message.createdAt,
        )
        : new Date(),
  };
}


const ChatBot = ({
  open,
  onClose,
}: Props) => {
  const [
    messages,
    setMessages,
  ] = useState<
    ChatMessage[]
  >(() => [
    createWelcomeMessage(),
  ]);

  const [
    sourcesByMessageId,
    setSourcesByMessageId,
  ] = useState<
    Record<
      string,
      ChatSource[]
    >
  >({});

  const [
    conversationId,
    setConversationId,
  ] = useState<
    string | null
  >(null);

  const [
    conversations,
    setConversations,
  ] = useState<
    ChatConversationSummary[]
  >([]);

  const [
    historyOpen,
    setHistoryOpen,
  ] = useState(false);

  const [
    historyLoading,
    setHistoryLoading,
  ] = useState(false);

  const [
    deletingConversationId,
    setDeletingConversationId,
  ] = useState<
    string | null
  >(null);

  const [
    renamingConversationId,
    setRenamingConversationId,
  ] = useState<
    string | null
  >(null);

  const [
    clearingHistory,
    setClearingHistory,
  ] = useState(false);

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    useReasoningModel,
  ] = useState(false);


  const conversationHistory =
    useMemo<
      ChatHistoryMessage[]
    >(() => {
      return messages
        .slice(1)
        .map(
          (message) => ({
            role:
              message.role,

            content:
              message.content,
          }),
        )
        .slice(-30);
    }, [messages]);


  const refreshConversations =
    useCallback(
      async (): Promise<void> => {
        try {
          const result =
            await getChatConversations(
              50,
            );

          setConversations(
            result,
          );
        } catch (
          requestError
        ) {
          console.error(
            "Unable to load chat history:",
            requestError,
          );

          setError(
            requestError
              instanceof Error
              ? requestError.message
              : "Unable to load chat history.",
          );
        }
      },
      [],
    );


  useEffect(() => {
    if (!open) {
      return;
    }

    void refreshConversations();
  }, [
    open,
    refreshConversations,
  ]);


  const resetCurrentChat =
    useCallback(() => {
      setConversationId(
        null,
      );

      setMessages([
        createWelcomeMessage(),
      ]);

      setSourcesByMessageId(
        {},
      );

      setError(
        "",
      );
    }, []);


  const startNewChat =
    useCallback(() => {
      if (
        loading
        || historyLoading
        || clearingHistory
        || renamingConversationId
      ) {
        return;
      }

      resetCurrentChat();

      setHistoryOpen(
        false,
      );
    }, [
      clearingHistory,
      historyLoading,
      loading,
      renamingConversationId,
      resetCurrentChat,
    ]);


  const openConversation =
    useCallback(
      async (
        selectedId: string,
      ): Promise<void> => {
        if (
          loading
          || historyLoading
          || clearingHistory
          || renamingConversationId
        ) {
          return;
        }

        setHistoryLoading(
          true,
        );

        setError(
          "",
        );

        try {
          const conversation =
            await getChatConversation(
              selectedId,
            );

          const restoredMessages:
            ChatMessage[] = [
              createWelcomeMessage(),
            ];

          const restoredSources:
            Record<
              string,
              ChatSource[]
            > = {};

          for (
            const storedMessage
            of conversation.messages
          ) {
            const restored =
              storedMessageToChatMessage(
                storedMessage,
              );

            restoredMessages.push(
              restored,
            );

            if (
              storedMessage.role
              === "assistant"
              && Array.isArray(
                storedMessage.sources,
              )
              && storedMessage.sources
                .length > 0
            ) {
              restoredSources[
                restored.id
              ] =
                storedMessage.sources;
            }
          }

          setConversationId(
            conversation.id,
          );

          setMessages(
            restoredMessages,
          );

          setSourcesByMessageId(
            restoredSources,
          );

          setHistoryOpen(
            false,
          );
        } catch (
          requestError
        ) {
          console.error(
            "Unable to open conversation:",
            requestError,
          );

          setError(
            requestError
              instanceof Error
              ? requestError.message
              : "Unable to open the conversation.",
          );
        } finally {
          setHistoryLoading(
            false,
          );
        }
      },
      [
        clearingHistory,
        historyLoading,
        loading,
        renamingConversationId,
      ],
    );


  const renameConversation =
    useCallback(
      async (
        selectedId: string,
        title: string,
      ): Promise<void> => {
        if (
          renamingConversationId
          || deletingConversationId
          || clearingHistory
        ) {
          return;
        }

        setRenamingConversationId(
          selectedId,
        );

        setError(
          "",
        );

        try {
          const updated =
            await renameChatConversation(
              selectedId,
              title,
            );

          setConversations(
            (previous) =>
              previous.map(
                (conversation) =>
                  conversation.id
                  === updated.id
                    ? updated
                    : conversation,
              ),
          );
        } catch (
          requestError
        ) {
          console.error(
            "Unable to rename conversation:",
            requestError,
          );

          const message =
            requestError
              instanceof Error
              ? requestError.message
              : "Unable to rename the conversation.";

          setError(
            message,
          );

          throw requestError;
        } finally {
          setRenamingConversationId(
            null,
          );
        }
      },
      [
        clearingHistory,
        deletingConversationId,
        renamingConversationId,
      ],
    );


  const removeConversation =
    useCallback(
      async (
        selectedId: string,
      ): Promise<void> => {
        if (
          deletingConversationId
          || renamingConversationId
          || loading
          || clearingHistory
        ) {
          return;
        }

        const confirmed =
          window.confirm(
            "Delete this conversation?",
          );

        if (!confirmed) {
          return;
        }

        setDeletingConversationId(
          selectedId,
        );

        setError(
          "",
        );

        try {
          await deleteChatConversation(
            selectedId,
          );

          setConversations(
            (previous) =>
              previous.filter(
                (
                  conversation,
                ) =>
                  conversation.id
                  !== selectedId,
              ),
          );

          if (
            conversationId
            === selectedId
          ) {
            resetCurrentChat();
          }
        } catch (
          requestError
        ) {
          console.error(
            "Unable to delete conversation:",
            requestError,
          );

          setError(
            requestError
              instanceof Error
              ? requestError.message
              : "Unable to delete the conversation.",
          );
        } finally {
          setDeletingConversationId(
            null,
          );
        }
      },
      [
        clearingHistory,
        conversationId,
        deletingConversationId,
        loading,
        renamingConversationId,
        resetCurrentChat,
      ],
    );


  const clearAllHistory =
    useCallback(
      async (): Promise<void> => {
        if (
          clearingHistory
          || loading
          || renamingConversationId
          || conversations.length
            === 0
        ) {
          return;
        }

        const confirmed =
          window.confirm(
            "Clear all Rudrix conversation history? "
            + "This cannot be undone.",
          );

        if (!confirmed) {
          return;
        }

        setClearingHistory(
          true,
        );

        setError(
          "",
        );

        try {
          await clearChatConversations();

          setConversations(
            [],
          );

          resetCurrentChat();

          setHistoryOpen(
            true,
          );
        } catch (
          requestError
        ) {
          console.error(
            "Unable to clear chat history:",
            requestError,
          );

          setError(
            requestError
              instanceof Error
              ? requestError.message
              : "Unable to clear chat history.",
          );
        } finally {
          setClearingHistory(
            false,
          );
        }
      },
      [
        clearingHistory,
        conversations.length,
        loading,
        renamingConversationId,
        resetCurrentChat,
      ],
    );


  const toggleHistory =
    useCallback(() => {
      if (
        loading
        || clearingHistory
        || renamingConversationId
      ) {
        return;
      }

      setHistoryOpen(
        (previous) => {
          const next =
            !previous;

          if (next) {
            void refreshConversations();
          }

          return next;
        },
      );
    }, [
      clearingHistory,
      loading,
      refreshConversations,
      renamingConversationId,
    ]);


  const sendMessage =
    useCallback(
      async (
        text: string,
      ): Promise<void> => {
        const normalizedText =
          text.trim();

        if (
          !normalizedText
          || loading
          || clearingHistory
        ) {
          return;
        }

        const historyBeforeMessage =
          conversationHistory;

        const userMessage:
          ChatMessage = {
            id:
              createMessageId(),

            role:
              "user",

            content:
              normalizedText,

            timestamp:
              new Date(),
          };

        setMessages(
          (previous) => [
            ...previous,
            userMessage,
          ],
        );

        setLoading(
          true,
        );

        setError(
          "",
        );

        try {
          const response =
            await askAI(
              normalizedText,
              historyBeforeMessage,
              conversationId,
              useReasoningModel,
            );

          setConversationId(
            response.conversationId,
          );

          const responseSources =
            Array.isArray(
              response.sources,
            )
              ? response.sources
              : [];

          const assistantMessageId =
            createMessageId();

          const assistantMessage:
            ChatMessage = {
              id:
                assistantMessageId,

              role:
                "assistant",

              content:
                stripStructuredSourceFooter(
                  response.message
                  || "No response was generated.",
                  responseSources,
                ),

              timestamp:
                new Date(),
            };

          setMessages(
            (previous) => [
              ...previous,
              assistantMessage,
            ],
          );

          if (
            responseSources.length
            > 0
          ) {
            setSourcesByMessageId(
              (previous) => ({
                ...previous,

                [assistantMessageId]:
                  responseSources,
              }),
            );
          }

          await refreshConversations();
        } catch (
          requestError
        ) {
          console.error(
            "AI assistant request failed:",
            requestError,
          );

          const message =
            requestError
              instanceof Error
              ? requestError.message
              : "Unable to reach Rudrix.";

          setError(
            message,
          );

          const errorMessage:
            ChatMessage = {
              id:
                createMessageId(),

              role:
                "assistant",

              content:
                "I could not complete that request.\n\n"
                + message,

              timestamp:
                new Date(),
            };

          setMessages(
            (previous) => [
              ...previous,
              errorMessage,
            ],
          );
        } finally {
          setLoading(
            false,
          );
        }
      },
      [
        clearingHistory,
        conversationHistory,
        conversationId,
        loading,
        refreshConversations,
        useReasoningModel,
      ],
    );


  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={
        loading
          ? undefined
          : onClose
      }
      ModalProps={{
        keepMounted: true,
      }}
      slotProps={{
        backdrop: {
          sx: {
            backgroundColor:
              "rgba(0, 0, 0, 0.18)",
          },
        },

        paper: {
          sx: {
            width: {
              xs: "100%",
              sm: "380px",
              md: "400px",
            },

            maxWidth:
              "100vw",

            top: {
              xs: 0,
              sm: "72px !important",
            },

            bottom: {
              xs: 0,
              sm: "16px !important",
            },

            height: {
              xs: "100dvh",
              sm: "auto !important",
            },

            maxHeight: {
              xs: "100dvh",
              sm: "calc(100dvh - 88px)",
            },

            right: {
              xs: 0,
              sm: "12px !important",
            },

            display:
              "flex",

            flexDirection:
              "column",

            overflow:
              "hidden",

            bgcolor:
              "background.paper",

            borderRadius: {
              xs: 0,
              sm: "14px",
            },

            boxShadow:
              "-6px 4px 22px rgba(0,0,0,0.15)",
          },
        },
      }}
    >
      <ChatHeader
        historyOpen={
          historyOpen
        }

        disabled={
          loading
          || historyLoading
          || clearingHistory
          || renamingConversationId
            !== null
        }

        onNewChat={
          startNewChat
        }

        onToggleHistory={
          toggleHistory
        }

        onClose={
          onClose
        }
      />


      {error && (
        <Alert
          severity="error"
          onClose={() =>
            setError("")
          }
          sx={{
            mx: 1.5,
            mt: 1.25,
            flexShrink: 0,
          }}
        >
          {error}
        </Alert>
      )}


      {historyOpen ? (
        <ChatHistoryPanel
          conversations={
            conversations
          }

          selectedConversationId={
            conversationId
          }

          loading={
            historyLoading
          }

          deletingConversationId={
            deletingConversationId
          }

          renamingConversationId={
            renamingConversationId
          }

          clearingHistory={
            clearingHistory
          }

          onSelect={
            openConversation
          }

          onDelete={
            removeConversation
          }

          onRename={
            renameConversation
          }

          onClearAll={
            clearAllHistory
          }
        />
      ) : (
        <>
          <SuggestedPrompts
            onSelect={
              sendMessage
            }
          />

          <ChatMessages
            messages={
              messages
            }

            sourcesByMessageId={
              sourcesByMessageId
            }
          />


          {loading && (
            <Box
              sx={{
                px: 2,
                py: 1,

                display:
                  "flex",

                alignItems:
                  "center",

                gap: 1,

                borderTop: 1,
                borderColor:
                  "divider",

                bgcolor:
                  "background.paper",

                flexShrink: 0,
              }}
            >
              <CircularProgress
                size={18}
              />

              <Box
                component="span"
                sx={{
                  fontSize: 13,
                  color:
                    "text.secondary",
                }}
              >
                Rudrix is thinking...
              </Box>
            </Box>
          )}


          <Box
            sx={{
              px: 1.5,
              py: 1.25,

              borderTop: 1,
              borderColor:
                "divider",

              bgcolor:
                "background.paper",

              flexShrink: 0,
            }}
          >
            <ChatInput
              onSend={
                sendMessage
              }

              disabled={
                loading
                || clearingHistory
              }
            />
          </Box>
        </>
      )}
    </Drawer>
  );
};


export default ChatBot;