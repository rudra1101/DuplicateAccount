import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
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

import { useAuth } from "../../auth/AuthContext";
import PageContainer from "../../components/common/PageContainer";
import {
  type RemediationItem,
  type RemediationStatus,
  type ReviewDecisionHistoryItem,
  getRemediationItems,
  getReviewDecisionHistory,
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

const accountName = (
  account: Record<string, unknown>,
  stableKey: string,
): string => {
  const username = valueOf(account, "username");
  return username === "Not available" ? stableKey : username;
};

const decisionLabel = (value: string): string => {
  if (value === "DUPLICATE") return "Confirmed Duplicate";
  if (value === "NOT_DUPLICATE") return "Not Duplicate";
  return "Uncertain";
};

const RemediationQueue = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<PageTab>("queue");
  const [statusFilter, setStatusFilter] = useState<QueueFilter>("PENDING_ACTION");
  const [items, setItems] = useState<RemediationItem[]>([]);
  const [history, setHistory] = useState<ReviewDecisionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [queueItems, historyItems] = await Promise.all([
        getRemediationItems(statusFilter),
        getReviewDecisionHistory(),
      ]);
      setItems(queueItems);
      setHistory(historyItems);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load remediation data.",
      );
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const setStatus = async (item: RemediationItem, status: RemediationStatus) => {
    try {
      setUpdatingId(item.id);
      setError("");
      await updateRemediationStatus(
        item.id,
        status,
        null,
        user?.fullName || user?.username || null,
      );
      await loadData();
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Unable to update remediation item.",
      );
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <PageContainer title="Remediation">
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 2,
          flexWrap: "wrap",
          mb: 3,
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Duplicate Account Remediation
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Track reviewer-confirmed duplicates separately from detection and record downstream action status.
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={loading ? <CircularProgress size={18} /> : <RefreshIcon />}
          onClick={loadData}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      <Paper variant="outlined" sx={{ borderRadius: 3, mb: 3 }}>
        <Tabs value={activeTab} onChange={(_event, value: PageTab) => setActiveTab(value)}>
          <Tab value="queue" label={`Remediation Queue (${items.length})`} />
          <Tab value="history" label={`Decision History (${history.length})`} />
        </Tabs>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ minHeight: 300, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <CircularProgress />
        </Box>
      ) : activeTab === "queue" ? (
        <>
          <Box sx={{ mb: 2, maxWidth: 260 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(event) => setStatusFilter(event.target.value as QueueFilter)}
              >
                <MenuItem value="PENDING_ACTION">Pending Action</MenuItem>
                <MenuItem value="ACTIONED">Actioned</MenuItem>
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
                  <TableCell>Reviewer</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                      No remediation items for this status.
                    </TableCell>
                  </TableRow>
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
                    <TableCell>{item.reviewerName ?? "Not available"}</TableCell>
                    <TableCell><Chip size="small" label={item.status.replaceAll("_", " ")} /></TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button
                          size="small"
                          variant="outlined"
                          disabled={updatingId === item.id || item.status === "ACTIONED"}
                          onClick={() => setStatus(item, "ACTIONED")}
                        >
                          Mark Actioned
                        </Button>
                        <Button
                          size="small"
                          color="inherit"
                          disabled={updatingId === item.id || item.status === "IGNORED"}
                          onClick={() => setStatus(item, "IGNORED")}
                        >
                          Ignore
                        </Button>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Application</TableCell>
                <TableCell>Account Pair</TableCell>
                <TableCell>Decision</TableCell>
                <TableCell>AI Confidence</TableCell>
                <TableCell>Reviewer</TableCell>
                <TableCell>Source</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {history.length === 0 ? (
                <TableRow><TableCell colSpan={7} align="center" sx={{ py: 6 }}>No reviewer decision history yet.</TableCell></TableRow>
              ) : history.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.createdAt ? new Date(item.createdAt).toLocaleString() : "Not available"}</TableCell>
                  <TableCell>{item.application}</TableCell>
                  <TableCell>
                    <Typography variant="body2">{accountName(item.account1, item.account1Key)}</Typography>
                    <Typography variant="caption" color="text.secondary">↔ {accountName(item.account2, item.account2Key)}</Typography>
                  </TableCell>
                  <TableCell><Chip size="small" label={decisionLabel(item.decision)} /></TableCell>
                  <TableCell>{item.confidence === null ? "Not available" : `${item.confidence}%`}</TableCell>
                  <TableCell>{item.reviewerName ?? "Not available"}</TableCell>
                  <TableCell>{item.source.replaceAll("_", " ")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </PageContainer>
  );
};

export default RemediationQueue;
