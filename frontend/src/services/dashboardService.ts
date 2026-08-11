const API_URL = "http://127.0.0.1:8000/api";

export type DashboardPeriod =
  | "daily"
  | "weekly"
  | "monthly"
  | "yearly";

export interface DashboardScan {
  id: number;
  filename: string;
  status: string;
  createdAt: string | null;
}

export interface DashboardTotals {
  accountsScanned: number;
  applications: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  highConfidenceMatches: number;
}

export interface DashboardApplication {
  application: string;
  duplicateGroups: number;
  duplicateAccounts: number;
  highestConfidence: number;
  highConfidenceGroups: number;
}

export interface DashboardTrendItem {
  scanId: number;
  name: string;
  filename: string;
  accountsScanned: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  highConfidence: number;
  createdAt: string | null;
}

export interface DashboardResponse {
  hasData: boolean;
  period: DashboardPeriod;
  scan: DashboardScan | null;
  summary: DashboardTotals;
  applications: DashboardApplication[];
  trend: DashboardTrendItem[];
}

export async function getDashboardSummary(
  period: DashboardPeriod = "daily"
): Promise<DashboardResponse> {
  const response = await fetch(
    `${API_URL}/dashboard/?period=${period}`
  );

  if (!response.ok) {
    const responseBody = await response.text();

    throw new Error(
      responseBody ||
        `Dashboard request failed with status ${response.status}`
    );
  }

  return response.json() as Promise<DashboardResponse>;
}