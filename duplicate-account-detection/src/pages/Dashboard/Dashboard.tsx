import { useState } from "react";
import {
  Box,
  Grid,
  FormControl,
  Select,
  MenuItem,
  Typography,
} from "@mui/material";

import PageContainer from "../../components/common/PageContainer";
import KpiCard from "../../components/dashboard/KpiCard";

const Dashboard = () => {
  const [period, setPeriod] = useState("Daily");

  const dashboardData = {
    Daily: {
      scannedAccounts: 8425,
      duplicateAccounts: 148,
      aiMatched: 121,
      pendingReview: 27,
    },
    Weekly: {
      scannedAccounts: 48236,
      duplicateAccounts: 764,
      aiMatched: 639,
      pendingReview: 125,
    },
    Monthly: {
      scannedAccounts: 184265,
      duplicateAccounts: 2861,
      aiMatched: 2397,
      pendingReview: 464,
    },
  };

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
    mb: 3,
  }}
>
  <Typography
    variant="h5"
    sx={{
      fontWeight: 600,
    }}
  >
    Duplicate Account Analytics
  </Typography>

  <FormControl size="small" sx={{ width: 170 }}>
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

      <Grid container spacing={3}>

        <Grid size={{ xs: 12, md: 3 }}>
          <KpiCard
            title="Accounts Scanned"
            value={stats.scannedAccounts.toLocaleString()}
            color="#1976d2"
          />
        </Grid>

        <Grid size={{ xs: 12, md: 3 }}>
          <KpiCard
            title="Duplicate Accounts"
            value={stats.duplicateAccounts}
            color="#d32f2f"
          />
        </Grid>

        <Grid size={{ xs: 12, md: 3 }}>
          <KpiCard
            title="AI Matched"
            value={stats.aiMatched}
            color="#2e7d32"
          />
        </Grid>

        <Grid size={{ xs: 12, md: 3 }}>
          <KpiCard
            title="Pending Review"
            value={stats.pendingReview}
            color="#ed6c02"
          />
        </Grid>

      </Grid>

    </PageContainer>
  );
};

export default Dashboard;