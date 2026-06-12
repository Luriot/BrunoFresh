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

  const response = (error as { response?: { data?: { detail?: unknown } } }).response;
  if (typeof response?.data?.detail === "string") {
    return sanitizeInlineMessage(response.data.detail);
  }

  const message = (error as { message?: unknown }).message;
  if (typeof message === "string") {
    return sanitizeInlineMessage(message);
  }

  return null;
}