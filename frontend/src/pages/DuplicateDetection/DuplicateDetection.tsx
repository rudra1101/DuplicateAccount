import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Drawer,
  FormControl,
  InputAdornment,
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
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import CloseIcon from "@mui/icons-material/Close";
import IconButton from "@mui/material/IconButton";
import { useNavigate } from "react-router-dom";

import PageContainer from "../../components/common/PageContainer";
import { useAuth } from "../../auth/AuthContext";
import {
  getDuplicateGroupDetails,
  getDuplicateGroups,
  getReviewQueue,
  type DuplicateGroupDetails,
  type ReviewSummary,
} from "../../services/reviewService";

interface DetectionRow {
  groupId: number;
  integrationId: number | null;
  integrationName: string | null;
  scanId: number;
  application: string;
  primaryAccount: string;
  duplicates: number;
  highestConfidence: number;
}

const confidenceOptions = [
  { value: "ALL", label: "All confidence" },
  { value: "HIGH", label: "High (95%+)" },
  { value: "MEDIUM", label: "Medium (80-94%)" },
  { value: "LOW", label: "Low (<80%)" },
];

function confidenceColor(value: number): "success" | "warning" | "error" {
  if (value >= 95) return "success";
  if (value >= 80) return "warning";
  return "error";
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

const DuplicateDetection = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const canReview = hasPermission("duplicate.review");

  const [rows, setRows] = useState<DetectionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [application, setApplication] = useState("ALL");
  const [integration, setIntegration] = useState("ALL");
  const [confidence, setConfidence] = useState("ALL");
  const [details, setDetails] = useState<DuplicateGroupDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState("");

  const loadDuplicates = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const summaries = await getReviewQueue();
      const withDuplicates = summaries.filter((item) => item.duplicateGroups > 0);

      const groupLists = await Promise.all(
        withDuplicates.map(async (summary: ReviewSummary) => {
          const groups = await getDuplicateGroups(summary.application, summary.integrationId);
          return groups.map((group) => ({
            groupId: group.groupId,
            integrationId: summary.integrationId,
            integrationName: summary.integrationName,
            scanId: group.scanId,
            application: summary.application,
            primaryAccount: group.primaryAccount,
            duplicates: group.duplicates,
            highestConfidence: group.highestConfidence,
          }));
        }),
      );

      setRows(groupLists.flat().sort((a, b) => b.highestConfidence - a.highestConfidence));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load duplicate groups.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDuplicates();
  }, [loadDuplicates]);

  const applications = useMemo(
    () => [...new Set(rows.map((row) => row.application))].sort(),
    [rows],
  );

  const integrations = useMemo(() => {
    const map = new Map<string, string>();
    rows.forEach((row) => {
      const key = String(row.integrationId ?? "legacy");
      map.set(key, row.integrationName ?? (row.integrationId ? `Integration #${row.integrationId}` : "Legacy upload"));
    });
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [rows]);

  const filteredRows = useMemo(() => {
    const query = search.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesSearch = !query || [
        row.primaryAccount,
        row.application,
        row.integrationName ?? "",
        String(row.groupId),
      ].some((value) => value.toLowerCase().includes(query));

      const matchesApplication = application === "ALL" || row.application === application;
      const matchesIntegration = integration === "ALL" || String(row.integrationId ?? "legacy") === integration;
      const matchesConfidence =
        confidence === "ALL" ||
        (confidence === "HIGH" && row.highestConfidence >= 95) ||
        (confidence === "MEDIUM" && row.highestConfidence >= 80 && row.highestConfidence < 95) ||
        (confidence === "LOW" && row.highestConfidence < 80);

      return matchesSearch && matchesApplication && matchesIntegration && matchesConfidence;
    });
  }, [rows, search, application, integration, confidence]);

  const totalCandidates = useMemo(
    () => filteredRows.reduce((sum, row) => sum + row.duplicates, 0),
    [filteredRows],
  );

  const highConfidence = useMemo(
    () => filteredRows.filter((row) => row.highestConfidence >= 95).length,
    [filteredRows],
  );

  const openDetails = async (row: DetectionRow) => {
    try {
      setDetails(null);
      setDetailsError("");
      setDetailsLoading(true);
      setDetails(await getDuplicateGroupDetails(row.groupId, row.integrationId));
    } catch (detailError) {
      setDetailsError(detailError instanceof Error ? detailError.message : "Unable to load duplicate details.");
    } finally {
      setDetailsLoading(false);
    }
  };

  return (
    <PageContainer title="Duplicate Detection">
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2} sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>Detected Duplicate Accounts</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Search and investigate duplicate groups from the latest completed integration scans.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          {canReview && (
            <Button
              variant="outlined"
              startIcon={<FactCheckOutlinedIcon />}
              onClick={() => navigate("/review")}
            >
              Review Queue
            </Button>
          )}
          <Button
            variant="outlined"
            startIcon={loading ? <CircularProgress size={17} /> : <RefreshIcon />}
            onClick={() => void loadDuplicates()}
            disabled={loading}
          >
            Refresh
          </Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ mb: 3 }}>
        {[
          ["Duplicate Groups", filteredRows.length],
          ["Candidate Accounts", totalCandidates],
          ["High Confidence", highConfidence],
        ].map(([label, value]) => (
          <Paper key={String(label)} variant="outlined" sx={{ px: 2.5, py: 2, borderRadius: 3, minWidth: 190 }}>
            <Typography variant="body2" color="text.secondary">{label}</Typography>
            <Typography variant="h5" fontWeight={700} sx={{ mt: 0.5 }}>{value}</Typography>
          </Paper>
        ))}
      </Stack>

      <Paper variant="outlined" sx={{ p: 2, borderRadius: 3, mb: 3 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
          <TextField
            size="small"
            placeholder="Search username, application, integration or group ID"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            sx={{ flex: 1, minWidth: 260 }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment>
                ),
              },
            }}
          />

          <FormControl size="small" sx={{ minWidth: 180 }}>
            <Select value={application} onChange={(event) => setApplication(event.target.value)}>
              <MenuItem value="ALL">All applications</MenuItem>
              {applications.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 180 }}>
            <Select value={integration} onChange={(event) => setIntegration(event.target.value)}>
              <MenuItem value="ALL">All integrations</MenuItem>
              {integrations.map(([key, label]) => <MenuItem key={key} value={key}>{label}</MenuItem>)}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 170 }}>
            <Select value={confidence} onChange={(event) => setConfidence(event.target.value)}>
              {confidenceOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: "#f8fafc" }}>
              <TableCell>Primary Account</TableCell>
              <TableCell>Application</TableCell>
              <TableCell>Integration</TableCell>
              <TableCell align="center">Candidates</TableCell>
              <TableCell align="center">Confidence</TableCell>
              <TableCell align="right">Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={6} align="center" sx={{ py: 8 }}><CircularProgress /></TableCell></TableRow>
            ) : filteredRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 7 }}>
                  <Typography fontWeight={700}>No duplicate groups match the current filters.</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    Change the filters or run a new integration scan.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : filteredRows.map((row) => (
              <TableRow key={row.groupId} hover>
                <TableCell>
                  <Typography fontWeight={700}>{row.primaryAccount}</Typography>
                  <Typography variant="caption" color="text.secondary">Group #{row.groupId} · Scan #{row.scanId}</Typography>
                </TableCell>
                <TableCell>{row.application}</TableCell>
                <TableCell>{row.integrationName ?? (row.integrationId ? `Integration #${row.integrationId}` : "Legacy upload")}</TableCell>
                <TableCell align="center">{row.duplicates}</TableCell>
                <TableCell align="center">
                  <Chip size="small" label={`${row.highestConfidence}%`} color={confidenceColor(row.highestConfidence)} variant="outlined" />
                </TableCell>
                <TableCell align="right">
                  <Button size="small" startIcon={<VisibilityOutlinedIcon />} onClick={() => void openDetails(row)}>
                    Investigate
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Drawer
        anchor="right"
        open={detailsLoading || Boolean(details) || Boolean(detailsError)}
        onClose={() => { setDetails(null); setDetailsError(""); }}
        PaperProps={{ sx: { width: { xs: "100%", sm: 560 }, p: 3 } }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Box>
            <Typography variant="h6" fontWeight={700}>Duplicate Group Investigation</Typography>
            {details && <Typography variant="caption" color="text.secondary">Group #{details.groupId} · {details.application}</Typography>}
          </Box>
          <IconButton onClick={() => { setDetails(null); setDetailsError(""); }}><CloseIcon /></IconButton>
        </Stack>

        {detailsLoading && <Box sx={{ py: 8, textAlign: "center" }}><CircularProgress /></Box>}
        {detailsError && <Alert severity="error">{detailsError}</Alert>}

        {details && (
          <Stack spacing={2.5}>
            <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography fontWeight={700}>Primary Account</Typography>
                <Chip size="small" label={`${details.highestConfidence}% highest confidence`} color={confidenceColor(details.highestConfidence)} />
              </Stack>
              <Stack spacing={0.8}>
                <Typography><strong>Username:</strong> {displayValue(details.primaryAccount.username)}</Typography>
                <Typography><strong>Display name:</strong> {displayValue(details.primaryAccount.displayName)}</Typography>
                <Typography><strong>Email:</strong> {displayValue(details.primaryAccount.email)}</Typography>
                <Typography><strong>Employee ID:</strong> {displayValue(details.primaryAccount.employeeId)}</Typography>
                <Typography><strong>Department:</strong> {displayValue(details.primaryAccount.department)}</Typography>
                <Typography><strong>Manager:</strong> {displayValue(details.primaryAccount.manager)}</Typography>
              </Stack>
            </Paper>

            <Typography variant="subtitle1" fontWeight={700}>Candidate Accounts ({details.duplicates.length})</Typography>

            {details.duplicates.map((candidate) => {
              const account = candidate.account ?? {};
              return (
                <Paper key={candidate.candidateRecordId} variant="outlined" sx={{ p: 2.5, borderRadius: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                    <Box>
                      <Typography fontWeight={700}>{displayValue(account.username ?? account.displayName ?? `Candidate ${candidate.id}`)}</Typography>
                      <Typography variant="body2" color="text.secondary">{displayValue(account.application ?? details.application)}</Typography>
                    </Box>
                    <Chip size="small" label={`${candidate.confidence}%`} color={confidenceColor(candidate.confidence)} />
                  </Stack>

                  <Divider sx={{ my: 1.5 }} />
                  <Stack spacing={0.7}>
                    <Typography variant="body2"><strong>Email:</strong> {displayValue(account.email)}</Typography>
                    <Typography variant="body2"><strong>Employee ID:</strong> {displayValue(account.employeeId)}</Typography>
                    <Typography variant="body2"><strong>Department:</strong> {displayValue(account.department)}</Typography>
                  </Stack>

                  {candidate.matchedAttributes.length > 0 && (
                    <Box sx={{ mt: 1.5 }}>
                      <Typography variant="caption" color="text.secondary">Matched attributes</Typography>
                      <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap" sx={{ mt: 0.5 }}>
                        {candidate.matchedAttributes.map((item) => <Chip key={item} size="small" label={item} variant="outlined" color="success" />)}
                      </Stack>
                    </Box>
                  )}

                  {candidate.reviewDecision && (
                    <Alert severity="info" sx={{ mt: 1.5 }}>Review decision: {candidate.reviewDecision}</Alert>
                  )}
                </Paper>
              );
            })}

            {canReview && (
              <Button variant="contained" startIcon={<FactCheckOutlinedIcon />} onClick={() => navigate("/review")}>
                Continue in Review Queue
              </Button>
            )}
          </Stack>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default DuplicateDetection;
