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

interface Details {
  confidence: number;
  recommendation: string;
  matchedAttributes: string[];
  differentAttributes: string[];
  account1: Account;
  account2: Account;
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
            Select a duplicate pair from the left panel.
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

  const rows = [
    {
      label: "Username",
      a: details.account1.username,
      b: details.account2.username,
      match: false,
    },
    {
      label: "Display Name",
      a: details.account1.displayName,
      b: details.account2.displayName,
      match: true,
    },
    {
      label: "Email",
      a: details.account1.email,
      b: details.account2.email,
      match: true,
    },
    {
      label: "Employee ID",
      a: details.account1.employeeId,
      b: details.account2.employeeId,
      match: true,
    },
    {
      label: "Department",
      a: details.account1.department,
      b: details.account2.department,
      match: true,
    },
    {
      label: "Manager",
      a: details.account1.manager,
      b: details.account2.manager,
      match: true,
    },
    {
      label: "Status",
      a: details.account1.status,
      b: details.account2.status,
      match: true,
    },
    {
      label: "Created",
      a: details.account1.created,
      b: details.account2.created,
      match: false,
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
            <TableCell>
              <strong>Attribute</strong>
            </TableCell>

            <TableCell>
              <strong>Account A</strong>
            </TableCell>

            <TableCell>
              <strong>Account B</strong>
            </TableCell>

            <TableCell align="center">
              <strong>Match</strong>
            </TableCell>
          </TableRow>
        </TableHead>

        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.label}>
              <TableCell>{row.label}</TableCell>

              <TableCell>{row.a}</TableCell>

              <TableCell>{row.b}</TableCell>

              <TableCell align="center">
                {row.match ? (
                  <Chip
                    label="Match"
                    color="success"
                    size="small"
                  />
                ) : (
                  <Chip
                    label="Different"
                    color="warning"
                    size="small"
                  />
                )}
              </TableCell>
            </TableRow>
          ))}
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

      <Alert severity="success" sx={{ mb: 3 }}>
        AI recommends <strong>{details.recommendation}</strong> with{" "}
        <strong>{details.confidence}% confidence</strong>.
      </Alert>

      <Grid container spacing={4}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Typography fontWeight={700} mb={2}>
            Matched Attributes
          </Typography>

          <Stack spacing={1}>
            {details.matchedAttributes.map((attr) => (
              <Chip
                key={attr}
                label={attr}
                color="success"
              />
            ))}
          </Stack>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Typography fontWeight={700} mb={2}>
            Different Attributes
          </Typography>

          <Stack spacing={1}>
            {details.differentAttributes.map((attr) => (
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

        <Button
          variant="outlined"
        >
          Ignore
        </Button>
      </Stack>
    </Paper>
  );
};

export default AccountComparison;