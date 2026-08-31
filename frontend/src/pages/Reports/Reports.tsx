import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import RefreshIcon from "@mui/icons-material/Refresh";
import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import { useEffect, useMemo, useState } from "react";

import {
  downloadReport,
  getReportCatalog,
  previewReport,
  type ReportCatalog,
  type ReportFilters,
  type ReportPreview,
} from "../../services/reportService";
import ScheduledExecutiveReportCard from "./ScheduledExecutiveReportCard";
import ScheduledReportHistoryCard from "./ScheduledReportHistoryCard";


const DECISIONS = [
  "PENDING",
  "DUPLICATE",
  "NOT_DUPLICATE",
  "UNCERTAIN",
];

const STATUS_OPTIONS: Record<string, string[]> = {
  accounts: ["ACTIVE", "INACTIVE", "DISABLED", "LOCKED"],
  remediation: ["PENDING_ACTION", "ACTIONED", "IGNORED", "FAILED"],
  executions: ["RUNNING", "COMPLETED", "FAILED"],
};

function formatColumnName(value: string): string {
  return value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .replace(/^./, (character) => character.toUpperCase());
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function Reports() {
  const [catalog, setCatalog] = useState<ReportCatalog | null>(null);
  const [reportType, setReportType] = useState("");
  const [filters, setFilters] = useState<ReportFilters>({});
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        setLoadingCatalog(true);
        const result = await getReportCatalog();
        if (!active) return;
        setCatalog(result);
        if (result.reports.length > 0) {
          setReportType(result.reports[0].type);
        }
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Unable to load reports.");
      } finally {
        if (active) setLoadingCatalog(false);
      }
    };

    void load();
    return () => {
      active = false;
    };
  }, []);

  const selectedReport = useMemo(
    () => catalog?.reports.find((item) => item.type === reportType) ?? null,
    [catalog, reportType],
  );

  const availableFilters = useMemo(
    () => new Set(selectedReport?.filters ?? []),
    [selectedReport],
  );

  const updateFilter = <K extends keyof ReportFilters>(
    key: K,
    value: ReportFilters[K],
  ) => {
    setFilters((current) => ({ ...current, [key]: value }));
    setPreview(null);
  };

  const handleReportTypeChange = (value: string) => {
    setReportType(value);
    setFilters({});
    setPreview(null);
    setError("");
  };

  const payload = useMemo(
    () => ({ reportType, filters }),
    [reportType, filters],
  );

  const handlePreview = async () => {
    if (!reportType) return;
    try {
      setGenerating(true);
      setError("");
      setPreview(await previewReport(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate report.");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async () => {
    if (!reportType) return;
    try {
      setDownloading(true);
      setError("");
      await downloadReport(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download report.");
    } finally {
      setDownloading(false);
    }
  };

  const resetFilters = () => {
    setFilters({});
    setPreview(null);
    setError("");
  };

  if (loadingCatalog) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <AssessmentOutlinedIcon fontSize="large" />
          <Box>
            <Typography variant="h4" fontWeight={700}>
              Reports
            </Typography>
            <Typography color="text.secondary">
              Create filtered operational and governance reports, preview the results,
              and download the full dataset as CSV.
            </Typography>
          </Box>
        </Stack>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      <ScheduledExecutiveReportCard />
      <ScheduledReportHistoryCard />

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2.5}>
            <Box>
              <Typography variant="h6" fontWeight={700}>
                Report Builder
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Select a report type and narrow the dataset using the available filters.
              </Typography>
            </Box>

            <Divider />

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 4 }}>
                <FormControl fullWidth>
                  <InputLabel>Report Type</InputLabel>
                  <Select
                    label="Report Type"
                    value={reportType}
                    onChange={(event) => handleReportTypeChange(event.target.value)}
                  >
                    {catalog?.reports.map((report) => (
                      <MenuItem key={report.type} value={report.type}>
                        {report.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {availableFilters.has("integrationId") && (
                <Grid size={{ xs: 12, md: 4 }}>
                  <FormControl fullWidth>
                    <InputLabel>Integration</InputLabel>
                    <Select
                      label="Integration"
                      value={filters.integrationId ?? ""}
                      onChange={(event) =>
                        updateFilter(
                          "integrationId",
                          event.target.value === "" ? null : Number(event.target.value),
                        )
                      }
                    >
                      <MenuItem value="">All integrations</MenuItem>
                      {catalog?.integrations.map((integration) => (
                        <MenuItem key={integration.id} value={integration.id}>
                          {integration.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              )}

              {availableFilters.has("application") && (
                <Grid size={{ xs: 12, md: 4 }}>
                  <FormControl fullWidth>
                    <InputLabel>Application</InputLabel>
                    <Select
                      label="Application"
                      value={filters.application ?? ""}
                      onChange={(event) => updateFilter("application", event.target.value)}
                    >
                      <MenuItem value="">All applications</MenuItem>
                      {catalog?.applications.map((application) => (
                        <MenuItem key={application} value={application}>
                          {application}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              )}

              {availableFilters.has("status") && (
                <Grid size={{ xs: 12, md: 4 }}>
                  <FormControl fullWidth>
                    <InputLabel>Status</InputLabel>
                    <Select
                      label="Status"
                      value={filters.status ?? ""}
                      onChange={(event) => updateFilter("status", event.target.value)}
                    >
                      <MenuItem value="">All statuses</MenuItem>
                      {(STATUS_OPTIONS[reportType] ?? []).map((status) => (
                        <MenuItem key={status} value={status}>
                          {status.replace(/_/g, " ")}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              )}

              {availableFilters.has("decision") && (
                <Grid size={{ xs: 12, md: 4 }}>
                  <FormControl fullWidth>
                    <InputLabel>Review Decision</InputLabel>
                    <Select
                      label="Review Decision"
                      value={filters.decision ?? ""}
                      onChange={(event) => updateFilter("decision", event.target.value)}
                    >
                      <MenuItem value="">All decisions</MenuItem>
                      {DECISIONS.map((decision) => (
                        <MenuItem key={decision} value={decision}>
                          {decision.replace(/_/g, " ")}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              )}

              {availableFilters.has("minimumConfidence") && (
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Minimum Confidence"
                    value={filters.minimumConfidence ?? ""}
                    inputProps={{ min: 0, max: 100, step: 1 }}
                    onChange={(event) =>
                      updateFilter(
                        "minimumConfidence",
                        event.target.value === "" ? null : Number(event.target.value),
                      )
                    }
                  />
                </Grid>
              )}

              {availableFilters.has("reviewer") && (
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    fullWidth
                    label="Reviewer / Actioned By"
                    value={filters.reviewer ?? ""}
                    onChange={(event) => updateFilter("reviewer", event.target.value)}
                  />
                </Grid>
              )}

              {availableFilters.has("search") && (
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    fullWidth
                    label="Search"
                    placeholder="Username, email, employee ID..."
                    value={filters.search ?? ""}
                    onChange={(event) => updateFilter("search", event.target.value)}
                  />
                </Grid>
              )}

              {availableFilters.has("dateFrom") && (
                <Grid size={{ xs: 12, md: 3 }}>
                  <TextField
                    fullWidth
                    type="date"
                    label="From Date"
                    value={filters.dateFrom ?? ""}
                    slotProps={{ inputLabel: { shrink: true } }}
                    onChange={(event) => updateFilter("dateFrom", event.target.value)}
                  />
                </Grid>
              )}

              {availableFilters.has("dateTo") && (
                <Grid size={{ xs: 12, md: 3 }}>
                  <TextField
                    fullWidth
                    type="date"
                    label="To Date"
                    value={filters.dateTo ?? ""}
                    slotProps={{ inputLabel: { shrink: true } }}
                    onChange={(event) => updateFilter("dateTo", event.target.value)}
                  />
                </Grid>
              )}
            </Grid>

            {selectedReport && (
              <Alert severity="info" icon={false}>
                <strong>{selectedReport.name}:</strong> {selectedReport.description}
              </Alert>
            )}

            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <Button
                variant="contained"
                onClick={handlePreview}
                disabled={!reportType || generating}
                startIcon={generating ? <CircularProgress size={16} /> : undefined}
              >
                {generating ? "Generating..." : "Generate Preview"}
              </Button>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleDownload}
                disabled={!reportType || downloading}
              >
                {downloading ? "Downloading..." : "Download CSV"}
              </Button>
              <Button startIcon={<RefreshIcon />} onClick={resetFilters}>
                Reset Filters
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {preview && (
        <Card variant="outlined">
          <CardContent sx={{ p: 0 }}>
            <Box sx={{ px: 2.5, py: 2 }}>
              <Typography variant="h6" fontWeight={700}>
                Report Preview
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Showing {preview.rows.length.toLocaleString()} of {preview.total.toLocaleString()} matching rows.
                Preview is capped at 100 rows; CSV download contains the full filtered result.
              </Typography>
            </Box>

            <Divider />

            {preview.rows.length === 0 ? (
              <Box sx={{ py: 6, textAlign: "center" }}>
                <Typography color="text.secondary">
                  No records matched the selected filters.
                </Typography>
              </Box>
            ) : (
              <TableContainer sx={{ maxHeight: 560 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      {preview.columns.map((column) => (
                        <TableCell key={column} sx={{ fontWeight: 700, whiteSpace: "nowrap" }}>
                          {formatColumnName(column)}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {preview.rows.map((row, rowIndex) => (
                      <TableRow key={rowIndex} hover>
                        {preview.columns.map((column) => (
                          <TableCell
                            key={column}
                            sx={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                            title={formatCell(row[column])}
                          >
                            {formatCell(row[column])}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}

export default Reports;
