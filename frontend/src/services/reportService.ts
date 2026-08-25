import { API_BASE_URL } from "../config/api";

export interface ReportDefinition {
  type: string;
  name: string;
  description: string;
  filters: string[];
}

export interface ReportCatalog {
  reports: ReportDefinition[];
  integrations: Array<{ id: number; name: string }>;
  applications: string[];
}

export interface ReportFilters {
  integrationId?: number | null;
  application?: string;
  status?: string;
  decision?: string;
  minimumConfidence?: number | null;
  reviewer?: string;
  search?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface ReportRequest {
  reportType: string;
  filters: ReportFilters;
}

export interface ReportPreview {
  reportType: string;
  total: number;
  columns: string[];
  rows: Array<Record<string, unknown>>;
}

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const body = await response.text();
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      throw new Error(parsed.detail || fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== "Unexpected end of JSON input") {
        throw error;
      }
      throw new Error(body || fallback);
    }
  }

  return response.json() as Promise<T>;
}

export async function getReportCatalog(): Promise<ReportCatalog> {
  const response = await fetch(`${API_BASE_URL}/reports/catalog`, {
    credentials: "include",
  });
  return parseResponse<ReportCatalog>(response, "Unable to load report catalog.");
}

export async function previewReport(payload: ReportRequest): Promise<ReportPreview> {
  const response = await fetch(`${API_BASE_URL}/reports/preview`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<ReportPreview>(response, "Unable to generate report preview.");
}

export async function downloadReport(payload: ReportRequest): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/reports/download`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.text();
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      throw new Error(parsed.detail || "Unable to download report.");
    } catch (error) {
      if (error instanceof Error && error.message !== "Unexpected end of JSON input") {
        throw error;
      }
      throw new Error(body || "Unable to download report.");
    }
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] ?? `${payload.reportType}.csv`;

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
