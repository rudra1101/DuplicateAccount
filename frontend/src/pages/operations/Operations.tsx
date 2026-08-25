import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import ReplayIcon from "@mui/icons-material/Replay";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import WorkHistoryOutlinedIcon from "@mui/icons-material/WorkHistoryOutlined";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";

import PageContainer from "../../components/common/PageContainer";
import ExecutionDetailsDrawer from "../../components/operations/ExecutionDetailsDrawer";
import {
  getOperations,
  getOperationsSummary,
  retryOperation,
  type OperationExecution,
  type OperationStatus,
  type OperationSummary,
} from "../../services/operationsService";
import { getIntegrations, type Integration } from "../../services/integrationService";
import { formatDateTime } from "../../utils/dateTime";

function calculateDuration(startedAt: string | null, completedAt: string | null): string {
  if (!startedAt) return "-";
  if (!completedAt) return "Running";

  const start = new Date(startedAt);
  const end = new Date(completedAt);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "-";

  const milliseconds = Math.max(0, end.getTime() - start.getTime());
  if (milliseconds < 1000) return `${milliseconds} ms`;

  const totalSeconds = milliseconds / 1000;
  if (totalSeconds < 60) return `${totalSeconds.toFixed(2)} sec`;

  return `${Math.floor(totalSeconds / 60)} min ${Math.floor(totalSeconds % 60)} sec`;
}

function statusColor(status: string): "success" | "error" | "info" | "warning" | "default" {
  if (status === "COMPLETED") return "success";
  if (status === "FAILED") return "error";
  if (status === "RUNNING") return "info";
  if (status === "SKIPPED") return "warning";
  return "default";
}

interface SummaryCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
}

const SummaryCard = ({ title, value, icon }: SummaryCardProps) => (
  <Card variant="outlined" sx={{ height: "100%", borderRadius: 3 }}>
    <CardContent>
      <Box
        sx={{
          width: 44,
          height: 44,
          borderRadius: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "action.hover",
          mb: 2,
        }}
      >
        {icon}
      </Box>
      <Typography color="text.secondary" variant="body2">{title}</Typography>
      <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
        {value.toLocaleString()}
      </Typography>
    </CardContent>
  </Card>
);

