const API_URL = "http://127.0.0.1:8000/api";

export type ConnectorFieldType =
  "text" | "password" | "number" | "select" | "boolean";

export interface ConnectorOption {
  label: string;
  value: string | number | boolean;
}

export interface ConnectorField {
  name: string;
  label: string;
  type: ConnectorFieldType;
  required?: boolean;
  default?: string | number | boolean;
  placeholder?: string;
  helpText?: string;
  options?: ConnectorOption[];
}

export interface ConnectorConfigurationSchema {
  fields: ConnectorField[];
}

export interface ConnectorType {
  type: string;
  displayName: string;
  description: string;
  configurationSchema: ConnectorConfigurationSchema;
}

export interface Integration {
  id: number;
  name: string;
  connectorType: string;
  description: string | null;
  configuration: Record<string, unknown>;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CreateIntegrationPayload {
  name: string;
  connectorType: string;
  description?: string | null;
  configuration: Record<string, unknown>;
  enabled: boolean;
}

export interface UpdateIntegrationPayload {
  name?: string;
  description?: string | null;
  configuration?: Record<string, unknown>;
  enabled?: boolean;
}

export interface IntegrationTestResult {
  integrationId: number;
  connectorType: string;
  success: boolean;
  message: string;
  details: Record<string, unknown>;
}

export interface DetectedSchemaAttribute {
  name: string;
  displayName: string;
  dataType: string;
  required: boolean;
  multiValued: boolean;
  position: number;
  useForMatching: boolean;
  matchType: "NONE";
  matchWeight: number;
  normalizationType: "NONE";
}

export interface SchemaDetectionResult {
  filename: string;
  sourcePath: string;
  sampledRows: number;
  attributes: DetectedSchemaAttribute[];
}

export interface IntegrationExecution {
  executionId: number;
  integrationId: number;
  scanId: number | null;
  status: "RUNNING" | "COMPLETED" | "FAILED";
  sourceFileName: string | null;
  sourcePath: string | null;
  fileChecksum: string | null;
  accountsScanned: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface JobSchedule {
  id: number;
  integrationId: number;
  name: string;
  scheduleType: string;
  cronExpression: string;
  timezone: string;
  enabled: boolean;
  lastRunAt: string | null;
  lastRunStatus: string | null;
  nextRunAt: string | null;
  lastError: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface CreateSchedulePayload {
  name: string;
  cronExpression: string;
  timezone: string;
  enabled: boolean;
}

export interface UpdateSchedulePayload {
  name?: string;
  cronExpression?: string;
  timezone?: string;
  enabled?: boolean;
}

async function parseResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  if (!response.ok) {
    const responseBody = await response.text();

    let message = fallbackMessage;

    try {
      const parsed = JSON.parse(responseBody) as {
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

export async function getConnectorTypes(): Promise<ConnectorType[]> {
  const response = await fetch(`${API_URL}/integrations/connector-types`);

  return parseResponse<ConnectorType[]>(
    response,
    "Unable to load connector types.",
  );
}

export async function detectIntegrationSchema(
  connectorType: string,
  configuration: Record<string, unknown>,
): Promise<SchemaDetectionResult> {
  const response = await fetch(`${API_URL}/integrations/detect-schema`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connectorType, configuration }),
  });

  return parseResponse<SchemaDetectionResult>(
    response,
    "Unable to detect schema from the configured CSV source.",
  );
}

export async function getIntegrations(): Promise<Integration[]> {
  const response = await fetch(`${API_URL}/integrations/`);

  return parseResponse<Integration[]>(response, "Unable to load integrations.");
}

export async function getIntegration(
  integrationId: number,
): Promise<Integration> {
  const response = await fetch(`${API_URL}/integrations/${integrationId}`);

  return parseResponse<Integration>(response, "Unable to load integration.");
}

export async function createIntegration(
  payload: CreateIntegrationPayload,
): Promise<Integration> {
  const response = await fetch(`${API_URL}/integrations/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseResponse<Integration>(response, "Unable to create integration.");
}

export async function updateIntegration(
  integrationId: number,
  payload: UpdateIntegrationPayload,
): Promise<Integration> {
  const response = await fetch(`${API_URL}/integrations/${integrationId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseResponse<Integration>(response, "Unable to update integration.");
}

export async function deleteIntegration(integrationId: number): Promise<void> {
  const response = await fetch(`${API_URL}/integrations/${integrationId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const body = await response.text();

    throw new Error(body || "Unable to delete integration.");
  }
}

export async function testIntegration(
  integrationId: number,
): Promise<IntegrationTestResult> {
  const response = await fetch(
    `${API_URL}/integrations/${integrationId}/test`,
    {
      method: "POST",
    },
  );

  return parseResponse<IntegrationTestResult>(
    response,
    "Unable to test integration.",
  );
}

export async function runIntegration(
  integrationId: number,
): Promise<IntegrationExecution> {
  const response = await fetch(`${API_URL}/integrations/${integrationId}/run`, {
    method: "POST",
  });

  return parseResponse<IntegrationExecution>(
    response,
    "Unable to run integration.",
  );
}

export async function getIntegrationExecutions(
  integrationId: number,
  limit = 20,
): Promise<IntegrationExecution[]> {
  const response = await fetch(
    `${API_URL}/integrations/${integrationId}/executions?limit=${limit}`,
  );

  return parseResponse<IntegrationExecution[]>(
    response,
    "Unable to load execution history.",
  );
}

export async function getIntegrationSchedule(
  integrationId: number,
): Promise<JobSchedule | null> {
  const response = await fetch(
    `${API_URL}/integrations/${integrationId}/schedule`,
  );

  if (response.status === 404) {
    return null;
  }

  return parseResponse<JobSchedule>(
    response,
    "Unable to load integration schedule.",
  );
}

export async function createIntegrationSchedule(
  integrationId: number,
  payload: CreateSchedulePayload,
): Promise<JobSchedule> {
  const response = await fetch(
    `${API_URL}/integrations/${integrationId}/schedule`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  return parseResponse<JobSchedule>(
    response,
    "Unable to create integration schedule.",
  );
}

export async function updateIntegrationSchedule(
  integrationId: number,
  payload: UpdateSchedulePayload,
): Promise<JobSchedule> {
  const response = await fetch(
    `${API_URL}/integrations/${integrationId}/schedule`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  return parseResponse<JobSchedule>(
    response,
    "Unable to update integration schedule.",
  );
}

export async function enableIntegrationSchedule(
  integrationId: number,
): Promise<JobSchedule> {
  const response = await fetch(
    `${API_URL}/integrations/${integrationId}/schedule/enable`,
    {
      method: "POST",
    },
  );

  return parseResponse<JobSchedule>(
    response,
    "Unable to enable integration schedule.",
  );
}

export async function disableIntegrationSchedule(
  integrationId: number,
): Promise<JobSchedule> {
  const response = await fetch(
    `${API_URL}/integrations/${integrationId}/schedule/disable`,
    {
      method: "POST",
    },
  );

  return parseResponse<JobSchedule>(
    response,
    "Unable to disable integration schedule.",
  );
}

export async function deleteIntegrationSchedule(
  integrationId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/integrations/${integrationId}/schedule`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    const body = await response.text();

    throw new Error(body || "Unable to delete integration schedule.");
  }
}
