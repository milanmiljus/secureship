import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import PackageManager from "./PackageManager";

const SHIPMENTS = [
  {
    id: "ship-1",
    tracking_number: "TBA67533963605766",
    carrier: "Amazon Logistics",
  },
  { id: "ship-2", tracking_number: "1Z99737631165667", carrier: "UPS" },
];

const PACKAGES = [
  {
    id: "pkg-1",
    shipment_id: "ship-1",
    description: "Automotive Parts",
    weight_kg: "28.964",
    declared_value: "670.67",
  },
];

function mockApi(packages = PACKAGES) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.startsWith("/admin/shipments")) {
      return { ok: true, json: async () => SHIPMENTS } as Response;
    }
    if (
      url.startsWith("/admin/packages") &&
      (!init || init.method === undefined)
    ) {
      return { ok: true, json: async () => packages } as Response;
    }
    return { ok: true, json: async () => ({}) } as Response;
  });
}

describe("PackageManager", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockApi());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("labels packages by tracking number rather than shipment id", async () => {
    render(<PackageManager token="tok" />);

    expect(await screen.findByText("TBA67533963605766")).toBeInTheDocument();
    expect(screen.getByText("Automotive Parts")).toBeInTheDocument();
    expect(screen.queryByText("ship-1")).not.toBeInTheDocument();
  });

  it("formats decimal columns that arrive as strings", async () => {
    render(<PackageManager token="tok" />);

    expect(await screen.findByText("28.964 kg")).toBeInTheDocument();
    expect(screen.getByText("$670.67")).toBeInTheDocument();
  });

  it("sends the selected shipment and numeric fields when creating", async () => {
    const fetchMock = mockApi();
    vi.stubGlobal("fetch", fetchMock);
    render(<PackageManager token="tok" />);
    await screen.findByText("TBA67533963605766");

    fireEvent.click(screen.getByText("+ Add Package"));
    // [0] is the header filter, [1] is the shipment picker in the new-package form.
    fireEvent.change(screen.getAllByRole("combobox")[1], {
      target: { value: "ship-2" },
    });
    fireEvent.change(screen.getByPlaceholderText("Description"), {
      target: { value: "Books" },
    });
    fireEvent.change(screen.getByPlaceholderText("Weight (kg)"), {
      target: { value: "2.5" },
    });
    fireEvent.change(screen.getByPlaceholderText("Declared value"), {
      target: { value: "40" },
    });
    fireEvent.click(screen.getByText("Save"));

    await waitFor(() => {
      const post = fetchMock.mock.calls.find(
        ([, init]) => (init as RequestInit)?.method === "POST",
      );
      expect(post).toBeDefined();
      expect(JSON.parse((post![1] as RequestInit).body as string)).toEqual({
        shipment_id: "ship-2",
        description: "Books",
        weight_kg: 2.5,
        declared_value: 40,
      });
    });
  });

  it("rejects a package with no shipment selected without calling the API", async () => {
    const fetchMock = mockApi();
    vi.stubGlobal("fetch", fetchMock);
    render(<PackageManager token="tok" />);
    await screen.findByText("TBA67533963605766");

    fireEvent.click(screen.getByText("+ Add Package"));
    fireEvent.change(screen.getByPlaceholderText("Description"), {
      target: { value: "Books" },
    });
    fireEvent.click(screen.getByText("Save"));

    expect(
      await screen.findByText("Pick a shipment for this package"),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([, init]) => (init as RequestInit)?.method === "POST",
      ),
    ).toBe(false);
  });

  it("keeps focus while typing a description", async () => {
    // The form fields must not be a component declared inside render, or React remounts
    // them on every keystroke and the field drops focus after one character.
    render(<PackageManager token="tok" />);
    await screen.findByText("TBA67533963605766");

    fireEvent.click(screen.getByText("+ Add Package"));
    const description = screen.getByPlaceholderText(
      "Description",
    ) as HTMLInputElement;
    description.focus();

    for (const char of "Drone Parts") {
      fireEvent.change(description, {
        target: { value: description.value + char },
      });
    }

    const current = screen.getByPlaceholderText(
      "Description",
    ) as HTMLInputElement;
    expect(current.value).toBe("Drone Parts");
    expect(document.activeElement).toBe(current);
  });

  it("shows an empty state instead of a bare table", async () => {
    vi.stubGlobal("fetch", mockApi([]));
    render(<PackageManager token="tok" />);

    expect(await screen.findByText(/No packages/)).toBeInTheDocument();
  });

  it("surfaces a failed load", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.startsWith("/admin/shipments"))
          return { ok: true, json: async () => [] } as Response;
        return {
          ok: false,
          status: 401,
          statusText: "Unauthorized",
        } as Response;
      }),
    );
    render(<PackageManager token="" />);

    expect(await screen.findByText("401 Unauthorized")).toBeInTheDocument();
  });
});
