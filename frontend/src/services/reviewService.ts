import { API_BASE_URL } from "../config/api";

const BASE_URL = API_BASE_URL;

export interface ReviewSummary {
  integrationId: number | null;
  integrationName: string | null;
  scanId: number;
  application: string;
  totalAccounts: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  highConfidence: number;
  lastScan: string | null;
}

export interface DuplicateGroup {
  groupId: number;
  integrationId: number | null;
  integrationName: string | null;
  scanId: number;
  primaryAccount: string;
  duplicates: number;
  highestConfidence: number;
}

export interface Account {
  id?: string | null;
  application: string;
  username: string;
  displayName: string;
  email: string;
  employeeId?: string | null;
  department?: string | null;
  manager?: string | null;
  status?: string | null;
  created?: string | null;
  rawAttributes?: Record<string, unknown>;
}

export type ReviewDecision =
  | "DUPLICATE"
  | "NOT_DUPLICATE"
  | "UNCERTAIN";

export interface ReviewReason {
  field: string;
  message: string;
  impact: string;
  similarity: number | null;
}

export interface DuplicateCandidate {
  id: number;
  candidateRecordId: number;
  confidence: number;
  recommendation: string | null;
  classification: string | null;
  modelVersion: string | null;
  matchedAttributes: string[];
  differentAttributes: string[];
  reasons: ReviewReason[];
  warnings: ReviewReason[];
  features: Record<string, unknown>;
  account: Record<string, unknown>;
  reviewDecision: ReviewDecision | null;
  reviewComment: string | null;
  reviewerName: string | null;
  reviewedAt: string | null;
}

export interface DuplicateGroupDetails {
  groupId: number;
  integrationId: number | null;
  integrationName: string | null;
  scanId: number;
  application: string;
  highestConfidence: number;
  primaryAccount: Account;
  duplicates: DuplicateCandidate[];
}

export interface CandidateDecisionPayload {
  decision: ReviewDecision;
  comment?: string | null;
  reviewerName?: string | null;
}

export interface TrainingLabelSummary {
  totalUsableLabels: number;
  duplicateLabels: number;
  notDuplicateLabels: number;
  minimumRequired: number;
  readyForTraining: boolean;
}

export interface CandidateDecisionResponse {
  candidateId: number;
  decision: ReviewDecision;
  comment: string | null;
  reviewerName: string | null;
  reviewedAt: string | null;
  trainingLabelId: number;
  labelSummary: TrainingLabelSummary;
}

export interface StandaloneReviewCandidate {
  id: number;
  scanId: number;
  application: string;
  account1Key: string;
  account2Key: string;
  account1: Record<string, unknown>;
  account2: Record<string, unknown>;
  confidence: number;
  classification: string | null;
  reviewReason: string;
  modelVersion: string | null;
  matchedAttributes: string[];
  conflictingAttributes: string[];
  features: Record<string, unknown>;
  reasons: ReviewReason[];
  warnings: ReviewReason[];
  reviewDecision: ReviewDecision | null;
  reviewComment: string | null;
  reviewerName: string | null;
  reviewedAt: string | null;
}

interface StandaloneReviewCandidateListResponse {
  count: number;
  candidates: StandaloneReviewCandidate[];
}

export interface ReviewScanStatus {
  accounts: number;
  applications: number;
  integrations: number;
  lastScan: string | null;
}

function buildIntegrationQuery(
  integrationId?: number | null,
): string {
  if (
    integrationId === null ||
    integrationId === undefined
  ) {
    return "";
  }

  if (
    !Number.isInteger(integrationId) ||
    integrationId <= 0
  ) {
    throw new Error(
      `Invalid integration ID: ${integrationId}`,
    );
  }

  return `?integrationId=${integrationId}`;
}

function buildReviewCandidateQuery(
  integrationId?: number | null,
  decision = "PENDING",
): string {
  const params = new URLSearchParams();

  if (
    integrationId !== null &&
    integrationId !== undefined
  ) {
    if (
      !Number.isInteger(integrationId) ||
      integrationId <= 0
    ) {
      throw new Error(
        `Invalid integration ID: ${integrationId}`,
      );
    }

    params.set(
      "integrationId",
      String(integrationId),
    );
  }

  if (decision) {
    params.set("decision", decision);
  }

  const query = params.toString();
  return query ? `?${query}` : "";
}

