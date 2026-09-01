import { API_BASE_URL } from "../config/api";

export type RemediationStatus =
  | "PENDING_ACTION"
  | "TICKET_OPEN"
  | "ACTIONED"
  | "IGNORED"
  | "FAILED";

export type RemediationAction = "DISABLE" | "DELETE";
export type RemediationTarget = "ACCOUNT_1" | "ACCOUNT_2";

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
  remediationAction: RemediationAction | null;
  targetAccountKey: string | null;
  ticketId: string | null;
  ticketStatus: string | null;
  ticketUrl: string | null;
  ticketCreatedAt: string | null;
  ticketLastSyncedAt: string | null;
  ticketError: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface ReviewDecisionHistoryItem {
  id: number;
  integrationId: number;
  application: string;
  account1Key: string;
  account2Key: string;
  decision: "DUPLICATE" | "NOT_DUPLICATE" | "UNCERTAIN" | "REMEDIATED";
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
    `${API_BASE_URL}/remediation/${query ? `?${query}` : ""}`,
    { credentials: "include" },
  );
  const result = await parseResponse<RemediationListResponse>(
    response,
    "Unable to load remediation queue.",
  );
  return Array.isArray(result.items) ? result.items : [];
}

export async function getReviewDecisionHistory(): Promise<ReviewDecisionHistoryItem[]> {
  const response = await fetch(`${API_BASE_URL}/remediation/history`, { credentials: "include" });
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
  const response = await fetch(`${API_BASE_URL}/remediation/${itemId}/status`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, comment: comment ?? null, actionedBy: actionedBy ?? null }),
  });
  await parseResponse(response, "Unable to update remediation item.");
}

export async function createRemediationTicket(
  itemId: number,
  target: RemediationTarget,
  action: RemediationAction,
  requestedBy?: string | null,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/remediation/${itemId}/ticket`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, action, requestedBy: requestedBy ?? null }),
  });
  await parseResponse(response, "Unable to create Service Desk ticket.");
}

export async function syncRemediationTicket(itemId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/remediation/${itemId}/ticket/sync`, {
    method: "POST",
    credentials: "include",
  });
  await parseResponse(response, "Unable to synchronize Service Desk ticket.");
}
