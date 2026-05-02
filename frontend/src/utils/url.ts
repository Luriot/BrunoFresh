/**
 * Returns true only if the URL uses an allowed scheme (http or https).
 * Use this before rendering user-supplied URLs in <a href>.
 */
export function isSafeUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}
