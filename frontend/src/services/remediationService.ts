import { API_BASE_URL } from "../config/api";

export type RemediationStatus =
  | "PENDING_ACTION"
  | "TICKET_OPEN"
  | "ACTIONED"
  | "IGNORED"
  | "FAILED";

export type RemediationAction = "DISABLE" | "DELETE";
export type RemediationTarget = "ACCOUNT_1" | "ACCOUNT_2";

export interface RemediationFilters {
  status?: RemediationStatus | "ALL";
  integrationId?: number | null;
  application?: string;
  minConfidence?: number | null;
  maxConfidence?: number | null;
  remediationAction?: RemediationAction | "ALL";
  ticketStatus?: string;
  hasTicket?: boolean | null;
}

export interface BulkActionResult {
  requested: number;
  succeeded: number;
  failed: number;
  results: Array<{ itemId: number; success: boolean; error: string | null }>;
}

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
      if (error instanceof Error && error.message !== fallback && text) throw error;
      throw new Error(text || fallback);
    }
  }
  return response.json() as Promise<T>;
}

export async function getRemediationItems(filters: RemediationFilters = {}): Promise<RemediationItem[]> {
  const params = new URLSearchParams();
  if (filters.status && filters.status !== "ALL") params.set("status", filters.status);
  if (filters.integrationId) params.set("integrationId", String(filters.integrationId));
  if (filters.application?.trim()) params.set("application", filters.application.trim());
  if (filters.minConfidence !== null && filters.minConfidence !== undefined) params.set("minConfidence", String(filters.minConfidence));
  if (filters.maxConfidence !== null && filters.maxConfidence !== undefined) params.set("maxConfidence", String(filters.maxConfidence));
  if (filters.remediationAction && filters.remediationAction !== "ALL") params.set("remediationAction", filters.remediationAction);
  if (filters.ticketStatus?.trim()) params.set("ticketStatus", filters.ticketStatus.trim());
  if (filters.hasTicket !== null && filters.hasTicket !== undefined) params.set("hasTicket", String(filters.hasTicket));
  const query = params.toString();
  const response = await fetch(`${API_BASE_URL}/remediation/${query ? `?${query}` : ""}`, { credentials: "include" });
  const result = await parseResponse<RemediationListResponse>(response, "Unable to load remediation queue.");
  return Array.isArray(result.items) ? result.items : [];
}

export async function getReviewDecisionHistory(): Promise<ReviewDecisionHistoryItem[]> {
  const response = await fetch(`${API_BASE_URL}/remediation/history`, { credentials: "include" });
  const result = await parseResponse<HistoryListResponse>(response, "Unable to load reviewer decision history.");
  return Array.isArray(result.items) ? result.items : [];
}

export async function updateRemediationStatus(itemId: number, status: RemediationStatus, comment?: string | null, actionedBy?: string | null): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/remediation/${itemId}/status`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, comment: comment ?? null, actionedBy: actionedBy ?? null }),
  });
  await parseResponse(response, "Unable to update remediation item.");
}

export async function createRemediationTicket(itemId: number, target: RemediationTarget, action: RemediationAction, requestedBy?: string | null): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/remediation/${itemId}/ticket`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, action, requestedBy: requestedBy ?? null }),
  });
  await parseResponse(response, "Unable to create Service Desk ticket.");
}

export async function syncRemediationTicket(itemId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/remediation/${itemId}/ticket/sync`, { method: "POST", credentials: "include" });
  await parseResponse(response, "Unable to synchronize Service Desk ticket.");
}

export async function createBulkRemediationTickets(itemIds: number[], target: RemediationTarget, action: RemediationAction, requestedBy?: string | null): Promise<BulkActionResult> {
  const response = await fetch(`${API_BASE_URL}/remediation/bulk/tickets`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ itemIds, target, action, requestedBy: requestedBy ?? null }),
  });
  return parseResponse<BulkActionResult>(response, "Unable to create bulk remediation tickets.");
}

export async function syncBulkRemediationTickets(itemIds: number[]): Promise<BulkActionResult> {
  const response = await fetch(`${API_BASE_URL}/remediation/bulk/tickets/sync`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ itemIds }),
  });
  return parseResponse<BulkActionResult>(response, "Unable to synchronize bulk remediation tickets.");
}

export async function ignoreBulkRemediationItems(itemIds: number[], actionedBy?: string | null): Promise<BulkActionResult> {
  const response = await fetch(`${API_BASE_URL}/remediation/bulk/ignore`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ itemIds, actionedBy: actionedBy ?? null }),
  });
  return parseResponse<BulkActionResult>(response, "Unable to ignore selected remediation items.");
}
