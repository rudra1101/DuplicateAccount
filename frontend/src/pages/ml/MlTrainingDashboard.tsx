import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  LinearProgress,
  Stack,
  Typography,
} from "@mui/material";

import PsychologyIcon from "@mui/icons-material/Psychology";
import ModelTrainingIcon from "@mui/icons-material/ModelTraining";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import DataUsageIcon from "@mui/icons-material/DataUsage";
import RefreshIcon from "@mui/icons-material/Refresh";

import PageContainer from "../../components/common/PageContainer";
import { formatDateTime } from "../../utils/dateTime";

import {
  type MlDashboardResponse,
  getMlDashboard,
  trainMlModel,
} from "../../services/mlService";


function formatMetric(
  value: number | null
): string {
  if (value === null || value === undefined) {
    return "Not available";
  }

  return `${(value * 100).toFixed(1)}%`;
}


interface MetricCardProps {
  title: string;
  value: string;
  description: string;
}


const MetricCard = ({
  title,
  value,
  description,
}: MetricCardProps) => {
  return (
    <Card
      sx={{
        borderRadius: 3,
        height: "100%",
        boxShadow: 2,
      }}
    >
      <CardContent>
        <Typography
          variant="body2"
          color="text.secondary"
        >
          {title}
        </Typography>

        <Typography
          variant="h5"
          fontWeight={700}
          sx={{ mt: 1 }}
        >
          {value}
        </Typography>

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            display: "block",
            mt: 1,
          }}
        >
          {description}
        </Typography>
      </CardContent>
    </Card>
  );
};


