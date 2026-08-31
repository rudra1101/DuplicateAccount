import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import { useCallback, useEffect, useState } from "react";

import {
  downloadScheduledReport,
  getScheduledReportHistory,
  type ScheduledReportRun,
} from "../../services/scheduledReportService";


function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function statusColor(status: string): "success" | "warning" | "default" {
  if (status === "SENT") return "success";
  if (status === "EMAIL_FAILED") return "warning";
  return "default";
}

export default function ScheduledReportHistoryCard() {
  const [runs, setRuns] = useState<ScheduledReportRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const loadHistory = useCallback(async (refresh = false) => {
    try {
      refresh ? setRefreshing(true) : setLoading(true);
      setError("");
      setRuns(await getScheduledReportHistory());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load scheduled report history.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadHistory();
    const refreshAfterGeneration = () => void loadHistory(true);
    window.addEventListener("scheduled-report-generated", refreshAfterGeneration);
    return () => {
      window.removeEventListener("scheduled-report-generated", refreshAfterGeneration);
    };
  }, [loadHistory]);

  const handleDownload = async (run: ScheduledReportRun) => {
    try {
      setDownloadingId(run.id);
      setError("");
      await downloadScheduledReport(run);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download scheduled report.");
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            justifyContent="space-between"
            alignItems={{ xs: "stretch", sm: "center" }}
          >
            <Box>
              <Stack direction="row" spacing={1} alignItems="center">
                <HistoryOutlinedIcon />
                <Typography variant="h6" fontWeight={700}>
                  Scheduled Report History
                </Typography>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Generated scheduled reports are retained here. Anyone with report viewing
                permission can download them, even if email delivery failed.
              </Typography>
            </Box>
            <Button
              variant="outlined"
              startIcon={refreshing ? <CircularProgress size={16} /> : <RefreshOutlinedIcon />}
              disabled={refreshing}
              onClick={() => void loadHistory(true)}
            >
              Refresh
            </Button>
          </Stack>

          {error && <Alert severity="error">{error}</Alert>}

          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
              <CircularProgress size={28} />
            </Box>
          ) : runs.length === 0 ? (
            <Alert severity="info">
              No scheduled reports have been generated yet. The next scheduled run or test
              report will appear here automatically.
            </Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Generated</TableCell>
                    <TableCell>Report</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Rows</TableCell>
                    <TableCell>Recipients</TableCell>
                    <TableCell align="right">Download</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.id} hover>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>
                        {formatDate(run.generatedAt)}
                      </TableCell>
                      <TableCell>
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight={600}>
                            {run.reportName}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {run.filename}
                          </Typography>
                          {run.testMode && <Chip label="Test" size="small" variant="outlined" />}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Tooltip title={run.errorMessage ?? ""} disableHoverListener={!run.errorMessage}>
                          <Chip
                            size="small"
                            label={run.status === "EMAIL_FAILED" ? "Email failed" : run.status}
                            color={statusColor(run.status)}
                            variant="outlined"
                          />
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right">{run.rowCount.toLocaleString()}</TableCell>
                      <TableCell>
                        {run.recipients.length > 0 ? run.recipients.join(", ") : "—"}
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          startIcon={
                            downloadingId === run.id
                              ? <CircularProgress size={14} />
                              : <DownloadOutlinedIcon />
                          }
                          disabled={downloadingId === run.id}
                          onClick={() => void handleDownload(run)}
                        >
                          CSV
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
