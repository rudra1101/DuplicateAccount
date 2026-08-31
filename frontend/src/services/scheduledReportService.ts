import { API_BASE_URL } from "../config/api";

export type ScheduledFrequency = "WEEKLY" | "MONTHLY" | "QUARTERLY";

export interface ScheduledReportColumn {
  key: string;
  label: string;
}

export interface ScheduledReportConfig {
  enabled: boolean;
  frequency: ScheduledFrequency;
  includeAdmins: boolean;
  recipientEmails: string[];
  selectedColumns: string[];
  availableColumns: ScheduledReportColumn[];
  timezone: string;
  lastSentAt: string | null;
  lastStatus: string | null;
  lastError: string | null;
  nextRunAt: string | null;
}

export interface ExecutiveDuplicateSnapshot {
  duplicateGroups: number;
  duplicateCandidates: number;
  pendingReview: number;
  confirmedDuplicates: number;
  awaitingRemediation: number;
  highConfidenceUnresolved: number;
  generatedAt: string;
}

export interface ScheduledReportResponse {
  config: ScheduledReportConfig;
  snapshot: ExecutiveDuplicateSnapshot;
}

export interface ScheduledReportUpdate {
  enabled: boolean;
  frequency: ScheduledFrequency;
  includeAdmins: boolean;
  recipientEmails: string[];
  selectedColumns: string[];
}

export interface ScheduledReportRun {
  id: number;
  reportName: string;
  filename: string;
  status: "GENERATED" | "SENT" | "EMAIL_FAILED" | string;
  testMode: boolean;
  recipients: string[];
  snapshot: ExecutiveDuplicateSnapshot;
  rowCount: number;
  errorMessage: string | null;
  generatedAt: string;
}

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || fallback);
  }
  return response.json() as Promise<T>;
}

export async function getScheduledReport(): Promise<ScheduledReportResponse> {
  const response = await fetch(`${API_BASE_URL}/reports/schedule`, {
    credentials: "include",
  });
  return parseResponse(response, "Unable to load scheduled report settings.");
}

export async function updateScheduledReport(
  payload: ScheduledReportUpdate,
): Promise<ScheduledReportConfig> {
  const response = await fetch(`${API_BASE_URL}/reports/schedule`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Unable to save scheduled report settings.");
}

export async function sendScheduledReportTest(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/reports/schedule/send-test`, {
    method: "POST",
    credentials: "include",
  });
  await parseResponse(response, "Unable to send test report.");
}

export async function getScheduledReportHistory(limit = 50): Promise<ScheduledReportRun[]> {
  const response = await fetch(`${API_BASE_URL}/reports/schedule/history?limit=${limit}`, {
    credentials: "include",
  });
  const body = await parseResponse<{ runs: ScheduledReportRun[] }>(
    response,
    "Unable to load scheduled report history.",
  );
  return body.runs;
}

export async function downloadScheduledReport(run: ScheduledReportRun): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/reports/schedule/history/${run.id}/download`,
    { credentials: "include" },
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || "Unable to download scheduled report.");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] ?? run.filename;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