const MlTrainingDashboard = () => {
  const [dashboard, setDashboard] =
    useState<MlDashboardResponse | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [training, setTraining] =
    useState(false);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");


  const loadDashboard =
    useCallback(async () => {
      try {
        setLoading(true);
        setError("");

        const data =
          await getMlDashboard();

        setDashboard(data);
      } catch (loadError) {
        console.error(
          "Failed to load ML dashboard:",
          loadError
        );

        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load ML dashboard."
        );
      } finally {
        setLoading(false);
      }
    }, []);


  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);


  const handleTrainModel = async () => {
    try {
      setTraining(true);
      setError("");
      setSuccess("");

      const response =
        await trainMlModel();

      setSuccess(
        `Model ${response.model.modelVersion} trained successfully.`
      );

      await loadDashboard();
    } catch (trainError) {
      console.error(
        "Model training failed:",
        trainError
      );

      setError(
        trainError instanceof Error
          ? trainError.message
          : "Unable to train the model."
      );
    } finally {
      setTraining(false);
    }
  };


  if (loading && !dashboard) {
    return (
      <PageContainer title="ML Training">
        <Box
          sx={{
            minHeight: 400,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <CircularProgress />
        </Box>
      </PageContainer>
    );
  }


  if (!dashboard) {
    return (
      <PageContainer title="ML Training">
        <Alert severity="error">
          {error || "ML dashboard data is unavailable."}
        </Alert>
      </PageContainer>
    );
  }


  const {
    labels,
    progressPercentage,
    model,
  } = dashboard;


  return (
    <PageContainer title="ML Training">
      <Stack spacing={3}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box>
            <Stack
              direction="row"
              spacing={1.5}
              alignItems="center"
            >
              <PsychologyIcon
                color="primary"
                sx={{ fontSize: 34 }}
              />

              <Typography
                variant="h5"
                fontWeight={700}
              >
                Machine Learning Training
              </Typography>
            </Stack>

            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 1 }}
            >
              Train the duplicate detection model
              using reviewer-labelled account pairs.
            </Typography>
          </Box>

          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadDashboard}
            disabled={loading || training}
          >
            Refresh
          </Button>
        </Box>

        {error && (
          <Alert severity="error">
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success">
            {success}
          </Alert>
        )}

        <Grid container spacing={3}>
          <Grid
            size={{
              xs: 12,
              sm: 6,
              lg: 3,
            }}
          >
            <MetricCard
              title="Usable Labels"
              value={labels.totalUsableLabels.toString()}
              description="Latest duplicate or not-duplicate decisions."
            />
          </Grid>

          <Grid
            size={{
              xs: 12,
              sm: 6,
              lg: 3,
            }}
          >
            <MetricCard
              title="Duplicate Labels"
              value={labels.duplicateLabels.toString()}
              description="Reviewer-confirmed duplicate pairs."
            />
          </Grid>

          <Grid
            size={{
              xs: 12,
              sm: 6,
              lg: 3,
            }}
          >
            <MetricCard
              title="Not Duplicate Labels"
              value={labels.notDuplicateLabels.toString()}
              description="Reviewer-confirmed separate identities."
            />
          </Grid>

          <Grid
            size={{
              xs: 12,
              sm: 6,
              lg: 3,
            }}
          >
            <MetricCard
              title="Training Progress"
              value={`${progressPercentage.toFixed(0)}%`}
              description={`${labels.totalUsableLabels} of ${labels.minimumRequired} required labels.`}
            />
          </Grid>
        </Grid>

        <Card
          sx={{
            borderRadius: 3,
            boxShadow: 3,
          }}
        >
          <CardContent>
            <Stack spacing={3}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: 2,
                }}
              >
                <Box>
                  <Typography
                    variant="h6"
                    fontWeight={700}
                  >
                    Dataset Readiness
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.5 }}
                  >
                    A minimum number of balanced reviewer
                    decisions is required before training.
                  </Typography>
                </Box>

                <Chip
                  icon={
                    labels.readyForTraining
                      ? <CheckCircleIcon />
                      : <CancelIcon />
                  }
                  label={
                    labels.readyForTraining
                      ? "Ready for Training"
                      : "Not Ready"
                  }
                  color={
                    labels.readyForTraining
                      ? "success"
                      : "warning"
                  }
                />
              </Box>

              <Box>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Typography variant="body2">
                    Label collection progress
                  </Typography>

                  <Typography
                    variant="body2"
                    fontWeight={600}
                  >
                    {labels.totalUsableLabels}
                    {" / "}
                    {labels.minimumRequired}
                  </Typography>
                </Box>

                <LinearProgress
                  variant="determinate"
                  value={progressPercentage}
                  sx={{
                    height: 12,
                    borderRadius: 8,
                  }}
                />
              </Box>

              <Stack
                direction={{
                  xs: "column",
                  sm: "row",
                }}
                spacing={2}
              >
                <Chip
                  icon={<CheckCircleIcon />}
                  label={`Duplicate: ${labels.duplicateLabels}`}
                  color="success"
                  variant="outlined"
                />

                <Chip
                  icon={<CancelIcon />}
                  label={`Not Duplicate: ${labels.notDuplicateLabels}`}
                  color="error"
                  variant="outlined"
                />
              </Stack>

              {!labels.readyForTraining && (
                <Alert severity="info">
                  Continue reviewing duplicate candidates.
                  You currently need{" "}
                  {Math.max(
                    0,
                    labels.minimumRequired -
                      labels.totalUsableLabels
                  )}{" "}
                  additional usable labels.
                </Alert>
              )}

              <Box>
                <Button
                  variant="contained"
                  size="large"
                  startIcon={
                    training
                      ? (
                        <CircularProgress
                          size={20}
                          color="inherit"
                        />
                      )
                      : <ModelTrainingIcon />
                  }
                  disabled={
                    !labels.readyForTraining ||
                    training
                  }
                  onClick={handleTrainModel}
                >
                  {training
                    ? "Training Model..."
                    : "Train Model"}
                </Button>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        <Card
          sx={{
            borderRadius: 3,
            boxShadow: 3,
          }}
        >
          <CardContent>
            <Stack spacing={3}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: 2,
                }}
              >
                <Box>
                  <Typography
                    variant="h6"
                    fontWeight={700}
                  >
                    Current ML Model
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.5 }}
                  >
                    Details and validation metrics for
                    the currently deployed model.
                  </Typography>
                </Box>

                <Chip
                  icon={<DataUsageIcon />}
                  label={
                    model.available
                      ? "Model Available"
                      : "No Trained Model"
                  }
                  color={
                    model.available
                      ? "success"
                      : "default"
                  }
                />
              </Box>

              <Divider />

              {!model.available ? (
                <Alert severity="info">
                  No trained model is available yet.
                  The platform is currently using the
                  evidence and FAISS reranking engine.
                </Alert>
              ) : (
                <>
                  <Grid container spacing={3}>
                    <Grid
                      size={{
                        xs: 12,
                        sm: 6,
                        lg: 2.4,
                      }}
                    >
                      <MetricCard
                        title="Accuracy"
                        value={formatMetric(
                          model.metrics.accuracy
                        )}
                        description="Overall correct predictions."
                      />
                    </Grid>

                    <Grid
                      size={{
                        xs: 12,
                        sm: 6,
                        lg: 2.4,
                      }}
                    >
                      <MetricCard
                        title="Precision"
                        value={formatMetric(
                          model.metrics.precision
                        )}
                        description="Quality of duplicate predictions."
                      />
                    </Grid>

                    <Grid
                      size={{
                        xs: 12,
                        sm: 6,
                        lg: 2.4,
                      }}
                    >
                      <MetricCard
                        title="Recall"
                        value={formatMetric(
                          model.metrics.recall
                        )}
                        description="Duplicate pairs successfully detected."
                      />
                    </Grid>

                    <Grid
                      size={{
                        xs: 12,
                        sm: 6,
                        lg: 2.4,
                      }}
                    >
                      <MetricCard
                        title="F1 Score"
                        value={formatMetric(
                          model.metrics.f1
                        )}
                        description="Balance of precision and recall."
                      />
                    </Grid>

                    <Grid
                      size={{
                        xs: 12,
                        sm: 6,
                        lg: 2.4,
                      }}
                    >
                      <MetricCard
                        title="ROC-AUC"
                        value={formatMetric(
                          model.metrics.rocAuc
                        )}
                        description="Model ranking performance."
                      />
                    </Grid>
                  </Grid>

                  <Box>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                    >
                      Model Version
                    </Typography>

                    <Typography
                      fontWeight={600}
                    >
                      {model.modelVersion}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                    >
                      Training Rows
                    </Typography>

                    <Typography
                      fontWeight={600}
                    >
                      {model.trainingRows}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                    >
                      Last Trained
                    </Typography>

                    <Typography
                      fontWeight={600}
                    >
                      {model.trainedAt
                        ? formatDateTime(
                            model.trainedAt
                          )
                        : "Not available"}
                    </Typography>
                  </Box>
                </>
              )}
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    </PageContainer>
  );
};

export default MlTrainingDashboard;