const Operations = () => {
  const [executions, setExecutions] = useState<OperationExecution[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [summary, setSummary] = useState<OperationSummary>({ total: 0, running: 0, completed: 0, failed: 0 });
  const [status, setStatus] = useState<OperationStatus | "">("");
  const [integrationId, setIntegrationId] = useState<number | "">("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [retryingId, setRetryingId] = useState<number | null>(null);
  const [detailsTarget, setDetailsTarget] = useState<OperationExecution | null>(null);
  const [error, setError] = useState("");

  const loadOperations = useCallback(async (showInitialLoader = false) => {
    try {
      if (showInitialLoader) setLoading(true);
      else setRefreshing(true);
      setError("");

      const [summaryResult, operationsResult, integrationsResult] = await Promise.all([
        getOperationsSummary(),
        getOperations({
          status,
          integrationId: integrationId === "" ? null : integrationId,
          search: appliedSearch,
          limit: 200,
        }),
        getIntegrations(1, 100),
      ]);

      setSummary(summaryResult);
      setExecutions(operationsResult);
      setIntegrations(integrationsResult.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load operations.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [status, integrationId, appliedSearch]);

  useEffect(() => {
    void loadOperations(true);
  }, [loadOperations]);

  const handleRetry = async (execution: OperationExecution) => {
    try {
      setRetryingId(execution.executionId);
      setError("");
      await retryOperation(execution.executionId);
      await loadOperations();
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Unable to retry execution.");
    } finally {
      setRetryingId(null);
    }
  };

  const clearFilters = () => {
    setStatus("");
    setIntegrationId("");
    setSearch("");
    setAppliedSearch("");
  };

  const hasFilters = useMemo(
    () => Boolean(status || integrationId || appliedSearch),
    [status, integrationId, appliedSearch],
  );

  return (
    <PageContainer title="Operations">
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 2, mb: 4 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>Operations Center</Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Monitor manual and scheduled integration executions.
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={refreshing ? <CircularProgress size={18} /> : <RefreshIcon />}
          disabled={refreshing}
          onClick={() => void loadOperations()}
        >
          Refresh
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError("")}>{error}</Alert>}

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <SummaryCard title="Total Executions" value={summary.total} icon={<WorkHistoryOutlinedIcon color="primary" />} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <SummaryCard title="Running" value={summary.running} icon={<PlayCircleOutlineIcon color="info" />} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <SummaryCard title="Completed" value={summary.completed} icon={<CheckCircleOutlineIcon color="success" />} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <SummaryCard title="Failed" value={summary.failed} icon={<ErrorOutlineIcon color="error" />} />
        </Grid>
      </Grid>

      <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3, mb: 3 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            fullWidth
            size="small"
            label="Search"
            value={search}
            placeholder="Integration, filename, path or error"
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") setAppliedSearch(search.trim());
            }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start"><SearchIcon /></InputAdornment>
                ),
              },
            }}
          />

          <FormControl size="small" sx={{ minWidth: 170 }}>
            <InputLabel>Status</InputLabel>
            <Select
              label="Status"
              value={status}
              onChange={(event) => setStatus(event.target.value as OperationStatus | "")}
            >
              <MenuItem value="">All statuses</MenuItem>
              <MenuItem value="RUNNING">Running</MenuItem>
              <MenuItem value="COMPLETED">Completed</MenuItem>
              <MenuItem value="FAILED">Failed</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 210 }}>
            <InputLabel>Integration</InputLabel>
            <Select
              label="Integration"
              value={integrationId}
              onChange={(event) => setIntegrationId(event.target.value ? Number(event.target.value) : "")}
            >
              <MenuItem value="">All integrations</MenuItem>
              {integrations.map((integration) => (
                <MenuItem key={integration.id} value={integration.id}>{integration.name}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button variant="contained" onClick={() => setAppliedSearch(search.trim())}>Apply</Button>
          {hasFilters && <Button onClick={clearFilters}>Clear</Button>}
        </Stack>
      </Paper>

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3, overflowX: "auto" }}>
        {loading ? (
          <Box sx={{ minHeight: 350, display: "flex", justifyContent: "center", alignItems: "center" }}>
            <CircularProgress />
          </Box>
        ) : executions.length === 0 ? (
          <Box sx={{ p: 5 }}><Alert severity="info">No executions match the selected filters.</Alert></Box>
        ) : (
          <Table sx={{ minWidth: 1180 }}>
            <TableHead>
              <TableRow>
                <TableCell>Execution</TableCell>
                <TableCell>Integration</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Source File</TableCell>
                <TableCell>Started</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell align="right">Accounts</TableCell>
                <TableCell align="right">Groups</TableCell>
                <TableCell align="right">Duplicates</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {executions.map((execution) => (
                <TableRow
                  key={execution.executionId}
                  hover
                  sx={{ cursor: "pointer" }}
                  onClick={() => setDetailsTarget(execution)}
                >
                  <TableCell>
                    <Typography fontWeight={700}>#{execution.executionId}</Typography>
                    {execution.scanId && <Typography variant="caption" color="text.secondary">Scan #{execution.scanId}</Typography>}
                  </TableCell>
                  <TableCell>
                    <Typography fontWeight={600}>{execution.integrationName}</Typography>
                    <Typography variant="caption" color="text.secondary">{execution.connectorType}</Typography>
                  </TableCell>
                  <TableCell><Chip size="small" label={execution.status} color={statusColor(execution.status)} /></TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      sx={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                      title={execution.sourceFileName ?? ""}
                    >
                      {execution.sourceFileName ?? "-"}
                    </Typography>
                  </TableCell>
                  <TableCell>{formatDateTime(execution.startedAt, "Asia/Kolkata")}</TableCell>
                  <TableCell>{calculateDuration(execution.startedAt, execution.completedAt)}</TableCell>
                  <TableCell align="right">{Number(execution.accountsScanned ?? 0).toLocaleString()}</TableCell>
                  <TableCell align="right">{Number(execution.duplicateGroups ?? 0).toLocaleString()}</TableCell>
                  <TableCell align="right">{Number(execution.duplicateAccounts ?? 0).toLocaleString()}</TableCell>
                  <TableCell align="center">
                    <Stack direction="row" spacing={0.5} justifyContent="center">
                      <Tooltip title="View details">
                        <IconButton
                          color="primary"
                          onClick={(event) => {
                            event.stopPropagation();
                            setDetailsTarget(execution);
                          }}
                        >
                          <VisibilityOutlinedIcon />
                        </IconButton>
                      </Tooltip>
                      {execution.status === "FAILED" && (
                        <Tooltip title="Retry execution">
                          <span>
                            <IconButton
                              color="primary"
                              disabled={retryingId === execution.executionId}
                              onClick={(event) => {
                                event.stopPropagation();
                                void handleRetry(execution);
                              }}
                            >
                              {retryingId === execution.executionId ? <CircularProgress size={20} /> : <ReplayIcon />}
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <ExecutionDetailsDrawer
        open={Boolean(detailsTarget)}
        execution={detailsTarget}
        onClose={() => setDetailsTarget(null)}
      />
    </PageContainer>
  );
};

export default Operations;
