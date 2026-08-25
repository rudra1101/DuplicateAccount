import { API_BASE_URL } from "../config/api";

const REVIEW_BASE_URL = `${API_BASE_URL}/review`;

export async function getApplicationSummary() {
  const response = await fetch(REVIEW_BASE_URL);

  if (!response.ok) {
    throw new Error("Failed to fetch application summary");
  }

  return response.json();
}

export async function getDuplicatePairs(application: string) {
  const response = await fetch(
    `${REVIEW_BASE_URL}/${encodeURIComponent(application)}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch duplicate pairs");
  }

  return response.json();
}

export async function getDuplicateDetails(id: number) {
  const response = await fetch(
    `${REVIEW_BASE_URL}/details/${id}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch duplicate details");
  }

  return response.json();
}
