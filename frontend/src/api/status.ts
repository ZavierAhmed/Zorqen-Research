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

function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (configured && configured.trim().length > 0) {
    return configured.replace(/\/$/, "");
  }
  // Empty base uses the Vite proxy during local development.
  return "";
}

export async function fetchSystemStatus(
  fetchImpl: typeof fetch = fetch,
): Promise<SystemStatus> {
  const base = apiBaseUrl();

  let liveOk = false;
  try {
    const liveResponse = await fetchImpl(`${base}/api/v1/health/live`);
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
    const readyResponse = await fetchImpl(`${base}/api/v1/health/ready`);
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
