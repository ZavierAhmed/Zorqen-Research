import { afterEach, describe, expect, it, vi } from "vitest";
import {
  buildHealthUrl,
  fetchSystemStatus,
  resolveApiBaseUrl,
} from "./status";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("resolveApiBaseUrl", () => {
  it("defaults to empty (same-origin relative) when unset", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("");
    expect(resolveApiBaseUrl(null)).toBe("");
  });

  it("treats empty and whitespace-only values as same-origin", () => {
    expect(resolveApiBaseUrl("")).toBe("");
    expect(resolveApiBaseUrl("   ")).toBe("");
  });

  it("strips trailing slashes from an explicit base", () => {
    expect(resolveApiBaseUrl("http://example.test:8000")).toBe(
      "http://example.test:8000",
    );
    expect(resolveApiBaseUrl("http://example.test:8000/")).toBe(
      "http://example.test:8000",
    );
    expect(resolveApiBaseUrl("http://example.test:8000///")).toBe(
      "http://example.test:8000",
    );
  });
});

describe("buildHealthUrl", () => {
  it("uses relative /api paths when base is empty", () => {
    expect(buildHealthUrl("/api/v1/health/live", "")).toBe(
      "/api/v1/health/live",
    );
    expect(buildHealthUrl("/api/v1/health/ready", "")).toBe(
      "/api/v1/health/ready",
    );
  });

  it("joins an explicit base without a trailing slash", () => {
    expect(
      buildHealthUrl("/api/v1/health/live", "http://example.test:8000"),
    ).toBe("http://example.test:8000/api/v1/health/live");
  });

  it("does not produce a duplicate slash when base had trailing slashes removed", () => {
    const base = resolveApiBaseUrl("http://example.test:8000/");
    expect(buildHealthUrl("/api/v1/health/ready", base)).toBe(
      "http://example.test:8000/api/v1/health/ready",
    );
    expect(buildHealthUrl("/api/v1/health/ready", base)).not.toContain("//api");
  });
});

describe("fetchSystemStatus", () => {
  it("requests relative live and ready URLs when base is empty", async () => {
    const urls: string[] = [];
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      urls.push(url);
      if (url.endsWith("/live")) {
        return new Response(JSON.stringify({ status: "healthy" }), {
          status: 200,
        });
      }
      return new Response(
        JSON.stringify({
          status: "ready",
          components: { database: { status: "healthy" } },
        }),
        { status: 200 },
      );
    });

    const status = await fetchSystemStatus(fetchImpl, "");

    expect(urls).toEqual([
      "/api/v1/health/live",
      "/api/v1/health/ready",
    ]);
    expect(status.overall).toBe("healthy");
    expect(status.apiLive).toBe("healthy");
    expect(status.database).toBe("healthy");
  });

  it("uses absolute URLs when an explicit base is provided", async () => {
    const urls: string[] = [];
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      urls.push(String(input));
      if (String(input).endsWith("/live")) {
        return new Response("{}", { status: 200 });
      }
      return new Response(
        JSON.stringify({
          status: "ready",
          components: { database: { status: "healthy" } },
        }),
        { status: 200 },
      );
    });

    await fetchSystemStatus(fetchImpl, "http://example.test:8000");

    expect(urls).toEqual([
      "http://example.test:8000/api/v1/health/live",
      "http://example.test:8000/api/v1/health/ready",
    ]);
  });

  it("returns unavailable when the live request fails", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });

    const status = await fetchSystemStatus(fetchImpl, "");

    expect(status.overall).toBe("unavailable");
    expect(status.apiLive).toBe("unhealthy");
    expect(status.database).toBe("unknown");
  });

  it("returns degraded when readiness is 503 with valid JSON", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/live")) {
        return new Response(JSON.stringify({ status: "healthy" }), {
          status: 200,
        });
      }
      return new Response(
        JSON.stringify({
          status: "not_ready",
          components: { database: { status: "unhealthy" } },
        }),
        { status: 503 },
      );
    });

    const status = await fetchSystemStatus(fetchImpl, "");

    expect(status.overall).toBe("degraded");
    expect(status.apiLive).toBe("healthy");
    expect(status.database).toBe("unhealthy");
  });

  it("keeps API healthy and marks database unknown when readiness is malformed", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/live")) {
        return new Response(JSON.stringify({ status: "healthy" }), {
          status: 200,
        });
      }
      return new Response("not-json", { status: 200 });
    });

    const status = await fetchSystemStatus(fetchImpl, "");

    expect(status.overall).toBe("degraded");
    expect(status.apiLive).toBe("healthy");
    expect(status.database).toBe("unknown");
  });
});
