import {
  useState,
} from "react";

import {
  Alert,
  Box,
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
  Typography,
  Button,
} from "@mui/material";

import DescriptionOutlinedIcon
  from "@mui/icons-material/DescriptionOutlined";

import CloseIcon
  from "@mui/icons-material/Close";

import type {
  ChatSource,
  KnowledgeDocumentDetails,
} from "../../services/aiService";

import {
  getKnowledgeDocument,
} from "../../services/aiService";


interface Props {
  message: string;
  role: "user" | "assistant";
  sources?: ChatSource[];
}


const MessageBubble = ({
  message,
  role,
  sources = [],
}: Props) => {
  const isUser =
    role === "user";

  const hasSources =
    !isUser
    && sources.length > 0;

  const [
    selectedSource,
    setSelectedSource,
  ] = useState<
    ChatSource | null
  >(null);

  const [
    document,
    setDocument,
  ] = useState<
    KnowledgeDocumentDetails | null
  >(null);

  const [
    loadingDocument,
    setLoadingDocument,
  ] = useState(false);

  const [
    documentError,
    setDocumentError,
  ] = useState("");


  const handleSourceClick =
  async (
    source: ChatSource,
  ) => {
    setSelectedSource(
      source,
    );

    setDocument(
      null,
    );

    setDocumentError(
      "",
    );

    if (
      source.documentId
      == null
    ) {
      setDocumentError(
        "This source does not have a valid document ID.",
      );

      return;
    }

    setLoadingDocument(
      true,
    );

    try {
      const result =
        await getKnowledgeDocument(
          source.documentId,
        );

      setDocument(
        result,
      );
    } catch (
      error
    ) {
      const message =
        error instanceof Error
          ? error.message
          : (
            "Unable to load the "
            + "knowledge document."
          );

      setDocumentError(
        message,
      );
    } finally {
      setLoadingDocument(
        false,
      );
    }
  };


  const handleClose =
    () => {
      setSelectedSource(
        null,
      );

      setDocument(
        null,
      );

      setDocumentError(
        "",
      );
    };


  const visibleChunks =
    document?.chunks.filter(
      (
        chunk
      ) => {
        if (
          selectedSource?.pageNumber
          == null
        ) {
          return true;
        }

        return (
          chunk.pageNumber
          === selectedSource.pageNumber
        );
      },
    ) ?? [];


  return (
    <>
      <Box
        display="flex"
        justifyContent={
          isUser
            ? "flex-end"
            : "flex-start"
        }
        mb={2}
      >
        <Paper
          sx={{
            p: 2,
            maxWidth: "80%",
            bgcolor: isUser
              ? "#1976d2"
              : "#f5f5f5",
            color: isUser
              ? "white"
              : "black",
            borderRadius: 3,
          }}
        >
          <Typography
            variant="body2"
            whiteSpace="pre-line"
          >
            {message}
          </Typography>

          {hasSources && (
            <Box
              sx={{
                mt: 1.5,
                pt: 1.25,
                borderTop: 1,
                borderColor:
                  "divider",
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  display:
                    "block",

                  mb:
                    0.75,

                  color:
                    "text.secondary",

                  fontWeight:
                    600,
                }}
              >
                Sources
              </Typography>

              <Stack
                direction="row"
                spacing={
                  0.75
                }
                useFlexGap
                flexWrap="wrap"
              >
                {sources.map(
                  (
                    source,
                    index,
                  ) => {
                    const label =
                      source.pageNumber
                        ? (
                          `${source.documentName}`
                          + ` · Page ${source.pageNumber}`
                        )
                        : source.documentName;

                    return (
                      <Chip
                        key={
                          `${source.documentId}`
                          + `-${source.pageNumber ?? "document"}`
                          + `-${index}`
                        }
                        icon={
                          <DescriptionOutlinedIcon />
                        }
                        label={
                          label
                        }
                        size="small"
                        variant="outlined"
                        clickable
                        onClick={() =>
                          handleSourceClick(
                            source,
                          )
                        }
                        sx={{
                          maxWidth:
                            "100%",

                          bgcolor:
                            "background.paper",

                          cursor:
                            "pointer",

                          "& .MuiChip-label":
                            {
                              overflow:
                                "hidden",

                              textOverflow:
                                "ellipsis",

                              whiteSpace:
                                "nowrap",
                            },
                        }}
                      />
                    );
                  },
                )}
              </Stack>
            </Box>
          )}
        </Paper>
      </Box>


      <Dialog
        open={
          Boolean(
            selectedSource,
          )
        }
        onClose={
          handleClose
        }
        fullWidth
        maxWidth="md"
      >
        <DialogTitle
          sx={{
            display:
              "flex",

            alignItems:
              "center",

            justifyContent:
              "space-between",

            gap:
              2,
          }}
        >
          <Box
            sx={{
              display:
                "flex",

              alignItems:
                "center",

              gap:
                1,
            }}
          >
            <DescriptionOutlinedIcon />

            <Typography
              variant="h6"
              component="span"
            >
              {
                selectedSource
                  ?.documentName
              }
            </Typography>
          </Box>

          <IconButton
            onClick={
              handleClose
            }
            aria-label="Close"
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        <Divider />

        <DialogContent
          sx={{
            minHeight:
              300,
          }}
        >
          {loadingDocument && (
            <Box
              sx={{
                minHeight:
                  250,

                display:
                  "flex",

                alignItems:
                  "center",

                justifyContent:
                  "center",

                flexDirection:
                  "column",

                gap:
                  2,
              }}
            >
              <CircularProgress />

              <Typography
                variant="body2"
                color="text.secondary"
              >
                Loading source...
              </Typography>
            </Box>
          )}


          {documentError && (
            <Alert
              severity="error"
            >
              {
                documentError
              }
            </Alert>
          )}


          {
            !loadingDocument
            && !documentError
            && document
            && (
              <Stack
                spacing={
                  2
                }
              >
                <Stack
                  direction="row"
                  spacing={
                    1
                  }
                  useFlexGap
                  flexWrap="wrap"
                >
                  <Chip
                    size="small"
                    label={
                      document.status
                    }
                    color={
                      document.status
                      === "COMPLETED"
                        ? "success"
                        : "default"
                    }
                    variant="outlined"
                  />

                  <Chip
                    size="small"
                    label={
                      `${document.chunkCount} `
                      + (
                        document.chunkCount
                        === 1
                          ? "chunk"
                          : "chunks"
                      )
                    }
                    variant="outlined"
                  />

                  {
                    document.contentType
                    && (
                      <Chip
                        size="small"
                        label={
                          document.contentType
                        }
                        variant="outlined"
                      />
                    )
                  }

                  {
                    selectedSource
                      ?.pageNumber
                    && (
                      <Chip
                        size="small"
                        label={
                          `Page ${
                            selectedSource
                              .pageNumber
                          }`
                        }
                        variant="outlined"
                      />
                    )
                  }
                </Stack>


                {
                  visibleChunks.length
                  === 0
                    ? (
                      <Alert
                        severity="info"
                      >
                        No preview content
                        is available for
                        this source.
                      </Alert>
                    )
                    : (
                      visibleChunks.map(
                        (
                          chunk
                        ) => (
                          <Paper
                            key={
                              chunk.id
                            }
                            variant="outlined"
                            sx={{
                              p:
                                2,

                              borderRadius:
                                2,
                            }}
                          >
                            {
                              chunk.pageNumber
                              != null
                              && (
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{
                                    display:
                                      "block",

                                    mb:
                                      1,

                                    fontWeight:
                                      600,
                                  }}
                                >
                                  Page {
                                    chunk.pageNumber
                                  }
                                </Typography>
                              )
                            }

                            <Typography
                              variant="body2"
                              whiteSpace="pre-line"
                              sx={{
                                lineHeight:
                                  1.7,
                              }}
                            >
                              {
                                chunk.content
                              }
                            </Typography>
                          </Paper>
                        ),
                      )
                    )
                }
              </Stack>
            )
          }
        </DialogContent>

        <Divider />

        <DialogActions>
          <Button
            onClick={
              handleClose
            }
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};


export default MessageBubble;