import type { AuthUser, UserRole } from "../auth/types";

const API_URL = "http://127.0.0.1:8000/api";

export interface CreateUserPayload {
  username: string;
  email: string;
  fullName: string;
  password: string;
  role: UserRole;
}

export async function getUsers(): Promise<AuthUser[]> {
  const response = await fetch(`${API_URL}/users/`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Unable to load users.");
  }

  return response.json();
}

export async function createUser(payload: CreateUserPayload): Promise<AuthUser> {
  const response = await fetch(`${API_URL}/users/`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body.detail || "Unable to create user.");
  }

  return body as AuthUser;
}
