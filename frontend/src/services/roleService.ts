const API_URL = "http://127.0.0.1:8000/api";

export interface PermissionItem {
  id: number;
  code: string;
  name: string;
  description: string;
  category: string;
}

export interface RoleItem {
  id: number;
  name: string;
  description: string;
  isSystem: boolean;
  permissions: string[];
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail || "Request failed.";
  } catch {
    return "Request failed.";
  }
}

export async function getRoles(): Promise<RoleItem[]> {
  const response = await fetch(`${API_URL}/roles/`, { credentials: "include" });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function getPermissions(): Promise<PermissionItem[]> {
  const response = await fetch(`${API_URL}/roles/permissions`, { credentials: "include" });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function createRole(payload: {
  name: string;
  description: string;
  permissions: string[];
}): Promise<RoleItem> {
  const response = await fetch(`${API_URL}/roles/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function updateRolePermissions(
  roleId: number,
  permissions: string[],
): Promise<RoleItem> {
  const response = await fetch(`${API_URL}/roles/${roleId}/permissions`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ permissions }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}
