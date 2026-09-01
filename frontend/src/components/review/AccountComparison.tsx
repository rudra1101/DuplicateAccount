import { useEffect, useState } from "react";

import {
  Alert,
  Box,
  Chip,
  Divider,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import type {
  DuplicateCandidate,
  DuplicateGroup,
  DuplicateGroupDetails,
} from "../../services/reviewService";

import DuplicateCandidateList from "./DuplicateCandidateList";
import CandidateDecisionPanel from "./CandidateDecisionPanel";

interface Props {
  pair: DuplicateGroup | null;
  details: DuplicateGroupDetails | null;
  onReviewStateChanged?: () => void | Promise<void>;
}

type MatchStatus = "match" | "different" | "missing";

const displayValue = (
  value: string | number | null | undefined,
): string => {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }
  return String(value);
};

const normalizeValue = (
  value: string | number | null | undefined,
): string => {
  if (value === null || value === undefined) return "";
  return String(value).trim().toLowerCase();
};

const getMatchStatus = (
  primaryValue: string | number | null | undefined,
  duplicateValue: string | number | null | undefined,
  backendLabel: string,
  matchedAttributes: string[],
): MatchStatus => {
  const primary = normalizeValue(primaryValue);
  const duplicate = normalizeValue(duplicateValue);

  if (!primary && !duplicate) return "missing";
  if (primary === duplicate || matchedAttributes.includes(backendLabel)) {
    return "match";
  }
  return "different";
};