async function parseResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  if (!response.ok) {
    const responseBody =
      await response.text();

    let message = fallbackMessage;

    try {
      const parsed = JSON.parse(
        responseBody,
      ) as {
        detail?: string;
      };

      if (parsed.detail) {
        message = parsed.detail;
      }
    } catch {
      if (responseBody) {
        message = responseBody;
      }
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function getReviewQueue(
  integrationId?: number | null,
): Promise<ReviewSummary[]> {
  const query = buildIntegrationQuery(
    integrationId,
  );

  const response = await fetch(
    `${BASE_URL}/review/${query}`,
  );

  return parseResponse<ReviewSummary[]>(
    response,
    "Unable to load review queue.",
  );
}

export async function getReviewScanStatus(
  integrationId?: number | null,
): Promise<ReviewScanStatus> {
  const query = buildIntegrationQuery(
    integrationId,
  );

  const response = await fetch(
    `${BASE_URL}/review/status${query}`,
  );

  return parseResponse<ReviewScanStatus>(
    response,
    "Unable to load review scan status.",
  );
}

export async function getDuplicateGroups(
  application: string,
  integrationId?: number | null,
): Promise<DuplicateGroup[]> {
  const query = buildIntegrationQuery(
    integrationId,
  );

  const response = await fetch(
    `${BASE_URL}/review/${encodeURIComponent(
      application,
    )}${query}`,
  );

  return parseResponse<DuplicateGroup[]>(
    response,
    "Unable to load duplicate groups.",
  );
}

export async function getDuplicateGroupDetails(
  groupId: number,
  integrationId?: number | null,
): Promise<DuplicateGroupDetails> {
  if (
    !Number.isInteger(groupId) ||
    groupId <= 0
  ) {
    throw new Error(
      `Invalid duplicate group ID: ${groupId}`,
    );
  }

  const query = buildIntegrationQuery(
    integrationId,
  );

  const response = await fetch(
    `${BASE_URL}/review/details/${groupId}${query}`,
  );

  return parseResponse<DuplicateGroupDetails>(
    response,
    "Unable to load duplicate-group details.",
  );
}

export async function submitCandidateDecision(
  candidateRecordId: number,
  payload: CandidateDecisionPayload,
): Promise<CandidateDecisionResponse> {
  if (
    !Number.isInteger(candidateRecordId) ||
    candidateRecordId <= 0
  ) {
    throw new Error(
      `Invalid candidate record ID: ${candidateRecordId}`,
    );
  }

  const response = await fetch(
    `${BASE_URL}/review/candidates/${candidateRecordId}/decision`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  return parseResponse<CandidateDecisionResponse>(
    response,
    "Unable to save the reviewer decision.",
  );
}

export async function getStandaloneReviewCandidates(
  integrationId?: number | null,
  decision = "PENDING",
): Promise<StandaloneReviewCandidate[]> {
  const query = buildReviewCandidateQuery(
    integrationId,
    decision,
  );

  const response = await fetch(
    `${BASE_URL}/review/review-candidates${query}`,
  );

  const result =
    await parseResponse<StandaloneReviewCandidateListResponse>(
      response,
      "Unable to load review candidates.",
    );

  return Array.isArray(result.candidates)
    ? result.candidates
    : [];
}

export async function submitStandaloneReviewDecision(
  candidateId: number,
  payload: CandidateDecisionPayload,
): Promise<StandaloneReviewCandidate> {
  if (
    !Number.isInteger(candidateId) ||
    candidateId <= 0
  ) {
    throw new Error(
      `Invalid review candidate ID: ${candidateId}`,
    );
  }

  const response = await fetch(
    `${BASE_URL}/review/review-candidates/${candidateId}/decision`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  return parseResponse<StandaloneReviewCandidate>(
    response,
    "Unable to save the review-candidate decision.",
  );
}
