import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import AnalyticsOutlinedIcon from "@mui/icons-material/AnalyticsOutlined";

import PageContainer from "../../components/common/PageContainer";
import {
  type EvidencePerformanceRow,
  type ReviewerFeedbackAnalytics,
  getReviewerFeedbackAnalytics,
} from "../../services/mlService";


const percent = (value: number | null): string =>
  value === null ? "Not available" : `${value.toFixed(1)}%`;

interface MetricCardProps {
  title: string;
  value: string;
  description: string;
}

const MetricCard = ({ title, value, description }: MetricCardProps) => (
  <Card variant="outlined" sx={{ borderRadius: 3, height: "100%" }}>
    <CardContent>
      <Typography variant="body2" color="text.secondary">{title}</Typography>
      <Typography variant="h5" fontWeight={700} sx={{ mt: 1 }}>{value}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
        {description}
      </Typography>
    </CardContent>
  </Card>
);

interface EvidenceTableProps {
  title: string;
  description: string;
  rows: EvidencePerformanceRow[];
  firstColumn: string;
}

const EvidenceTable = ({ title, description, rows, firstColumn }: EvidenceTableProps) => (
  <Box>
    <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>{title}</Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{description}</Typography>
    <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>{firstColumn}</TableCell>
            <TableCell align="right">Reviewed</TableCell>
            <TableCell align="right">Confirmed Duplicate</TableCell>
            <TableCell align="right">Not Duplicate</TableCell>
            <TableCell align="right">Uncertain</TableCell>
            <TableCell align="right">Confirmation Rate</TableCell>
            <TableCell align="right">False Positive Rate</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={7} align="center" sx={{ py: 5 }}>
                No reviewed evidence is available yet.
              </TableCell>
            </TableRow>
          ) : rows.map((row) => (
            <TableRow key={row.evidence} hover>
              <TableCell sx={{ maxWidth: 420 }}>{row.evidence}</TableCell>
              <TableCell align="right">{row.reviewed}</TableCell>
              <TableCell align="right">{row.confirmedDuplicates}</TableCell>
              <TableCell align="right">{row.notDuplicates}</TableCell>
              <TableCell align="right">{row.uncertain}</TableCell>
              <TableCell align="right">{percent(row.confirmationRate)}</TableCell>
              <TableCell align="right">{percent(row.falsePositiveRate)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  </Box>
);

const ReviewerAnalytics = () => {
  const [analytics, setAnalytics] = useState<ReviewerFeedbackAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      setAnalytics(await getReviewerFeedbackAnalytics());
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load reviewer feedback analytics.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAnalytics();
  }, [loadAnalytics]);

  return (
    <PageContainer title="Model Evaluation">
      <Stack spacing={3}>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
          <Box>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <AnalyticsOutlinedIcon color="primary" sx={{ fontSize: 34 }} />
              <Typography variant="h5" fontWeight={700}>Reviewer Feedback Evaluation</Typography>
            </Stack>
            <Typography color="text.secondary" sx={{ mt: 1 }}>
              Measure duplicate-detection quality using human reviewer decisions as ground truth.
            </Typography>
          </Box>
          <Button
            variant="outlined"
            startIcon={loading ? <CircularProgress size={18} /> : <RefreshIcon />}
            disabled={loading}
            onClick={loadAnalytics}
          >
            Refresh
          </Button>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}

        {loading && !analytics ? (
          <Box sx={{ minHeight: 320, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <CircularProgress />
          </Box>
        ) : analytics ? (
          <>
            <Grid container spacing={2.5}>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard title="Reviewed Pairs" value={String(analytics.reviewedPairs)} description="All reviewer decisions recorded." />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard title="Confirmed Duplicates" value={String(analytics.confirmedDuplicates)} description="Pairs reviewers confirmed as duplicates." />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard title="Not Duplicates" value={String(analytics.notDuplicates)} description="Pairs reviewers explicitly kept separate." />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard title="Uncertain" value={String(analytics.uncertain)} description="Pairs requiring additional review." />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard title="Duplicate Group Precision" value={percent(analytics.duplicateGroupPrecision)} description="Share of reviewed AI duplicate-group pairs confirmed by reviewers." />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard title="Review Acceptance Rate" value={percent(analytics.reviewAcceptanceRate)} description="Confirmed duplicates among usable reviewer decisions." />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard title="Candidate Acceptance" value={percent(analytics.reviewCandidateAcceptanceRate)} description="Standalone review candidates confirmed as duplicates." />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                <MetricCard title="Avg Confirmed Confidence" value={percent(analytics.averageConfirmedConfidence)} description="Average AI confidence for confirmed duplicate decisions." />
              </Grid>
            </Grid>

            <Box>
              <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>Confidence Calibration</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Compare model confidence bands with the decisions reviewers actually made.
              </Typography>
              <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Confidence</TableCell>
                      <TableCell align="right">Reviewed</TableCell>
                      <TableCell align="right">Confirmed Duplicate</TableCell>
                      <TableCell align="right">Not Duplicate</TableCell>
                      <TableCell align="right">Uncertain</TableCell>
                      <TableCell align="right">Confirmation Rate</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {analytics.confidenceBands.map((band) => (
                      <TableRow key={band.band} hover>
                        <TableCell>{band.band === "Not available" ? band.band : `${band.band}%`}</TableCell>
                        <TableCell align="right">{band.reviewed}</TableCell>
                        <TableCell align="right">{band.confirmedDuplicates}</TableCell>
                        <TableCell align="right">{band.notDuplicates}</TableCell>
                        <TableCell align="right">{band.uncertain}</TableCell>
                        <TableCell align="right">{percent(band.confirmationRate)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>

            <EvidenceTable
              title="Evidence Performance"
              description="See which individual identity signals produce confirmed duplicates versus reviewer-rejected false positives."
              rows={analytics.evidencePerformance}
              firstColumn="Evidence"
            />

            <EvidenceTable
              title="Evidence Combination Performance"
              description="Measure how combinations of identity signals perform together. These patterns are ranked by reviewed volume."
              rows={analytics.evidencePatterns}
              firstColumn="Evidence Combination"
            />
          </>
        ) : null}
      </Stack>
    </PageContainer>
  );
};

export default ReviewerAnalytics;
