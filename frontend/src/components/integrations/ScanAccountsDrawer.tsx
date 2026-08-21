import {
  Alert,
  Box,
  CircularProgress,
  Drawer,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Stack,
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

import CloseIcon from "@mui/icons-material/Close";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";

import { useEffect, useState } from "react";

import {
  getScanAccounts,
  type ScanAccount,
} from "../../services/integrationService";

interface Props {
  open: boolean;
  scanId: number | null;
  onClose: () => void;
}

const ScanAccountsDrawer = ({ open, scanId, onClose }: Props) => {
  const [accounts, setAccounts] = useState<ScanAccount[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadAccounts = async () => {
    if (!scanId) return;

    try {
      setLoading(true);
      setError("");
      const data = await getScanAccounts(
        scanId,
        page + 1,
        pageSize,
        search,
      );
      setAccounts(data.items);
      setTotal(data.total);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load scanned accounts.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && scanId) loadAccounts();
  }, [open, scanId, page, pageSize]);

  useEffect(() => {
    if (!open) {
      setAccounts([]);
      setTotal(0);
      setPage(0);
      setSearch("");
      setError("");
    }
  }, [open]);

  const submitSearch = () => {
    if (page !== 0) {
      setPage(0);
    } else {
      loadAccounts();
    }
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      slotProps={{
        paper: {
          sx: {
            width: { xs: "100%", md: "82%" },
            maxWidth: 1200,
          },
        },
      }}
    >
      <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <Box sx={{ px: 3, py: 2.5, borderBottom: 1, borderColor: "divider" }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
            <Box>
              <Typography variant="h6" fontWeight={700}>
                Scanned Accounts
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Scan #{scanId} · {total.toLocaleString()} accounts
              </Typography>
            </Box>

            <Stack direction="row">
              <Tooltip title="Refresh">
                <span>
                  <IconButton onClick={loadAccounts} disabled={loading}>
                    {loading ? <CircularProgress size={20} /> : <RefreshIcon />}
                  </IconButton>
                </span>
              </Tooltip>
              <IconButton onClick={onClose}>
                <CloseIcon />
              </IconButton>
            </Stack>
          </Stack>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mt: 2 }}>
            <TextField
              fullWidth
              size="small"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") submitSearch();
              }}
              placeholder="Search username, email, employee ID, source ID, application..."
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              select
              size="small"
              label="Rows"
              value={pageSize}
              onChange={(event) => {
                setPage(0);
                setPageSize(Number(event.target.value));
              }}
              sx={{ minWidth: 110 }}
            >
              {[25, 50, 100].map((size) => (
                <MenuItem key={size} value={size}>{size}</MenuItem>
              ))}
            </TextField>
          </Stack>
        </Box>

        <Box sx={{ flex: 1, overflow: "auto", p: 3 }}>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          {loading && accounts.length === 0 ? (
            <Box sx={{ minHeight: 280, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <CircularProgress />
            </Box>
          ) : (
            <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden" }}>
              <TableContainer>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Username</TableCell>
                      <TableCell>Display Name</TableCell>
                      <TableCell>Email</TableCell>
                      <TableCell>Employee ID</TableCell>
                      <TableCell>Application</TableCell>
                      <TableCell>Source Account ID</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {accounts.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} align="center" sx={{ py: 5 }}>
                          No accounts found.
                        </TableCell>
                      </TableRow>
                    ) : (
                      accounts.map((account) => (
                        <TableRow key={account.id} hover>
                          <TableCell>{account.username || "-"}</TableCell>
                          <TableCell>{account.displayName || "-"}</TableCell>
                          <TableCell>{account.email || "-"}</TableCell>
                          <TableCell>{account.employeeId || "-"}</TableCell>
                          <TableCell>{account.application || "-"}</TableCell>
                          <TableCell sx={{ maxWidth: 260, overflowWrap: "anywhere" }}>
                            {account.sourceAccountId || "-"}
                          </TableCell>
                          <TableCell>{account.status || "-"}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>

              <TablePagination
                component="div"
                count={total}
                page={page}
                rowsPerPage={pageSize}
                rowsPerPageOptions={[25, 50, 100]}
                onPageChange={(_, newPage) => setPage(newPage)}
                onRowsPerPageChange={(event) => {
                  setPage(0);
                  setPageSize(Number(event.target.value));
                }}
                showFirstButton
                showLastButton
              />
            </Paper>
          )}
        </Box>
      </Box>
    </Drawer>
  );
};

export default ScanAccountsDrawer;