const AccountComparison = ({
  pair,
  details,
  onReviewStateChanged,
}: Props) => {
  const [selectedCandidate, setSelectedCandidate] =
    useState<DuplicateCandidate | null>(null);

  useEffect(() => {
    setSelectedCandidate(details?.duplicates?.[0] ?? null);
  }, [details]);

  if (!pair) {
    return (
      <Paper
        variant="outlined"
        sx={{
          width: "100%",
          height: "100%",
          minHeight: 500,
          borderRadius: 3,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          p: 4,
        }}
      >
        <Box textAlign="center">
          <Typography variant="h5" fontWeight={700}>
            No duplicate group selected
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Select a group from the left panel.
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (!details) {
    return (
      <Paper
        variant="outlined"
        sx={{
          width: "100%",
          height: "100%",
          minHeight: 500,
          borderRadius: 3,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Typography>Loading account details...</Typography>
      </Paper>
    );
  }

  if (!details.primaryAccount || !details.duplicates?.length) {
    return (
      <Paper
        variant="outlined"
        sx={{ width: "100%", height: "100%", minHeight: 500, borderRadius: 3, p: 4 }}
      >
        <Alert severity="info">No duplicate candidates were found.</Alert>
      </Paper>
    );
  }

  if (!selectedCandidate) {
    return (
      <Paper
        variant="outlined"
        sx={{ width: "100%", height: "100%", minHeight: 500, borderRadius: 3, p: 4 }}
      >
        <Alert severity="info">Select a duplicate candidate.</Alert>
      </Paper>
    );
  }

  const duplicate = selectedCandidate;
  const matchedAttributes = duplicate.matchedAttributes ?? [];

  const rows = [
    { label: "Username", primary: details.primaryAccount.username, duplicate: duplicate.account.username },
    { label: "Display Name", primary: details.primaryAccount.displayName, duplicate: duplicate.account.displayName },
    { label: "Email", primary: details.primaryAccount.email, duplicate: duplicate.account.email },
    { label: "Employee ID", primary: details.primaryAccount.employeeId, duplicate: duplicate.account.employeeId },
    { label: "Department", primary: details.primaryAccount.department, duplicate: duplicate.account.department },
    { label: "Manager", primary: details.primaryAccount.manager, duplicate: duplicate.account.manager },
    { label: "Status", primary: details.primaryAccount.status, duplicate: duplicate.account.status },
    { label: "Created", primary: details.primaryAccount.created, duplicate: duplicate.account.created },
  ];

  return (
    <Box
      sx={{
        width: "100%",
        height: { xs: "auto", lg: "100%" },
        minWidth: 0,
        minHeight: 0,
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "300px minmax(0, 1fr)" },
        gap: 2,
        alignItems: "stretch",
        overflow: { xs: "visible", lg: "hidden" },
      }}
    >
      <Paper
        variant="outlined"
        sx={{
          width: "100%",
          height: { xs: 480, lg: "100%" },
          minHeight: 0,
          boxSizing: "border-box",
          borderRadius: 3,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            px: 2,
            py: 1.75,
            borderBottom: 1,
            borderColor: "divider",
            flexShrink: 0,
            backgroundColor: "background.paper",
          }}
        >
          <Typography variant="h6" fontWeight={700}>
            Possible Duplicates
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Primary: {details.primaryAccount.username}
          </Typography>
        </Box>

        <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden", p: 1.5 }}>
          <DuplicateCandidateList
            candidates={details.duplicates}
            selectedCandidateId={selectedCandidate.id}
            onSelect={setSelectedCandidate}
          />
        </Box>
      </Paper>

      <Paper
        variant="outlined"
        sx={{
          width: "100%",
          height: { xs: "auto", lg: "100%" },
          minWidth: 0,
          minHeight: 0,
          boxSizing: "border-box",
          borderRadius: 3,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            px: { xs: 2, md: 3 },
            py: 2,
            borderBottom: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
            flexShrink: 0,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box>
            <Typography variant="h5" fontWeight={700}>
              Account Comparison
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {details.primaryAccount.username} vs {duplicate.account.username}
            </Typography>
          </Box>

          <Stack direction="row" spacing={1}>
            <Chip
              size="small"
              label={duplicate.recommendation}
              color={duplicate.recommendation === "MERGE" ? "success" : "warning"}
            />
            <Chip
              size="small"
              label={`${duplicate.confidence}% confidence`}
              color={
                duplicate.confidence >= 95
                  ? "success"
                  : duplicate.confidence >= 80
                    ? "warning"
                    : "error"
              }
              variant="outlined"
            />
          </Stack>
        </Box>

        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            overflowY: "auto",
            overflowX: "hidden",
            px: { xs: 2, md: 3 },
            py: 2,
          }}
        >
          <Box sx={{ overflowX: "auto" }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell><strong>Attribute</strong></TableCell>
                  <TableCell><strong>Primary Account</strong></TableCell>
                  <TableCell><strong>Duplicate Candidate</strong></TableCell>
                  <TableCell align="center"><strong>Result</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => {
                  const status = getMatchStatus(
                    row.primary,
                    row.duplicate,
                    row.label,
                    matchedAttributes,
                  );
                  return (
                    <TableRow key={row.label} hover>
                      <TableCell><Typography fontWeight={600}>{row.label}</Typography></TableCell>
                      <TableCell>{displayValue(row.primary)}</TableCell>
                      <TableCell>{displayValue(row.duplicate)}</TableCell>
                      <TableCell align="center">
                        <Chip
                          size="small"
                          label={
                            status === "match"
                              ? "Match"
                              : status === "different"
                                ? "Different"
                                : "Missing data"
                          }
                          color={
                            status === "match"
                              ? "success"
                              : status === "different"
                                ? "warning"
                                : "default"
                          }
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" fontWeight={700} gutterBottom>
            AI Recommendation
          </Typography>
          <Alert
            severity={duplicate.recommendation === "MERGE" ? "success" : "warning"}
            sx={{ mb: 3 }}
          >
            AI recommends <strong>{duplicate.recommendation}</strong> with{" "}
            <strong>{duplicate.confidence}% confidence</strong>.
          </Alert>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
              gap: 2,
            }}
          >
            <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
              <Typography fontWeight={700} sx={{ mb: 2 }}>Matched Attributes</Typography>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                {matchedAttributes.length > 0 ? (
                  matchedAttributes.map((attribute) => (
                    <Chip key={attribute} size="small" label={attribute} color="success" variant="outlined" />
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No matched attributes reported.
                  </Typography>
                )}
              </Stack>
            </Paper>

            <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
              <Typography fontWeight={700} sx={{ mb: 2 }}>Different Attributes</Typography>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                {duplicate.differentAttributes.length > 0 ? (
                  duplicate.differentAttributes.map((attribute) => (
                    <Chip key={attribute} size="small" label={attribute} color="warning" variant="outlined" />
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No different attributes reported.
                  </Typography>
                )}
              </Stack>
            </Paper>
          </Box>

          <Divider sx={{ my: 3 }} />

          {duplicate.candidateRecordId ? (
            <CandidateDecisionPanel
              candidateRecordId={duplicate.candidateRecordId}
              currentDecision={duplicate.reviewDecision}
              currentComment={duplicate.reviewComment}
              currentReviewerName={duplicate.reviewerName}
              reviewedAt={duplicate.reviewedAt}
              onDecisionSaved={async (response) => {
                setSelectedCandidate((current) =>
                  current
                    ? {
                        ...current,
                        reviewDecision: response.decision,
                        reviewComment: response.comment,
                        reviewerName: response.reviewerName,
                        reviewedAt: response.reviewedAt,
                      }
                    : current,
                );

                if (
                  response.decision === "DUPLICATE"
                  || response.decision === "NOT_DUPLICATE"
                ) {
                  await onReviewStateChanged?.();
                }
              }}
            />
          ) : (
            <Alert severity="warning">
              Candidate database ID is unavailable. Refresh this duplicate group after restarting the backend.
            </Alert>
          )}
        </Box>
      </Paper>
    </Box>
  );
};

export default AccountComparison;
