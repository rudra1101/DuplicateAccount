import { API_BASE_URL } from "../config/api";

export type AccountState = "ACTIVE" | "INACTIVE" | "UNKNOWN";

export interface SourceAccount {
  id: number;
  integrationId: number;
  applicationId: number | null;
  schemaId: number | null;
  application: string;
  nativeIdentity: string;
  displayName: string | null;
  username: string | null;
  email: string | null;
  employeeId: string | null;
  status: string | null;
  rawAttributes: Record<string, unknown>;
  active: boolean;
  deleted: boolean;
  lastLoginAt: string | null;
  inactiveDays: number | null;
  dormancyThresholdDays: number | null;
  dormant: boolean;
  lastDormancyReminderAt: string | null;
  dormancyTicketId: string | null;
  dormancyTicketStatus: string | null;
  dormancyTicketUrl: string | null;
  dormancyTicketCreatedAt: string | null;
  dormancyTicketLastSyncedAt: string | null;
  dormancyTicketError: string | null;
  firstSeenAt: string | null;
  lastSeenAt: string | null;
  lastScanId: number | null;
}

export interface SourceAccountListResponse {
  page: number;
  pageSize: number;
  total: number;
  items: SourceAccount[];
}

export interface DormancyReminderResponse {
  accountId: number;
  recipient: string;
  sentAt: string;
  inactiveDays: number;
  thresholdDays: number;
  requestedBy: string | null;
}

export interface DormancyTicketResponse {
  accountId: number;
  ticketId: string | null;
  ticketStatus: string | null;
  ticketUrl: string | null;
  ticketCreatedAt: string | null;
  ticketLastSyncedAt: string | null;
  ticketError: string | null;
}

export interface DuplicateFinding {
  id: number;
  integrationId: number;
  primaryAccount: SourceAccount;
  duplicateAccount: SourceAccount;
  confidence: number;
  status: string;
  active: boolean;
  evidence: Record<string, unknown>;
  firstDetectedAt: string | null;
  lastDetectedAt: string | null;
  lastScanId: number | null;
}

export interface OrphanFinding {
  id: number;
  findingType: string;
  orphanType: string;
  scanId: number;
  accountId: number;
  application: string;
  username: string;
  displayName: string;
  email: string;
  employeeId: string | null;
  accountStatus: string | null;
  confidence: number;
  riskScore: number;
  severity: string;
  correlationMethod: string | null;
  matchedIdentityId: number | null;
  evidence: Record<string, unknown>;
  status: string;
  createdAt: string;
}

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      throw new Error(parsed.detail || fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== "Unexpected end of JSON input") throw error;
      throw new Error(text || fallback);
    }
  }
  return response.json() as Promise<T>;
}

export async function getSourceAccounts(
  integrationId: number,
  page = 1,
  pageSize = 50,
  search = "",
  active?: boolean,
  accountState?: AccountState,
  dormant = false,
): Promise<SourceAccountListResponse> {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  if (search.trim()) params.set("search", search.trim());
  if (active !== undefined) params.set("active", String(active));
  if (accountState) params.set("accountState", accountState);
  if (dormant) params.set("dormant", "true");
  const response = await fetch(`${API_BASE_URL}/integrations/${integrationId}/accounts?${params.toString()}`);
  return parseResponse<SourceAccountListResponse>(response, "Unable to load source accounts.");
}

export async function sendDormancyReminder(
  integrationId: number,
  accountId: number,
  requestedBy?: string | null,
): Promise<DormancyReminderResponse> {
  const response = await fetch(
    `${API_BASE_URL}/integrations/${integrationId}/accounts/${accountId}/dormancy-reminder`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ requestedBy: requestedBy ?? null }),
    },
  );
  return parseResponse<DormancyReminderResponse>(response, "Unable to send dormancy reminder.");
}

export async function createDormancyDisableTicket(
  integrationId: number,
  accountId: number,
  requestedBy?: string | null,
): Promise<DormancyTicketResponse> {
  const response = await fetch(
    `${API_BASE_URL}/integrations/${integrationId}/accounts/${accountId}/dormancy-disable-ticket`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ requestedBy: requestedBy ?? null }),
    },
  );
  return parseResponse<DormancyTicketResponse>(response, "Unable to create dormant-account disable ticket.");
}

export async function syncDormancyDisableTicket(
  integrationId: number,
  accountId: number,
): Promise<DormancyTicketResponse> {
  const response = await fetch(
    `${API_BASE_URL}/integrations/${integrationId}/accounts/${accountId}/dormancy-disable-ticket/sync`,
    { method: "POST", credentials: "include" },
  );
  return parseResponse<DormancyTicketResponse>(response, "Unable to synchronize dormant-account disable ticket.");
}

export async function getDuplicateFindings(
  integrationId: number,
  includeResolved = false,
): Promise<DuplicateFinding[]> {
  const response = await fetch(
    `${API_BASE_URL}/integrations/${integrationId}/duplicate-findings?includeResolved=${String(includeResolved)}`,
  );
  return parseResponse<DuplicateFinding[]>(response, "Unable to load duplicate findings.");
}

export async function getOrphanFindings(
  integrationId: number,
  severity?: string,
): Promise<OrphanFinding[]> {
  const params = new URLSearchParams({
    integrationId: String(integrationId),
    latestOnly: "true",
  });
  if (severity?.trim()) params.set("severity", severity.trim());
  const response = await fetch(`${API_BASE_URL}/orphans/?${params.toString()}`);
  return parseResponse<OrphanFinding[]>(response, "Unable to load orphan accounts.");
}
