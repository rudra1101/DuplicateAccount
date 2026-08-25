import type { AuthUser } from "../auth/types";
import { API_BASE_URL } from "../config/api";

export interface CreateUserPayload {
  username: string;
  email: string;
  fullName: string;
  password: string;
  role: string;
}

export async function getUsers(): Promise<AuthUser[]> {
  const response = await fetch(`${API_BASE_URL}/users/`, { credentials: "include" });
  if (!response.ok) throw new Error("Unable to load users.");
  return response.json();
}

export async function createUser(payload: CreateUserPayload): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/users/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Unable to create user.");
  return body as AuthUser;
}

export async function updateUserRole(userId: number, role: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/users/${userId}/role`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Unable to update role.");
  return body as AuthUser;
}
