import { API_BASE_URL } from "../config/api";

export interface ReportEmailTemplate {
  id: number;
  name: string;
  subjectTemplate: string;
  textBodyTemplate: string;
  htmlBodyTemplate: string;
  isActive: boolean;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface ReportEmailTemplatePayload {
  name: string;
  subjectTemplate: string;
  textBodyTemplate: string;
  htmlBodyTemplate: string;
  isActive: boolean;
}

export interface ReportEmailTemplateListResponse {
  variables: string[];
  templates: ReportEmailTemplate[];
}

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || fallback);
  }
  return response.json() as Promise<T>;
}

export async function getReportEmailTemplates(): Promise<ReportEmailTemplateListResponse> {
  const response = await fetch(`${API_BASE_URL}/reports/email-templates`, {
    credentials: "include",
  });
  return parseResponse(response, "Unable to load report email templates.");
}

export async function createReportEmailTemplate(
  payload: ReportEmailTemplatePayload,
): Promise<ReportEmailTemplate> {
  const response = await fetch(`${API_BASE_URL}/reports/email-templates`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Unable to create report email template.");
}

export async function updateReportEmailTemplate(
  id: number,
  payload: ReportEmailTemplatePayload,
): Promise<ReportEmailTemplate> {
  const response = await fetch(`${API_BASE_URL}/reports/email-templates/${id}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Unable to update report email template.");
}

export async function deleteReportEmailTemplate(id: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/reports/email-templates/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  await parseResponse(response, "Unable to delete report email template.");
}
