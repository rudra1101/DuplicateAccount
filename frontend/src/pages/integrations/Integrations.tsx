import { type MouseEvent, useCallback, useEffect, useState } from "react";

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
  FormControl,
  IconButton,
  InputLabel,
  Menu,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import SearchIcon from "@mui/icons-material/Search";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import PageContainer from "../../components/common/PageContainer";
import ScheduleDialog from "../../components/integrations/ScheduleDialog";
import ExecutionHistoryDrawer from "../../components/integrations/ExecutionHistoryDrawer";
import ScanAccountsDrawer from "../../components/integrations/ScanAccountsDrawer";
import {
  deleteIntegration,
  getIntegrationExecutions,
  getIntegrationSchedule,
  getIntegrations,
  runIntegration,
  testIntegration,
  type Integration,
  type JobSchedule,
} from "../../services/integrationService";

const PAGE_SIZE_OPTIONS = [25, 50, 100];
const RUNNING_POLL_INTERVAL_MS = 3000;

type EnabledFilter = "all" | "enabled" | "disabled";

const Integrations = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();

  const canCreate = hasPermission("integration.create");
  const canRun = hasPermission("integration.run");
  const canSchedule = hasPermission("integration.schedule");
  const canViewHistory = hasPermission("integration.view");
  const canTest = hasPermission("integration.test");
  const canEdit = hasPermission("integration.edit");
  const canDelete = hasPermission("integration.delete");

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [schedules, setSchedules] = useState<Record<number, JobSchedule | null>>({});
  const [runningIds, setRunningIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [testingId, setTestingId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Integration | null>(null);
  const [scheduleTarget, setScheduleTarget] = useState<Integration | null>(null);
  const [historyTarget, setHistoryTarget] = useState<Integration | null>(null);
  const [selectedScanId, setSelectedScanId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"success" | "error">("success");

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [enabledFilter, setEnabledFilter] = useState<EnabledFilter>("all");
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const [menuTarget, setMenuTarget] = useState<Integration | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setPage(0);
      setSearch(searchInput.trim());
    }, 350);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const loadRunningStates = useCallback(async (items: Integration[]) => {
    const results = await Promise.all(
      items.map(async (integration) => {
        try {
          const executions = await getIntegrationExecutions(integration.id, 1);
          return {
            integrationId: integration.id,
            running: executions[0]?.status === "RUNNING",
          };
        } catch (executionError) {
          console.warn(
            `Unable to load execution state for integration ${integration.id}:`,
            executionError,
          );
          return { integrationId: integration.id, running: false };
        }
      }),
    );

    setRunningIds(
      new Set(
        results
          .filter((item) => item.running)
          .map((item) => item.integrationId),
      ),
    );
  }, []);

  const loadIntegrations = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const enabled =
        enabledFilter === "all"
          ? undefined
          : enabledFilter === "enabled";

      const data = await getIntegrations(page + 1, pageSize, search, enabled);
      setIntegrations(data.items);
      setTotal(data.total);

      const scheduleMap: Record<number, JobSchedule | null> = {};
      data.items.forEach((integration) => {
        scheduleMap[integration.id] = integration.schedule;
      });
      setSchedules(scheduleMap);

      await loadRunningStates(data.items);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load integrations.",
      );
    } finally {
      setLoading(false);
    }
  }, [enabledFilter, loadRunningStates, page, pageSize, search]);

  useEffect(() => {
    void loadIntegrations();
  }, [loadIntegrations]);

  useEffect(() => {
    if (runningIds.size === 0) return;

    const poll = async () => {
      const ids = Array.from(runningIds);
      const results = await Promise.all(
        ids.map(async (integrationId) => {
          try {
            const executions = await getIntegrationExecutions(integrationId, 1);
            return {
              integrationId,
              running: executions[0]?.status === "RUNNING",
            };
          } catch (executionError) {
            console.warn(
              `Unable to poll execution state for integration ${integrationId}:`,
              executionError,
            );
            return { integrationId, running: true };
          }
        }),
      );

      setRunningIds((current) => {
        const next = new Set(current);
        results.forEach(({ integrationId, running }) => {
          if (running) next.add(integrationId);
          else next.delete(integrationId);
        });
        return next;
      });
    };

    const timer = window.setInterval(() => {
      void poll();
    }, RUNNING_POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [runningIds]);

  const handleTest = async (integration: Integration) => {
    if (!canTest) return;
    try {
      setTestingId(integration.id);
      const result = await testIntegration(integration.id);
      setMessage(result.message);
      setMessageType(result.success ? "success" : "error");
    } catch (testError) {
      setMessage(
        testError instanceof Error
          ? testError.message
          : "Connection test failed.",
      );
      setMessageType("error");
    } finally {
      setTestingId(null);
    }
  };

  const handleRun = async (integration: Integration) => {
    if (!canRun || runningIds.has(integration.id)) return;

    setRunningIds((current) => new Set(current).add(integration.id));

    try {
      const result = await runIntegration(integration.id);
      setMessage(
        `${result.sourceFileName ?? "File"} processed successfully. `
          + `${result.accountsScanned.toLocaleString()} accounts scanned, `
          + `${result.duplicateGroups.toLocaleString()} duplicate groups found.`,
      );
      setMessageType("success");

      if (result.scanId) setSelectedScanId(result.scanId);

      if (canSchedule) {
        try {
          const updatedSchedule = await getIntegrationSchedule(integration.id);
          setSchedules((current) => ({
            ...current,
            [integration.id]: updatedSchedule,
          }));
        } catch {
          // An integration can be run without a schedule.
        }
      }
    } catch (runError) {
      setMessage(
        runError instanceof Error
          ? runError.message
          : "Integration execution failed.",
      );
      setMessageType("error");
    } finally {
      try {
        const executions = await getIntegrationExecutions(integration.id, 1);
        const stillRunning = executions[0]?.status === "RUNNING";
        setRunningIds((current) => {
          const next = new Set(current);
          if (stillRunning) next.add(integration.id);
          else next.delete(integration.id);
          return next;
        });
      } catch {
        setRunningIds((current) => {
          const next = new Set(current);
          next.delete(integration.id);
          return next;
        });
      }
    }
  };

  const confirmDelete = async () => {
    if (!canDelete || !deleteTarget) return;
    try {
      await deleteIntegration(deleteTarget.id);
      setMessage("Integration deleted successfully.");
      setMessageType("success");
      setDeleteTarget(null);

      const remainingOnPage = integrations.length - 1;
      if (remainingOnPage === 0 && page > 0) {
        setPage((current) => current - 1);
      } else {
        await loadIntegrations();
      }
    } catch (deleteError) {
      setMessage(
        deleteError instanceof Error
          ? deleteError.message
          : "Unable to delete integration.",
      );
      setMessageType("error");
      setDeleteTarget(null);
    }
  };

  const handleScheduleSaved = (
    integrationId: number,
    schedule: JobSchedule | null,
  ) => {
    setSchedules((current) => ({ ...current, [integrationId]: schedule }));
    setIntegrations((current) =>
      current.map((integration) =>
        integration.id === integrationId
          ? { ...integration, schedule }
          : integration,
      ),
    );
    setMessage(
      schedule
        ? "Schedule saved successfully."
        : "Schedule deleted successfully.",
    );
    setMessageType("success");
  };

  const openActions = (
    event: MouseEvent<HTMLElement>,
    integration: Integration,
  ) => {
    setMenuAnchor(event.currentTarget);
    setMenuTarget(integration);
  };

  const closeActions = () => {
    setMenuAnchor(null);
    setMenuTarget(null);
  };

  const runMenuAction = (
    action: (integration: Integration) => void,
  ) => {
    if (!menuTarget) return;
    const target = menuTarget;
    closeActions();
    action(target);
  };

  const formatSchedule = (schedule: JobSchedule | null | undefined) => {
    if (!schedule) return "Not scheduled";
    if (!schedule.enabled) return "Disabled";
    return schedule.name || schedule.cronExpression || "Scheduled";
  };

  const menuTargetRunning = menuTarget
    ? runningIds.has(menuTarget.id)
    : false;

  return (
    <PageContainer title="Integrations">
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 2,
          mb: 3,
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>Integrations</Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Manage, run and schedule configured account-source integrations.
          </Typography>
        </Box>

        {canCreate && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate("/integrations/new")}
          >
            Add Integration
          </Button>
        )}
      </Box>

      <Paper variant="outlined" sx={{ mb: 2, p: 2 }}>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", alignItems: "center" }}>
          <TextField
            size="small"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search integrations"
            sx={{ minWidth: { xs: "100%", sm: 320 } }}
            slotProps={{
              input: {
                startAdornment: (
                  <SearchIcon fontSize="small" sx={{ mr: 1, color: "text.secondary" }} />
                ),
              },
            }}
          />

          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Status</InputLabel>
            <Select
              label="Status"
              value={enabledFilter}
              onChange={(event) => {
                setPage(0);
                setEnabledFilter(event.target.value as EnabledFilter);
              }}
            >
              <MenuItem value="all">All statuses</MenuItem>
              <MenuItem value="enabled">Enabled</MenuItem>
              <MenuItem value="disabled">Disabled</MenuItem>
            </Select>
          </FormControl>

          <Typography variant="body2" color="text.secondary" sx={{ ml: { sm: "auto" } }}>
            {total.toLocaleString()} integration{total === 1 ? "" : "s"}
          </Typography>
        </Box>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        <TableContainer sx={{ overflowX: "auto" }}>
          <Table size="small" sx={{ minWidth: 900 }}>
            <TableHead>
              <TableRow sx={{ bgcolor: "action.hover" }}>
                <TableCell sx={{ fontWeight: 700 }}>Application / Integration</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Connector Type</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Schedule</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Description</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, width: 70 }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 8 }}>
                    <CircularProgress size={32} />
                  </TableCell>
                </TableRow>
              ) : integrations.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 8 }}>
                    <Typography fontWeight={600}>No integrations found</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      {search || enabledFilter !== "all"
                        ? "Try changing your search or filters."
                        : "No integrations are configured yet."}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                integrations.map((integration) => {
                  const schedule = schedules[integration.id];
                  const isRunning = runningIds.has(integration.id);
                  return (
                    <TableRow key={integration.id} hover>
                      <TableCell>
                        <Typography fontWeight={600}>{integration.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          ID: {integration.id}
                        </Typography>
                      </TableCell>
                      <TableCell>{integration.connectorType}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={
                            isRunning
                              ? "Running"
                              : integration.enabled
                                ? "Enabled"
                                : "Disabled"
                          }
                          color={isRunning || integration.enabled ? "success" : "default"}
                          variant={isRunning || integration.enabled ? "filled" : "outlined"}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{formatSchedule(schedule)}</Typography>
                        {schedule?.nextRunAt && schedule.enabled && (
                          <Typography variant="caption" color="text.secondary" display="block">
                            Next: {new Date(schedule.nextRunAt).toLocaleString()}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 340 }}>
                        <Typography variant="body2" noWrap title={integration.description ?? ""}>
                          {integration.description || "—"}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Actions">
                          <IconButton size="small" onClick={(event) => openActions(event, integration)}>
                            <MoreVertIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={(_, nextPage) => setPage(nextPage)}
          rowsPerPage={pageSize}
          onRowsPerPageChange={(event) => {
            setPageSize(Number(event.target.value));
            setPage(0);
          }}
          rowsPerPageOptions={PAGE_SIZE_OPTIONS}
          labelRowsPerPage="Rows per page:"
          showFirstButton
          showLastButton
        />
      </Paper>

      <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={closeActions}>
        {canRun && (
          <MenuItem
            disabled={!menuTarget?.enabled || menuTargetRunning}
            onClick={() => runMenuAction((integration) => void handleRun(integration))}
          >
            {menuTargetRunning ? "Running..." : "Run Now"}
          </MenuItem>
        )}
        {canTest && (
          <MenuItem
            disabled={testingId === menuTarget?.id}
            onClick={() => runMenuAction((integration) => void handleTest(integration))}
          >
            {testingId === menuTarget?.id ? "Testing..." : "Test Connection"}
          </MenuItem>
        )}
        {canSchedule && (
          <MenuItem onClick={() => runMenuAction(setScheduleTarget)}>Schedule</MenuItem>
        )}
        {canViewHistory && (
          <MenuItem onClick={() => runMenuAction(setHistoryTarget)}>Execution History</MenuItem>
        )}
        {canEdit && (
          <MenuItem onClick={() => runMenuAction((item) => navigate(`/integrations/${item.id}/edit`))}>
            Edit
          </MenuItem>
        )}
        {canDelete && (
          <MenuItem onClick={() => runMenuAction(setDeleteTarget)} sx={{ color: "error.main" }}>
            Delete
          </MenuItem>
        )}
      </Menu>

      {canSchedule && (
        <ScheduleDialog
          open={Boolean(scheduleTarget)}
          integration={scheduleTarget}
          onClose={() => setScheduleTarget(null)}
          onSaved={handleScheduleSaved}
        />
      )}

      {canViewHistory && (
        <ExecutionHistoryDrawer
          open={Boolean(historyTarget)}
          integration={historyTarget}
          schedule={historyTarget ? schedules[historyTarget.id] : null}
          onClose={() => setHistoryTarget(null)}
        />
      )}

      <ScanAccountsDrawer
        open={selectedScanId !== null}
        scanId={selectedScanId}
        onClose={() => setSelectedScanId(null)}
      />

      {canDelete && (
        <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
          <DialogTitle>Delete Integration</DialogTitle>
          <DialogContent>
            Are you sure you want to delete <strong>{deleteTarget?.name}</strong>?
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button color="error" variant="contained" onClick={() => void confirmDelete()}>
              Delete
            </Button>
          </DialogActions>
        </Dialog>
      )}

      <Snackbar open={Boolean(message)} autoHideDuration={5000} onClose={() => setMessage("")}>
        <Alert severity={messageType} onClose={() => setMessage("")} variant="filled">
          {message}
        </Alert>
      </Snackbar>
    </PageContainer>
  );
};

export default Integrations;
