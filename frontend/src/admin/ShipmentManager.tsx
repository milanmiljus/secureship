import { useState, useEffect, useRef } from "react";

type ShipmentStatus =
  | "label_created"
  | "in_transit"
  | "out_for_delivery"
  | "delivered"
  | "exception";

const STATUSES: ShipmentStatus[] = [
  "label_created",
  "in_transit",
  "out_for_delivery",
  "delivered",
  "exception",
];

interface Shipment {
  id: string;
  customer_id: string;
  tracking_number: string;
  status: ShipmentStatus;
  carrier: string;
  origin: string;
  destination: string;
  estimated_delivery: string;
  last_update: string;
}

interface Props {
  token: string;
}

const apiHeaders = (token: string) => ({
  "Content-Type": "application/json",
  ...(token ? { Authorization: `Bearer ${token}` } : {}),
});

const emptyForm = {
  customer_id: "",
  tracking_number: "",
  status: "label_created" as ShipmentStatus,
  carrier: "",
  origin: "",
  destination: "",
  estimated_delivery: "",
};

export default function ShipmentManager({ token }: Props) {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Shipment | null>(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [filterCustomerId, setFilterCustomerId] = useState("");
  const requestId = useRef(0);

  const load = async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "200" });
      if (filterCustomerId) params.set("customer_id", filterCustomerId);
      const res = await fetch(`/admin/shipments?${params}`, {
        headers: apiHeaders(token),
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      if (id === requestId.current) setShipments(data);
    } catch (e: any) {
      if (id === requestId.current) setError(e.message);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [token, filterCustomerId]);

  const handleAdd = async () => {
    const res = await fetch("/admin/shipments", {
      method: "POST",
      headers: apiHeaders(token),
      body: JSON.stringify(form),
    });
    if (res.ok) {
      setAdding(false);
      setForm(emptyForm);
      load();
    } else {
      const body = await res.json().catch(() => ({}));
      setError(body.detail || "Failed to create shipment");
    }
  };

  const handleUpdate = async () => {
    if (!editing) return;
    const { customer_id, tracking_number, ...updateFields } = form;
    const res = await fetch(`/admin/shipments/${editing.id}`, {
      method: "PUT",
      headers: apiHeaders(token),
      body: JSON.stringify(updateFields),
    });
    if (res.ok) {
      setEditing(null);
      load();
    } else setError("Failed to update shipment");
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this shipment and all its packages?")) return;
    await fetch(`/admin/shipments/${id}`, {
      method: "DELETE",
      headers: apiHeaders(token),
    });
    load();
  };

  const startEdit = (s: Shipment) => {
    setEditing(s);
    setAdding(false);
    setForm({
      customer_id: s.customer_id,
      tracking_number: s.tracking_number,
      status: s.status,
      carrier: s.carrier,
      origin: s.origin,
      destination: s.destination,
      estimated_delivery: s.estimated_delivery,
    });
  };

  const setField = (key: keyof typeof form, val: string) =>
    setForm((prev) => ({ ...prev, [key]: val }));

  // Returns elements rather than being a component: a component declared here gets a new
  // identity every render, so React would remount it and the focused input would lose focus.
  const formFields = (isEdit = false) => (
    <div className="grid grid-cols-2 gap-3 mt-2">
      {!isEdit && (
        <input
          placeholder="Customer ID"
          className="border rounded px-2 py-1 text-sm"
          value={form.customer_id}
          onChange={(e) => setField("customer_id", e.target.value)}
        />
      )}
      {!isEdit && (
        <input
          placeholder="Tracking number"
          className="border rounded px-2 py-1 text-sm"
          value={form.tracking_number}
          onChange={(e) => setField("tracking_number", e.target.value)}
        />
      )}
      <select
        className="border rounded px-2 py-1 text-sm"
        value={form.status}
        onChange={(e) => setField("status", e.target.value)}
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s.replace(/_/g, " ")}
          </option>
        ))}
      </select>
      <input
        placeholder="Carrier"
        className="border rounded px-2 py-1 text-sm"
        value={form.carrier}
        onChange={(e) => setField("carrier", e.target.value)}
      />
      <input
        placeholder="Origin"
        className="border rounded px-2 py-1 text-sm"
        value={form.origin}
        onChange={(e) => setField("origin", e.target.value)}
      />
      <input
        placeholder="Destination"
        className="border rounded px-2 py-1 text-sm"
        value={form.destination}
        onChange={(e) => setField("destination", e.target.value)}
      />
      <input
        type="date"
        placeholder="Estimated delivery"
        className="border rounded px-2 py-1 text-sm"
        value={form.estimated_delivery}
        onChange={(e) => setField("estimated_delivery", e.target.value)}
      />
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold">
          Shipments ({shipments.length})
        </h2>
        <div className="flex items-center gap-2">
          <input
            placeholder="Filter by customer ID"
            className="border rounded px-2 py-1 text-xs w-48"
            value={filterCustomerId}
            onChange={(e) => setFilterCustomerId(e.target.value)}
          />
          <button
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm"
            onClick={() => {
              setAdding(true);
              setEditing(null);
              setForm(emptyForm);
            }}
          >
            + Add Shipment
          </button>
        </div>
      </div>

      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      {adding && (
        <div className="bg-white border rounded p-4 mb-4">
          <p className="text-sm font-medium mb-2">New Shipment</p>
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
      ) : (
        <div className="bg-white rounded border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {[
                  "Tracking",
                  "Status",
                  "Carrier",
                  "Origin → Dest",
                  "Est. Delivery",
                  "",
                ].map((h) => (
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
              {shipments.map((s) => (
                <>
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">
                      {s.tracking_number}
                    </td>
                    <td className="px-4 py-2">
                      <span className="px-1.5 py-0.5 rounded text-xs bg-blue-50 text-blue-700">
                        {s.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-500">{s.carrier}</td>
                    <td className="px-4 py-2 text-gray-500">
                      {s.origin} → {s.destination}
                    </td>
                    <td className="px-4 py-2 text-gray-500">
                      {s.estimated_delivery}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        className="text-blue-600 mr-3 text-xs"
                        onClick={() => startEdit(s)}
                      >
                        Edit
                      </button>
                      <button
                        className="text-red-500 text-xs"
                        onClick={() => handleDelete(s.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                  {editing?.id === s.id && (
                    <tr key={`edit-${s.id}`}>
                      <td colSpan={6} className="px-4 pb-3">
                        {formFields(true)}
                        <div className="flex gap-2 mt-2">
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
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
