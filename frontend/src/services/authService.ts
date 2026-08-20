import type { AuthUser } from "../auth/types";

const API_URL = "http://127.0.0.1:8000/api";

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (body && typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Ignore JSON parse failures.
  }

  return `Request failed with status ${response.status}`;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  const body = await response.json();
  return body.user as AuthUser;
}

export async function getCurrentUser(): Promise<AuthUser> {
  const response = await fetch(`${API_URL}/auth/me`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  const body = await response.json();
  return body.user as AuthUser;
}

export async function logout(): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}
