import { ChangeEvent, DragEvent, useRef, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Chip,
  LinearProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DescriptionIcon from "@mui/icons-material/Description";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";

import { useNavigate } from "react-router-dom";

import PageContainer from "../../components/common/PageContainer";
import ScanSummary from "../../components/upload/ScanSummary";

import {
  
  getDashboardSummary,
} from "../../services/dashboardService";

const API_URL = "http://127.0.0.1:8000/api";

interface ScanSummaryData {
  accountsScanned: number;
  applications: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  highConfidence: number;
  lastScan: string | null;
}

interface UploadResult {
  status: string;
  accountsUploaded: number;
  applications: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  message: string;
}

const UploadAccounts = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [summary, setSummary] = useState<ScanSummaryData | null>(null);

  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const validateAndSetFile = (file: File) => {
    setError("");
    setSuccessMessage("");
    setSummary(null);

    const isCsv =
      file.type === "text/csv" || file.name.toLowerCase().endsWith(".csv");

    if (!isCsv) {
      setSelectedFile(null);
      setError("Only CSV files are supported.");
      return;
    }

    const maximumSize = 100 * 1024 * 1024;

    if (file.size > maximumSize) {
      setSelectedFile(null);
      setError("The maximum permitted file size is 100 MB.");
      return;
    }

    setSelectedFile(file);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    if (file) {
      validateAndSetFile(file);
    }

    // Allows selecting the same file again.
    event.target.value = "";
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);

    const file = event.dataTransfer.files?.[0];

    if (file) {
      validateAndSetFile(file);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setSummary(null);
    setError("");
    setSuccessMessage("");
  };

  const runScan = async () => {
    if (!selectedFile || uploading) {
      return;
    }

    setUploading(true);
    setError("");
    setSuccessMessage("");
    setSummary(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const uploadResponse = await fetch(`${API_URL}/upload/`, {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        const responseBody = await uploadResponse.text();

        throw new Error(
          responseBody || `Upload failed with status ${uploadResponse.status}`,
        );
      }

      const uploadResult: UploadResult = await uploadResponse.json();

      console.log("Upload result:", uploadResult);

      /*
       * The dashboard endpoint reads the latest values from
       * memory_store and returns the exact fields expected by
       * ScanSummary.
       */
      const dashboardResult = await getDashboardSummary();

      console.log("Dashboard result after scan:", dashboardResult);

      setSummary({
        accountsScanned: dashboardResult.summary.accountsScanned,

        applications: dashboardResult.summary.applications,

        duplicateGroups: dashboardResult.summary.duplicateGroups,

        duplicateAccounts: dashboardResult.summary.duplicateAccounts,

        highConfidence: dashboardResult.summary.highConfidenceMatches,

        lastScan: dashboardResult.scan?.createdAt ?? null,
      });

      setSuccessMessage(
        uploadResult.message || "Duplicate detection completed successfully.",
      );
    } catch (scanError) {
      console.error("Scan failed:", scanError);

      setError(
        scanError instanceof Error
          ? scanError.message
          : "The duplicate scan failed.",
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <PageContainer title="Upload Accounts">
      <Box mb={4}>
        <Typography variant="h5" fontWeight={700}>
          Upload Enterprise Accounts
        </Typography>

        <Typography color="text.secondary" mt={1}>
          Upload a CSV exported from Active Directory, Entra ID, Workday, SAP,
          or another enterprise application.
        </Typography>
      </Box>

      <Paper
        variant="outlined"
        sx={{
          p: {
            xs: 2,
            md: 4,
          },
          borderRadius: 4,
        }}
      >
        <Box
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          sx={{
            minHeight: 290,
            border: "2px dashed",
            borderColor: dragging ? "primary.main" : "divider",
            backgroundColor: dragging ? "action.hover" : "background.default",
            borderRadius: 4,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            textAlign: "center",
            px: 3,
            transition: "border-color 0.2s, background-color 0.2s",
          }}
        >
          <CloudUploadIcon
            sx={{
              fontSize: 72,
              color: "primary.main",
              mb: 2,
            }}
          />

          <Typography variant="h6" fontWeight={700}>
            Drag & Drop CSV File
          </Typography>

          <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
            or choose a file from your computer
          </Typography>

          <input
            ref={fileInputRef}
            hidden
            type="file"
            accept=".csv,text/csv"
            onChange={handleFileChange}
          />

          <Button
            variant="contained"
            startIcon={<DescriptionIcon />}
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            Choose File
          </Button>

          <Typography variant="body2" color="text.secondary" mt={3}>
            Supported format: CSV
          </Typography>

          <Typography variant="body2" color="text.secondary">
            Maximum size: 100 MB
          </Typography>
        </Box>

        {selectedFile && (
          <Paper
            variant="outlined"
            sx={{
              mt: 3,
              p: 2.5,
              borderRadius: 3,
            }}
          >
            <Stack
              direction={{
                xs: "column",
                sm: "row",
              }}
              spacing={2}
              justifyContent="space-between"
              alignItems={{
                xs: "flex-start",
                sm: "center",
              }}
            >
              <Stack direction="row" spacing={2} alignItems="center">
                <DescriptionIcon color="primary" />

                <Box>
                  <Typography fontWeight={700}>{selectedFile.name}</Typography>

                  <Typography variant="body2" color="text.secondary">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </Typography>
                </Box>
              </Stack>

              <Stack direction="row" spacing={1} alignItems="center">
                <Chip label="Ready" color="success" size="small" />

                <Button
                  color="error"
                  startIcon={<DeleteOutlineIcon />}
                  onClick={clearFile}
                  disabled={uploading}
                >
                  Remove
                </Button>
              </Stack>
            </Stack>
          </Paper>
        )}

        <Box
          sx={{
            mt: 4,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <Button
            variant="contained"
            size="large"
            startIcon={<PlayArrowIcon />}
            disabled={!selectedFile || uploading}
            onClick={runScan}
            sx={{
              minWidth: 270,
              py: 1.4,
            }}
          >
            {uploading ? "Scanning Accounts..." : "Run AI Duplicate Scan"}
          </Button>
        </Box>

        {uploading && (
          <Box mt={3}>
            <LinearProgress />

            <Typography
              variant="body2"
              color="text.secondary"
              textAlign="center"
              mt={1.5}
            >
              Uploading accounts and running duplicate detection. Please wait.
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 3 }}>
            {error}
          </Alert>
        )}

        {successMessage && (
          <Alert severity="success" sx={{ mt: 3 }}>
            {successMessage}
          </Alert>
        )}
      </Paper>

      {summary && (
        <ScanSummary summary={summary} onReview={() => navigate("/review")} />
      )}
    </PageContainer>
  );
};

export default UploadAccounts;
