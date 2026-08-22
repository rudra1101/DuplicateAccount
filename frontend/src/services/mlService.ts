const API_URL = "http://127.0.0.1:8000/api";

export interface MlLabelSummary {
  totalUsableLabels: number;
  duplicateLabels: number;
  notDuplicateLabels: number;
  minimumRequired: number;
  readyForTraining: boolean;
}

export interface MlMetrics {
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  rocAuc: number | null;
}

export interface MlModelSummary {
  available: boolean;
  modelVersion: string | null;
  trainedAt: string | null;
  trainingRows: number;
  metrics: MlMetrics;
}

export interface MlDashboardResponse {
  labels: MlLabelSummary;
  progressPercentage: number;
  model: MlModelSummary;
}

export interface ReviewerConfidenceBand {
  band: string;
  reviewed: number;
  confirmedDuplicates: number;
  notDuplicates: number;
  uncertain: number;
  confirmationRate: number | null;
}

export interface ReviewerFeedbackAnalytics {
  reviewedPairs: number;
  confirmedDuplicates: number;
  notDuplicates: number;
  uncertain: number;
  usableDecisions: number;
  reviewAcceptanceRate: number | null;
  duplicateGroupPrecision: number | null;
  reviewCandidateAcceptanceRate: number | null;
  averageConfirmedConfidence: number | null;
  confidenceBands: ReviewerConfidenceBand[];
}

export interface TrainModelMetadata {
  modelVersion: string;
  trainedAt: string;
  trainingRows: number;
  featureNames: string[];
  metrics: MlMetrics;
}

export interface TrainModelResponse {
  status: string;
  model: TrainModelMetadata;
}

async function parseResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  if (!response.ok) {
    const responseBody = await response.text();
    let message = fallbackMessage;

    try {
      const parsed = JSON.parse(responseBody) as { detail?: string };
      if (parsed.detail) message = parsed.detail;
    } catch {
      if (responseBody) message = responseBody;
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function getMlDashboard(): Promise<MlDashboardResponse> {
  const response = await fetch(`${API_URL}/ml/dashboard`);
  return parseResponse<MlDashboardResponse>(response, "Unable to load ML dashboard.");
}

export async function getReviewerFeedbackAnalytics(): Promise<ReviewerFeedbackAnalytics> {
  const response = await fetch(`${API_URL}/ml/analytics/reviewer-feedback`);
  return parseResponse<ReviewerFeedbackAnalytics>(
    response,
    "Unable to load reviewer feedback analytics.",
  );
}

export async function trainMlModel(): Promise<TrainModelResponse> {
  const response = await fetch(`${API_URL}/ml/train`, { method: "POST" });
  return parseResponse<TrainModelResponse>(response, "Unable to train the ML model.");
}

export async function getMlCurrentModel(): Promise<{
  available: boolean;
  model: TrainModelMetadata | null;
}> {
  const response = await fetch(`${API_URL}/ml/current`);
  return parseResponse<{ available: boolean; model: TrainModelMetadata | null }>(
    response,
    "Unable to load the current ML model.",
  );
}

export async function getMlLabelSummary(): Promise<MlLabelSummary> {
  const response = await fetch(`${API_URL}/ml/labels/summary`);
  return parseResponse<MlLabelSummary>(response, "Unable to load ML label summary.");
}
