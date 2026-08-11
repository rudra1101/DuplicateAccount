import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  MenuItem,
  Select,
  Stack,
  Typography,
} from "@mui/material";

import type {
  SelectChangeEvent,
} from "@mui/material/Select";

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

    loadDashboard();

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
            Combined analytics from
            the latest completed scan
            of every integration.
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
      </Box>

      <Stack
        direction="row"
        spacing={1}
        useFlexGap
        flexWrap="wrap"
        sx={{ mb: 3 }}
      >
        {scans.map(
          (scanItem) => (
            <Chip
              key={[
                scanItem.integrationId
                  ?? "legacy",
                scanItem.id,
              ].join(":")}
              label={
                `${
                  scanItem.integrationName
                    ?? (
                      scanItem.integrationId
                        ? (
                          `Integration #${
                            scanItem.integrationId
                          }`
                        )
                        : "Legacy"
                    )
                } · Scan #${scanItem.id}`
              }
              variant="outlined"
              color="primary"
              size="small"
            />
          ),
        )}
      </Stack>

      <Grid
        container
        spacing={3}
        sx={{ mb: 4 }}
      >
        <Grid
          size={{
            xs: 12,
            sm: 6,
            lg: 2.4,
          }}
        >
          <KpiCard
            title="Accounts Scanned"
            value={Number(
              summary.accountsScanned
              ?? 0,
            ).toLocaleString()}
            color="#1976d2"
          />
        </Grid>

        <Grid
          size={{
            xs: 12,
            sm: 6,
            lg: 2.4,
          }}
        >
          <KpiCard
            title="Integrations"
            value={
              summary.integrations
              ?? 0
            }
            color="#455a64"
          />
        </Grid>

        <Grid
          size={{
            xs: 12,
            sm: 6,
            lg: 2.4,
          }}
        >
          <KpiCard
            title="Applications"
            value={
              summary.applications
              ?? 0
            }
            color="#6a1b9a"
          />
        </Grid>

        <Grid
          size={{
            xs: 12,
            sm: 6,
            lg: 2.4,
          }}
        >
          <KpiCard
            title="Duplicate Groups"
            value={
              summary.duplicateGroups
              ?? 0
            }
            color="#d32f2f"
          />
        </Grid>

        <Grid
          size={{
            xs: 12,
            sm: 6,
            lg: 2.4,
          }}
        >
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
        {scans.map(
          (scanItem) => (
            <Grid
              key={
                `scan-summary-${scanItem.id}`
              }
              size={{
                xs: 12,
                md: 6,
                lg: 4,
              }}
            >
              <Card
                variant="outlined"
                sx={{
                  borderRadius: 3,
                  height: "100%",
                }}
              >
                <CardContent>
                  <Typography
                    variant="h6"
                    fontWeight={700}
                  >
                    {scanItem.integrationName
                      ?? (
                        scanItem.integrationId
                          ? (
                            `Integration #${
                              scanItem.integrationId
                            }`
                          )
                          : "Legacy Scan"
                      )}
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.5 }}
                  >
                    {scanItem.filename}
                  </Typography>

                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      display: "block",
                      mt: 0.5,
                    }}
                  >
                    Scan #{scanItem.id}

                    {scanItem.createdAt
                      ? (
                        ` · ${formatDateTime(
                          scanItem.createdAt,
                          "Asia/Kolkata",
                        )}`
                      )
                      : ""}
                  </Typography>

                  <Box
                    sx={{
                      mt: 2,
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(2, 1fr)",
                      gap: 1.5,
                    }}
                  >
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        Accounts
                      </Typography>

                      <Typography
                        fontWeight={700}
                      >
                        {Number(
                          scanItem
                            .accountsScanned
                          ?? 0,
                        ).toLocaleString()}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        Applications
                      </Typography>

                      <Typography
                        fontWeight={700}
                      >
                        {scanItem
                          .applications
                          ?? 0}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        Duplicate Groups
                      </Typography>

                      <Typography
                        fontWeight={700}
                      >
                        {scanItem
                          .duplicateGroups
                          ?? 0}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        Duplicate Accounts
                      </Typography>

                      <Typography
                        fontWeight={700}
                      >
                        {scanItem
                          .duplicateAccounts
                          ?? 0}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ),
        )}
      </Grid>

      <Grid
        container
        spacing={3}
      >
        <Grid
          size={{
            xs: 12,
            lg: 8,
          }}
        >
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: 3,
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
                Completed integration scans
                for the selected period.
              </Typography>

              <Box sx={{ height: 315 }}>
                <DuplicateTrendChart
                  data={trendData}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid
          size={{
            xs: 12,
            lg: 4,
          }}
        >
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: 3,
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
                Duplicate Source Distribution
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mb: 2 }}
              >
                Duplicate accounts by
                application across the latest
                scan of every integration.
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