import { useEffect, useState } from "react";
import {
  Box,
  Grid,
  Typography,
  FormControl,
  Select,
  MenuItem,
  Card,
  CardContent,
  CircularProgress,
} from "@mui/material";

import PageContainer from "../../components/common/PageContainer";
import KpiCard from "../../components/dashboard/KpiCard";
import DuplicateTrendChart from "../../components/dashboard/DuplicateTrendChart";
import DuplicateSourceChart from "../../components/dashboard/DuplicateSourceChart";

import {
  getDashboardSummary,
  DashboardSummary,
} from "../../services/dashboardService";

const dashboardData = {
  Daily: {
    trendData: [
      { name: "Mon", duplicates: 18 },
      { name: "Tue", duplicates: 24 },
      { name: "Wed", duplicates: 19 },
      { name: "Thu", duplicates: 28 },
      { name: "Fri", duplicates: 35 },
      { name: "Sat", duplicates: 14 },
      { name: "Sun", duplicates: 10 },
    ],
  },

  Weekly: {
    trendData: [
      { name: "Week 1", duplicates: 140 },
      { name: "Week 2", duplicates: 185 },
      { name: "Week 3", duplicates: 205 },
      { name: "Week 4", duplicates: 234 },
    ],
  },

  Monthly: {
    trendData: [
      { name: "Jan", duplicates: 182 },
      { name: "Feb", duplicates: 205 },
      { name: "Mar", duplicates: 248 },
      { name: "Apr", duplicates: 310 },
      { name: "May", duplicates: 392 },
      { name: "Jun", duplicates: 455 },
    ],
  },
};

const Dashboard = () => {
  const [period, setPeriod] = useState("Daily");

  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const data = await getDashboardSummary();
        setSummary(data);
      } catch (error) {
        console.error("Failed to load dashboard", error);
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  const trend =
    dashboardData[period as keyof typeof dashboardData];

  if (loading) {
    return (
      <PageContainer title="Dashboard">
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            mt: 10,
          }}
        >
          <CircularProgress />
        </Box>
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Dashboard">
      {/* Header */}

      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 4,
          flexWrap: "wrap",
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Duplicate Account Analytics
          </Typography>

          <Typography variant="body2" color="text.secondary">
            AI-powered duplicate account detection across enterprise applications
          </Typography>
        </Box>

        <FormControl size="small" sx={{ minWidth: 180 }}>
          <Select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
          >
            <MenuItem value="Daily">Today</MenuItem>
            <MenuItem value="Weekly">Last 7 Days</MenuItem>
            <MenuItem value="Monthly">Last 30 Days</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* KPI Cards */}

      <Grid container spacing={3} mb={4}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <KpiCard
            title="Accounts Scanned"
            value={summary?.accountsScanned.toLocaleString() ?? "0"}
            color="#1976d2"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <KpiCard
            title="Applications"
            value={summary?.applications ?? 0}
            color="#6a1b9a"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <KpiCard
            title="Duplicate Groups"
            value={summary?.duplicateGroups ?? 0}
            color="#d32f2f"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <KpiCard
            title="High Confidence"
            value={summary?.highConfidence ?? 0}
            color="#2e7d32"
          />
        </Grid>
      </Grid>

      {/* Charts */}

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: 3,
              height: 430,
            }}
          >
            <CardContent sx={{ height: "100%" }}>
              <Typography variant="h6" fontWeight={600} mb={2}>
                Duplicate Detection Trend
              </Typography>

              <Box sx={{ height: 340 }}>
                <DuplicateTrendChart
                  data={trend.trendData}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, lg: 4 }}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: 3,
              height: 430,
            }}
          >
            <CardContent sx={{ height: "100%" }}>
              <Typography variant="h6" fontWeight={600} mb={2}>
                Duplicate Source Distribution
              </Typography>

              <Box
                sx={{
                  height: 340,
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <DuplicateSourceChart />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </PageContainer>
  );
};

export default Dashboard;