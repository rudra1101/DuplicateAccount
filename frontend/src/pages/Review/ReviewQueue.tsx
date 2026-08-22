import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Paper,
  Stack,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";

import RefreshIcon from "@mui/icons-material/Refresh";
import InboxOutlinedIcon from "@mui/icons-material/InboxOutlined";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";

import PageContainer from "../../components/common/PageContainer";

import ApplicationCard, {
  type ApplicationSummary,
} from "../../components/review/ApplicationCard";

import {
  type ReviewDecision,
  type ReviewSummary,
  type StandaloneReviewCandidate,
  getReviewQueue,
  getStandaloneReviewCandidates,
  submitStandaloneReviewDecision,
} from "../../services/reviewService";


type ReviewTab = "groups" | "candidates";

type CandidateWithIntegration =
  StandaloneReviewCandidate & {
    integrationId: number | null;
    integrationName: string | null;
  };


const displayValue = (
  account: Record<string, unknown>,
  key: string,
): string => {
  const value = account[key];

  if (
    value === null ||
    value === undefined ||
    String(value).trim() === ""
  ) {
    return "Not available";
  }

  return String(value);
};


const ReviewQueue = () => {
  const navigate = useNavigate();

  const [
    activeTab,
    setActiveTab,
  ] = useState<ReviewTab>("groups");

  const [
    applications,
    setApplications,
  ] = useState<ReviewSummary[]>([]);

  const [
    reviewCandidates,
    setReviewCandidates,
  ] = useState<CandidateWithIntegration[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  const [
    candidateError,
    setCandidateError,
  ] = useState("");

  const [
    savingCandidateId,
    setSavingCandidateId,
  ] = useState<number | null>(null);


  const loadApplications =
    useCallback(async () => {
      try {
        setLoading(true);
        setError("");
        setCandidateError("");

        const data =
          await getReviewQueue();

        const summaries =
          Array.isArray(data)
            ? data
            : [];

        setApplications(summaries);

        const integrationMap =
          new Map<
            string,
            {
              integrationId: number | null;
              integrationName: string | null;
            }
          >();

        for (const summary of summaries) {
          const key =
            summary.integrationId === null
              ? "legacy"
              : String(summary.integrationId);

          if (!integrationMap.has(key)) {
            integrationMap.set(key, {
              integrationId:
                summary.integrationId,
              integrationName:
                summary.integrationName,
            });
          }
        }

        const sources =
          Array.from(
            integrationMap.values(),
          );

        const candidateResults =
          await Promise.allSettled(
            sources.map(
              async (source) => {
                const candidates =
                  await getStandaloneReviewCandidates(
                    source.integrationId,
                  );

                return candidates.map(
                  (candidate) => ({
                    ...candidate,
                    integrationId:
                      source.integrationId,
                    integrationName:
                      source.integrationName,
                  }),
                );
              },
            ),
          );

        const loadedCandidates:
          CandidateWithIntegration[] = [];

        const candidateFailures:
          string[] = [];

        for (
          const result of candidateResults
        ) {
          if (
            result.status === "fulfilled"
          ) {
            loadedCandidates.push(
              ...result.value,
            );
          } else {
            candidateFailures.push(
              result.reason instanceof Error
                ? result.reason.message
                : "Unable to load review candidates.",
            );
          }
        }

        loadedCandidates.sort(
          (left, right) =>
            right.confidence
            - left.confidence,
        );

        setReviewCandidates(
          loadedCandidates,
        );

        if (candidateFailures.length > 0) {
          setCandidateError(
            candidateFailures[0],
          );
        }
      } catch (loadError) {
        console.error(
          "Unable to load review queue:",
          loadError,
        );

        setError(
          loadError instanceof Error
            ? loadError.message
            : (
              "Unable to load "
              + "duplicate-account "
              + "review data."
            ),
        );
      } finally {
        setLoading(false);
      }
    }, []);


  useEffect(() => {
    loadApplications();
  }, [loadApplications]);


  const handleViewDetails = (
    summary: ReviewSummary,
  ) => {
    const query = new URLSearchParams();

    if (
      summary.integrationId !== null
    ) {
      query.set(
        "integrationId",
        String(summary.integrationId),
      );
    }

    if (summary.integrationName) {
      query.set(
        "integrationName",
        summary.integrationName,
      );
    }

    if (summary.scanId) {
      query.set(
        "scanId",
        String(summary.scanId),
      );
    }

    const queryString =
      query.toString();

    navigate(
      `/review/${encodeURIComponent(
        summary.application,
      )}${
        queryString
          ? `?${queryString}`
          : ""
      }`,
    );
  };


  const handleCandidateDecision =
    async (
      candidate: CandidateWithIntegration,
      decision: ReviewDecision,
    ) => {
      try {
        setSavingCandidateId(
          candidate.id,
        );
        setCandidateError("");

        await submitStandaloneReviewDecision(
          candidate.id,
          {
            decision,
          },
        );

        setReviewCandidates(
          (current) =>
            current.filter(
              (item) =>
                item.id !== candidate.id,
            ),
        );
      } catch (saveError) {
        console.error(
          "Unable to save review candidate decision:",
          saveError,
        );

        setCandidateError(
          saveError instanceof Error
            ? saveError.message
            : "Unable to save the review decision.",
        );
      } finally {
        setSavingCandidateId(null);
      }
    };


  const candidateCountLabel =
    useMemo(
      () => `Review Candidates (${reviewCandidates.length})`,
      [reviewCandidates.length],
    );


  return (
    <PageContainer title="Review Queue">
      <Box
        sx={{
          display: "flex",
          justifyContent:
            "space-between",
          alignItems:
            "flex-start",
          flexWrap: "wrap",
          gap: 2,
          mb: 3,
        }}
      >
        <Box>
          <Typography
            variant="h5"
            fontWeight={700}
          >
            Review Duplicate Accounts
          </Typography>

          <Typography
            variant="body1"
            color="text.secondary"
            sx={{ mt: 1 }}
          >
            Review confirmed duplicate groups
            and evidence-aware candidates from
            the latest completed integration scans.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={
            loading
              ? (
                <CircularProgress
                  size={18}
                />
              )
              : <RefreshIcon />
          }
          onClick={loadApplications}
          disabled={loading}
        >
          {loading
            ? "Refreshing..."
            : "Refresh"}
        </Button>
      </Box>

      <Paper
        variant="outlined"
        sx={{
          borderRadius: 3,
          mb: 3,
          overflow: "hidden",
        }}
      >
        <Tabs
          value={activeTab}
          onChange={(
            _event,
            value: ReviewTab,
          ) => setActiveTab(value)}
          sx={{ px: 1 }}
        >
          <Tab
            value="groups"
            label="Duplicate Groups"
          />
          <Tab
            value="candidates"
            label={candidateCountLabel}
          />
        </Tabs>
      </Paper>

      {loading && (
        <Box
          sx={{
            minHeight: 300,
            display: "flex",
            alignItems: "center",
            justifyContent:
              "center",
          }}
        >
          <CircularProgress />
        </Box>
      )}

      {!loading && error && (
        <Alert
          severity="error"
          action={
            <Button
              color="inherit"
              size="small"
              onClick={
                loadApplications
              }
            >
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {!loading
        && !error
        && activeTab === "groups"
        && applications.length === 0
        && (
          <Paper
            variant="outlined"
            sx={{
              p: 6,
              borderRadius: 3,
              textAlign: "center",
              borderStyle:
                "dashed",
            }}
          >
            <InboxOutlinedIcon
              sx={{
                fontSize: 64,
                color:
                  "text.secondary",
                mb: 2,
              }}
            />

            <Typography
              variant="h6"
              fontWeight={700}
            >
              No duplicate accounts available
            </Typography>

            <Typography
              color="text.secondary"
              sx={{ mt: 1 }}
            >
              Run an integration or upload
              account data to create a scan.
            </Typography>

            <Button
              variant="contained"
              sx={{ mt: 3 }}
              onClick={() =>
                navigate("/integrations")
              }
            >
              View Integrations
            </Button>
          </Paper>
        )}

      {!loading
        && !error
        && activeTab === "groups"
        && applications.length > 0
        && (
          <Grid
            container
            spacing={3}
          >
            {applications.map(
              (summary) => {
                const cardData =
                  summary as ApplicationSummary;

                return (
                  <Grid
                    key={[
                      summary.integrationId
                        ?? "legacy",
                      summary.scanId,
                      summary.application,
                    ].join(":")}
                    size={{
                      xs: 12,
                      sm: 6,
                      md: 4,
                      lg: 3,
                    }}
                  >
                    <Box
                      sx={{
                        height: "100%",
                        position: "relative",
                      }}
                    >
                      <ApplicationCard
                        application={
                          cardData
                        }
                        onView={() =>
                          handleViewDetails(
                            summary,
                          )
                        }
                      />

                      <Box
                        sx={{
                          mt: 1,
                          px: 0.5,
                        }}
                      >
                        <Typography
                          variant="caption"
                          color="text.secondary"
                        >
                          Integration:{" "}
                          <strong>
                            {summary.integrationName
                              ?? (
                                summary.integrationId
                                  ? `#${summary.integrationId}`
                                  : "Legacy upload"
                              )}
                          </strong>
                          {" · "}
                          Scan #{summary.scanId}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                );
              },
            )}
          </Grid>
        )}

      {!loading
        && !error
        && activeTab === "candidates"
        && (
          <Box>
            {candidateError && (
              <Alert
                severity="error"
                sx={{ mb: 2 }}
              >
                {candidateError}
              </Alert>
            )}

            {reviewCandidates.length === 0 ? (
              <Paper
                variant="outlined"
                sx={{
                  p: 6,
                  borderRadius: 3,
                  textAlign: "center",
                  borderStyle: "dashed",
                }}
              >
                <CompareArrowsIcon
                  sx={{
                    fontSize: 64,
                    color: "text.secondary",
                    mb: 2,
                  }}
                />
                <Typography
                  variant="h6"
                  fontWeight={700}
                >
                  No pending review candidates
                </Typography>
                <Typography
                  color="text.secondary"
                  sx={{ mt: 1 }}
                >
                  Evidence-aware candidates will
                  appear here when a scan finds
                  uncertain duplicate pairs.
                </Typography>
              </Paper>
            ) : (
              <Stack spacing={2}>
                {reviewCandidates.map(
                  (candidate) => {
                    const account1 =
                      candidate.account1 ?? {};
                    const account2 =
                      candidate.account2 ?? {};
                    const isSaving =
                      savingCandidateId
                      === candidate.id;

                    return (
                      <Paper
                        key={candidate.id}
                        variant="outlined"
                        sx={{
                          p: 2.5,
                          borderRadius: 3,
                        }}
                      >
                        <Box
                          sx={{
                            display: "flex",
                            justifyContent:
                              "space-between",
                            alignItems: "flex-start",
                            gap: 2,
                            flexWrap: "wrap",
                          }}
                        >
                          <Box>
                            <Stack
                              direction="row"
                              spacing={1}
                              useFlexGap
                              flexWrap="wrap"
                              sx={{ mb: 1 }}
                            >
                              <Chip
                                size="small"
                                label={`${candidate.confidence}% confidence`}
                                color="warning"
                                variant="outlined"
                              />
                              <Chip
                                size="small"
                                label={candidate.reviewReason
                                  .replaceAll("_", " ")}
                                variant="outlined"
                              />
                              <Chip
                                size="small"
                                label={candidate.application}
                              />
                            </Stack>

                            <Typography
                              variant="h6"
                              fontWeight={700}
                            >
                              {displayValue(
                                account1,
                                "username",
                              )}
                              {"  ↔  "}
                              {displayValue(
                                account2,
                                "username",
                              )}
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
                              disabled={isSaving}
                              onClick={() =>
                                handleCandidateDecision(
                                  candidate,
                                  "DUPLICATE",
                                )
                              }
                            >
                              Confirm Duplicate
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              disabled={isSaving}
                              onClick={() =>
                                handleCandidateDecision(
                                  candidate,
                                  "NOT_DUPLICATE",
                                )
                              }
                            >
                              Not Duplicate
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              disabled={isSaving}
                              onClick={() =>
                                handleCandidateDecision(
                                  candidate,
                                  "UNCERTAIN",
                                )
                              }
                            >
                              Uncertain
                            </Button>
                          </Stack>
                        </Box>

                        <Divider sx={{ my: 2 }} />

                        <Grid
                          container
                          spacing={2}
                        >
                          <Grid
                            size={{
                              xs: 12,
                              md: 6,
                            }}
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
                                Account 1
                              </Typography>
                              <Typography variant="body2">
                                Display Name: {displayValue(
                                  account1,
                                  "displayName",
                                )}
                              </Typography>
                              <Typography variant="body2">
                                Email: {displayValue(
                                  account1,
                                  "email",
                                )}
                              </Typography>
                              <Typography variant="body2">
                                Employee ID: {displayValue(
                                  account1,
                                  "employeeId",
                                )}
                              </Typography>
                            </Paper>
                          </Grid>

                          <Grid
                            size={{
                              xs: 12,
                              md: 6,
                            }}
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
                                Account 2
                              </Typography>
                              <Typography variant="body2">
                                Display Name: {displayValue(
                                  account2,
                                  "displayName",
                                )}
                              </Typography>
                              <Typography variant="body2">
                                Email: {displayValue(
                                  account2,
                                  "email",
                                )}
                              </Typography>
                              <Typography variant="body2">
                                Employee ID: {displayValue(
                                  account2,
                                  "employeeId",
                                )}
                              </Typography>
                            </Paper>
                          </Grid>
                        </Grid>

                        {isSaving && (
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
                  },
                )}
              </Stack>
            )}
          </Box>
        )}
    </PageContainer>
  );
};


export default ReviewQueue;
