import { API_BASE_URL } from "../config/api";

export interface SmtpSettings {
  enabled: boolean;
  host: string;
  port: number;
  username: string;
  fromEmail: string;
  useTls: boolean;
  passwordConfigured: boolean;
  source: "database" | "environment" | "unconfigured";
}

export interface SmtpSettingsUpdate {
  enabled: boolean;
  host: string;
  port: number;
  username: string;
  password?: string;
  fromEmail: string;
  useTls: boolean;
  clearPassword?: boolean;
}

export interface BrandingSettings {
  customLogo: boolean;
  filename: string | null;
  updatedAt: string | null;
}

async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json();
    if (body && typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Ignore non-JSON error bodies.
  }
  return fallback;
}

async function expectJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readError(response, fallback));
  }
  return response.json() as Promise<T>;
}

export async function getSmtpSettings(): Promise<SmtpSettings> {
  const response = await fetch(`${API_BASE_URL}/settings/smtp`, {
    credentials: "include",
  });
  return expectJson<SmtpSettings>(response, "Unable to load SMTP settings.");
}

export async function saveSmtpSettings(
  payload: SmtpSettingsUpdate,
): Promise<SmtpSettings> {
  const response = await fetch(`${API_BASE_URL}/settings/smtp`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return expectJson<SmtpSettings>(response, "Unable to save SMTP settings.");
}

export async function sendSmtpTest(recipient: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/settings/smtp/test`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recipient }),
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Unable to send SMTP test email."));
  }
}

export async function getBrandingSettings(): Promise<BrandingSettings> {
  const response = await fetch(`${API_BASE_URL}/settings/branding`, {
    credentials: "include",
  });
  return expectJson<BrandingSettings>(response, "Unable to load branding settings.");
}

export function customLogoUrl(updatedAt?: string | null): string {
  const version = updatedAt ? `?v=${encodeURIComponent(updatedAt)}` : "";
  return `${API_BASE_URL}/settings/branding/logo${version}`;
}

export async function uploadLogo(file: File): Promise<BrandingSettings> {
  const form = new FormData();
  form.append("logo", file);

  const response = await fetch(`${API_BASE_URL}/settings/branding/logo`, {
    method: "PUT",
    credentials: "include",
    body: form,
  });
  return expectJson<BrandingSettings>(response, "Unable to upload logo.");
}

export async function resetLogo(): Promise<BrandingSettings> {
  const response = await fetch(`${API_BASE_URL}/settings/branding/logo`, {
    method: "DELETE",
    credentials: "include",
  });
  return expectJson<BrandingSettings>(response, "Unable to reset logo.");
}
