import { API_BASE_URL } from "../config/api";

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
): Promise<SourceAccountListResponse> {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  if (search.trim()) params.set("search", search.trim());
  if (active !== undefined) params.set("active", String(active));
  const response = await fetch(`${API_BASE_URL}/integrations/${integrationId}/accounts?${params.toString()}`);
  return parseResponse<SourceAccountListResponse>(response, "Unable to load source accounts.");
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
