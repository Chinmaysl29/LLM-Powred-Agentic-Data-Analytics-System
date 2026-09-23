/**
 * Shared API client using the native fetch API.
 *
 * Provides a central place for:
 * - Base URL configuration (via VITE_API_BASE_URL)
 * - HTTP request handling with typed methods
 * - Consistent error normalization
 * - Timeout handling
 *
 * Authentication-specific logic (token injection, credential handling)
 * is NOT included here. It will be added in a later phase via a clean
 * extension point (e.g. request interceptor or auth header injection).
 */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

function getApiBaseUrl(): string {
  const url = import.meta.env.VITE_API_BASE_URL;
  if (!url) {
    throw new Error(
      'VITE_API_BASE_URL is not configured. ' +
        'Set it in the frontend .env file (see .env.example).',
    );
  }
  return url as string;
}

const API_BASE_URL: string = getApiBaseUrl();

const DEFAULT_TIMEOUT_MS = 30_000;

// ---------------------------------------------------------------------------
// Error Model
// ---------------------------------------------------------------------------

/**
 * Normalized API error thrown by all client methods.
 *
 * - `status`  — HTTP status code, or 0 for network/timeout errors.
 * - `code`    — Machine-readable error code for programmatic handling.
 * - `message` — Human-readable description safe to display in UI.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

/** Maps HTTP status codes to machine-readable error codes. */
function errorCodeFromStatus(status: number): string {
  switch (status) {
    case 400:
      return 'VALIDATION_ERROR';
    case 401:
      return 'UNAUTHORIZED';
    case 403:
      return 'FORBIDDEN';
    case 404:
      return 'NOT_FOUND';
    case 409:
      return 'CONFLICT';
    case 422:
      return 'VALIDATION_ERROR';
    case 429:
      return 'RATE_LIMITED';
    default:
      return status >= 500 ? 'SERVER_ERROR' : 'UNKNOWN_ERROR';
  }
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

interface RequestOptions {
  /** Query parameters appended to the URL. */
  params?: Record<string, string>;
  /** Additional headers merged with defaults. */
  headers?: Record<string, string>;
  /** Request timeout in milliseconds. Defaults to 30 000. */
  timeout?: number;
  /** AbortSignal for external cancellation. */
  signal?: AbortSignal;
}

/**
 * Core request function. All public methods delegate here.
 *
 * Throws {@link ApiError} for HTTP errors, network failures, and timeouts.
 */
async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const url = new URL(path, API_BASE_URL);

  if (options.params) {
    for (const [key, value] of Object.entries(options.params)) {
      url.searchParams.set(key, value);
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...options.headers,
  };

  // Timeout handling via AbortController
  const timeoutMs = options.timeout ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // If the caller provided an external signal, abort when it fires.
  if (options.signal) {
    options.signal.addEventListener('abort', () => controller.abort(), {
      once: true,
    });
  }

  try {
    const response = await fetch(url.toString(), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    // --- Success path ---
    if (response.ok) {
      // Handle 204 No Content
      if (response.status === 204) {
        return undefined as T;
      }
      return (await response.json()) as T;
    }

    // --- Error path: attempt to parse backend error body ---
    let message = response.statusText || 'Request failed';
    try {
      const errorBody: unknown = await response.json();
      if (
        typeof errorBody === 'object' &&
        errorBody !== null &&
        'detail' in errorBody
      ) {
        const detail = (errorBody as { detail: unknown }).detail;
        message = typeof detail === 'string' ? detail : JSON.stringify(detail);
      }
    } catch {
      // Body is not JSON — use statusText as the message.
    }

    throw new ApiError(
      response.status,
      errorCodeFromStatus(response.status),
      message,
    );
  } catch (error: unknown) {
    // Re-throw ApiError instances as-is.
    if (error instanceof ApiError) {
      throw error;
    }

    // Network failure or abort
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(0, 'TIMEOUT', 'Request timed out');
    }

    if (error instanceof TypeError) {
      throw new ApiError(0, 'NETWORK_ERROR', 'Network request failed');
    }

    throw new ApiError(0, 'UNKNOWN_ERROR', 'An unexpected error occurred');
  } finally {
    clearTimeout(timeoutId);
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export const apiClient = {
  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>('GET', path, undefined, options);
  },

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('POST', path, body, options);
  },

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('PUT', path, body, options);
  },

  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('PATCH', path, body, options);
  },

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>('DELETE', path, undefined, options);
  },
};
