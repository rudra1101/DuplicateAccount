import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import WorkHistoryOutlinedIcon from "@mui/icons-material/WorkHistoryOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import RuleOutlinedIcon from "@mui/icons-material/RuleOutlined";

import PageContainer from "../../components/common/PageContainer";
import { getSystemStatus, type SystemStatus as SystemStatusData } from "../../services/operationsService";
import { formatDateTime } from "../../utils/dateTime";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
}

const MetricCard = ({ title, value, subtitle, icon }: MetricCardProps) => (
  <Card variant="outlined" sx={{ height: "100%", borderRadius: 3 }}>
    <CardContent>
      <Stack direction="row" justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="body2" color="text.secondary">{title}</Typography>
          <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
            {typeof value === "number" ? value.toLocaleString() : value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">{subtitle}</Typography>
          )}
        </Box>
        <Box
          sx={{
            width: 44,
            height: 44,
            borderRadius: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "action.hover",
          }}
        >
          {icon}
        </Box>
      </Stack>
    </CardContent>
  </Card>
);

function healthColor(status: string): "success" | "warning" | "error" | "default" {
  if (status === "healthy") return "success";
  if (status === "degraded") return "warning";
  if (status === "unhealthy") return "error";
  return "default";
}

const SystemStatus = () => {
  const [status, setStatus] = useState<SystemStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    try {
      refresh ? setRefreshing(true) : setLoading(true);
      setError("");
      setStatus(await getSystemStatus());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load system status.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <PageContainer title="Operations">
      <Stack spacing={3}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", sm: "flex-start" }}
          spacing={2}
        >
          <Box>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Typography variant="h5" fontWeight={700}>System Status</Typography>
              {status && (
                <Chip
                  size="small"
                  label={status.status.toUpperCase()}
                  color={healthColor(status.status)}
                  variant="outlined"
                />
              )}
            </Stack>
            <Typography color="text.secondary" sx={{ mt: 1 }}>
              Live operational view of the database, scheduler, integrations, and duplicate-processing workload.
            </Typography>
          </Box>
          <Button
            variant="outlined"
            startIcon={refreshing ? <CircularProgress size={18} /> : <RefreshIcon />}
            disabled={refreshing}
            onClick={() => void load(true)}
          >
            Refresh
          </Button>
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}

        {loading && !status ? (
          <Box sx={{ minHeight: 320, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <CircularProgress />
          </Box>
        ) : status ? (
          <>
            <Grid container spacing={2.5}>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard
                  title="Database"
                  value={status.database.backend.toUpperCase()}
                  subtitle={`Pool: ${status.database.pool.checkedOut ?? "-"}/${status.database.pool.size ?? "-"} checked out`}
                  icon={<StorageOutlinedIcon color="primary" />}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard
                  title="Scheduler Jobs"
                  value={status.scheduler.registeredJobs}
                  subtitle={status.scheduler.running ? "Scheduler running" : "Scheduler stopped"}
                  icon={<ScheduleOutlinedIcon color={status.scheduler.running ? "success" : "warning"} />}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard
                  title="Integrations"
                  value={status.application.integrations.total}
                  subtitle={`${status.application.integrations.enabled} enabled · ${status.application.integrations.disabled} disabled`}
                  icon={<HubOutlinedIcon color="primary" />}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard
                  title="Job Executions"
                  value={status.application.executions.total}
                  subtitle={`${status.application.executions.running} running · ${status.application.executions.failed} failed`}
                  icon={<WorkHistoryOutlinedIcon color="primary" />}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard
                  title="Scans"
                  value={status.application.scans}
                  icon={<AccountTreeOutlinedIcon color="primary" />}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard
                  title="Accounts"
                  value={status.application.accounts}
                  icon={<GroupsOutlinedIcon color="primary" />}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard
                  title="Duplicate Candidates"
                  value={status.application.duplicateCandidates}
                  subtitle={`${status.application.duplicateGroups.toLocaleString()} duplicate groups`}
                  icon={<RuleOutlinedIcon color="warning" />}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard
                  title="Pending Remediation"
                  value={status.application.pendingRemediation}
                  icon={<RuleOutlinedIcon color={status.application.pendingRemediation > 0 ? "warning" : "success"} />}
                />
              </Grid>
            </Grid>

            <Card variant="outlined" sx={{ borderRadius: 3 }}>
              <CardContent>
                <Stack spacing={2}>
                  <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1}>
                    <Box>
                      <Typography variant="h6" fontWeight={700}>Scheduler</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Registered background jobs and their next scheduled run.
                      </Typography>
                    </Box>
                    <Chip
                      size="small"
                      label={status.scheduler.status.toUpperCase()}
                      color={healthColor(status.scheduler.status)}
                      variant="outlined"
                    />
                  </Stack>

                  {status.scheduler.jobs.length === 0 ? (
                    <Alert severity="info">No scheduler jobs are currently registered.</Alert>
                  ) : (
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Job</TableCell>
                            <TableCell>Identifier</TableCell>
                            <TableCell>Next Run</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {status.scheduler.jobs.map((job) => (
                            <TableRow key={job.id} hover>
                              <TableCell>{job.name}</TableCell>
                              <TableCell>{job.id}</TableCell>
                              <TableCell>{formatDateTime(job.nextRunTime, "Asia/Kolkata")}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </Stack>
              </CardContent>
            </Card>

            <Typography variant="caption" color="text.secondary">
              Snapshot generated {formatDateTime(status.generatedAt, "Asia/Kolkata")}.
            </Typography>
          </>
        ) : null}
      </Stack>
    </PageContainer>
  );
};

export default SystemStatus;
