import { API_BASE_URL } from "../config/api";

export interface OrphanFinding {
  id: number;
  findingType: string;
  orphanType: string;
  scanId: number | null;
  accountId: number;
  sourceAccountId: number | null;
  application: string;
  nativeIdentity: string | null;
  username: string | null;
  displayName: string | null;
  email: string | null;
  employeeId: string | null;
  accountStatus: string | null;
  correlationMethod: string | null;
  matchedIdentityId: number | null;
  evidence: Record<string, unknown>;
  status: string;
  active: boolean;
  firstDetectedAt: string;
  lastDetectedAt: string;
  createdAt: string;
}

export async function getCurrentOrphanFindings(
  integrationId: number,
  orphanType?: string,
): Promise<OrphanFinding[]> {
  const params = new URLSearchParams({
    integrationId: String(integrationId),
    latestOnly: "true",
  });
  if (orphanType?.trim()) params.set("orphanType", orphanType.trim());
  const response = await fetch(`${API_BASE_URL}/orphans/?${params.toString()}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to load orphan accounts.");
  }
  return response.json() as Promise<OrphanFinding[]>;
}
