import { useState } from "react";
import {
  Box,
  Grid,
  Typography,
  FormControl,
  Select,
  MenuItem,
  Card,
  CardContent,
} from "@mui/material";

import PageContainer from "../../components/common/PageContainer";
import KpiCard from "../../components/dashboard/KpiCard";
import DuplicateTrendChart from "../../components/dashboard/DuplicateTrendChart";
import DuplicateSourceChart from "../../components/dashboard/DuplicateSourceChart";

const dashboardData = {
  Daily: {
    scannedAccounts: 8425,
    duplicateAccounts: 148,
    aiMatched: 121,
    pendingReview: 27,
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
    scannedAccounts: 48236,
    duplicateAccounts: 764,
    aiMatched: 639,
    pendingReview: 125,
    trendData: [
      { name: "Week 1", duplicates: 140 },
      { name: "Week 2", duplicates: 185 },
      { name: "Week 3", duplicates: 205 },
      { name: "Week 4", duplicates: 234 },
    ],
  },

  Monthly: {
    scannedAccounts: 184265,
    duplicateAccounts: 2861,
    aiMatched: 2397,
    pendingReview: 464,
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

  const stats =
    dashboardData[period as keyof typeof dashboardData];

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
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
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

      {/* KPI */}

      <Grid container spacing={3} mb={4}>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <KpiCard
            title="Accounts Scanned"
            value={stats.scannedAccounts.toLocaleString()}
            color="#1976d2"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <KpiCard
            title="Duplicate Accounts"
            value={stats.duplicateAccounts}
            color="#d32f2f"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <KpiCard
            title="AI Matched"
            value={stats.aiMatched}
            color="#2e7d32"
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <KpiCard
            title="Pending Review"
            value={stats.pendingReview}
            color="#ed6c02"
          />
        </Grid>

      </Grid>

      {/* Charts */}

      <Grid container spacing={3}>

        {/* Trend Chart */}

        <Grid size={{ xs: 12, lg: 8 }}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: 3,
              height: 430,
            }}
          >
            <CardContent sx={{ height: "100%" }}>

              <Typography
                variant="h6"
                sx={{
                  fontWeight: 600,
                  mb: 2,
                }}
              >
                Duplicate Detection Trend
              </Typography>

              <Box sx={{ height: 340 }}>
                <DuplicateTrendChart
                  data={stats.trendData}
                />
              </Box>

            </CardContent>
          </Card>
        </Grid>

        {/* Source Chart */}

        <Grid size={{ xs: 12, lg: 4 }}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: 3,
              height: 430,
            }}
          >
            <CardContent sx={{ height: "100%" }}>

              <Typography
                variant="h6"
                sx={{
                  fontWeight: 600,
                  mb: 2,
                }}
              >
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