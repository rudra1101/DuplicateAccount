import { useRef, useState } from "react";
import {
  Box,
  Paper,
  Typography,
  Button,
  LinearProgress,
  Chip,
} from "@mui/material";

import UploadFileIcon from "@mui/icons-material/UploadFile";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DescriptionIcon from "@mui/icons-material/Description";
import ScanSummary from "../../components/upload/ScanSummary";
import { useNavigate } from "react-router-dom";
import { getDashboardSummary } from "../../services/dashboardService";

import PageContainer from "../../components/common/PageContainer";

const UploadPage = () => {
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState<any>(null);

  const handleSelect = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (event.target.files?.length) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleRunScan = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      setSummary(null);

      // Simulating file upload/processing delay
      await new Promise((resolve) => setTimeout(resolve, 2000));

      const dashboard = await getDashboardSummary();
      setSummary(dashboard);
    } catch (error) {
      console.error("Scan failed:", error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <PageContainer title="Upload Accounts">

      <Paper
        sx={{
          p: 5,
          borderRadius: 4,
        }}
      >
        <Typography
          variant="h5"
          fontWeight={700}
          mb={1}
        >
          Upload Enterprise Accounts
        </Typography>

        <Typography
          color="text.secondary"
          mb={4}
        >
          Upload a CSV exported from Active Directory,
          Entra ID or any enterprise application.
        </Typography>

        <Paper
          variant="outlined"
          sx={{
            p: 6,
            borderRadius: 4,
            borderStyle: "dashed",
            textAlign: "center",
            background: "#fafafa",
          }}
        >
          <CloudUploadIcon
            sx={{
              fontSize: 80,
              color: "#1976d2",
              mb: 2,
            }}
          />

          <Typography
            variant="h6"
            fontWeight={600}
          >
            Drag & Drop CSV File
          </Typography>

          <Typography
            color="text.secondary"
            mt={1}
            mb={3}
          >
            or choose a file from your computer
          </Typography>

          <input
            hidden
            ref={inputRef}
            type="file"
            accept=".csv"
            onChange={handleSelect}
          />

          <Button
            variant="contained"
            startIcon={<UploadFileIcon />}
            onClick={() => inputRef.current?.click()}
          >
            Choose File
          </Button>

          <Typography
            mt={3}
            color="text.secondary"
          >
            Supported format: CSV
          </Typography>

          <Typography
            color="text.secondary"
          >
            Maximum size: 100 MB
          </Typography>
        </Paper>

        {selectedFile && (
          <Paper
            sx={{
              mt: 4,
              p: 2.5,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderRadius: 3,
            }}
          >
            <Box
              display="flex"
              alignItems="center"
              gap={2}
            >
              <DescriptionIcon
                color="primary"
              />

              <Box>
                <Typography fontWeight={600}>
                  {selectedFile.name}
                </Typography>

                <Typography
                  variant="body2"
                  color="text.secondary"
                >
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </Typography>
              </Box>
            </Box>

            <Chip
              label="Ready"
              color="success"
            />
          </Paper>
        )}

        <Box
          mt={5}
          display="flex"
          justifyContent="center"
        >
          <Button
            variant="contained"
            size="large"
            disabled={!selectedFile || uploading}
            onClick={handleRunScan}
            sx={{
              px: 6,
              py: 1.5,
            }}
          >
            Run AI Duplicate Scan
          </Button>
        </Box>

        {uploading && (
          <Box mt={5}>
            <LinearProgress />

            <Typography
              mt={2}
              textAlign="center"
            >
              Running duplicate detection...
            </Typography>
          </Box>
        )}

        {summary && (
          <Box mt={5}>
            <ScanSummary
              summary={summary}
              onReview={() => navigate("/duplicate-detection")}
            />
          </Box>
        )}
      </Paper>

    </PageContainer>
  );
};

export default UploadPage;
