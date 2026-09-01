import { useCallback, useEffect, useState } from "react";

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
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import ConfirmationNumberOutlinedIcon from "@mui/icons-material/ConfirmationNumberOutlined";

import { useAuth } from "../../auth/AuthContext";
import PageContainer from "../../components/common/PageContainer";
import {
  type RemediationAction,
  type RemediationItem,
  type RemediationStatus,
  type RemediationTarget,
  type ReviewDecisionHistoryItem,
  createRemediationTicket,
  getRemediationItems,
  getReviewDecisionHistory,
  syncRemediationTicket,
  updateRemediationStatus,
} from "../../services/remediationService";


type PageTab = "queue" | "history";
type QueueFilter = RemediationStatus | "ALL";

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

const RemediationQueue = () => {
  const { user, hasPermission } = useAuth();
  const canViewQueue = hasPermission("remediation.view");
  const canViewHistory = hasPermission("remediation.history.view");
  const canManage = hasPermission("remediation.manage");

  const [activeTab, setActiveTab] = useState<PageTab>(canViewQueue ? "queue" : "history");
  const [statusFilter, setStatusFilter] = useState<QueueFilter>("PENDING_ACTION");
  const [items, setItems] = useState<RemediationItem[]>([]);
  const [history, setHistory] = useState<ReviewDecisionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [ticketItem, setTicketItem] = useState<RemediationItem | null>(null);
  const [ticketTarget, setTicketTarget] = useState<RemediationTarget>("ACCOUNT_2");
  const [ticketAction, setTicketAction] = useState<RemediationAction>("DISABLE");

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [queueItems, historyItems] = await Promise.all([
        canViewQueue ? getRemediationItems(statusFilter) : Promise.resolve([]),
        canViewHistory ? getReviewDecisionHistory() : Promise.resolve([]),
      ]);
      setItems(queueItems);
      setHistory(historyItems);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load remediation data.");
    } finally {
      setLoading(false);
    }
  }, [canViewQueue, canViewHistory, statusFilter]);

  useEffect(() => {
    if (activeTab === "queue" && !canViewQueue && canViewHistory) setActiveTab("history");
    if (activeTab === "history" && !canViewHistory && canViewQueue) setActiveTab("queue");
  }, [activeTab, canViewQueue, canViewHistory]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const setStatus = async (item: RemediationItem, status: RemediationStatus) => {
    if (!canManage) return;
    try {
      setUpdatingId(item.id);
      setError("");
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
      await createRemediationTicket(
        ticketItem.id,
        ticketTarget,
        ticketAction,
        user?.fullName || user?.username || null,
      );
      setTicketItem(null);
      setStatusFilter("TICKET_OPEN");
      await loadData();
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

  return (
    <PageContainer title="Remediation">
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 2, flexWrap: "wrap", mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>Duplicate Account Remediation</Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Create disable/delete Service Desk tickets for reviewer-confirmed duplicates and automatically complete remediation when the ticket is resolved.
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

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ minHeight: 300, display: "flex", alignItems: "center", justifyContent: "center" }}><CircularProgress /></Box>
      ) : activeTab === "queue" && canViewQueue ? (
        <>
          <Box sx={{ mb: 2, maxWidth: 260 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select value={statusFilter} label="Status" onChange={(event) => setStatusFilter(event.target.value as QueueFilter)}>
                <MenuItem value="PENDING_ACTION">Pending Action</MenuItem>
                <MenuItem value="TICKET_OPEN">Ticket Open</MenuItem>
                <MenuItem value="ACTIONED">Completed</MenuItem>
                <MenuItem value="IGNORED">Ignored</MenuItem>
                <MenuItem value="FAILED">Failed</MenuItem>
                <MenuItem value="ALL">All</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <TableContainer component={Paper} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Integration / Application</TableCell>
                  <TableCell>Account 1</TableCell>
                  <TableCell>Account 2</TableCell>
                  <TableCell>AI Confidence</TableCell>
                  <TableCell>Status / Ticket</TableCell>
                  {canManage && <TableCell align="right">Action</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {items.length === 0 ? (
                  <TableRow><TableCell colSpan={canManage ? 6 : 5} align="center" sx={{ py: 6 }}>No remediation items for this status.</TableCell></TableRow>
                ) : items.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell>
                      <Typography fontWeight={700}>{item.integrationName ?? `#${item.integrationId}`}</Typography>
                      <Typography variant="caption" color="text.secondary">{item.application}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography fontWeight={600}>{accountName(item.account1, item.account1Key)}</Typography>
                      <Typography variant="caption" color="text.secondary">{valueOf(item.account1, "email")}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography fontWeight={600}>{accountName(item.account2, item.account2Key)}</Typography>
                      <Typography variant="caption" color="text.secondary">{valueOf(item.account2, "email")}</Typography>
                    </TableCell>
                    <TableCell>{item.confidence === null ? "Not available" : `${item.confidence}%`}</TableCell>
                    <TableCell>
                      <Stack spacing={0.5} alignItems="flex-start">
                        <Chip size="small" label={item.status.replaceAll("_", " ")} />
                        {item.ticketId && (
                          item.ticketUrl ? (
                            <Link href={item.ticketUrl} target="_blank" rel="noopener noreferrer" variant="caption">{item.ticketId} · {item.ticketStatus ?? "Unknown"}</Link>
                          ) : (
                            <Typography variant="caption">{item.ticketId} · {item.ticketStatus ?? "Unknown"}</Typography>
                          )
                        )}
                        {item.remediationAction && <Typography variant="caption" color="text.secondary">{item.remediationAction} · {item.targetAccountKey}</Typography>}
                        {item.ticketError && <Typography variant="caption" color="error">Last sync: {item.ticketError}</Typography>}
                      </Stack>
                    </TableCell>
                    {canManage && (
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          {!item.ticketId && item.status === "PENDING_ACTION" && (
                            <Button size="small" variant="contained" startIcon={<ConfirmationNumberOutlinedIcon />} disabled={updatingId === item.id} onClick={() => openTicketDialog(item)}>Create Ticket</Button>
                          )}
                          {item.ticketId && item.status === "TICKET_OPEN" && (
                            <Button size="small" variant="outlined" disabled={updatingId === item.id} onClick={() => void syncTicket(item)}>Sync Ticket</Button>
                          )}
                          {!item.ticketId && (
                            <Button size="small" color="inherit" disabled={updatingId === item.id || item.status === "IGNORED"} onClick={() => void setStatus(item, "IGNORED")}>Ignore</Button>
                          )}
                        </Stack>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      ) : canViewHistory ? (
        <TableContainer component={Paper} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Application</TableCell>
                <TableCell>Account Pair</TableCell>
                <TableCell>Decision / Event</TableCell>
                <TableCell>Source</TableCell>
                <TableCell>Reviewer / Actor</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {history.length === 0 ? (
                <TableRow><TableCell colSpan={6} align="center" sx={{ py: 6 }}>No decision history yet.</TableCell></TableRow>
              ) : history.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.createdAt ? new Date(item.createdAt).toLocaleString() : "Not available"}</TableCell>
                  <TableCell>{item.application}</TableCell>
                  <TableCell>
                    <Typography variant="body2">{accountName(item.account1, item.account1Key)}</Typography>
                    <Typography variant="caption" color="text.secondary">↔ {accountName(item.account2, item.account2Key)}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={decisionLabel(item.decision)} />
                    {item.comment && <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>{item.comment}</Typography>}
                  </TableCell>
                  <TableCell>{item.source}</TableCell>
                  <TableCell>{item.reviewerName ?? "System"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null}

      <Dialog open={Boolean(ticketItem)} onClose={() => setTicketItem(null)} fullWidth maxWidth="sm">
        <DialogTitle>Create Service Desk Remediation Ticket</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <Alert severity="warning">
              Choose the duplicate account that should be changed. The other account is treated as the account to retain.
            </Alert>
            <FormControl fullWidth>
              <InputLabel>Target Account</InputLabel>
              <Select value={ticketTarget} label="Target Account" onChange={(event) => setTicketTarget(event.target.value as RemediationTarget)}>
                <MenuItem value="ACCOUNT_1">Account 1 — {ticketItem ? accountName(ticketItem.account1, ticketItem.account1Key) : ""}</MenuItem>
                <MenuItem value="ACCOUNT_2">Account 2 — {ticketItem ? accountName(ticketItem.account2, ticketItem.account2Key) : ""}</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Remediation Action</InputLabel>
              <Select value={ticketAction} label="Remediation Action" onChange={(event) => setTicketAction(event.target.value as RemediationAction)}>
                <MenuItem value="DISABLE">Disable Account</MenuItem>
                <MenuItem value="DELETE">Delete Account</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTicketItem(null)}>Cancel</Button>
          <Button variant="contained" onClick={() => void createTicket()} disabled={ticketItem ? updatingId === ticketItem.id : false}>Create Ticket</Button>
        </DialogActions>
      </Dialog>
    </PageContainer>
  );
};

export default RemediationQueue;
