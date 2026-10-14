import { useState, useEffect, useRef } from "react";

interface Customer {
  id: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  address: string;
}

interface Props {
  token: string;
}

const apiHeaders = (token: string) => ({
  "Content-Type": "application/json",
  ...(token ? { Authorization: `Bearer ${token}` } : {}),
});

export default function CustomerManager({ token }: Props) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Customer | null>(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    phone_number: "",
    address: "",
  });
  const requestId = useRef(0);

  const load = async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/admin/customers?limit=200", {
        headers: apiHeaders(token),
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      if (id === requestId.current) setCustomers(data);
    } catch (e: any) {
      if (id === requestId.current) setError(e.message);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [token]);

  const handleAdd = async () => {
    const res = await fetch("/admin/customers", {
      method: "POST",
      headers: apiHeaders(token),
      body: JSON.stringify(form),
    });
    if (res.ok) {
      setAdding(false);
      setForm({ first_name: "", last_name: "", phone_number: "", address: "" });
      load();
    } else {
      setError("Failed to create customer");
    }
  };

  const handleUpdate = async () => {
    if (!editing) return;
    const res = await fetch(`/admin/customers/${editing.id}`, {
      method: "PUT",
      headers: apiHeaders(token),
      body: JSON.stringify(form),
    });
    if (res.ok) {
      setEditing(null);
      load();
    } else setError("Failed to update customer");
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this customer and all their shipments?")) return;
    await fetch(`/admin/customers/${id}`, {
      method: "DELETE",
      headers: apiHeaders(token),
    });
    load();
  };

  const startEdit = (c: Customer) => {
    setEditing(c);
    setAdding(false);
    setForm({
      first_name: c.first_name,
      last_name: c.last_name,
      phone_number: c.phone_number,
      address: c.address,
    });
  };

  // Returns elements rather than being a component: a component declared here gets a new
  // identity every render, so React would remount it and the focused input would lose focus.
  const formFields = () => (
    <div className="grid grid-cols-2 gap-3 mt-2">
      {(["first_name", "last_name", "phone_number", "address"] as const).map(
        (f) => (
          <input
            key={f}
            placeholder={f.replace("_", " ")}
            className="border rounded px-2 py-1 text-sm"
            value={form[f]}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, [f]: e.target.value }))
            }
          />
        ),
      )}
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold">
          Customers ({customers.length})
        </h2>
        <button
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm"
          onClick={() => {
            setAdding(true);
            setEditing(null);
            setForm({
              first_name: "",
              last_name: "",
              phone_number: "",
              address: "",
            });
          }}
        >
          + Add Customer
        </button>
      </div>

      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      {adding && (
        <div className="bg-white border rounded p-4 mb-4">
          <p className="text-sm font-medium mb-2">New Customer</p>
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
                {["Customer ID", "Name", "Phone", "Address", ""].map((h) => (
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
              {customers.map((c) => (
                <>
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2">{c.id}</td>
                    <td className="px-4 py-2">
                      {c.first_name} {c.last_name}
                    </td>
                    <td className="px-4 py-2 text-gray-500">
                      {c.phone_number}
                    </td>
                    <td className="px-4 py-2 text-gray-500 max-w-xs truncate">
                      {c.address}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        className="text-blue-600 mr-3 text-xs"
                        onClick={() => startEdit(c)}
                      >
                        Edit
                      </button>
                      <button
                        className="text-red-500 text-xs"
                        onClick={() => handleDelete(c.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                  {editing?.id === c.id && (
                    <tr key={`edit-${c.id}`}>
                      <td colSpan={4} className="px-4 pb-3">
                        {formFields()}
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
