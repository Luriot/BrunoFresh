const MAX_ERROR_LENGTH = 180;

function sanitizeInlineMessage(value: string): string {
  return value
    .replace(/[<>"'`]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_ERROR_LENGTH);
}

export function extractApiDetail(error: unknown): string | null {
  if (!error || typeof error !== "object") {
    return null;
  }

  const detail = (error as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return sanitizeInlineMessage(detail);
  }

  const message = (error as { message?: unknown }).message;
  if (typeof message === "string") {
    return sanitizeInlineMessage(message);
  }

  return null;
}