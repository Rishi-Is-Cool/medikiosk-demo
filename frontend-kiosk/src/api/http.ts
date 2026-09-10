import { API_BASE_URL } from "./config";
import { ApiError } from "./types";

/** Single fetch wrapper. Every network failure becomes an ApiError with a
 *  stable `code`, so screens can pick a patient-safe message instead of
 *  leaking a stack trace or an HTTP status (build spec §15). */
export async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const { timeoutMs = 15000, ...rest } = init ?? {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        ...(rest.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...rest.headers,
      },
    });

    if (!response.ok) {
      throw new ApiError(
        `http_${response.status}`,
        `Request to ${path} failed with ${response.status}`,
        response.status >= 500 || response.status === 429,
      );
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("timeout", `Request to ${path} timed out`);
    }
    throw new ApiError("network", `Could not reach ${path}`);
  } finally {
    clearTimeout(timer);
  }
}
