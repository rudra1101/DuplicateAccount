const BASE_URL = "http://127.0.0.1:8000/api/review";

export async function getApplicationSummary() {
  const response = await fetch(BASE_URL);

  if (!response.ok) {
    throw new Error("Failed to fetch application summary");
  }

  return response.json();
}

export async function getDuplicatePairs(application: string) {
  const response = await fetch(
    `${BASE_URL}/${encodeURIComponent(application)}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch duplicate pairs");
  }

  return response.json();
}

export async function getDuplicateDetails(id: number) {
  const response = await fetch(
    `${BASE_URL}/details/${id}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch duplicate details");
  }

  return response.json();
}