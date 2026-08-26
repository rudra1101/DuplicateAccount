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

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || fallback);
  }
  return response.json() as Promise<T>;
}

export async function getScheduledReport(): Promise<ScheduledReportResponse> {
  const response = await fetch(`${API_BASE_URL}/reports/schedule`);
  return parseResponse(response, "Unable to load scheduled report settings.");
}

export async function updateScheduledReport(
  payload: ScheduledReportUpdate,
): Promise<ScheduledReportConfig> {
  const response = await fetch(`${API_BASE_URL}/reports/schedule`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Unable to save scheduled report settings.");
}

export async function sendScheduledReportTest(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/reports/schedule/send-test`, {
    method: "POST",
  });
  await parseResponse(response, "Unable to send test report.");
}
