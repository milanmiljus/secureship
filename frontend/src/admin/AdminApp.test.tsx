import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const auth0 = {
  isLoading: false,
  isAuthenticated: true,
  loginWithRedirect: vi.fn(),
  logout: vi.fn(),
  user: { email: "admin@example.com" },
  getAccessTokenSilently: vi.fn(),
};

vi.mock("@auth0/auth0-react", () => ({ useAuth0: () => auth0 }));

import AdminApp from "./AdminApp";

function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const adminCalls = (fetchMock: ReturnType<typeof vi.fn>) =>
  fetchMock.mock.calls.filter(([url]) => String(url).startsWith("/admin/"));

describe("AdminApp token handling", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.stubEnv("VITE_AUTH0_DOMAIN", "test.auth0.com");
    fetchMock = vi.fn(
      async () => ({ ok: true, json: async () => [] }) as Response,
    );
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("does not call the admin API before the access token resolves", async () => {
    // Requesting with an empty token 401s, and that late failure used to overwrite
    // the successful retry, leaving "401 Unauthorized" on screen next to the data.
    const token = deferred<string>();
    auth0.getAccessTokenSilently.mockReturnValue(token.promise);

    render(<AdminApp />);

    expect(await screen.findByText("Loading…")).toBeInTheDocument();
    expect(adminCalls(fetchMock)).toHaveLength(0);

    token.resolve("real-token");

    await waitFor(() =>
      expect(adminCalls(fetchMock).length).toBeGreaterThan(0),
    );
    for (const [, init] of adminCalls(fetchMock)) {
      expect((init as RequestInit).headers).toMatchObject({
        Authorization: "Bearer real-token",
      });
    }
    expect(screen.queryByText("401 Unauthorized")).not.toBeInTheDocument();
  });

  it("reports a token failure instead of hanging on the loading state", async () => {
    auth0.getAccessTokenSilently.mockRejectedValue(
      new Error("consent required"),
    );

    render(<AdminApp />);

    expect(await screen.findByText(/consent required/)).toBeInTheDocument();
    expect(adminCalls(fetchMock)).toHaveLength(0);
  });

  it("offers a packages tab", async () => {
    auth0.getAccessTokenSilently.mockResolvedValue("real-token");

    render(<AdminApp />);

    expect(
      await screen.findByRole("button", { name: "packages" }),
    ).toBeInTheDocument();
  });
});
