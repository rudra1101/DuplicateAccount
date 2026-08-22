const BASE_URL = "http://127.0.0.1:8000/api";

export type RemediationStatus =
  | "PENDING_ACTION"
  | "ACTIONED"
  | "IGNORED"
  | "FAILED";

export interface RemediationItem {
  id: number;
  integrationId: number;
  integrationName: string | null;
  application: string;
  account1Key: string;
  account2Key: string;
  account1: Record<string, unknown>;
  account2: Record<string, unknown>;
  confidence: number | null;
  reviewerName: string | null;
  reviewComment: string | null;
  status: RemediationStatus;
  actionComment: string | null;
  actionedBy: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface ReviewDecisionHistoryItem {
  id: number;
  integrationId: number;
  application: string;
  account1Key: string;
  account2Key: string;
  decision: "DUPLICATE" | "NOT_DUPLICATE" | "UNCERTAIN";
  confidence: number | null;
  reviewerName: string | null;
  comment: string | null;
  source: string;
  account1: Record<string, unknown>;
  account2: Record<string, unknown>;
  createdAt: string | null;
}

interface RemediationListResponse {
  count: number;
  items: RemediationItem[];
}

interface HistoryListResponse {
  count: number;
  items: ReviewDecisionHistoryItem[];
}

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      throw new Error(parsed.detail || fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== fallback && text) {
        throw error;
      }
      throw new Error(text || fallback);
    }
  }
  return response.json() as Promise<T>;
}

export async function getRemediationItems(
  status: RemediationStatus | "ALL" = "PENDING_ACTION",
): Promise<RemediationItem[]> {
  const params = new URLSearchParams();
  if (status !== "ALL") {
    params.set("status", status);
  }
  const query = params.toString();
  const response = await fetch(
    `${BASE_URL}/remediation/${query ? `?${query}` : ""}`,
  );
  const result = await parseResponse<RemediationListResponse>(
    response,
    "Unable to load remediation queue.",
  );
  return Array.isArray(result.items) ? result.items : [];
}

export async function getReviewDecisionHistory(): Promise<ReviewDecisionHistoryItem[]> {
  const response = await fetch(`${BASE_URL}/remediation/history`);
  const result = await parseResponse<HistoryListResponse>(
    response,
    "Unable to load reviewer decision history.",
  );
  return Array.isArray(result.items) ? result.items : [];
}

export async function updateRemediationStatus(
  itemId: number,
  status: RemediationStatus,
  comment?: string | null,
  actionedBy?: string | null,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/remediation/${itemId}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, comment: comment ?? null, actionedBy: actionedBy ?? null }),
  });
  await parseResponse(response, "Unable to update remediation item.");
}
