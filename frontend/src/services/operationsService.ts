const API_URL =
  "http://127.0.0.1:8000/api";

export type OperationStatus =
  | "RUNNING"
  | "COMPLETED"
  | "FAILED";

export interface OperationSummary {
  total: number;
  running: number;
  completed: number;
  failed: number;
}

export interface OperationExecution {
  executionId: number;
  integrationId: number;
  integrationName: string;
  connectorType: string;

  scanId: number | null;
  status: OperationStatus;

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

interface OperationFilters {
  status?: OperationStatus | "";
  integrationId?: number | null;
  search?: string;
  limit?: number;
  offset?: number;
}

async function parseResponse<T>(
  response: Response,
  fallbackMessage: string
): Promise<T> {
  if (!response.ok) {
    const body = await response.text();

    try {
      const parsed = JSON.parse(body) as {
        detail?: string;
      };

      throw new Error(
        parsed.detail || fallbackMessage
      );
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }

      throw new Error(
        body || fallbackMessage
      );
    }
  }

  return response.json() as Promise<T>;
}

export async function getOperationsSummary():
Promise<OperationSummary> {
  const response = await fetch(
    `${API_URL}/operations/summary`
  );

  return parseResponse<OperationSummary>(
    response,
    "Unable to load operations summary."
  );
}

export async function getOperations(
  filters: OperationFilters = {}
): Promise<OperationExecution[]> {
  const parameters =
    new URLSearchParams();

  if (filters.status) {
    parameters.set(
      "status",
      filters.status
    );
  }

  if (filters.integrationId) {
    parameters.set(
      "integrationId",
      String(filters.integrationId)
    );
  }

  if (filters.search?.trim()) {
    parameters.set(
      "search",
      filters.search.trim()
    );
  }

  parameters.set(
    "limit",
    String(filters.limit ?? 100)
  );

  parameters.set(
    "offset",
    String(filters.offset ?? 0)
  );

  const response = await fetch(
    `${API_URL}/operations/?${parameters.toString()}`
  );

  return parseResponse<
    OperationExecution[]
  >(
    response,
    "Unable to load job executions."
  );
}

export async function retryOperation(
  executionId: number
): Promise<OperationExecution> {
  const response = await fetch(
    `${API_URL}/operations/${executionId}/retry`,
    {
      method: "POST",
    }
  );

  return parseResponse<OperationExecution>(
    response,
    "Unable to retry execution."
  );
}``