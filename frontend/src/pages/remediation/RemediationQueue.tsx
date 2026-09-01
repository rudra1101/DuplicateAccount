import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  Link,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import ConfirmationNumberOutlinedIcon from "@mui/icons-material/ConfirmationNumberOutlined";

import { useAuth } from "../../auth/AuthContext";
import PageContainer from "../../components/common/PageContainer";
import {
  type RemediationAction,
  type RemediationFilters,
  type RemediationItem,
  type RemediationSlaStatus,
  type RemediationStatus,
  type RemediationTarget,
  type ReviewDecisionHistoryItem,
  createBulkRemediationTickets,
  createRemediationTicket,
  getRemediationItems,
  getReviewDecisionHistory,
  ignoreBulkRemediationItems,
  syncBulkRemediationTickets,
  syncRemediationTicket,
  updateRemediationStatus,
} from "../../services/remediationService";


type PageTab = "queue" | "history";
type QueueFilter = RemediationStatus | "ALL";
type TicketPresence = "ALL" | "WITH" | "WITHOUT";
type SlaFilter = Exclude<RemediationSlaStatus, "NONE"> | "ALL";

const valueOf = (account: Record<string, unknown>, key: string): string => {
  const value = account[key];
  return value === null || value === undefined || String(value).trim() === ""
    ? "Not available"
    : String(value);
};

const accountName = (account: Record<string, unknown>, stableKey: string): string => {
  const username = valueOf(account, "username");
  return username === "Not available" ? stableKey : username;
};

const decisionLabel = (value: string): string => {
  if (value === "DUPLICATE") return "Confirmed Duplicate";
  if (value === "NOT_DUPLICATE") return "Not Duplicate";
  if (value === "REMEDIATED") return "Remediated";
  return "Uncertain";
};

const slaLabel = (status: RemediationSlaStatus): string => {
  if (status === "ON_TRACK") return "On Track";
  if (status === "WARNING") return "SLA Warning";
  if (status === "OVERDUE") return "Overdue";
  if (status === "ESCALATED") return "Escalated";
  return "Not Tracked";
};

const slaColor = (status: RemediationSlaStatus): "success" | "warning" | "error" | "default" => {
  if (status === "ON_TRACK") return "success";
  if (status === "WARNING") return "warning";
  if (status === "OVERDUE" || status === "ESCALATED") return "error";
  return "default";
};

