import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
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

import { useAuth } from "../../auth/AuthContext";
import PageContainer from "../../components/common/PageContainer";
import {
  type EvidenceCalibrationAnalytics,
  type EvidencePerformanceRow,
  type ReviewerFeedbackAnalytics,
  getEvidenceCalibrationAnalytics,
  getReviewerFeedbackAnalytics,
} from "../../services/mlService";


const percent = (value: number | null): string =>
  value === null ? "Not available" : `${value.toFixed(1)}%`;

const sampleLabel = (value: EvidencePerformanceRow["sampleQuality"] | undefined): string => {
  if (value === "SUFFICIENT") return "Sufficient";
  if (value === "DEVELOPING") return "Developing";
  return "Limited";
};

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
  rows?: EvidencePerformanceRow[];
  firstColumn: string;
}

const EvidenceTable = ({ title, description, rows, firstColumn }: EvidenceTableProps) => {
  const safeRows = rows ?? [];

  return (
    <Box>
      <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>{title}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{description}</Typography>
      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>{firstColumn}</TableCell>
              <TableCell align="right">Reviewed</TableCell>
              <TableCell align="right">Usable</TableCell>
              <TableCell align="right">Confirmed Duplicate</TableCell>
              <TableCell align="right">Not Duplicate</TableCell>
              <TableCell align="right">Uncertain</TableCell>
              <TableCell align="right">Confirmation Rate</TableCell>
              <TableCell align="right">False Positive Rate</TableCell>
              <TableCell>Sample Quality</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {safeRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} align="center" sx={{ py: 5 }}>
                  No reviewed evidence is available yet.
                </TableCell>
              </TableRow>
            ) : safeRows.map((row) => (
              <TableRow key={row.evidence} hover>
                <TableCell sx={{ maxWidth: 420 }}>{row.evidence}</TableCell>
                <TableCell align="right">{row.reviewed}</TableCell>
                <TableCell align="right">{row.usableSamples ?? row.confirmedDuplicates + row.notDuplicates}</TableCell>
                <TableCell align="right">{row.confirmedDuplicates}</TableCell>
                <TableCell align="right">{row.notDuplicates}</TableCell>
                <TableCell align="right">{row.uncertain}</TableCell>
                <TableCell align="right">{percent(row.confirmationRate)}</TableCell>
                <TableCell align="right">{percent(row.falsePositiveRate)}</TableCell>
                <TableCell><Chip size="small" variant="outlined" label={sampleLabel(row.sampleQuality)} /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

const ReviewerAnalytics = () => {
  const { hasPermission } = useAuth();
  const canViewSummary = hasPermission("ml.analytics.view");
  const canViewCalibration = hasPermission("ml.calibration.view");

  const [analytics, setAnalytics] = useState<ReviewerFeedbackAnalytics | null>(null);
  const [calibration, setCalibration] = useState<EvidenceCalibrationAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [summaryData, calibrationData] = await Promise.all([
        canViewSummary ? getReviewerFeedbackAnalytics() : Promise.resolve(null),
        canViewCalibration ? getEvidenceCalibrationAnalytics() : Promise.resolve(null),
      ]);
      setAnalytics(summaryData);
      setCalibration(calibrationData);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load model evaluation analytics.",
      );
    } finally {
      setLoading(false);
    }
  }, [canViewSummary, canViewCalibration]);

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

        {loading ? (
          <Box sx={{ minHeight: 320, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {canViewSummary && analytics && (
              <>
                <Grid container spacing={2.5}>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard title="Reviewed Pairs" value={String(analytics.reviewedPairs)} description="All reviewer decisions recorded." /></Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard title="Confirmed Duplicates" value={String(analytics.confirmedDuplicates)} description="Pairs reviewers confirmed as duplicates." /></Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard title="Not Duplicates" value={String(analytics.notDuplicates)} description="Pairs reviewers explicitly kept separate." /></Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard title="Uncertain" value={String(analytics.uncertain)} description="Pairs requiring additional review." /></Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard title="Duplicate Group Precision" value={percent(analytics.duplicateGroupPrecision)} description="Share of reviewed AI duplicate-group pairs confirmed by reviewers." /></Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard title="Review Acceptance Rate" value={percent(analytics.reviewAcceptanceRate)} description="Confirmed duplicates among usable reviewer decisions." /></Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard title="Candidate Acceptance" value={percent(analytics.reviewCandidateAcceptanceRate)} description="Standalone review candidates confirmed as duplicates." /></Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard title="Avg Confirmed Confidence" value={percent(analytics.averageConfirmedConfidence)} description="Average AI confidence for confirmed duplicate decisions." /></Grid>
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
                          <TableCell>Sample Quality</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {(analytics.confidenceBands ?? []).map((band) => (
                          <TableRow key={band.band} hover>
                            <TableCell>{band.band === "Not available" ? band.band : `${band.band}%`}</TableCell>
                            <TableCell align="right">{band.reviewed}</TableCell>
                            <TableCell align="right">{band.confirmedDuplicates}</TableCell>
                            <TableCell align="right">{band.notDuplicates}</TableCell>
                            <TableCell align="right">{band.uncertain}</TableCell>
                            <TableCell align="right">{percent(band.confirmationRate)}</TableCell>
                            <TableCell><Chip size="small" variant="outlined" label={sampleLabel(band.sampleQuality)} /></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              </>
            )}

            {canViewCalibration && calibration && (
              <>
                <Alert severity="info">
                  Evidence rates are calibration signals. Limited and developing samples should not be used alone to change production behavior.
                </Alert>
                <EvidenceTable title="Evidence Family Performance" description="Group correlated fields into independent evidence families so username, email-local and fuzzy email evidence are not counted as separate proofs." rows={calibration.evidenceFamilyPerformance} firstColumn="Evidence Family" />
                <EvidenceTable title="Evidence Family Combinations" description="Measure which independent evidence families work well together. This is the preferred view for calibration decisions." rows={calibration.evidenceFamilyPatterns} firstColumn="Evidence Family Combination" />
                <EvidenceTable title="Evidence Performance" description="Inspect normalized individual identity signals. Similarity percentages are bucketed to avoid fragmented one-off rows." rows={calibration.evidencePerformance} firstColumn="Evidence" />
                <EvidenceTable title="Evidence Combination Performance" description="Inspect detailed signal combinations after taxonomy normalization." rows={calibration.evidencePatterns} firstColumn="Evidence Combination" />
              </>
            )}
          </>
        )}
      </Stack>
    </PageContainer>
  );
};

export default ReviewerAnalytics;
