import { useState, useEffect, useRef } from "react";

interface Package {
  id: string;
  shipment_id: string;
  description: string;
  weight_kg: number | string;
  declared_value: number | string;
}

interface ShipmentOption {
  id: string;
  tracking_number: string;
  carrier: string;
}

interface Props {
  token: string;
}

const apiHeaders = (token: string) => ({
  "Content-Type": "application/json",
  ...(token ? { Authorization: `Bearer ${token}` } : {}),
});

const emptyForm = {
  shipment_id: "",
  description: "",
  weight_kg: "",
  declared_value: "",
};

// Numeric columns arrive as Decimal, which may serialise as a JSON string.
const num = (v: number | string) => Number(v);

export default function PackageManager({ token }: Props) {
  const [packages, setPackages] = useState<Package[]>([]);
  const [shipments, setShipments] = useState<ShipmentOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Package | null>(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [filterShipmentId, setFilterShipmentId] = useState("");
  const requestId = useRef(0);

  const load = async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filterShipmentId) params.set("shipment_id", filterShipmentId);
      const res = await fetch(`/admin/packages?${params}`, {
        headers: apiHeaders(token),
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      if (id === requestId.current) setPackages(data);
    } catch (e: any) {
      if (id === requestId.current) setError(e.message);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [token, filterShipmentId]);

  // Shipments are fetched to label packages by tracking number — their IDs are never shown.
  useEffect(() => {
    let cancelled = false;
    fetch("/admin/shipments?limit=200", { headers: apiHeaders(token) })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (!cancelled) setShipments(data);
      })
      .catch(() => {
        /* the package list already surfaces auth/network errors */
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const trackingFor = (shipmentId: string) =>
    shipments.find((s) => s.id === shipmentId)?.tracking_number ?? shipmentId;

  const payload = () => ({
    description: form.description,
    weight_kg: Number(form.weight_kg),
    declared_value: Number(form.declared_value),
  });

  const invalidForm = () =>
    !form.description.trim() ||
    !Number.isFinite(Number(form.weight_kg)) ||
    form.weight_kg === "" ||
    !Number.isFinite(Number(form.declared_value)) ||
    form.declared_value === "";

  const handleAdd = async () => {
    if (!form.shipment_id) {
      setError("Pick a shipment for this package");
      return;
    }
    if (invalidForm()) {
      setError("Description, weight and value are required");
      return;
    }
    const res = await fetch("/admin/packages", {
      method: "POST",
      headers: apiHeaders(token),
      body: JSON.stringify({ shipment_id: form.shipment_id, ...payload() }),
    });
    if (res.ok) {
      setAdding(false);
      setForm(emptyForm);
      load();
    } else {
      const body = await res.json().catch(() => ({}));
      setError(body.detail || "Failed to create package");
    }
  };

  const handleUpdate = async () => {
    if (!editing) return;
    if (invalidForm()) {
      setError("Description, weight and value are required");
      return;
    }
    const res = await fetch(`/admin/packages/${editing.id}`, {
      method: "PUT",
      headers: apiHeaders(token),
      body: JSON.stringify(payload()),
    });
    if (res.ok) {
      setEditing(null);
      load();
    } else setError("Failed to update package");
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this package?")) return;
    await fetch(`/admin/packages/${id}`, {
      method: "DELETE",
      headers: apiHeaders(token),
    });
    load();
  };

  const startEdit = (p: Package) => {
    setEditing(p);
    setAdding(false);
    setForm({
      shipment_id: p.shipment_id,
      description: p.description,
      weight_kg: String(num(p.weight_kg)),
      declared_value: String(num(p.declared_value)),
    });
  };

  const setField = (key: keyof typeof form, val: string) =>
    setForm((prev) => ({ ...prev, [key]: val }));

  // Returns elements rather than being a component: a component declared here gets a new
  // identity every render, so React would remount it and the focused input would lose focus.
  const formFields = (isEdit = false) => (
    <div className="grid grid-cols-2 gap-3 mt-2">
      {!isEdit && (
        <select
          className="border rounded px-2 py-1 text-sm col-span-2"
          value={form.shipment_id}
          onChange={(e) => setField("shipment_id", e.target.value)}
        >
          <option value="">Select a shipment…</option>
          {shipments.map((s) => (
            <option key={s.id} value={s.id}>
              {s.tracking_number} — {s.carrier}
            </option>
          ))}
        </select>
      )}
      <input
        placeholder="Description"
        className="border rounded px-2 py-1 text-sm col-span-2"
        value={form.description}
        onChange={(e) => setField("description", e.target.value)}
      />
      <input
        type="number"
        step="0.001"
        min="0"
        placeholder="Weight (kg)"
        className="border rounded px-2 py-1 text-sm"
        value={form.weight_kg}
        onChange={(e) => setField("weight_kg", e.target.value)}
      />
      <input
        type="number"
        step="0.01"
        min="0"
        placeholder="Declared value"
        className="border rounded px-2 py-1 text-sm"
        value={form.declared_value}
        onChange={(e) => setField("declared_value", e.target.value)}
      />
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold">
          Packages ({packages.length})
        </h2>
        <div className="flex items-center gap-2">
          <select
            className="border rounded px-2 py-1 text-xs w-56"
            value={filterShipmentId}
            onChange={(e) => setFilterShipmentId(e.target.value)}
          >
            <option value="">All shipments</option>
            {shipments.map((s) => (
              <option key={s.id} value={s.id}>
                {s.tracking_number} — {s.carrier}
              </option>
            ))}
          </select>
          <button
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm"
            onClick={() => {
              setAdding(true);
              setEditing(null);
              setForm({ ...emptyForm, shipment_id: filterShipmentId });
            }}
          >
            + Add Package
          </button>
        </div>
      </div>

      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      {adding && (
        <div className="bg-white border rounded p-4 mb-4">
          <p className="text-sm font-medium mb-2">New Package</p>
          {formFields()}
          <div className="flex gap-2 mt-3">
            <button
              className="px-3 py-1 bg-green-600 text-white rounded text-sm"
              onClick={handleAdd}
            >
              Save
            </button>
            <button
              className="px-3 py-1 border rounded text-sm"
              onClick={() => setAdding(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : packages.length === 0 ? (
        <p className="text-sm text-gray-500">
          No packages{filterShipmentId ? " on this shipment" : ""} yet.
        </p>
      ) : (
        <div className="bg-white rounded border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Shipment", "Description", "Weight", "Value", ""].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {packages.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs">
                    {trackingFor(p.shipment_id)}
                  </td>
                  <td className="px-4 py-2">{p.description}</td>
                  <td className="px-4 py-2 text-gray-500">
                    {num(p.weight_kg)} kg
                  </td>
                  <td className="px-4 py-2 text-gray-500">
                    ${num(p.declared_value).toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      className="text-blue-600 mr-3 text-xs"
                      onClick={() => startEdit(p)}
                    >
                      Edit
                    </button>
                    <button
                      className="text-red-500 text-xs"
                      onClick={() => handleDelete(p.id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <div className="bg-white border rounded p-4 mt-4">
          <p className="text-sm font-medium mb-2">
            Edit package on {trackingFor(editing.shipment_id)}
          </p>
          {formFields(true)}
          <div className="flex gap-2 mt-3">
            <button
              className="px-3 py-1 bg-green-600 text-white rounded text-sm"
              onClick={handleUpdate}
            >
              Save
            </button>
            <button
              className="px-3 py-1 border rounded text-sm"
              onClick={() => setEditing(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
