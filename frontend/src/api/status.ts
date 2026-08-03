export type ComponentHealth = "healthy" | "unhealthy" | "unknown";

export type OverallState =
  | "loading"
  | "healthy"
  | "degraded"
  | "unavailable";

export interface LivenessResponse {
  service: string;
  status: string;
}

export interface ReadinessResponse {
  service: string;
  status: string;
  components: {
    database: {
      status: ComponentHealth | string;
    };
  };
}

export interface SystemStatus {
  overall: OverallState;
  apiLive: ComponentHealth;
  database: ComponentHealth;
  detail: string;
}

/**
 * Resolve the API origin used by the browser.
 *
 * Default is an empty string so requests stay same-origin relative
 * (`/api/...`) and rely on the Vite or nginx proxy.
 *
 * Pass `configured` explicitly in tests. In the browser, omit it so the
 * build-time `VITE_API_BASE_URL` is read (empty/unset => relative /api).
 */
export function resolveApiBaseUrl(configured?: string | null): string {
  const raw =
    configured !== undefined
      ? configured
      : (import.meta.env.VITE_API_BASE_URL as string | undefined);
  if (raw == null) {
    return "";
  }
  const trimmed = raw.trim();
  if (trimmed.length === 0) {
    return "";
  }
  return trimmed.replace(/\/+$/, "");
}

/** Build a health endpoint URL from an optional API base. */
export function buildHealthUrl(
  path: "/api/v1/health/live" | "/api/v1/health/ready",
  base: string = resolveApiBaseUrl(),
): string {
  if (!base) {
    return path;
  }
  return `${base}${path}`;
}

export async function fetchSystemStatus(
  fetchImpl: typeof fetch = fetch,
  apiBase: string = resolveApiBaseUrl(),
): Promise<SystemStatus> {
  const liveUrl = buildHealthUrl("/api/v1/health/live", apiBase);
  const readyUrl = buildHealthUrl("/api/v1/health/ready", apiBase);

  let liveOk = false;
  try {
    const liveResponse = await fetchImpl(liveUrl);
    if (!liveResponse.ok) {
      return {
        overall: "unavailable",
        apiLive: "unhealthy",
        database: "unknown",
        detail: "API liveness check failed.",
      };
    }
    liveOk = true;
  } catch {
    return {
      overall: "unavailable",
      apiLive: "unhealthy",
      database: "unknown",
      detail: "API is unreachable.",
    };
  }

  try {
    const readyResponse = await fetchImpl(readyUrl);
    const payload = (await readyResponse.json()) as ReadinessResponse;
    const dbStatus =
      payload.components?.database?.status === "healthy"
        ? "healthy"
        : "unhealthy";

    if (readyResponse.ok && dbStatus === "healthy") {
      return {
        overall: "healthy",
        apiLive: liveOk ? "healthy" : "unhealthy",
        database: "healthy",
        detail: "API and database are ready.",
      };
    }

    return {
      overall: "degraded",
      apiLive: "healthy",
      database: "unhealthy",
      detail: "API is alive but the database is not ready.",
    };
  } catch {
    return {
      overall: "degraded",
      apiLive: "healthy",
      database: "unknown",
      detail: "API is alive but readiness could not be determined.",
    };
  }
}
