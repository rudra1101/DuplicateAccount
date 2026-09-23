import {
  useCallback,
  useEffect,
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
  Grid,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import RefreshIcon from "@mui/icons-material/Refresh";
import InboxOutlinedIcon from "@mui/icons-material/InboxOutlined";

import PageContainer from "../../components/common/PageContainer";

import ApplicationCard, {
  type ApplicationSummary,
} from "../../components/review/ApplicationCard";

import {
  type ReviewSummary,
  type StandaloneReviewCandidate,
  getReviewQueue,
  getStandaloneReviewCandidates,
} from "../../services/reviewService";


type CandidateWithIntegration =
  StandaloneReviewCandidate & {
    integrationId: number | null;
    integrationName: string | null;
  };


const ReviewQueue = () => {
  const navigate = useNavigate();

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
                : "Unable to load possible duplicates.",
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


  const totalPossibleDuplicates =
    applications.reduce(
      (total, application) =>
        total + application.duplicateAccounts,
      0,
    )
    + reviewCandidates.length;


  return (
    <PageContainer title="Review Possible Duplicates">
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
            Review Possible Duplicates
          </Typography>

          <Typography
            variant="body1"
            color="text.secondary"
            sx={{ mt: 1 }}
          >
            Review all accounts flagged as possible duplicates by application. The status identifies
            which possible duplicates still require a decision.
          </Typography>

          <Stack
            direction="row"
            spacing={1}
            useFlexGap
            flexWrap="wrap"
            sx={{ mt: 1.5 }}
          >
            <Chip
              size="small"
              label={`${totalPossibleDuplicates.toLocaleString()} possible duplicates`}
              variant="outlined"
            />
            <Chip
              size="small"
              label={`${reviewCandidates.length.toLocaleString()} pending review`}
              color="warning"
              variant="outlined"
            />
          </Stack>
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
        && applications.length === 0
        && reviewCandidates.length === 0
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
        && applications.length > 0
        && (
          <Grid
            container
            spacing={3}
          >
            {applications.map(
              (summary) => {
                const pendingReviewGroups =
                  reviewCandidates.filter(
                    (candidate) =>
                      candidate.application
                        === summary.application
                      && candidate.integrationId
                        === summary.integrationId,
                  ).length;

                const cardData:
                  ApplicationSummary = {
                    ...summary,
                    pendingReviewGroups,
                  };

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
        && candidateError
        && (
          <Alert severity="warning" sx={{ mt: 3 }}>
            Application cards are available, but some pending-review
            counts could not be loaded: {candidateError}
          </Alert>
        )}
    </PageContainer>
  );
};


export default ReviewQueue;
