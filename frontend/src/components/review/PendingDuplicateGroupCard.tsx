import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import type {
  ReviewDecision,
  StandaloneReviewCandidate,
} from "../../services/reviewService";


export type PendingGroupCandidate =
  StandaloneReviewCandidate & {
    integrationId: number | null;
    integrationName: string | null;
  };


interface Props {
  candidate: PendingGroupCandidate;
  saving: boolean;
  onDecision: (
    candidate: PendingGroupCandidate,
    decision: ReviewDecision,
  ) => void;
}


const displayValue = (
  account: Record<string, unknown>,
  key: string,
): string => {
  const value = account[key];

  if (
    value === null
    || value === undefined
    || String(value).trim() === ""
  ) {
    return "Not available";
  }

  return String(value);
};


const PendingDuplicateGroupCard = ({
  candidate,
  saving,
  onDecision,
}: Props) => {
  const account1 = candidate.account1 ?? {};
  const account2 = candidate.account2 ?? {};

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2.5,
        borderRadius: 3,
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 2,
          flexWrap: "wrap",
        }}
      >
        <Box>
          <Typography
            variant="overline"
            color="text.secondary"
            fontWeight={700}
          >
            Possible Duplicate #{candidate.id}
          </Typography>

          <Stack
            direction="row"
            spacing={1}
            useFlexGap
            flexWrap="wrap"
            sx={{ mb: 1 }}
          >
            <Chip
              size="small"
              label="Pending Review"
              color="warning"
            />
            <Chip
              size="small"
              label={`${candidate.confidence}% confidence`}
              color="warning"
              variant="outlined"
            />
            <Chip
              size="small"
              label={candidate.reviewReason.replaceAll("_", " ")}
              variant="outlined"
            />
          </Stack>

          <Typography
            variant="h6"
            fontWeight={700}
          >
            {displayValue(account1, "username")}
            {"  ↔  "}
            {displayValue(account2, "username")}
          </Typography>

          <Typography
            variant="caption"
            color="text.secondary"
          >
            Integration:{" "}
            {candidate.integrationName
              ?? (
                candidate.integrationId
                  ? `#${candidate.integrationId}`
                  : "Legacy upload"
              )}
            {" · "}
            Scan #{candidate.scanId}
          </Typography>
        </Box>

        <Stack
          direction="row"
          spacing={1}
          useFlexGap
          flexWrap="wrap"
        >
          <Button
            size="small"
            variant="contained"
            color="success"
            disabled={saving}
            onClick={() =>
              onDecision(candidate, "DUPLICATE")
            }
          >
            Confirm Duplicate
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="error"
            disabled={saving}
            onClick={() =>
              onDecision(candidate, "NOT_DUPLICATE")
            }
          >
            Not Duplicate
          </Button>
          <Button
            size="small"
            variant="outlined"
            disabled={saving}
            onClick={() =>
              onDecision(candidate, "UNCERTAIN")
            }
          >
            Uncertain
          </Button>
        </Stack>
      </Box>

      <Divider sx={{ my: 2 }} />

      <Grid container spacing={2}>
        {[
          ["Account 1", account1],
          ["Account 2", account2],
        ].map(([label, account]) => (
          <Grid
            key={String(label)}
            size={{ xs: 12, md: 6 }}
          >
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                borderRadius: 2,
                height: "100%",
              }}
            >
              <Typography
                fontWeight={700}
                sx={{ mb: 1 }}
              >
                {String(label)}
              </Typography>
              <Typography variant="body2">
                Display Name: {displayValue(
                  account as Record<string, unknown>,
                  "displayName",
                )}
              </Typography>
              <Typography variant="body2">
                Email: {displayValue(
                  account as Record<string, unknown>,
                  "email",
                )}
              </Typography>
              <Typography variant="body2">
                Employee ID: {displayValue(
                  account as Record<string, unknown>,
                  "employeeId",
                )}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {saving && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            mt: 2,
          }}
        >
          <CircularProgress size={16} />
          <Typography
            variant="caption"
            color="text.secondary"
          >
            Saving decision...
          </Typography>
        </Box>
      )}
    </Paper>
  );
};


export default PendingDuplicateGroupCard;