const RemediationQueue = () => {
  const { user, hasPermission } = useAuth();
  const canViewQueue = hasPermission("remediation.view");
  const canViewHistory = hasPermission("remediation.history.view");
  const canManage = hasPermission("remediation.manage");

  const [activeTab, setActiveTab] = useState<PageTab>(canViewQueue ? "queue" : "history");
  const [statusFilter, setStatusFilter] = useState<QueueFilter>("PENDING_ACTION");
  const [applicationFilter, setApplicationFilter] = useState("");
  const [integrationFilter, setIntegrationFilter] = useState("");
  const [minConfidence, setMinConfidence] = useState("");
  const [maxConfidence, setMaxConfidence] = useState("");
  const [actionFilter, setActionFilter] = useState<RemediationAction | "ALL">("ALL");
  const [ticketStatusFilter, setTicketStatusFilter] = useState("");
  const [ticketPresence, setTicketPresence] = useState<TicketPresence>("ALL");
  const [slaFilter, setSlaFilter] = useState<SlaFilter>("ALL");
  const [appliedFilters, setAppliedFilters] = useState<RemediationFilters>({ status: "PENDING_ACTION" });

  const [items, setItems] = useState<RemediationItem[]>([]);
  const [history, setHistory] = useState<ReviewDecisionHistoryItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);

  const [ticketItem, setTicketItem] = useState<RemediationItem | null>(null);
  const [bulkTicketOpen, setBulkTicketOpen] = useState(false);
  const [ticketTarget, setTicketTarget] = useState<RemediationTarget>("ACCOUNT_2");
  const [ticketAction, setTicketAction] = useState<RemediationAction>("DISABLE");

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [queueItems, historyItems] = await Promise.all([
        canViewQueue ? getRemediationItems(appliedFilters) : Promise.resolve([]),
        canViewHistory ? getReviewDecisionHistory() : Promise.resolve([]),
      ]);
      setItems(queueItems);
      setHistory(historyItems);
      setSelectedIds(new Set());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load remediation data.");
    } finally {
      setLoading(false);
    }
  }, [appliedFilters, canViewQueue, canViewHistory]);

  useEffect(() => {
    if (activeTab === "queue" && !canViewQueue && canViewHistory) setActiveTab("history");
    if (activeTab === "history" && !canViewHistory && canViewQueue) setActiveTab("queue");
  }, [activeTab, canViewQueue, canViewHistory]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const selectedItems = useMemo(
    () => items.filter((item) => selectedIds.has(item.id)),
    [items, selectedIds],
  );
  const selectableIds = useMemo(() => items.map((item) => item.id), [items]);
  const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selectedIds.has(id));
  const someSelected = selectableIds.some((id) => selectedIds.has(id)) && !allSelected;

  const applyFilters = () => {
    const integrationId = integrationFilter.trim() ? Number(integrationFilter) : null;
    const min = minConfidence.trim() ? Number(minConfidence) : null;
    const max = maxConfidence.trim() ? Number(maxConfidence) : null;
    if (integrationId !== null && (!Number.isInteger(integrationId) || integrationId < 1)) {
      setError("Integration ID must be a positive whole number.");
      return;
    }
    if ((min !== null && (min < 0 || min > 100)) || (max !== null && (max < 0 || max > 100))) {
      setError("Confidence filters must be between 0 and 100.");
      return;
    }
    if (min !== null && max !== null && min > max) {
      setError("Minimum confidence cannot be greater than maximum confidence.");
      return;
    }
    setError("");
    setAppliedFilters({
      status: statusFilter,
      integrationId,
      application: applicationFilter,
      minConfidence: min,
      maxConfidence: max,
      remediationAction: actionFilter,
      ticketStatus: ticketStatusFilter,
      hasTicket: ticketPresence === "ALL" ? null : ticketPresence === "WITH",
      slaStatus: slaFilter,
    });
  };

  const clearFilters = () => {
    setStatusFilter("ALL");
    setApplicationFilter("");
    setIntegrationFilter("");
    setMinConfidence("");
    setMaxConfidence("");
    setActionFilter("ALL");
    setTicketStatusFilter("");
    setTicketPresence("ALL");
    setSlaFilter("ALL");
    setAppliedFilters({ status: "ALL" });
  };

  const toggleSelection = (id: number) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelectedIds(allSelected ? new Set() : new Set(selectableIds));
  };

  const setStatus = async (item: RemediationItem, status: RemediationStatus) => {
    if (!canManage) return;
    try {
      setUpdatingId(item.id);
      setError("");
      setSuccess("");
      await updateRemediationStatus(item.id, status, null, user?.fullName || user?.username || null);
      await loadData();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to update remediation item.");
    } finally {
      setUpdatingId(null);
    }
  };

  const openTicketDialog = (item: RemediationItem) => {
    setTicketItem(item);
    setTicketTarget("ACCOUNT_2");
    setTicketAction("DISABLE");
    setError("");
  };

  const createTicket = async () => {
    if (!ticketItem) return;
    try {
      setUpdatingId(ticketItem.id);
      setError("");
      await createRemediationTicket(ticketItem.id, ticketTarget, ticketAction, user?.fullName || user?.username || null);
      setTicketItem(null);
      setStatusFilter("TICKET_OPEN");
      setAppliedFilters((current) => ({ ...current, status: "TICKET_OPEN" }));
    } catch (ticketError) {
      setError(ticketError instanceof Error ? ticketError.message : "Unable to create Service Desk ticket.");
    } finally {
      setUpdatingId(null);
    }
  };

  const syncTicket = async (item: RemediationItem) => {
    try {
      setUpdatingId(item.id);
      setError("");
      await syncRemediationTicket(item.id);
      await loadData();
    } catch (syncError) {
      setError(syncError instanceof Error ? syncError.message : "Unable to synchronize ticket.");
    } finally {
      setUpdatingId(null);
    }
  };

  const runBulkTickets = async () => {
    const ids = selectedItems.filter((item) => !item.ticketId && item.status === "PENDING_ACTION").map((item) => item.id);
    if (!ids.length) {
      setError("Select at least one Pending Action item without an existing ticket.");
      return;
    }
    try {
      setBulkBusy(true);
      setError("");
      const result = await createBulkRemediationTickets(ids, ticketTarget, ticketAction, user?.fullName || user?.username || null);
      setBulkTicketOpen(false);
      setSuccess(`Bulk ticket creation finished: ${result.succeeded} succeeded, ${result.failed} failed.`);
      await loadData();
    } catch (bulkError) {
      setError(bulkError instanceof Error ? bulkError.message : "Bulk ticket creation failed.");
    } finally {
      setBulkBusy(false);
    }
  };

  const runBulkSync = async () => {
    const ids = selectedItems.filter((item) => item.ticketId && item.status === "TICKET_OPEN").map((item) => item.id);
    if (!ids.length) {
      setError("Select at least one open ticket.");
      return;
    }
    try {
      setBulkBusy(true);
      setError("");
      const result = await syncBulkRemediationTickets(ids);
      setSuccess(`Bulk ticket sync finished: ${result.succeeded} succeeded, ${result.failed} failed.`);
      await loadData();
    } catch (bulkError) {
      setError(bulkError instanceof Error ? bulkError.message : "Bulk ticket sync failed.");
    } finally {
      setBulkBusy(false);
    }
  };

  const runBulkIgnore = async () => {
    const ids = selectedItems.filter((item) => !item.ticketId).map((item) => item.id);
    if (!ids.length) {
      setError("Only remediation items without Service Desk tickets can be bulk ignored.");
      return;
    }
    try {
      setBulkBusy(true);
      setError("");
      const result = await ignoreBulkRemediationItems(ids, user?.fullName || user?.username || null);
      setSuccess(`Bulk ignore finished: ${result.succeeded} succeeded, ${result.failed} failed.`);
      await loadData();
    } catch (bulkError) {
      setError(bulkError instanceof Error ? bulkError.message : "Bulk ignore failed.");
    } finally {
      setBulkBusy(false);
    }
  };

  return (
    <PageContainer title="Remediation">
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 2, flexWrap: "wrap", mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>Duplicate Account Remediation</Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Filter, bulk-select, track SLA, and create disable/delete Service Desk tickets for reviewer-confirmed duplicate accounts.
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={loading ? <CircularProgress size={18} /> : <RefreshIcon />} onClick={loadData} disabled={loading}>Refresh</Button>
      </Box>

      <Paper variant="outlined" sx={{ borderRadius: 3, mb: 3 }}>
        <Tabs value={activeTab} onChange={(_event, value: PageTab) => setActiveTab(value)}>
          {canViewQueue && <Tab value="queue" label={`Remediation Queue (${items.length})`} />}
          {canViewHistory && <Tab value="history" label={`Decision History (${history.length})`} />}
        </Tabs>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>{success}</Alert>}

      {loading ? (
        <Box sx={{ minHeight: 300, display: "flex", alignItems: "center", justifyContent: "center" }}><CircularProgress /></Box>
      ) : activeTab === "queue" && canViewQueue ? (
        <>
          <Paper variant="outlined" sx={{ p: 2, borderRadius: 3, mb: 2 }}>
            <Stack spacing={2}>
              <Typography variant="subtitle1" fontWeight={700}>Filters</Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} useFlexGap flexWrap="wrap">
                <FormControl size="small" sx={{ minWidth: 170 }}>
                  <InputLabel>Status</InputLabel>
                  <Select value={statusFilter} label="Status" onChange={(event) => setStatusFilter(event.target.value as QueueFilter)}>
                    <MenuItem value="PENDING_ACTION">Pending Action</MenuItem><MenuItem value="TICKET_OPEN">Ticket Open</MenuItem><MenuItem value="ACTIONED">Completed</MenuItem><MenuItem value="IGNORED">Ignored</MenuItem><MenuItem value="FAILED">Failed</MenuItem><MenuItem value="ALL">All</MenuItem>
                  </Select>
                </FormControl>
                <TextField size="small" label="Application" value={applicationFilter} onChange={(event) => setApplicationFilter(event.target.value)} />
                <TextField size="small" label="Integration ID" type="number" value={integrationFilter} onChange={(event) => setIntegrationFilter(event.target.value)} sx={{ width: 140 }} />
                <TextField size="small" label="Min confidence" type="number" value={minConfidence} onChange={(event) => setMinConfidence(event.target.value)} sx={{ width: 145 }} inputProps={{ min: 0, max: 100 }} />
                <TextField size="small" label="Max confidence" type="number" value={maxConfidence} onChange={(event) => setMaxConfidence(event.target.value)} sx={{ width: 145 }} inputProps={{ min: 0, max: 100 }} />
                <FormControl size="small" sx={{ minWidth: 150 }}><InputLabel>Action</InputLabel><Select value={actionFilter} label="Action" onChange={(event) => setActionFilter(event.target.value as RemediationAction | "ALL")}><MenuItem value="ALL">All</MenuItem><MenuItem value="DISABLE">Disable</MenuItem><MenuItem value="DELETE">Delete</MenuItem></Select></FormControl>
                <TextField size="small" label="Ticket status" value={ticketStatusFilter} onChange={(event) => setTicketStatusFilter(event.target.value)} />
                <FormControl size="small" sx={{ minWidth: 155 }}><InputLabel>Ticket</InputLabel><Select value={ticketPresence} label="Ticket" onChange={(event) => setTicketPresence(event.target.value as TicketPresence)}><MenuItem value="ALL">All</MenuItem><MenuItem value="WITH">Has ticket</MenuItem><MenuItem value="WITHOUT">No ticket</MenuItem></Select></FormControl>
                <FormControl size="small" sx={{ minWidth: 165 }}><InputLabel>SLA</InputLabel><Select value={slaFilter} label="SLA" onChange={(event) => setSlaFilter(event.target.value as SlaFilter)}><MenuItem value="ALL">All SLA states</MenuItem><MenuItem value="ON_TRACK">On Track</MenuItem><MenuItem value="WARNING">Warning</MenuItem><MenuItem value="OVERDUE">Overdue</MenuItem><MenuItem value="ESCALATED">Escalated</MenuItem></Select></FormControl>
              </Stack>
              <Stack direction="row" spacing={1}><Button variant="contained" onClick={applyFilters}>Apply Filters</Button><Button variant="text" onClick={clearFilters}>Clear</Button></Stack>
            </Stack>
          </Paper>

          {canManage && selectedIds.size > 0 && (
            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 3, mb: 2 }}>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
                <Chip label={`${selectedIds.size} selected`} color="primary" variant="outlined" />
                <Button size="small" variant="contained" startIcon={<ConfirmationNumberOutlinedIcon />} onClick={() => { setTicketTarget("ACCOUNT_2"); setTicketAction("DISABLE"); setBulkTicketOpen(true); }} disabled={bulkBusy}>Create Tickets</Button>
                <Button size="small" variant="outlined" onClick={() => void runBulkSync()} disabled={bulkBusy}>Sync Tickets</Button>
                <Button size="small" color="inherit" onClick={() => void runBulkIgnore()} disabled={bulkBusy}>Ignore Selected</Button>
                <Button size="small" onClick={() => setSelectedIds(new Set())}>Clear Selection</Button>
              </Stack>
            </Paper>
          )}

          <TableContainer component={Paper} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
            <Table>
              <TableHead><TableRow>
                {canManage && <TableCell padding="checkbox"><Checkbox checked={allSelected} indeterminate={someSelected} onChange={toggleAll} /></TableCell>}
                <TableCell>Integration / Application</TableCell><TableCell>Account 1</TableCell><TableCell>Account 2</TableCell><TableCell>AI Confidence</TableCell><TableCell>SLA</TableCell><TableCell>Status / Ticket</TableCell>{canManage && <TableCell align="right">Action</TableCell>}
              </TableRow></TableHead>
              <TableBody>
                {items.length === 0 ? (
                  <TableRow><TableCell colSpan={canManage ? 8 : 6} align="center" sx={{ py: 6 }}>No remediation items match the current filters.</TableCell></TableRow>
                ) : items.map((item) => (
                  <TableRow key={item.id} hover selected={selectedIds.has(item.id)}>
                    {canManage && <TableCell padding="checkbox"><Checkbox checked={selectedIds.has(item.id)} onChange={() => toggleSelection(item.id)} /></TableCell>}
                    <TableCell><Typography fontWeight={700}>{item.integrationName ?? `#${item.integrationId}`}</Typography><Typography variant="caption" color="text.secondary">{item.application}</Typography></TableCell>
                    <TableCell><Typography fontWeight={600}>{accountName(item.account1, item.account1Key)}</Typography><Typography variant="caption" color="text.secondary">{valueOf(item.account1, "email")}</Typography></TableCell>
                    <TableCell><Typography fontWeight={600}>{accountName(item.account2, item.account2Key)}</Typography><Typography variant="caption" color="text.secondary">{valueOf(item.account2, "email")}</Typography></TableCell>
                    <TableCell>{item.confidence === null ? "Not available" : `${item.confidence}%`}</TableCell>
                    <TableCell><Stack spacing={0.5} alignItems="flex-start"><Chip size="small" label={slaLabel(item.slaStatus)} color={slaColor(item.slaStatus)} variant={item.slaStatus === "NONE" ? "outlined" : "filled"} />{item.slaDueAt && <Typography variant="caption" color="text.secondary">Due {new Date(item.slaDueAt).toLocaleString()}</Typography>}{item.slaEscalatedAt && <Typography variant="caption" color="error">Escalated {new Date(item.slaEscalatedAt).toLocaleString()}</Typography>}</Stack></TableCell>
                    <TableCell><Stack spacing={0.5} alignItems="flex-start"><Chip size="small" label={item.status.replaceAll("_", " ")} />{item.ticketId && (item.ticketUrl ? <Link href={item.ticketUrl} target="_blank" rel="noopener noreferrer" variant="caption">{item.ticketId} · {item.ticketStatus ?? "Unknown"}</Link> : <Typography variant="caption">{item.ticketId} · {item.ticketStatus ?? "Unknown"}</Typography>)}{item.remediationAction && <Typography variant="caption" color="text.secondary">{item.remediationAction} · {item.targetAccountKey}</Typography>}{item.ticketError && <Typography variant="caption" color="error">Last sync: {item.ticketError}</Typography>}</Stack></TableCell>
                    {canManage && <TableCell align="right"><Stack direction="row" spacing={1} justifyContent="flex-end">{!item.ticketId && item.status === "PENDING_ACTION" && <Button size="small" variant="contained" startIcon={<ConfirmationNumberOutlinedIcon />} disabled={updatingId === item.id} onClick={() => openTicketDialog(item)}>Create Ticket</Button>}{item.ticketId && item.status === "TICKET_OPEN" && <Button size="small" variant="outlined" disabled={updatingId === item.id} onClick={() => void syncTicket(item)}>Sync Ticket</Button>}{!item.ticketId && <Button size="small" color="inherit" disabled={updatingId === item.id || item.status === "IGNORED"} onClick={() => void setStatus(item, "IGNORED")}>Ignore</Button>}</Stack></TableCell>}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      ) : canViewHistory ? (
        <TableContainer component={Paper} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
          <Table><TableHead><TableRow><TableCell>Date</TableCell><TableCell>Application</TableCell><TableCell>Account Pair</TableCell><TableCell>Decision / Event</TableCell><TableCell>Source</TableCell><TableCell>Reviewer / Actor</TableCell></TableRow></TableHead>
            <TableBody>{history.length === 0 ? <TableRow><TableCell colSpan={6} align="center" sx={{ py: 6 }}>No decision history yet.</TableCell></TableRow> : history.map((item) => <TableRow key={item.id} hover><TableCell>{item.createdAt ? new Date(item.createdAt).toLocaleString() : "Not available"}</TableCell><TableCell>{item.application}</TableCell><TableCell><Typography variant="body2">{accountName(item.account1, item.account1Key)}</Typography><Typography variant="caption" color="text.secondary">↔ {accountName(item.account2, item.account2Key)}</Typography></TableCell><TableCell><Chip size="small" label={decisionLabel(item.decision)} />{item.comment && <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>{item.comment}</Typography>}</TableCell><TableCell>{item.source}</TableCell><TableCell>{item.reviewerName ?? "System"}</TableCell></TableRow>)}</TableBody>
          </Table>
        </TableContainer>
      ) : null}

      <Dialog open={Boolean(ticketItem)} onClose={() => setTicketItem(null)} fullWidth maxWidth="sm">
        <DialogTitle>Create Service Desk Remediation Ticket</DialogTitle><DialogContent><Stack spacing={2.5} sx={{ mt: 1 }}><Alert severity="warning">Choose the duplicate account that should be changed. The other account is treated as the account to retain.</Alert><FormControl fullWidth><InputLabel>Target Account</InputLabel><Select value={ticketTarget} label="Target Account" onChange={(event) => setTicketTarget(event.target.value as RemediationTarget)}><MenuItem value="ACCOUNT_1">Account 1 — {ticketItem ? accountName(ticketItem.account1, ticketItem.account1Key) : ""}</MenuItem><MenuItem value="ACCOUNT_2">Account 2 — {ticketItem ? accountName(ticketItem.account2, ticketItem.account2Key) : ""}</MenuItem></Select></FormControl><FormControl fullWidth><InputLabel>Remediation Action</InputLabel><Select value={ticketAction} label="Remediation Action" onChange={(event) => setTicketAction(event.target.value as RemediationAction)}><MenuItem value="DISABLE">Disable Account</MenuItem><MenuItem value="DELETE">Delete Account</MenuItem></Select></FormControl></Stack></DialogContent><DialogActions><Button onClick={() => setTicketItem(null)}>Cancel</Button><Button variant="contained" onClick={() => void createTicket()} disabled={ticketItem ? updatingId === ticketItem.id : false}>Create Ticket</Button></DialogActions>
      </Dialog>

      <Dialog open={bulkTicketOpen} onClose={() => !bulkBusy && setBulkTicketOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Create Bulk Service Desk Tickets</DialogTitle><DialogContent><Stack spacing={2.5} sx={{ mt: 1 }}><Alert severity="warning">The same target position and action will be applied to every selected Pending Action row. Verify that Account 1/Account 2 represents the correct duplicate account across the selection.</Alert><Typography variant="body2">Eligible selected items: <strong>{selectedItems.filter((item) => !item.ticketId && item.status === "PENDING_ACTION").length}</strong></Typography><FormControl fullWidth><InputLabel>Target Account</InputLabel><Select value={ticketTarget} label="Target Account" onChange={(event) => setTicketTarget(event.target.value as RemediationTarget)}><MenuItem value="ACCOUNT_1">Account 1 for all selected rows</MenuItem><MenuItem value="ACCOUNT_2">Account 2 for all selected rows</MenuItem></Select></FormControl><FormControl fullWidth><InputLabel>Remediation Action</InputLabel><Select value={ticketAction} label="Remediation Action" onChange={(event) => setTicketAction(event.target.value as RemediationAction)}><MenuItem value="DISABLE">Disable Account</MenuItem><MenuItem value="DELETE">Delete Account</MenuItem></Select></FormControl></Stack></DialogContent><DialogActions><Button onClick={() => setBulkTicketOpen(false)} disabled={bulkBusy}>Cancel</Button><Button variant="contained" onClick={() => void runBulkTickets()} disabled={bulkBusy}>{bulkBusy ? "Creating…" : "Create Tickets"}</Button></DialogActions>
      </Dialog>
    </PageContainer>
  );
};

export default RemediationQueue;
