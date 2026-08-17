import { useState } from "react";

import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";

import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";

import CloseIcon from "@mui/icons-material/Close";

import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";

import CheckIcon from "@mui/icons-material/Check";

import ThumbUpAltOutlinedIcon from "@mui/icons-material/ThumbUpAltOutlined";

import ThumbDownAltOutlinedIcon from "@mui/icons-material/ThumbDownAltOutlined";

import ThumbUpAltIcon from "@mui/icons-material/ThumbUpAlt";

import ThumbDownAltIcon from "@mui/icons-material/ThumbDownAlt";

import ReplayOutlinedIcon from "@mui/icons-material/ReplayOutlined";

import type {
  ChatFeedback,
  ChatFeedbackRating,
  ChatSource,
  KnowledgeDocumentDetails,
} from "../../services/aiService";

import MarkdownMessage from "./MarkdownMessage";

import { getKnowledgeDocument } from "../../services/aiService";

interface Props {
  message: string;
  role: "user" | "assistant";
  sources?: ChatSource[];

  serverMessageId?: number;

  feedback?: ChatFeedback;

  feedbackSaving?: boolean;

  canRegenerate?: boolean;

  regenerating?: boolean;

  onRegenerate?: () => void;

  onFeedback?: (
    messageId: number,
    rating: ChatFeedbackRating,
    comment: string | null,
  ) => Promise<void>;
}

async function copyText(value: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(value);

    return;
  }

  const textArea = document.createElement("textarea");

  textArea.value = value;
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";

  document.body.appendChild(textArea);

  textArea.focus();
  textArea.select();

  const successful = document.execCommand("copy");

  document.body.removeChild(textArea);

  if (!successful) {
    throw new Error("Unable to copy the response.");
  }
}

