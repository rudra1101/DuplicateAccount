import {
  useMemo,
  useState,
} from "react";

import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  InputAdornment,
  List,
  ListItemButton,
  ListItemText,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import SearchIcon
  from "@mui/icons-material/Search";
import EditOutlinedIcon
  from "@mui/icons-material/EditOutlined";
import DeleteOutlineIcon
  from "@mui/icons-material/DeleteOutline";
import DeleteSweepOutlinedIcon
  from "@mui/icons-material/DeleteSweepOutlined";
import ChatBubbleOutlineIcon
  from "@mui/icons-material/ChatBubbleOutline";

import type {
  ChatConversationSummary,
} from "../../services/aiService";


interface Props {
  conversations: ChatConversationSummary[];
  selectedConversationId: string | null;

  loading: boolean;
  deletingConversationId: string | null;
  renamingConversationId: string | null;
  clearingHistory: boolean;

  onSelect: (
    conversationId: string,
  ) => void;

  onDelete: (
    conversationId: string,
  ) => void;

  onRename: (
    conversationId: string,
    title: string,
  ) => Promise<void>;

  onClearAll: () => void;
}


function formatConversationDate(
  value: string | null,
): string {
  if (!value) {
    return "";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "";
  }

  return date.toLocaleString();
}


const ChatHistoryPanel = ({
  conversations,
  selectedConversationId,
  loading,
  deletingConversationId,
  renamingConversationId,
  clearingHistory,
  onSelect,
  onDelete,
  onRename,
  onClearAll,
}: Props) => {
  const [
    searchText,
    setSearchText,
  ] = useState("");

  const [
    renameTarget,
    setRenameTarget,
  ] = useState<
    ChatConversationSummary | null
  >(null);

  const [
    renameTitle,
    setRenameTitle,
  ] = useState("");

  const filteredConversations =
    useMemo(() => {
      const query =
        searchText
          .trim()
          .toLowerCase();

      if (!query) {
        return conversations;
      }

      return conversations.filter(
        (conversation) =>
          (
            conversation.title
            || "New Conversation"
          )
            .toLowerCase()
            .includes(query),
      );
    }, [
      conversations,
      searchText,
    ]);


  const openRenameDialog = (
    conversation:
      ChatConversationSummary,
  ) => {
    setRenameTarget(
      conversation,
    );

    setRenameTitle(
      conversation.title
      || "New Conversation",
    );
  };


  const closeRenameDialog = () => {
    if (renamingConversationId) {
      return;
    }

    setRenameTarget(
      null,
    );

    setRenameTitle(
      "",
    );
  };


  const submitRename =
    async () => {
      if (!renameTarget) {
        return;
      }

      const normalizedTitle =
        renameTitle
          .trim()
          .replace(
            /\s+/g,
            " ",
          );

      if (!normalizedTitle) {
        return;
      }

      await onRename(
        renameTarget.id,
        normalizedTitle,
      );

      setRenameTarget(
        null,
      );

      setRenameTitle(
        "",
      );
    };


  if (loading) {
    return (
      <Box
        sx={{
          flex: 1,

          display: "flex",
          alignItems: "center",
          justifyContent:
            "center",

          gap: 1,
        }}
      >
        <CircularProgress
          size={20}
        />

        <Typography
          variant="body2"
          color="text.secondary"
        >
          Loading conversations...
        </Typography>
      </Box>
    );
  }


  return (
    <>
      <Box
        sx={{
          flex: 1,
          minHeight: 0,

          display: "flex",
          flexDirection: "column",

          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            px: 2,
            pt: 1.5,
            pb: 1.25,

            borderBottom: 1,
            borderColor:
              "divider",

            bgcolor:
              "background.paper",

            flexShrink: 0,
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems:
                "center",
              justifyContent:
                "space-between",

              gap: 1,
              mb: 1.25,
            }}
          >
            <Box
              sx={{
                minWidth: 0,
              }}
            >
              <Typography
                variant="subtitle1"
                fontWeight={700}
              >
                Chat History
              </Typography>

              <Typography
                variant="caption"
                color="text.secondary"
              >
                Search, rename or
                reopen a Rudrix chat.
              </Typography>
            </Box>

            <Button
              size="small"
              color="error"
              startIcon={
                clearingHistory
                  ? (
                    <CircularProgress
                      size={14}
                      color="inherit"
                    />
                  )
                  : (
                    <DeleteSweepOutlinedIcon
                      fontSize="small"
                    />
                  )
              }
              onClick={
                onClearAll
              }
              disabled={
                clearingHistory
                || conversations
                  .length === 0
              }
              sx={{
                flexShrink: 0,
                textTransform:
                  "none",
              }}
            >
              Clear all
            </Button>
          </Box>

          <TextField
            fullWidth
            size="small"
            placeholder="Search conversations..."
            value={
              searchText
            }
            onChange={(
              event,
            ) =>
              setSearchText(
                event.target.value,
              )
            }
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment
                    position="start"
                  >
                    <SearchIcon
                      fontSize="small"
                    />
                  </InputAdornment>
                ),
              },
            }}
          />
        </Box>


        <Box
          sx={{
            flex: 1,
            minHeight: 0,

            overflowY:
              "auto",

            bgcolor:
              "background.default",
          }}
        >
          {conversations.length
            === 0 ? (
            <Box
              sx={{
                px: 2,
                py: 6,
                textAlign:
                  "center",
              }}
            >
              <ChatBubbleOutlineIcon
                sx={{
                  fontSize: 42,
                  color:
                    "text.disabled",
                  mb: 1.25,
                }}
              />

              <Typography
                variant="body2"
                fontWeight={600}
              >
                No saved chats
              </Typography>

              <Typography
                variant="caption"
                color="text.secondary"
              >
                Start a new
                conversation with
                Rudrix.
              </Typography>
            </Box>
          ) : filteredConversations
            .length === 0 ? (
            <Box
              sx={{
                px: 2,
                py: 5,
                textAlign:
                  "center",
              }}
            >
              <SearchIcon
                sx={{
                  fontSize: 38,
                  color:
                    "text.disabled",
                  mb: 1,
                }}
              />

              <Typography
                variant="body2"
                fontWeight={600}
              >
                No matching chats
              </Typography>

              <Typography
                variant="caption"
                color="text.secondary"
              >
                Try a different
                search term.
              </Typography>
            </Box>
          ) : (
            <List
              disablePadding
              sx={{
                p: 1,
              }}
            >
              {filteredConversations.map(
                (
                  conversation,
                ) => {
                  const deleting =
                    deletingConversationId
                    === conversation.id;

                  const renaming =
                    renamingConversationId
                    === conversation.id;

                  const selected =
                    selectedConversationId
                    === conversation.id;

                  const disabled =
                    deleting
                    || renaming
                    || clearingHistory;

                  return (
                    <Box
                      key={
                        conversation.id
                      }
                      sx={{
                        display:
                          "flex",

                        alignItems:
                          "center",

                        mb: 0.75,

                        borderRadius:
                          2,

                        border: 1,

                        borderColor:
                          selected
                            ? "primary.light"
                            : "divider",

                        bgcolor:
                          selected
                            ? "action.selected"
                            : "background.paper",

                        overflow:
                          "hidden",
                      }}
                    >
                      <ListItemButton
                        onClick={() =>
                          onSelect(
                            conversation.id,
                          )
                        }
                        disabled={
                          disabled
                        }
                        sx={{
                          minWidth: 0,
                          py: 1.05,
                        }}
                      >
                        <ListItemText
                          primary={
                            conversation.title
                            || "New Conversation"
                          }
                          secondary={
                            formatConversationDate(
                              conversation.updatedAt
                              ?? conversation.createdAt,
                            )
                          }
                          slotProps={{
                            primary: {
                              noWrap: true,

                              fontWeight:
                                selected
                                  ? 700
                                  : 600,

                              fontSize:
                                14,
                            },

                            secondary: {
                              noWrap: true,
                              fontSize:
                                11,
                            },
                          }}
                        />
                      </ListItemButton>


                      <Tooltip
                        title="Rename conversation"
                      >
                        <span>
                          <IconButton
                            size="small"
                            disabled={
                              disabled
                            }
                            onClick={(
                              event,
                            ) => {
                              event
                                .stopPropagation();

                              openRenameDialog(
                                conversation,
                              );
                            }}
                          >
                            {renaming
                              ? (
                                <CircularProgress
                                  size={16}
                                />
                              )
                              : (
                                <EditOutlinedIcon
                                  fontSize="small"
                                />
                              )}
                          </IconButton>
                        </span>
                      </Tooltip>


                      <Tooltip
                        title="Delete conversation"
                      >
                        <span>
                          <IconButton
                            size="small"
                            disabled={
                              disabled
                            }
                            onClick={(
                              event,
                            ) => {
                              event
                                .stopPropagation();

                              onDelete(
                                conversation.id,
                              );
                            }}
                            sx={{
                              mr: 0.5,
                            }}
                          >
                            {deleting
                              ? (
                                <CircularProgress
                                  size={16}
                                />
                              )
                              : (
                                <DeleteOutlineIcon
                                  fontSize="small"
                                />
                              )}
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Box>
                  );
                },
              )}
            </List>
          )}
        </Box>
      </Box>


      <Dialog
        open={
          renameTarget
          !== null
        }
        onClose={
          closeRenameDialog
        }
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>
          Rename conversation
        </DialogTitle>

        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            label="Conversation title"
            value={
              renameTitle
            }
            onChange={(
              event,
            ) =>
              setRenameTitle(
                event.target.value,
              )
            }
            onKeyDown={(
              event,
            ) => {
              if (
                event.key
                === "Enter"
              ) {
                event
                  .preventDefault();

                void submitRename();
              }
            }}
            inputProps={{
              maxLength: 60,
            }}
            helperText={
              `${renameTitle.length}/60`
            }
          />
        </DialogContent>

        <DialogActions>
          <Button
            onClick={
              closeRenameDialog
            }
            disabled={
              renamingConversationId
              !== null
            }
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            onClick={() =>
              void submitRename()
            }
            disabled={
              !renameTitle.trim()
              || renamingConversationId
                !== null
            }
          >
            {renamingConversationId
              ? "Saving..."
              : "Save"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};


export default ChatHistoryPanel;