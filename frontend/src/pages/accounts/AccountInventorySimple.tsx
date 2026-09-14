import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
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
import { getCurrentOrphanFindings, type OrphanFinding } from "../../services/orphanService";
import { getSourceAccounts, type SourceAccount } from "../../services/sourceAccountService";

const ORPHAN_TYPES = ["UNMATCHED_ACCOUNT", "TERMINATED_IDENTITY", "AMBIGUOUS_CORRELATION"];

const AccountInventorySimple = () => {
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
  const [orphanType, setOrphanType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const selectedIntegration = useMemo(
    () => integrations.find((item) => item.id === Number(integrationId)) ?? null,
    [integrations, integrationId],
  );

  useEffect(() => {
    const load = async () => {
      try {
        const response = await getIntegrations(1, 100);
        setIntegrations(response.items);
        if (response.items.length) setIntegrationId(response.items[0].id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load sources.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  useEffect(() => {
    if (!integrationId) return;
    const load = async () => {
      try {
        setLoading(true);
        setError("");
        const [accountResponse, orphanResponse] = await Promise.all([
          getSourceAccounts(Number(integrationId), page + 1, pageSize, search, true),
          getCurrentOrphanFindings(Number(integrationId), orphanType || undefined),
        ]);
        setAccounts(accountResponse.items);
        setTotal(accountResponse.total);
        setOrphans(orphanResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load account inventory.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [integrationId, page, pageSize, search, orphanType]);

  const accountLabel = (account: SourceAccount) => account.displayName || account.username || account.nativeIdentity;
  const orphanLabel = (finding: OrphanFinding) => finding.displayName || finding.username || finding.email || `Account ${finding.accountId}`;

  return (
    <PageContainer title="Accounts">
      <Stack spacing={3}>
        <Box>
          <Typography variant="h5" fontWeight={700}>Account Inventory</Typography>
          <Typography color="text.secondary">Persistent source accounts and current orphan findings.</Typography>
        </Box>

        <Paper variant="outlined" sx={{ p: 2.5 }}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <FormControl size="small" sx={{ minWidth: 280 }}>
              <InputLabel>Source</InputLabel>
              <Select label="Source" value={integrationId} onChange={(e) => { setIntegrationId(Number(e.target.value)); setPage(0); }}>
                {integrations.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
              </Select>
            </FormControl>
            {tab === 0 ? (
              <TextField size="small" placeholder="Search accounts..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} sx={{ flex: 1 }} />
            ) : (
              <FormControl size="small" sx={{ minWidth: 240 }}>
                <InputLabel>Orphan Type</InputLabel>
                <Select label="Orphan Type" value={orphanType} onChange={(e) => setOrphanType(e.target.value)}>
                  <MenuItem value="">All orphan types</MenuItem>
                  {ORPHAN_TYPES.map((type) => <MenuItem key={type} value={type}>{type.replaceAll("_", " ")}</MenuItem>)}
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

          {tab === 0 ? (
            <>
              <TableContainer>
                <Table size="small">
                  <TableHead><TableRow><TableCell>Account</TableCell><TableCell>Application</TableCell><TableCell>Native Identity</TableCell><TableCell>Employee ID</TableCell><TableCell>Status</TableCell><TableCell>Last Seen</TableCell></TableRow></TableHead>
                  <TableBody>
                    {loading ? <TableRow><TableCell colSpan={6} align="center"><CircularProgress size={26} /></TableCell></TableRow> : accounts.map((account) => (
                      <TableRow key={account.id} hover onClick={() => setSelectedAccount(account)} sx={{ cursor: "pointer" }}>
                        <TableCell>{accountLabel(account)}</TableCell><TableCell>{account.application}</TableCell><TableCell>{account.nativeIdentity}</TableCell><TableCell>{account.employeeId || "—"}</TableCell><TableCell>{account.status || "—"}</TableCell><TableCell>{account.lastSeenAt ? new Date(account.lastSeenAt).toLocaleString() : "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination component="div" count={total} page={page} rowsPerPage={pageSize} onPageChange={(_, value) => setPage(value)} onRowsPerPageChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }} rowsPerPageOptions={[25, 50, 100, 200]} />
            </>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead><TableRow><TableCell>Account</TableCell><TableCell>Application</TableCell><TableCell>Orphan Type</TableCell><TableCell>Correlation Method</TableCell><TableCell>Status</TableCell><TableCell>Detected</TableCell></TableRow></TableHead>
                <TableBody>
                  {loading ? <TableRow><TableCell colSpan={6} align="center"><CircularProgress size={26} /></TableCell></TableRow> : orphans.length === 0 ? (
                    <TableRow><TableCell colSpan={6} align="center">No orphan accounts found for {selectedIntegration?.name ?? "this source"}.</TableCell></TableRow>
                  ) : orphans.map((finding) => (
                    <TableRow key={finding.id} hover onClick={() => setSelectedOrphan(finding)} sx={{ cursor: "pointer" }}>
                      <TableCell>{orphanLabel(finding)}</TableCell><TableCell>{finding.application}</TableCell><TableCell>{finding.orphanType.replaceAll("_", " ")}</TableCell><TableCell>{finding.correlationMethod || "No identity matched"}</TableCell><TableCell>{finding.accountStatus || "—"}</TableCell><TableCell>{new Date(finding.createdAt).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      </Stack>

      <Drawer anchor="right" open={Boolean(selectedAccount)} onClose={() => setSelectedAccount(null)}>
        <Box sx={{ width: 560, p: 3 }}>
          <Typography variant="h6" fontWeight={700}>Account Details</Typography>
          {selectedAccount && <Stack spacing={2} sx={{ mt: 2 }}><Typography><strong>Native Identity:</strong> {selectedAccount.nativeIdentity}</Typography><Paper variant="outlined" sx={{ p: 2, maxHeight: 600, overflow: "auto" }}>{Object.entries(selectedAccount.rawAttributes).map(([key, value]) => <Box key={key} sx={{ py: 0.75 }}><Typography variant="caption" color="text.secondary">{key}</Typography><Typography variant="body2">{String(value ?? "") || "—"}</Typography></Box>)}</Paper></Stack>}
        </Box>
      </Drawer>

      <Drawer anchor="right" open={Boolean(selectedOrphan)} onClose={() => setSelectedOrphan(null)}>
        <Box sx={{ width: 600, p: 3 }}>
          <Typography variant="h6" fontWeight={700}>Orphan Account Details</Typography>
          {selectedOrphan && <Stack spacing={2} sx={{ mt: 2 }}><Typography><strong>Account:</strong> {orphanLabel(selectedOrphan)}</Typography><Typography><strong>Orphan Type:</strong> {selectedOrphan.orphanType.replaceAll("_", " ")}</Typography><Typography><strong>Correlation Method:</strong> {selectedOrphan.correlationMethod || "No identity matched"}</Typography><Typography><strong>Matched Identity:</strong> {selectedOrphan.matchedIdentityId ?? "—"}</Typography><Typography><strong>Finding Status:</strong> {selectedOrphan.status}</Typography><Typography fontWeight={700}>Correlation Evidence</Typography><Paper variant="outlined" sx={{ p: 2, maxHeight: 600, overflow: "auto" }}>{Object.entries(selectedOrphan.evidence).map(([key, value]) => <Box key={key} sx={{ py: 0.75 }}><Typography variant="caption" color="text.secondary">{key}</Typography><Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{typeof value === "object" ? JSON.stringify(value, null, 2) : String(value ?? "") || "—"}</Typography></Box>)}</Paper></Stack>}
        </Box>
      </Drawer>
    </PageContainer>
  );
};

export default AccountInventorySimple;
