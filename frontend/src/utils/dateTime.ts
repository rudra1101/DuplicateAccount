const DEFAULT_TIMEZONE = "Asia/Kolkata";

/**
 * Detect whether an ISO timestamp already contains a timezone.
 *
 * Examples:
 * 2026-08-04T08:46:37Z
 * 2026-08-04T14:16:37+05:30
 */
function hasTimezone(value: string): boolean {
  return (
    value.endsWith("Z") ||
    /[+-]\d{2}:\d{2}$/.test(value)
  );
}

/**
 * Converts backend timestamps into a JavaScript-compatible value.
 *
 * The backend currently stores and returns some timestamps as naive UTC:
 * 2026-08-04T08:46:37
 *
 * A trailing Z is added so JavaScript correctly interprets the value as UTC.
 */
function normalizeDateTime(value: string): string {
  const trimmedValue = value.trim();

  // Convert SQL-style timestamp into ISO format.
  const isoValue = trimmedValue.replace(" ", "T");

  if (hasTimezone(isoValue)) {
    return isoValue;
  }

  return `${isoValue}Z`;
}

export function formatDateTime(
  value: string | null | undefined,
  timezone: string = DEFAULT_TIMEZONE
): string {
  if (!value) {
    return "-";
  }

  const normalizedValue =
    normalizeDateTime(value);

  const date = new Date(normalizedValue);

  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  try {
    return date.toLocaleString("en-IN", {
      timeZone: timezone,
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  } catch {
    return date.toLocaleString("en-IN", {
      timeZone: DEFAULT_TIMEZONE,
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  }
}