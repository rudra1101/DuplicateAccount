import { API_BASE_URL } from "../config/api";

export type SourcePurpose = "ACCOUNT" | "AUTHORITATIVE";
export type CorrelationMatchType = "EXACT" | "CASE_INSENSITIVE" | "NORMALIZED";

export interface CorrelationRule {
  id?: number;
  priority: number;
  accountAttribute: string;
  identityAttribute: string;
  matchType: CorrelationMatchType;
  enabled: boolean;
}

export interface CorrelationPolicy {
  id: number;
  name: string;
  accountIntegrationId: number;
  authoritativeIntegrationId: number;
  strategy: "FIRST_MATCH_WINS";
  enabled: boolean;
  rules: CorrelationRule[];
  createdAt: string;
  updatedAt: string;
}

export interface CorrelationPolicyInput {
  name: string;
  accountIntegrationId: number;
  authoritativeIntegrationId: number;
  strategy: "FIRST_MATCH_WINS";
  enabled: boolean;
  rules: CorrelationRule[];
}

export interface CorrelationIntegration {
  id: number;
  name: string;
  connectorType: string;
  sourcePurpose: SourcePurpose;
  enabled: boolean;
}

export interface SourceApplication {
  id: number;
  integrationId: number;
  name: string;
  schema: {
    attributes: Array<{ id: number; name: string; displayName?: string | null }>;
  } | null;
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
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function getCorrelationIntegrations(): Promise<CorrelationIntegration[]> {
  const response = await fetch(`${API_BASE_URL}/integrations/?page=1&pageSize=100`);
  const data = await parseResponse<{ items: CorrelationIntegration[] }>(
    response,
    "Unable to load integrations.",
  );
  return data.items;
}

export async function setIntegrationPurpose(
  integrationId: number,
  sourcePurpose: SourcePurpose,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/integrations/${integrationId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sourcePurpose }),
  });
  await parseResponse(response, "Unable to update source purpose.");
}

export async function getSourceApplications(integrationId: number): Promise<SourceApplication[]> {
  const response = await fetch(`${API_BASE_URL}/integrations/${integrationId}/applications/`);
  return parseResponse<SourceApplication[]>(response, "Unable to load source schema.");
}

export async function getCorrelationPolicies(): Promise<CorrelationPolicy[]> {
  const response = await fetch(`${API_BASE_URL}/correlation-policies/`);
  return parseResponse<CorrelationPolicy[]>(response, "Unable to load correlation policies.");
}

export async function createCorrelationPolicy(
  payload: CorrelationPolicyInput,
): Promise<CorrelationPolicy> {
  const response = await fetch(`${API_BASE_URL}/correlation-policies/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<CorrelationPolicy>(response, "Unable to create correlation policy.");
}

export async function deleteCorrelationPolicy(policyId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/correlation-policies/${policyId}`, {
    method: "DELETE",
  });
  await parseResponse<void>(response, "Unable to delete correlation policy.");
}