const MessageBubble = ({
  message,
  role,
  sources = [],
  serverMessageId,
  feedback,
  feedbackSaving = false,
  canRegenerate = false,
  regenerating = false,
  onRegenerate,
  onFeedback,
}: Props) => {
  const isUser = role === "user";

  const hasSources = !isUser && sources.length > 0;

  const [copied, setCopied] = useState(false);

  const [copyError, setCopyError] = useState("");

  const [feedbackDialogOpen, setFeedbackDialogOpen] = useState(false);

  const [feedbackComment, setFeedbackComment] = useState("");

  const [selectedSource, setSelectedSource] = useState<ChatSource | null>(null);

  const [document, setDocument] = useState<KnowledgeDocumentDetails | null>(
    null,
  );

  const [loadingDocument, setLoadingDocument] = useState(false);

  const [documentError, setDocumentError] = useState("");

  const handleCopy = async () => {
    setCopyError("");

    try {
      await copyText(message);

      setCopied(true);

      window.setTimeout(() => {
        setCopied(false);
      }, 1600);
    } catch (error) {
      setCopyError(
        error instanceof Error ? error.message : "Unable to copy the response.",
      );
    }
  };

  const submitPositiveFeedback = async () => {
    if (!serverMessageId || !onFeedback) {
      return;
    }

    await onFeedback(serverMessageId, "UP", null);
  };

  const openNegativeFeedback = () => {
    setFeedbackComment(
      feedback?.rating === "DOWN" ? (feedback.comment ?? "") : "",
    );

    setFeedbackDialogOpen(true);
  };

  const submitNegativeFeedback = async () => {
    if (!serverMessageId || !onFeedback) {
      return;
    }

    await onFeedback(serverMessageId, "DOWN", feedbackComment.trim() || null);

    setFeedbackDialogOpen(false);
  };

  const handleSourceClick = async (source: ChatSource) => {
    setSelectedSource(source);

    setDocument(null);

    setDocumentError("");

    if (source.documentId == null) {
      setDocumentError("This source does not have a valid document ID.");

      return;
    }

    setLoadingDocument(true);

    try {
      const result = await getKnowledgeDocument(source.documentId);

      setDocument(result);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Unable to load the " + "knowledge document.";

      setDocumentError(errorMessage);
    } finally {
      setLoadingDocument(false);
    }
  };

  const handleClose = () => {
    setSelectedSource(null);

    setDocument(null);

    setDocumentError("");
  };

  const visibleChunks =
    document?.chunks.filter((chunk) => {
      if (selectedSource?.pageNumber == null) {
        return true;
      }

      return chunk.pageNumber === selectedSource.pageNumber;
    }) ?? [];

  return (
    <>
      <Box
        display="flex"
        justifyContent={isUser ? "flex-end" : "flex-start"}
        mb={2}
      >
        <Box
          sx={{
            maxWidth: "80%",
          }}
        >
          <Paper
            sx={{
              p: 2,

              bgcolor: isUser ? "primary.main" : "action.hover",

              color: isUser ? "primary.contrastText" : "text.primary",

              borderRadius: 3,
            }}
          >
            {isUser ? (
              <Typography
                variant="body2"
                whiteSpace="pre-line"
                sx={{
                  lineHeight: 1.65,
                  overflowWrap: "anywhere",
                }}
              >
                {message}
              </Typography>
            ) : (
              <MarkdownMessage content={message} />
            )}

            {hasSources && (
              <Box
                sx={{
                  mt: 1.5,
                  pt: 1.25,

                  borderTop: 1,

                  borderColor: "divider",
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    display: "block",

                    mb: 0.75,

                    color: "text.secondary",

                    fontWeight: 600,
                  }}
                >
                  Sources
                </Typography>

                <Stack
                  direction="row"
                  spacing={0.75}
                  useFlexGap
                  flexWrap="wrap"
                >
                  {sources.map((source, index) => {
                    const label = source.pageNumber
                      ? `${source.documentName}` +
                        ` · Page ${source.pageNumber}`
                      : source.documentName;

                    return (
                      <Chip
                        key={
                          `${source.documentId}` +
                          `-${source.pageNumber ?? "document"}` +
                          `-${index}`
                        }
                        icon={<DescriptionOutlinedIcon />}
                        label={label}
                        size="small"
                        variant="outlined"
                        clickable
                        onClick={() => handleSourceClick(source)}
                        sx={{
                          maxWidth: "100%",

                          bgcolor: "background.paper",

                          cursor: "pointer",

                          "& .MuiChip-label": {
                            overflow: "hidden",

                            textOverflow: "ellipsis",

                            whiteSpace: "nowrap",
                          },
                        }}
                      />
                    );
                  })}
                </Stack>
              </Box>
            )}
          </Paper>

          {!isUser && (
            <Box
              sx={{
                display: "flex",

                alignItems: "center",

                gap: 0.5,

                mt: 0.35,

                px: 0.5,
              }}
            >
              <Tooltip title={copied ? "Copied" : "Copy response"}>
                <IconButton
                  size="small"
                  onClick={() => void handleCopy()}
                  aria-label="Copy Rudrix response"
                  sx={{
                    width: 28,
                    height: 28,
                  }}
                >
                  {copied ? (
                    <CheckIcon
                      sx={{
                        fontSize: 16,
                      }}
                    />
                  ) : (
                    <ContentCopyOutlinedIcon
                      sx={{
                        fontSize: 16,
                      }}
                    />
                  )}
                </IconButton>
              </Tooltip>

              {copied && (
                <Typography variant="caption" color="text.secondary">
                  Copied
                </Typography>
              )}

              {serverMessageId && onFeedback && (
                <>
                  <Tooltip title="Helpful">
                    <span>
                      <IconButton
                        size="small"
                        disabled={feedbackSaving}
                        onClick={() => void submitPositiveFeedback()}
                        aria-label="Mark Rudrix response helpful"
                        color={
                          feedback?.rating === "UP" ? "primary" : "default"
                        }
                        sx={{
                          width: 28,
                          height: 28,
                        }}
                      >
                        {feedback?.rating === "UP" ? (
                          <ThumbUpAltIcon
                            sx={{
                              fontSize: 17,
                            }}
                          />
                        ) : (
                          <ThumbUpAltOutlinedIcon
                            sx={{
                              fontSize: 17,
                            }}
                          />
                        )}
                      </IconButton>
                    </span>
                  </Tooltip>

                  <Tooltip title="Not helpful">
                    <span>
                      <IconButton
                        size="small"
                        disabled={feedbackSaving}
                        onClick={openNegativeFeedback}
                        aria-label="Mark Rudrix response not helpful"
                        color={
                          feedback?.rating === "DOWN" ? "error" : "default"
                        }
                        sx={{
                          width: 28,
                          height: 28,
                        }}
                      >
                        {feedback?.rating === "DOWN" ? (
                          <ThumbDownAltIcon
                            sx={{
                              fontSize: 17,
                            }}
                          />
                        ) : (
                          <ThumbDownAltOutlinedIcon
                            sx={{
                              fontSize: 17,
                            }}
                          />
                        )}
                      </IconButton>
                    </span>
                  </Tooltip>

                  {feedbackSaving && (
                    <CircularProgress
                      size={14}
                      sx={{
                        mx: 0.5,
                      }}
                    />
                  )}
                </>
              )}

              {canRegenerate && (
                <Tooltip title="Regenerate response">
                  <span>
                    <IconButton
                      size="small"
                      disabled={regenerating}
                      onClick={onRegenerate}
                      aria-label="Regenerate Rudrix response"
                      sx={{
                        width: 28,
                        height: 28,
                      }}
                    >
                      {regenerating ? (
                        <CircularProgress size={15} />
                      ) : (
                        <ReplayOutlinedIcon
                          sx={{
                            fontSize: 17,
                          }}
                        />
                      )}
                    </IconButton>
                  </span>
                </Tooltip>
              )}
            </Box>
          )}

          {copyError && (
            <Alert
              severity="error"
              sx={{
                mt: 0.5,
                py: 0,
              }}
            >
              {copyError}
            </Alert>
          )}
        </Box>
      </Box>

      <Dialog
        open={feedbackDialogOpen}
        onClose={() => {
          if (!feedbackSaving) {
            setFeedbackDialogOpen(false);
          }
        }}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>What could Rudrix improve?</DialogTitle>

        <DialogContent>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              mb: 1.5,
            }}
          >
            Your comment is optional, but it helps improve future responses.
          </Typography>

          <Box
            component="textarea"
            value={feedbackComment}
            onChange={(event) => setFeedbackComment(event.target.value)}
            maxLength={1000}
            rows={4}
            sx={{
              width: "100%",
              boxSizing: "border-box",
              resize: "vertical",
              p: 1.25,
              font: "inherit",
              borderRadius: 1,
              border: 1,
              borderColor: "divider",
              outline: "none",
            }}
          />

          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: "block",
              textAlign: "right",
              mt: 0.5,
            }}
          >
            {feedbackComment.length}/1000
          </Typography>
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() => setFeedbackDialogOpen(false)}
            disabled={feedbackSaving}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            color="error"
            onClick={() => void submitNegativeFeedback()}
            disabled={feedbackSaving}
          >
            {feedbackSaving ? "Saving..." : "Submit"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(selectedSource)}
        onClose={handleClose}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle
          sx={{
            display: "flex",

            alignItems: "center",

            justifyContent: "space-between",

            gap: 2,
          }}
        >
          <Box
            sx={{
              display: "flex",

              alignItems: "center",

              gap: 1,
            }}
          >
            <DescriptionOutlinedIcon />

            <Typography variant="h6" component="span">
              {selectedSource?.documentName}
            </Typography>
          </Box>

          <IconButton onClick={handleClose} aria-label="Close">
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        <Divider />

        <DialogContent
          sx={{
            minHeight: 300,
          }}
        >
          {loadingDocument && (
            <Box
              sx={{
                minHeight: 250,

                display: "flex",

                alignItems: "center",

                justifyContent: "center",

                flexDirection: "column",

                gap: 2,
              }}
            >
              <CircularProgress />

              <Typography variant="body2" color="text.secondary">
                Loading source...
              </Typography>
            </Box>
          )}

          {documentError && <Alert severity="error">{documentError}</Alert>}

          {!loadingDocument && !documentError && document && (
            <Stack spacing={2}>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                <Chip
                  size="small"
                  label={document.status}
                  color={
                    document.status === "COMPLETED" ? "success" : "default"
                  }
                  variant="outlined"
                />

                <Chip
                  size="small"
                  label={
                    `${document.chunkCount} ` +
                    (document.chunkCount === 1 ? "chunk" : "chunks")
                  }
                  variant="outlined"
                />

                {document.contentType && (
                  <Chip
                    size="small"
                    label={document.contentType}
                    variant="outlined"
                  />
                )}

                {selectedSource?.pageNumber && (
                  <Chip
                    size="small"
                    label={`Page ${selectedSource.pageNumber}`}
                    variant="outlined"
                  />
                )}
              </Stack>

              {visibleChunks.length === 0 ? (
                <Alert severity="info">
                  No preview content is available for this source.
                </Alert>
              ) : (
                visibleChunks.map((chunk) => (
                  <Paper
                    key={chunk.id}
                    variant="outlined"
                    sx={{
                      p: 2,

                      borderRadius: 2,
                    }}
                  >
                    {chunk.pageNumber != null && (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{
                          display: "block",

                          mb: 1,

                          fontWeight: 600,
                        }}
                      >
                        Page {chunk.pageNumber}
                      </Typography>
                    )}

                    <Typography
                      variant="body2"
                      whiteSpace="pre-line"
                      sx={{
                        lineHeight: 1.7,
                      }}
                    >
                      {chunk.content}
                    </Typography>
                  </Paper>
                ))
              )}
            </Stack>
          )}
        </DialogContent>

        <Divider />

        <DialogActions>
          <Button onClick={handleClose}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default MessageBubble;
