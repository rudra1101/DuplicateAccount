import {
  ChangeEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";

import {
  CloudUploadOutlined,
  DeleteOutline,
  DescriptionOutlined,
  RefreshOutlined,
} from "@mui/icons-material";

import PageContainer from "../../components/common/PageContainer";

import {
  deleteKnowledgeDocument,
  getKnowledgeDocuments,
  KnowledgeDocument,
  uploadKnowledgeDocument,
} from "../../services/knowledgeService";


const MAX_FILE_SIZE =
  20 * 1024 * 1024;


function formatFileSize(
  characters: number
): string {
  if (!characters) {
    return "0 characters";
  }

  return `${characters.toLocaleString()} characters`;
}


function getStatusColor(
  status: string
):
  | "success"
  | "warning"
  | "error"
  | "default" {

  switch (
    status?.toUpperCase()
  ) {
    case "COMPLETED":
      return "success";

    case "PROCESSING":
      return "warning";

    case "FAILED":
      return "error";

    default:
      return "default";
  }
}


export default function KnowledgeBase() {
  const fileInputRef =
    useRef<HTMLInputElement | null>(
      null
    );

  const [
    documents,
    setDocuments,
  ] = useState<
    KnowledgeDocument[]
  >([]);

  const [
    loading,
    setLoading,
  ] = useState(
    true
  );

  const [
    uploading,
    setUploading,
  ] = useState(
    false
  );

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    success,
    setSuccess,
  ] = useState<
    string | null
  >(null);

  const [
    deleteTarget,
    setDeleteTarget,
  ] = useState<
    KnowledgeDocument | null
  >(null);

  const [
    deleting,
    setDeleting,
  ] = useState(
    false
  );


  const loadDocuments =
    useCallback(
      async () => {
        try {
          setLoading(
            true
          );

          setError(
            null
          );

          const data =
            await getKnowledgeDocuments();

          setDocuments(
            data
          );
        }
        catch (
          err
        ) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load knowledge documents."
          );
        }
        finally {
          setLoading(
            false
          );
        }
      },
      []
    );


  useEffect(
    () => {
      loadDocuments();
    },
    [
      loadDocuments,
    ]
  );


  const handleSelectFile =
    () => {
      fileInputRef.current?.click();
    };


  const handleFileChange =
    async (
      event:
        ChangeEvent<HTMLInputElement>
    ) => {

      const file =
        event.target.files?.[0];

      event.target.value =
        "";

      if (!file) {
        return;
      }

      setError(
        null
      );

      setSuccess(
        null
      );

      const extension =
        file.name
          .toLowerCase()
          .split(".")
          .pop();

      if (
        ![
          "pdf",
          "txt",
          "md",
        ].includes(
          extension ?? ""
        )
      ) {
        setError(
          "Only PDF, TXT and Markdown files are supported."
        );

        return;
      }

      if (
        file.size >
        MAX_FILE_SIZE
      ) {
        setError(
          "File size cannot exceed 20 MB."
        );

        return;
      }

      try {
        setUploading(
          true
        );

        await uploadKnowledgeDocument(
          file
        );

        setSuccess(
          `${file.name} uploaded and indexed successfully.`
        );

        await loadDocuments();
      }
      catch (
        err
      ) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to upload document."
        );
      }
      finally {
        setUploading(
          false
        );
      }
    };


  const handleDelete =
    async () => {
      if (
        !deleteTarget
      ) {
        return;
      }

      try {
        setDeleting(
          true
        );

        setError(
          null
        );

        await deleteKnowledgeDocument(
          deleteTarget.id
        );

        setSuccess(
          `${deleteTarget.name} deleted successfully.`
        );

        setDeleteTarget(
          null
        );

        await loadDocuments();
      }
      catch (
        err
      ) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to delete document."
        );
      }
      finally {
        setDeleting(
          false
        );
      }
    };


  return (
    <PageContainer>
      <Box
        sx={{
          display:
            "flex",
          flexDirection:
            "column",
          gap: 3,
        }}
      >

        <Box
          sx={{
            display:
              "flex",
            justifyContent:
              "space-between",
            alignItems:
              "center",
            gap: 2,
            flexWrap:
              "wrap",
          }}
        >
          <Box>
            <Typography
              variant="h4"
              fontWeight={700}
            >
              Knowledge Base
            </Typography>

            <Typography
              variant="body2"
              color="text.secondary"
              sx={{
                mt: 0.5,
              }}
            >
              Upload documents that
              IdentityAI can use for
              policy, procedure and
              technical knowledge.
            </Typography>
          </Box>

          <Stack
            direction="row"
            spacing={1}
          >
            <Tooltip
              title="Refresh"
            >
              <span>
                <IconButton
                  onClick={
                    loadDocuments
                  }
                  disabled={
                    loading
                  }
                >
                  <RefreshOutlined />
                </IconButton>
              </span>
            </Tooltip>

            <Button
              variant="contained"
              startIcon={
                uploading
                  ? (
                    <CircularProgress
                      size={18}
                      color="inherit"
                    />
                  )
                  : (
                    <CloudUploadOutlined />
                  )
              }
              disabled={
                uploading
              }
              onClick={
                handleSelectFile
              }
            >
              {uploading
                ? "Uploading..."
                : "Upload Document"
              }
            </Button>

            <input
              ref={
                fileInputRef
              }
              type="file"
              hidden
              accept=".pdf,.txt,.md"
              onChange={
                handleFileChange
              }
            />
          </Stack>
        </Box>


        {error && (
          <Alert
            severity="error"
            onClose={() =>
              setError(
                null
              )
            }
          >
            {error}
          </Alert>
        )}


        {success && (
          <Alert
            severity="success"
            onClose={() =>
              setSuccess(
                null
              )
            }
          >
            {success}
          </Alert>
        )}


        <Paper
          variant="outlined"
          sx={{
            borderRadius: 3,
            overflow:
              "hidden",
          }}
        >
          <Box
            sx={{
              px: 3,
              py: 2.5,
            }}
          >
            <Typography
              variant="h6"
              fontWeight={700}
            >
              Documents
            </Typography>

            <Typography
              variant="body2"
              color="text.secondary"
            >
              {
                documents.length
              } knowledge document
              {
                documents.length === 1
                  ? ""
                  : "s"
              }
            </Typography>
          </Box>

          <Divider />


          {loading ? (
            <Box
              sx={{
                minHeight: 280,
                display:
                  "flex",
                alignItems:
                  "center",
                justifyContent:
                  "center",
              }}
            >
              <CircularProgress />
            </Box>
          ) : documents.length === 0 ? (
            <Box
              sx={{
                minHeight: 280,
                display:
                  "flex",
                flexDirection:
                  "column",
                alignItems:
                  "center",
                justifyContent:
                  "center",
                textAlign:
                  "center",
                px: 3,
              }}
            >
              <DescriptionOutlined
                sx={{
                  fontSize: 56,
                  color:
                    "text.disabled",
                  mb: 2,
                }}
              />

              <Typography
                variant="h6"
                fontWeight={600}
              >
                No knowledge documents
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  mt: 1,
                  maxWidth: 420,
                }}
              >
                Upload a PDF,
                TXT or Markdown file
                to add knowledge to
                IdentityAI.
              </Typography>

              <Button
                variant="contained"
                startIcon={
                  <CloudUploadOutlined />
                }
                sx={{
                  mt: 2.5,
                }}
                onClick={
                  handleSelectFile
                }
              >
                Upload Document
              </Button>
            </Box>
          ) : (
            <Stack
              divider={
                <Divider />
              }
            >
              {
                documents.map(
                  (
                    document
                  ) => (
                    <Box
                      key={
                        document.id
                      }
                      sx={{
                        px: 3,
                        py: 2.5,
                        display:
                          "flex",
                        justifyContent:
                          "space-between",
                        alignItems:
                          "center",
                        gap: 3,

                        "&:hover": {
                          bgcolor:
                            "action.hover",
                        },
                      }}
                    >

                      <Box
                        sx={{
                          display:
                            "flex",
                          alignItems:
                            "center",
                          gap: 2,
                          minWidth: 0,
                        }}
                      >
                        <Box
                          sx={{
                            width: 44,
                            height: 44,
                            borderRadius: 2,
                            bgcolor:
                              "action.selected",
                            display:
                              "flex",
                            alignItems:
                              "center",
                            justifyContent:
                              "center",
                            flexShrink: 0,
                          }}
                        >
                          <DescriptionOutlined />
                        </Box>

                        <Box
                          sx={{
                            minWidth: 0,
                          }}
                        >
                          <Typography
                            fontWeight={600}
                            noWrap
                          >
                            {
                              document.name
                            }
                          </Typography>

                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              mt: 0.5,
                            }}
                          >
                            {
                              document.chunkCount
                            } chunks
                            {" • "}
                            {
                              formatFileSize(
                                document.characterCount
                              )
                            }
                          </Typography>

                          {
                            document.errorMessage &&
                            (
                              <Typography
                                variant="caption"
                                color="error"
                                display="block"
                                sx={{
                                  mt: 0.5,
                                }}
                              >
                                {
                                  document.errorMessage
                                }
                              </Typography>
                            )
                          }
                        </Box>
                      </Box>


                      <Stack
                        direction="row"
                        spacing={1.5}
                        alignItems="center"
                      >
                        <Chip
                          size="small"
                          label={
                            document.status
                          }
                          color={
                            getStatusColor(
                              document.status
                            )
                          }
                          variant="outlined"
                        />

                        <Tooltip
                          title="Delete"
                        >
                          <IconButton
                            color="error"
                            onClick={() =>
                              setDeleteTarget(
                                document
                              )
                            }
                          >
                            <DeleteOutline />
                          </IconButton>
                        </Tooltip>
                      </Stack>

                    </Box>
                  )
                )
              }
            </Stack>
          )}
        </Paper>


        <Paper
          variant="outlined"
          sx={{
            borderRadius: 3,
            p: 3,
          }}
        >
          <Typography
            fontWeight={700}
          >
            Supported files
          </Typography>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              mt: 1,
            }}
          >
            PDF, TXT and Markdown.
            Maximum file size:
            20 MB.
          </Typography>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              mt: 0.5,
            }}
          >
            Uploaded documents are
            chunked and indexed into
            the dedicated knowledge
            FAISS index used by
            IdentityAI.
          </Typography>
        </Paper>


        <Dialog
          open={
            Boolean(
              deleteTarget
            )
          }
          onClose={() => {
            if (
              !deleting
            ) {
              setDeleteTarget(
                null
              );
            }
          }}
        >
          <DialogTitle>
            Delete document?
          </DialogTitle>

          <DialogContent>
            <DialogContentText>
              This will remove{" "}
              <strong>
                {
                  deleteTarget?.name
                }
              </strong>{" "}
              from the knowledge base
              and remove its vectors
              from the knowledge
              index.
            </DialogContentText>
          </DialogContent>

          <DialogActions>
            <Button
              disabled={
                deleting
              }
              onClick={() =>
                setDeleteTarget(
                  null
                )
              }
            >
              Cancel
            </Button>

            <Button
              color="error"
              variant="contained"
              disabled={
                deleting
              }
              onClick={
                handleDelete
              }
            >
              {
                deleting
                  ? "Deleting..."
                  : "Delete"
              }
            </Button>
          </DialogActions>
        </Dialog>

      </Box>
    </PageContainer>
  );
}