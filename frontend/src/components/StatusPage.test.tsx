import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StatusPage } from "../components/StatusPage";
import type { SystemStatus } from "../api/status";

describe("StatusPage", () => {
  it("renders healthy API and database state", async () => {
    const fetcher = vi.fn(async (): Promise<SystemStatus> => ({
      overall: "healthy",
      apiLive: "healthy",
      database: "healthy",
      detail: "API and database are ready.",
    }));

    render(<StatusPage fetcher={fetcher} />);

    await waitFor(() => {
      expect(screen.getByTestId("status-panel")).toHaveAttribute(
        "data-state",
        "healthy",
      );
    });
    expect(screen.getByTestId("api-live-status")).toHaveTextContent("healthy");
    expect(screen.getByTestId("database-status")).toHaveTextContent("healthy");
    expect(screen.getByText(/Trading execution/i)).toBeInTheDocument();
  });

  it("renders loading state before status resolves", () => {
    const fetcher = vi.fn(
      () =>
        new Promise<SystemStatus>(() => {
          /* never resolves during this assertion */
        }),
    );

    render(<StatusPage fetcher={fetcher} />);

    expect(screen.getByTestId("status-panel")).toHaveAttribute(
      "data-state",
      "loading",
    );
    expect(screen.getByTestId("status-detail")).toHaveTextContent(
      /Checking system status/i,
    );
  });

  it("renders unavailable API state", async () => {
    const fetcher = vi.fn(async (): Promise<SystemStatus> => ({
      overall: "unavailable",
      apiLive: "unhealthy",
      database: "unknown",
      detail: "API is unreachable.",
    }));

    render(<StatusPage fetcher={fetcher} />);

    await waitFor(() => {
      expect(screen.getByTestId("status-panel")).toHaveAttribute(
        "data-state",
        "unavailable",
      );
    });
    expect(screen.getByTestId("api-live-status")).toHaveTextContent(
      "unhealthy",
    );
  });

  it("renders degraded database state", async () => {
    const fetcher = vi.fn(async (): Promise<SystemStatus> => ({
      overall: "degraded",
      apiLive: "healthy",
      database: "unhealthy",
      detail: "API is alive but the database is not ready.",
    }));

    render(<StatusPage fetcher={fetcher} />);

    await waitFor(() => {
      expect(screen.getByTestId("status-panel")).toHaveAttribute(
        "data-state",
        "degraded",
      );
    });
    expect(screen.getByTestId("database-status")).toHaveTextContent(
      "unhealthy",
    );
  });
});
