import { Account } from "../models/Account";

const BASE_URL = "http://localhost:8000/api";

export interface DuplicateGroup {
  groupId: number;
  primaryAccount: string;
  duplicates: number;
  highestConfidence: number;
}

export interface ReviewSummary {
  application: string;
  totalAccounts: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  highConfidence: number;
  lastScan: string;
}

export interface AccountDetails extends Account {}

export interface DuplicateAccount {
  id: number;
  confidence: number;
  recommendation: string;
  matchedAttributes: string[];
  differentAttributes: string[];
  account: AccountDetails;
}

export interface DuplicateGroupDetails {
  primaryAccount: AccountDetails;
  duplicates: DuplicateAccount[];
}

export async function getReviewSummary(): Promise<ReviewSummary[]> {
  const response = await fetch(`${BASE_URL}/review/`);

  if (!response.ok) {
    throw new Error("Failed to fetch review summary");
  }

  return response.json();
}

export async function getDuplicateGroups(
  application: string
): Promise<DuplicateGroup[]> {
  const response = await fetch(
    `${BASE_URL}/review/${encodeURIComponent(application)}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch duplicate groups");
  }

  return response.json();
}

export async function getDuplicateDetails(
  groupId: number
): Promise<DuplicateGroupDetails> {
  const response = await fetch(
    `${BASE_URL}/review/details/${groupId}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch duplicate details");
  }

  return response.json();
}