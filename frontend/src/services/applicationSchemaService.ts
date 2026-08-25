import { API_BASE_URL } from "../config/api";

export type MatchType = "EXACT" | "FUZZY" | "CONTAINS" | "NONE";
export type NormalizationType =
  | "NONE"
  | "TRIM"
  | "LOWERCASE"
  | "UPPERCASE"
  | "ALPHANUMERIC"
  | "EMAIL"
  | "PHONE"
  | "NAME";

export interface SchemaAttributeInput {
  name: string;
  displayName?: string | null;
  dataType: string;
  required: boolean;
  multiValued: boolean;
  position: number;
  useForMatching: boolean;
  matchType: MatchType;
  matchWeight: number;
  normalizationType: NormalizationType;
}

export interface ApplicationInput {
  name: string;
  displayName?: string | null;
  objectType?: string | null;
  enabled: boolean;
  schemaName?: string | null;
  attributes: SchemaAttributeInput[];
}

export interface ApplicationSchemaResponse {
  id: number;
  integrationId: number;
  name: string;
  displayName: string | null;
  objectType: string | null;
  enabled: boolean;
  schema: {
    id: number;
    version: number;
    name: string | null;
    isActive: boolean;
    attributes: Array<SchemaAttributeInput & { id: number }>;
  } | null;
}

export interface GeneratedMatchingAttribute {
  name: string;
  category: string;
  matchType: MatchType;
  matchWeight: number;
  normalizationType: NormalizationType;
  reason: string;
}

export interface GeneratedMatchingPolicy {
  applicationName: string;
  strategy: "AUTOMATIC";
  generatorVersion: string;
  recommendedThreshold: number;
  selectedAttributeCount: number;
  selectedAttributes: GeneratedMatchingAttribute[];
  ignoredTechnicalAttributes: string[];
  attributes: SchemaAttributeInput[];
}

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      throw new Error(parsed.detail || fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== "Unexpected end of JSON input") {
        throw error;
      }
      throw new Error(text || fallback);
    }
  }
  return response.json() as Promise<T>;
}

export async function getIntegrationApplications(
  integrationId: number,
): Promise<ApplicationSchemaResponse[]> {
  const response = await fetch(
    `${API_BASE_URL}/integrations/${integrationId}/applications/`,
  );
  return parseResponse<ApplicationSchemaResponse[]>(
    response,
    "Unable to load application schemas.",
  );
}

export async function saveIntegrationApplications(
  integrationId: number,
  applications: ApplicationInput[],
): Promise<ApplicationSchemaResponse[]> {
  const response = await fetch(
    `${API_BASE_URL}/integrations/${integrationId}/applications/`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ applications }),
    },
  );
  return parseResponse<ApplicationSchemaResponse[]>(
    response,
    "Unable to save application schemas.",
  );
}

export async function generateMatchingPolicy(
  applicationName: string,
  attributes: SchemaAttributeInput[],
): Promise<GeneratedMatchingPolicy> {
  const response = await fetch(
    `${API_BASE_URL}/matching-policy/generate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ applicationName, attributes }),
    },
  );

  return parseResponse<GeneratedMatchingPolicy>(
    response,
    "Unable to generate the automatic detection strategy.",
  );
}
