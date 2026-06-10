import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError } from "./api";

function mockFetch(response: { ok: boolean; status?: number; body?: unknown }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status ?? 200,
    json: () => Promise.resolve(response.body),
    text: () => Promise.resolve(JSON.stringify(response.body)),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ApiClient", () => {
  it("attaches the auth token as a Bearer header", async () => {
    const fetchMock = mockFetch({ ok: true, body: { status: "ok" } });
    const client = new ApiClient("http://api.test", () => Promise.resolve("token-123"));

    await client.get("/api/health");

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test/api/health");
    expect(new Headers(options.headers).get("Authorization")).toBe("Bearer token-123");
  });

  it("omits the Authorization header when there is no token", async () => {
    const fetchMock = mockFetch({ ok: true, body: {} });
    const client = new ApiClient("http://api.test", () => Promise.resolve(null));

    await client.get("/api/health");

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(options.headers).get("Authorization")).toBeNull();
  });

  it("throws ApiError with the response status on non-2xx responses", async () => {
    mockFetch({ ok: false, status: 503, body: { detail: "db down" } });
    const client = new ApiClient("http://api.test", () => Promise.resolve("token-123"));

    await expect(client.get("/api/health")).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
    });
    await expect(
      client.get("/api/health").catch((err: unknown) => err),
    ).resolves.toBeInstanceOf(ApiError);
  });
});
