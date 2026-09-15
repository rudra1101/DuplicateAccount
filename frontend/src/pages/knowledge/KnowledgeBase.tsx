import { ChangeEvent, useCallback, useEffect, useRef, useState } from "react";

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
  VisibilityOutlined,
} from "@mui/icons-material";

import PageContainer from "../../components/common/PageContainer";
import {
  deleteKnowledgeDocument,
  getKnowledgeDocument,
  getKnowledgeDocuments,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  uploadKnowledgeDocument,
} from "../../services/knowledgeService";

const MAX_FILE_SIZE = 20 * 1024 * 1024;

function formatFileSize(characters: number): string {
  if (!characters) return "0 characters";
  return `${characters.toLocaleString()} characters`;
}

function getStatusColor(status: string): "success" | "warning" | "error" | "default" {
  switch (status?.toUpperCase()) {
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
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeDocument | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerLoading, setViewerLoading] = useState(false);
  const [viewerDocument, setViewerDocument] = useState<KnowledgeDocumentDetail | null>(null);

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setDocuments(await getKnowledgeDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load knowledge documents.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const handleSelectFile = () => fileInputRef.current?.click();

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setError(null);
    setSuccess(null);

    const extension = file.name.toLowerCase().split(".").pop();
    if (!["pdf", "txt", "md"].includes(extension ?? "")) {
      setError("Only PDF, TXT and Markdown files are supported.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("File size cannot exceed 20 MB.");
      return;
    }

    try {
      setUploading(true);
      await uploadKnowledgeDocument(file);
      setSuccess(`${file.name} uploaded and indexed successfully.`);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload document.");
    } finally {
      setUploading(false);
    }
  };

  const handleOpenDocument = async (document: KnowledgeDocument) => {
    try {
      setViewerOpen(true);
      setViewerLoading(true);
      setViewerDocument(null);
      setError(null);
      setViewerDocument(await getKnowledgeDocument(document.id));
    } catch (err) {
      setViewerOpen(false);
      setError(err instanceof Error ? err.message : "Failed to open knowledge document.");
    } finally {
      setViewerLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      setDeleting(true);
      setError(null);
      await deleteKnowledgeDocument(deleteTarget.id);
      setSuccess(`${deleteTarget.name} deleted successfully.`);
      setDeleteTarget(null);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete document.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <PageContainer>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
          <Box>
            <Typography variant="h4" fontWeight={700}>Knowledge Base</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Upload documents that IdentityAI can use for policy, procedure and technical knowledge.
            </Typography>
          </Box>

          <Stack direction="row" spacing={1}>
            <Tooltip title="Refresh">
              <span>
                <IconButton onClick={() => void loadDocuments()} disabled={loading}>
                  <RefreshOutlined />
                </IconButton>
              </span>
            </Tooltip>
            <Button
              variant="contained"
              startIcon={uploading ? <CircularProgress size={18} color="inherit" /> : <CloudUploadOutlined />}
              disabled={uploading}
              onClick={handleSelectFile}
            >
              {uploading ? "Uploading..." : "Upload Document"}
            </Button>
            <input ref={fileInputRef} type="file" hidden accept=".pdf,.txt,.md" onChange={handleFileChange} />
          </Stack>
        </Box>

        {error && <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>}
        {success && <Alert severity="success" onClose={() => setSuccess(null)}>{success}</Alert>}

        <Paper variant="outlined" sx={{ borderRadius: 3, overflow: "hidden" }}>
          <Box sx={{ px: 3, py: 2.5 }}>
            <Typography variant="h6" fontWeight={700}>Documents</Typography>
            <Typography variant="body2" color="text.secondary">
              {documents.length} knowledge document{documents.length === 1 ? "" : "s"}
            </Typography>
          </Box>
          <Divider />

          {loading ? (
            <Box sx={{ minHeight: 280, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <CircularProgress />
            </Box>
          ) : documents.length === 0 ? (
            <Box sx={{ minHeight: 280, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", px: 3 }}>
              <DescriptionOutlined sx={{ fontSize: 56, color: "text.disabled", mb: 2 }} />
              <Typography variant="h6" fontWeight={600}>No knowledge documents</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1, maxWidth: 420 }}>
                Upload a PDF, TXT or Markdown file to add knowledge to IdentityAI.
              </Typography>
              <Button variant="contained" startIcon={<CloudUploadOutlined />} sx={{ mt: 2.5 }} onClick={handleSelectFile}>
                Upload Document
              </Button>
            </Box>
          ) : (
            <Stack divider={<Divider />}>
              {documents.map((document) => (
                <Box
                  key={document.id}
                  onClick={() => void handleOpenDocument(document)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      void handleOpenDocument(document);
                    }
                  }}
                  sx={{
                    px: 3,
                    py: 2.5,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 3,
                    cursor: "pointer",
                    "&:hover": { bgcolor: "action.hover" },
                    "&:focus-visible": { outline: "2px solid", outlineColor: "primary.main", outlineOffset: -2 },
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2, minWidth: 0 }}>
                    <Box sx={{ width: 44, height: 44, borderRadius: 2, bgcolor: "action.selected", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <DescriptionOutlined />
                    </Box>
                    <Box sx={{ minWidth: 0 }}>
                      <Typography fontWeight={600} noWrap>{document.name}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        {document.chunkCount} chunks • {formatFileSize(document.characterCount)}
                      </Typography>
                      {document.errorMessage && (
                        <Typography variant="caption" color="error" display="block" sx={{ mt: 0.5 }}>
                          {document.errorMessage}
                        </Typography>
                      )}
                    </Box>
                  </Box>

                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Chip size="small" label={document.status} color={getStatusColor(document.status)} variant="outlined" />
                    <Tooltip title="Open document">
                      <IconButton
                        onClick={(event) => {
                          event.stopPropagation();
                          void handleOpenDocument(document);
                        }}
                      >
                        <VisibilityOutlined />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        color="error"
                        onClick={(event) => {
                          event.stopPropagation();
                          setDeleteTarget(document);
                        }}
                      >
                        <DeleteOutline />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </Box>
              ))}
            </Stack>
          )}
        </Paper>

        <Paper variant="outlined" sx={{ borderRadius: 3, p: 3 }}>
          <Typography fontWeight={700}>Supported files</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            PDF, TXT and Markdown. Maximum file size: 20 MB.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Uploaded documents are chunked and indexed into the dedicated knowledge FAISS index used by IdentityAI.
          </Typography>
        </Paper>

        <Dialog open={viewerOpen} onClose={() => !viewerLoading && setViewerOpen(false)} fullWidth maxWidth="md">
          <DialogTitle>{viewerDocument?.name ?? "Opening document..."}</DialogTitle>
          <DialogContent dividers sx={{ minHeight: 320 }}>
            {viewerLoading ? (
              <Box sx={{ minHeight: 280, display: "flex", justifyContent: "center", alignItems: "center" }}>
                <CircularProgress />
              </Box>
            ) : viewerDocument ? (
              <Stack spacing={2.5}>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1} flexWrap="wrap">
                  <Chip size="small" label={viewerDocument.status} color={getStatusColor(viewerDocument.status)} />
                  <Chip size="small" variant="outlined" label={viewerDocument.originalFilename} />
                  <Chip size="small" variant="outlined" label={`${viewerDocument.chunkCount} chunks`} />
                </Stack>
                <Typography variant="body2" color="text.secondary">
                  This view shows the text extracted and indexed by IdentityAI from the uploaded policy document.
                </Typography>
                {viewerDocument.chunks.map((chunk) => (
                  <Paper key={chunk.id} variant="outlined" sx={{ p: 2.5, borderRadius: 2 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={700}>
                      {chunk.pageNumber ? `Page ${chunk.pageNumber} • ` : ""}Section {chunk.chunkIndex + 1}
                    </Typography>
                    <Typography sx={{ mt: 1, whiteSpace: "pre-wrap", lineHeight: 1.7 }}>
                      {chunk.content}
                    </Typography>
                  </Paper>
                ))}
              </Stack>
            ) : null}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setViewerOpen(false)} disabled={viewerLoading}>Close</Button>
          </DialogActions>
        </Dialog>

        <Dialog open={Boolean(deleteTarget)} onClose={() => !deleting && setDeleteTarget(null)}>
          <DialogTitle>Delete document?</DialogTitle>
          <DialogContent>
            <DialogContentText>
              This will remove <strong>{deleteTarget?.name}</strong> from the knowledge base and remove its vectors from the knowledge index.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button disabled={deleting} onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button color="error" variant="contained" disabled={deleting} onClick={() => void handleDelete()}>
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </PageContainer>
  );
}
