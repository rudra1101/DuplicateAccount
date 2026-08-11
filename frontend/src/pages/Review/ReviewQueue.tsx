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
  CircularProgress,
  Grid,
  Paper,
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
  getReviewQueue,
} from "../../services/reviewService";


const ReviewQueue = () => {
  const navigate = useNavigate();

  const [
    applications,
    setApplications,
  ] = useState<ReviewSummary[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");


  const loadApplications =
    useCallback(async () => {
      try {
        setLoading(true);
        setError("");

        const data =
          await getReviewQueue();

        setApplications(
          Array.isArray(data)
            ? data
            : [],
        );
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
          mb: 4,
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
            Review the latest completed
            scan for each integration.
            Running one integration no longer
            hides results from another.
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
                /*
                 * ApplicationCard currently uses
                 * ApplicationSummary. ReviewSummary
                 * contains all of those fields plus
                 * integration metadata.
                 */
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
    </PageContainer>
  );
};


export default ReviewQueue;