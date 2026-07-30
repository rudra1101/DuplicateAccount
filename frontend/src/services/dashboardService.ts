export interface DashboardSummary {
  accountsScanned: number;
  applications: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  highConfidence: number;
  lastScan: string | null;
}

const API = "http://localhost:8000/api";

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const response = await fetch(`${API}/dashboard/`);

  if (!response.ok) {
    throw new Error("Failed to load dashboard");
  }

  return response.json();
}