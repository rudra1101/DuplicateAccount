import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Drawer,
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
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import PageContainer from "../../components/common/PageContainer";
import { getIntegrations, type Integration } from "../../services/integrationService";
import {
  getOrphanFindings,
  getSourceAccounts,
  type OrphanFinding,
  type SourceAccount,
} from "../../services/sourceAccountService";

const AccountInventory = () => {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [integrationId, setIntegrationId] = useState<number | "">("");
  const [accounts, setAccounts] = useState<SourceAccount[]>([]);
  const [orphans, setOrphans] = useState<OrphanFinding[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<SourceAccount | null>(null);
  const [selectedOrphan, setSelectedOrphan] = useState<OrphanFinding | null>(null);
  const [tab, setTab] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "deleted">("active");
  const [severityFilter, setSeverityFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const selectedIntegration = useMemo(
    () => integrations.find((item) => item.id === Number(integrationId)) ?? null,
    [integrations, integrationId],
  );

  useEffect(() => {
    const loadSources = async () => {
      try {
        setLoading(true);
        const response = await getIntegrations(1, 100);
        setIntegrations(response.items);
        if (response.items.length > 0) setIntegrationId(response.items[0].id);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load sources.");
      } finally {
        setLoading(false);
      }
    };
    void loadSources();
  }, []);

  useEffect(() => {
    if (!integrationId) return;
    const loadInventory = async () => {
      try {
        setLoading(true);
        setError("");
        const active = activeFilter === "all" ? undefined : activeFilter === "active";
        const [accountResponse, orphanResponse] = await Promise.all([
          getSourceAccounts(Number(integrationId), page + 1, pageSize, search, active),
          getOrphanFindings(Number(integrationId), severityFilter || undefined),
        ]);
        setAccounts(accountResponse.items);
        setTotal(accountResponse.total);
        setOrphans(orphanResponse);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load account inventory.");
      } finally {
        setLoading(false);
      }
    };
    void loadInventory();
  }, [integrationId, page, pageSize, search, activeFilter, severityFilter]);

  const renderAccount = (account: SourceAccount) => (
    account.displayName || account.username || account.nativeIdentity
  );

  const orphanLabel = (finding: OrphanFinding) => (
    finding.displayName || finding.username || finding.email || `Account ${finding.accountId}`
  );

  const severityColor = (severity: string): "error" | "warning" | "info" | "default" => {
    if (severity === "CRITICAL") return "error";
    if (severity === "HIGH") return "warning";
    if (severity === "MEDIUM") return "info";
    return "default";
  };

  return (
    <PageContainer title="Accounts">
      <Stack spacing={3}>
        <Box>
          <Typography variant="h5" fontWeight={700}>Account Inventory</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Browse the current account state persisted from source aggregations and review current orphan accounts for each source.
          </Typography>
        </Box>

        <Paper variant="outlined" sx={{ p: 2.5 }}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }}>
            <FormControl size="small" sx={{ minWidth: 280 }}>
              <InputLabel>Source</InputLabel>
              <Select
                label="Source"
                value={integrationId}
                onChange={(event) => {
                  setIntegrationId(Number(event.target.value));
                  setPage(0);
                  setSelectedAccount(null);
                  setSelectedOrphan(null);
                }}
              >
                {integrations.map((integration) => (
                  <MenuItem key={integration.id} value={integration.id}>
                    {integration.name} · {integration.sourcePurpose === "AUTHORITATIVE" ? "Authoritative" : "Account"}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {tab === 0 ? (
              <>
                <TextField
                  size="small"
                  placeholder="Search native identity, username, email, employee ID..."
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(0);
                  }}
                  sx={{ flex: 1, minWidth: 280 }}
                />
                <FormControl size="small" sx={{ minWidth: 150 }}>
                  <InputLabel>State</InputLabel>
                  <Select
                    label="State"
                    value={activeFilter}
                    onChange={(event) => {
                      setActiveFilter(event.target.value as "all" | "active" | "deleted");
                      setPage(0);
                    }}
                  >
                    <MenuItem value="active">Active</MenuItem>
                    <MenuItem value="deleted">Deleted / Missing</MenuItem>
                    <MenuItem value="all">All</MenuItem>
                  </Select>
                </FormControl>
              </>
            ) : (
              <FormControl size="small" sx={{ minWidth: 180 }}>
                <InputLabel>Severity</InputLabel>
                <Select
                  label="Severity"
                  value={severityFilter}
                  onChange={(event) => setSeverityFilter(event.target.value)}
                >
                  <MenuItem value="">All severities</MenuItem>
                  <MenuItem value="CRITICAL">Critical</MenuItem>
                  <MenuItem value="HIGH">High</MenuItem>
                  <MenuItem value="MEDIUM">Medium</MenuItem>
                  <MenuItem value="LOW">Low</MenuItem>
                </Select>
              </FormControl>
            )}
          </Stack>
        </Paper>

        {error && <Alert severity="error">{error}</Alert>}

        <Paper variant="outlined">
          <Tabs value={tab} onChange={(_, value) => setTab(value)}>
            <Tab label={`All Accounts (${total})`} />
            <Tab label={`Orphan Accounts (${orphans.length})`} />
          </Tabs>

          {tab === 0 && (
            <>
              <TableContainer>
                <Table size="small" sx={{ minWidth: 900 }}>
                  <TableHead>
                    <TableRow sx={{ bgcolor: "action.hover" }}>
                      <TableCell>Account</TableCell>
                      <TableCell>Application</TableCell>
                      <TableCell>Native Identity</TableCell>
                      <TableCell>Employee ID</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Inventory State</TableCell>
                      <TableCell>Last Seen</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {loading ? (
                      <TableRow><TableCell colSpan={7} align="center" sx={{ py: 6 }}><CircularProgress size={28} /></TableCell></TableRow>
                    ) : accounts.length === 0 ? (
                      <TableRow><TableCell colSpan={7} align="center" sx={{ py: 6 }}>No persisted accounts found for this source yet. Run an aggregation first.</TableCell></TableRow>
                    ) : accounts.map((account) => (
                      <TableRow key={account.id} hover onClick={() => setSelectedAccount(account)} sx={{ cursor: "pointer" }}>
                        <TableCell>
                          <Typography fontWeight={600}>{renderAccount(account)}</Typography>
                          {account.email && <Typography variant="caption" color="text.secondary">{account.email}</Typography>}
                        </TableCell>
                        <TableCell>{account.application}</TableCell>
                        <TableCell>{account.nativeIdentity}</TableCell>
                        <TableCell>{account.employeeId || "—"}</TableCell>
                        <TableCell>{account.status || "—"}</TableCell>
                        <TableCell><Chip size="small" color={account.active ? "success" : "default"} label={account.active ? "Active" : "Missing / Deleted"} /></TableCell>
                        <TableCell>{account.lastSeenAt ? new Date(account.lastSeenAt).toLocaleString() : "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div"
                count={total}
                page={page}
                rowsPerPage={pageSize}
                onPageChange={(_, value) => setPage(value)}
                onRowsPerPageChange={(event) => {
                  setPageSize(Number(event.target.value));
                  setPage(0);
                }}
                rowsPerPageOptions={[25, 50, 100, 200]}
              />
            </>
          )}

          {tab === 1 && (
            <TableContainer>
              <Table size="small" sx={{ minWidth: 1050 }}>
                <TableHead>
                  <TableRow sx={{ bgcolor: "action.hover" }}>
                    <TableCell>Account</TableCell>
                    <TableCell>Application</TableCell>
                    <TableCell>Orphan Type</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell>Risk Score</TableCell>
                    <TableCell>Correlation</TableCell>
                    <TableCell>Account Status</TableCell>
                    <TableCell>Detected</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {loading ? (
                    <TableRow><TableCell colSpan={8} align="center" sx={{ py: 6 }}><CircularProgress size={28} /></TableCell></TableRow>
                  ) : orphans.length === 0 ? (
                    <TableRow><TableCell colSpan={8} align="center" sx={{ py: 6 }}>No orphan accounts found in the latest aggregation for {selectedIntegration?.name ?? "this source"}.</TableCell></TableRow>
                  ) : orphans.map((finding) => (
                    <TableRow key={finding.id} hover onClick={() => setSelectedOrphan(finding)} sx={{ cursor: "pointer" }}>
                      <TableCell>
                        <Typography fontWeight={600}>{orphanLabel(finding)}</Typography>
                        {finding.email && <Typography variant="caption" color="text.secondary">{finding.email}</Typography>}
                      </TableCell>
                      <TableCell>{finding.application}</TableCell>
                      <TableCell>{finding.orphanType.replaceAll("_", " ")}</TableCell>
                      <TableCell><Chip size="small" color={severityColor(finding.severity)} label={finding.severity} /></TableCell>
                      <TableCell>{finding.riskScore}</TableCell>
                      <TableCell>{finding.correlationMethod || "No match"}</TableCell>
                      <TableCell>{finding.accountStatus || "—"}</TableCell>
                      <TableCell>{new Date(finding.createdAt).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      </Stack>

      <Drawer anchor="right" open={Boolean(selectedAccount)} onClose={() => setSelectedAccount(null)}>
        <Box sx={{ width: { xs: 340, sm: 560 }, p: 3 }}>
          <Typography variant="h6" fontWeight={700}>Account Details</Typography>
          {selectedAccount && (
            <Stack spacing={2} sx={{ mt: 2 }}>
              <Box><Typography variant="caption" color="text.secondary">Source</Typography><Typography>{selectedIntegration?.name}</Typography></Box>
              <Box><Typography variant="caption" color="text.secondary">Application</Typography><Typography>{selectedAccount.application}</Typography></Box>
              <Box><Typography variant="caption" color="text.secondary">Native Identity</Typography><Typography sx={{ wordBreak: "break-all" }}>{selectedAccount.nativeIdentity}</Typography></Box>
              <Box><Typography variant="caption" color="text.secondary">First Seen</Typography><Typography>{selectedAccount.firstSeenAt ? new Date(selectedAccount.firstSeenAt).toLocaleString() : "—"}</Typography></Box>
              <Box><Typography variant="caption" color="text.secondary">Last Seen</Typography><Typography>{selectedAccount.lastSeenAt ? new Date(selectedAccount.lastSeenAt).toLocaleString() : "—"}</Typography></Box>
              <Typography fontWeight={700} sx={{ pt: 1 }}>Source Attributes</Typography>
              <Paper variant="outlined" sx={{ p: 2, maxHeight: 520, overflow: "auto" }}>
                {Object.entries(selectedAccount.rawAttributes).map(([key, value]) => (
                  <Box key={key} sx={{ py: 0.75, borderBottom: 1, borderColor: "divider" }}>
                    <Typography variant="caption" color="text.secondary">{key}</Typography>
                    <Typography variant="body2" sx={{ wordBreak: "break-word" }}>{String(value ?? "") || "—"}</Typography>
                  </Box>
                ))}
              </Paper>
            </Stack>
          )}
        </Box>
      </Drawer>

      <Drawer anchor="right" open={Boolean(selectedOrphan)} onClose={() => setSelectedOrphan(null)}>
        <Box sx={{ width: { xs: 340, sm: 600 }, p: 3 }}>
          <Typography variant="h6" fontWeight={700}>Orphan Account Details</Typography>
          {selectedOrphan && (
            <Stack spacing={2} sx={{ mt: 2 }}>
              <Box><Typography variant="caption" color="text.secondary">Account</Typography><Typography fontWeight={600}>{orphanLabel(selectedOrphan)}</Typography></Box>
              <Box><Typography variant="caption" color="text.secondary">Orphan Type</Typography><Typography>{selectedOrphan.orphanType.replaceAll("_", " ")}</Typography></Box>
              <Box><Typography variant="caption" color="text.secondary">Severity / Risk</Typography><Typography>{selectedOrphan.severity} · {selectedOrphan.riskScore}</Typography></Box>
              <Box><Typography variant="caption" color="text.secondary">Correlation Method</Typography><Typography>{selectedOrphan.correlationMethod || "No identity matched"}</Typography></Box>
              <Box><Typography variant="caption" color="text.secondary">Matched Identity</Typography><Typography>{selectedOrphan.matchedIdentityId ?? "—"}</Typography></Box>
              <Box><Typography variant="caption" color="text.secondary">Finding Status</Typography><Typography>{selectedOrphan.status}</Typography></Box>
              <Typography fontWeight={700} sx={{ pt: 1 }}>Correlation Evidence</Typography>
              <Paper variant="outlined" sx={{ p: 2, maxHeight: 520, overflow: "auto" }}>
                {Object.entries(selectedOrphan.evidence).map(([key, value]) => (
                  <Box key={key} sx={{ py: 0.75, borderBottom: 1, borderColor: "divider" }}>
                    <Typography variant="caption" color="text.secondary">{key}</Typography>
                    <Typography variant="body2" sx={{ wordBreak: "break-word", whiteSpace: "pre-wrap" }}>
                      {typeof value === "object" ? JSON.stringify(value, null, 2) : String(value ?? "") || "—"}
                    </Typography>
                  </Box>
                ))}
              </Paper>
            </Stack>
          )}
        </Box>
      </Drawer>
    </PageContainer>
  );
};

export default AccountInventory;
