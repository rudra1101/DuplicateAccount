import {
  Paper,
  Typography,
  Grid,
  Divider,
  Chip,
  Stack,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Alert,
  Box,
} from "@mui/material";

import { DuplicatePair } from "./DuplicatePairCard";

interface Account {
  username: string;
  displayName: string;
  email: string;
  employeeId: string;
  department: string;
  manager: string;
  status: string;
  created: string;
}

interface DuplicateAccount {
  confidence: number;
  recommendation: string;
  matchedAttributes: string[];
  differentAttributes: string[];
  account: Account;
}

interface Details {
  primaryAccount: Account;
  duplicates: DuplicateAccount[];
}

interface Props {
  pair: DuplicatePair | null;
  details: Details | null;
}

const AccountComparison = ({
  pair,
  details,
}: Props) => {
  if (!pair) {
    return (
      <Paper
        sx={{
          p: 6,
          borderRadius: 3,
          minHeight: 700,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Box textAlign="center">
          <Typography variant="h5" fontWeight={700}>
            No Duplicate Selected
          </Typography>

          <Typography color="text.secondary" mt={2}>
            Select a duplicate group from the left panel.
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (!details) {
    return (
      <Paper
        sx={{
          p: 6,
          borderRadius: 3,
          minHeight: 700,
        }}
      >
        <Typography>Loading account details...</Typography>
      </Paper>
    );
  }

  if (details.duplicates.length === 0) {
    return (
      <Paper sx={{ p: 6, borderRadius: 3 }}>
        <Typography>No duplicate accounts found.</Typography>
      </Paper>
    );
  }

  const duplicate = details.duplicates[0];

  const rows = [
    {
      label: "Username",
      a: details.primaryAccount.username,
      b: duplicate.account.username,
    },
    {
      label: "Display Name",
      a: details.primaryAccount.displayName,
      b: duplicate.account.displayName,
    },
    {
      label: "Email",
      a: details.primaryAccount.email,
      b: duplicate.account.email,
    },
    {
      label: "Employee ID",
      a: details.primaryAccount.employeeId,
      b: duplicate.account.employeeId,
    },
    {
      label: "Department",
      a: details.primaryAccount.department,
      b: duplicate.account.department,
    },
    {
      label: "Manager",
      a: details.primaryAccount.manager,
      b: duplicate.account.manager,
    },
    {
      label: "Status",
      a: details.primaryAccount.status,
      b: duplicate.account.status,
    },
    {
      label: "Created",
      a: details.primaryAccount.created,
      b: duplicate.account.created,
    },
  ];

  return (
    <Paper
      sx={{
        p: 4,
        borderRadius: 3,
      }}
    >
      <Typography
        variant="h5"
        fontWeight={700}
        mb={3}
      >
        Account Comparison
      </Typography>

      <Table>
        <TableHead>
          <TableRow>
            <TableCell><strong>Attribute</strong></TableCell>
            <TableCell><strong>Primary Account</strong></TableCell>
            <TableCell><strong>Duplicate Account</strong></TableCell>
            <TableCell align="center">
              <strong>Match</strong>
            </TableCell>
          </TableRow>
        </TableHead>

        <TableBody>
          {rows.map((row) => {
            const match =
              duplicate.matchedAttributes.includes(row.label);

            return (
              <TableRow key={row.label}>
                <TableCell>{row.label}</TableCell>

                <TableCell>{row.a}</TableCell>

                <TableCell>{row.b}</TableCell>

                <TableCell align="center">
                  <Chip
                    label={match ? "Match" : "Different"}
                    color={match ? "success" : "warning"}
                    size="small"
                  />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      <Divider sx={{ my: 4 }} />

      <Typography
        variant="h6"
        fontWeight={700}
        gutterBottom
      >
        AI Recommendation
      </Typography>

      <Alert
        severity={
          duplicate.recommendation === "MERGE"
            ? "success"
            : "warning"
        }
        sx={{ mb: 3 }}
      >
        AI recommends{" "}
        <strong>{duplicate.recommendation}</strong> with{" "}
        <strong>{duplicate.confidence}% confidence</strong>.
      </Alert>

      <Grid container spacing={4}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Typography
            fontWeight={700}
            mb={2}
          >
            Matched Attributes
          </Typography>

          <Stack spacing={1}>
            {duplicate.matchedAttributes.map((attr) => (
              <Chip
                key={attr}
                label={attr}
                color="success"
              />
            ))}
          </Stack>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Typography
            fontWeight={700}
            mb={2}
          >
            Different Attributes
          </Typography>

          <Stack spacing={1}>
            {duplicate.differentAttributes.map((attr) => (
              <Chip
                key={attr}
                label={attr}
                color="warning"
              />
            ))}
          </Stack>
        </Grid>
      </Grid>

      <Divider sx={{ my: 4 }} />

      <Typography
        variant="h6"
        fontWeight={700}
        gutterBottom
      >
        Reviewer Decision
      </Typography>

      <Stack direction="row" spacing={2}>
        <Button
          variant="contained"
          color="success"
        >
          Approve Merge
        </Button>

        <Button
          variant="contained"
          color="error"
        >
          Reject
        </Button>

        <Button variant="outlined">
          Ignore
        </Button>
      </Stack>
    </Paper>
  );
};

export default AccountComparison;