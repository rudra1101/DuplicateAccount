import {
  useEffect,
  useMemo,
  useState,
} from "react";

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
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import type {
  SelectChangeEvent,
} from "@mui/material/Select";
import { useNavigate } from "react-router-dom";

import PageContainer from "../../components/common/PageContainer";
import KpiCard from "../../components/dashboard/KpiCard";
import DuplicateTrendChart from "../../components/dashboard/DuplicateTrendChart";
import DuplicateSourceChart from "../../components/dashboard/DuplicateSourceChart";
import { formatDateTime } from "../../utils/dateTime";

import {
  type DashboardPeriod,
  type DashboardResponse,
  getDashboardSummary,
} from "../../services/dashboardService";


const DASHBOARD_PERIODS: DashboardPeriod[] = [
  "daily",
  "weekly",
  "monthly",
  "yearly",
];


function isDashboardPeriod(
  value: string,
): value is DashboardPeriod {
  return DASHBOARD_PERIODS.includes(
    value,
  );
}


const Dashboard = () => {
  const navigate = useNavigate();

  const [
    period,
    setPeriod,
  ] = useState<DashboardPeriod>(
    "daily",
  );

  const [
    dashboard,
    setDashboard,
  ] = useState<
    DashboardResponse | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");


  useEffect(() => {
    let cancelled = false;

    const loadDashboard =
      async () => {
        try {
          setLoading(true);
          setError("");

          const data =
            await getDashboardSummary(
              period,
            );

          if (!cancelled) {
            setDashboard(data);
          }
        } catch (loadError) {
          console.error(
            "Failed to load dashboard:",
            loadError,
          );

          if (!cancelled) {
            setError(
              loadError instanceof Error
                ? loadError.message
                : "Unable to load dashboard.",
            );
          }
        } finally {
          if (!cancelled) {
            setLoading(false);
          }
        }
      };

    void loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [period]);


  const handlePeriodChange = (
    event: SelectChangeEvent,
  ) => {
    const selectedValue =
      event.target.value;

    if (
      isDashboardPeriod(
        selectedValue,
      )
    ) {
      setPeriod(
        selectedValue,
      );
    }
  };


  const trendData = useMemo(() => {
    return (
      dashboard?.trend.map(
        (scanItem) => ({
          name:
            scanItem.integrationName
              ? (
                `${scanItem.name} · `
                + scanItem.integrationName
              )
              : scanItem.name,
          duplicates:
            scanItem.duplicateGroups,
        }),
      ) ?? []
    );
  }, [dashboard]);


  const sourceData = useMemo(() => {
    return (
      dashboard?.applications.map(
        (application) => ({
          name:
            application.application,
          value:
            application
              .duplicateAccounts,
        }),
      ) ?? []
    );
  }, [dashboard]);


  if (
    loading
    && !dashboard
  ) {
    return (
      <PageContainer title="Dashboard">
        <Box
          sx={{
            minHeight: 400,
            display: "flex",
            justifyContent:
              "center",
            alignItems:
              "center",
          }}
        >
          <CircularProgress />
        </Box>
      </PageContainer>
    );
  }


  if (error) {
    return (
      <PageContainer title="Dashboard">
        <Alert severity="error">
          {error}
        </Alert>
      </PageContainer>
    );
  }


  if (
    !dashboard
    || !dashboard.hasData
  ) {
    return (
      <PageContainer title="Dashboard">
        <Alert severity="info">
          No completed scan data
          is available.
        </Alert>
      </PageContainer>
    );
  }


  const {
    summary,
    scan,
    scans,
    applications,
    applicationCount,
  } = dashboard;


  return (
    <PageContainer title="Dashboard">
      <Box
        sx={{
          display: "flex",
          justifyContent:
            "space-between",
          alignItems:
            "flex-start",
          mb: 3,
          flexWrap: "wrap",
          gap: 2,
        }}
      >
        <Box>
          <Typography
            variant="h5"
            fontWeight={700}
          >
            Duplicate Account Analytics
          </Typography>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mt: 0.5 }}
          >
            Enterprise overview of duplicate risk,
            recent scans and applications requiring
            the most attention.
          </Typography>

          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: "block",
              mt: 1,
            }}
          >
            Most recent scan:{" "}
            {scan?.filename
              ?? "Not available"}

            {scan?.integrationName
              ? (
                ` · ${scan.integrationName}`
              )
              : ""}

            {scan?.createdAt
              ? (
                ` · ${formatDateTime(
                  scan.createdAt,
                  "Asia/Kolkata",
                )}`
              )
              : ""}
          </Typography>
        </Box>

        <Stack
          direction="row"
          spacing={1.5}
          alignItems="center"
          flexWrap="wrap"
          useFlexGap
        >
          <Button
            variant="outlined"
            endIcon={<ArrowForwardIcon />}
            onClick={() => navigate("/integrations")}
          >
            View Integrations
          </Button>

          <FormControl
            size="small"
            sx={{
              minWidth: 190,
            }}
          >
            <Select
              value={period}
              onChange={
                handlePeriodChange
              }
            >
              <MenuItem value="daily">
                Last 24 Hours
              </MenuItem>

              <MenuItem value="weekly">
                Last 7 Days
              </MenuItem>

              <MenuItem value="monthly">
                Last 30 Days
              </MenuItem>

              <MenuItem value="yearly">
                Last 12 Months
              </MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Box>

      <Grid
        container
        spacing={3}
        sx={{ mb: 4 }}
      >
        <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
          <KpiCard
            title="Accounts Scanned"
            value={Number(
              summary.accountsScanned
              ?? 0,
            ).toLocaleString()}
            color="#1976d2"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
          <KpiCard
            title="Integrations"
            value={
              summary.integrations
              ?? 0
            }
            color="#455a64"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
          <KpiCard
            title="Applications"
            value={
              summary.applications
              ?? 0
            }
            color="#6a1b9a"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
          <KpiCard
            title="Duplicate Groups"
            value={
              summary.duplicateGroups
              ?? 0
            }
            color="#d32f2f"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
          <KpiCard
            title="High Confidence"
            value={
              summary
                .highConfidenceMatches
              ?? 0
            }
            color="#2e7d32"
          />
        </Grid>
      </Grid>

      <Grid
        container
        spacing={3}
        sx={{ mb: 3 }}
      >
        <Grid size={{ xs: 12, lg: 7 }}>
          <Card
            variant="outlined"
            sx={{ borderRadius: 3, height: "100%" }}
          >
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ px: 3, py: 2.5 }}>
                <Typography variant="h6" fontWeight={700}>
                  Applications Requiring Attention
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Top {applications.length} applications ranked by duplicate accounts
                  {applicationCount > applications.length
                    ? ` out of ${applicationCount.toLocaleString()} affected applications.`
                    : "."}
                </Typography>
              </Box>

              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ bgcolor: "action.hover" }}>
                      <TableCell sx={{ fontWeight: 700 }}>Application</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>Duplicate Accounts</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>Groups</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>Highest Confidence</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {applications.map((application, index) => (
                      <TableRow key={application.application} hover>
                        <TableCell>
                          <Stack direction="row" spacing={1.25} alignItems="center">
                            <Chip
                              label={index + 1}
                              size="small"
                              variant="outlined"
                              sx={{ minWidth: 34 }}
                            />
                            <Typography fontWeight={600}>
                              {application.application || "Unknown Application"}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell align="right">
                          {application.duplicateAccounts.toLocaleString()}
                        </TableCell>
                        <TableCell align="right">
                          {application.duplicateGroups.toLocaleString()}
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            size="small"
                            label={`${Math.round(application.highestConfidence)}%`}
                            color={application.highestConfidence >= 95 ? "error" : "warning"}
                            variant="outlined"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, lg: 5 }}>
          <Card
            variant="outlined"
            sx={{ borderRadius: 3, height: "100%" }}
          >
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ px: 3, py: 2.5 }}>
                <Typography variant="h6" fontWeight={700}>
                  Recent Integration Scans
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Latest scan activity only. The dashboard intentionally avoids listing every integration.
                </Typography>
              </Box>

              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ bgcolor: "action.hover" }}>
                      <TableCell sx={{ fontWeight: 700 }}>Integration</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>Duplicates</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Last Scan</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {scans.map((scanItem) => (
                      <TableRow key={scanItem.id} hover>
                        <TableCell>
                          <Typography fontWeight={600}>
                            {scanItem.integrationName
                              ?? (scanItem.integrationId
                                ? `Integration #${scanItem.integrationId}`
                                : "Legacy Scan")}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Scan #{scanItem.id}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          {Number(scanItem.duplicateAccounts ?? 0).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {scanItem.createdAt
                              ? formatDateTime(scanItem.createdAt, "Asia/Kolkata")
                              : "—"}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid
        container
        spacing={3}
      >
        <Grid size={{ xs: 12, lg: 8 }}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: 2,
              height: 430,
            }}
          >
            <CardContent
              sx={{
                height: "100%",
                boxSizing:
                  "border-box",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent:
                    "space-between",
                  alignItems:
                    "center",
                  flexWrap: "wrap",
                  gap: 1,
                  mb: 1,
                }}
              >
                <Typography
                  variant="h6"
                  fontWeight={600}
                >
                  Duplicate Detection Trend
                </Typography>

                {loading && (
                  <CircularProgress
                    size={20}
                  />
                )}
              </Box>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mb: 2 }}
              >
                Recent completed scans for the selected period.
              </Typography>

              <Box sx={{ height: 315 }}>
                <DuplicateTrendChart
                  data={trendData}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, lg: 4 }}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: 2,
              height: 430,
            }}
          >
            <CardContent
              sx={{
                height: "100%",
                boxSizing:
                  "border-box",
              }}
            >
              <Typography
                variant="h6"
                fontWeight={600}
                sx={{ mb: 1 }}
              >
                Top Duplicate Sources
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mb: 2 }}
              >
                Distribution across the highest-risk applications only.
              </Typography>

              <Box
                sx={{
                  height: 315,
                  display: "flex",
                  justifyContent:
                    "center",
                  alignItems:
                    "center",
                }}
              >
                <DuplicateSourceChart
                  data={sourceData}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </PageContainer>
  );
};


export default Dashboard;
