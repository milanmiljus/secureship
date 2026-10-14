import { useState, useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import CustomerManager from "./CustomerManager";
import ShipmentManager from "./ShipmentManager";
import PackageManager from "./PackageManager";

type Tab = "customers" | "shipments" | "packages";

const TABS: Tab[] = ["customers", "shipments", "packages"];

function TabNav({ tab, onSelect }: { tab: Tab; onSelect: (t: Tab) => void }) {
  return (
    <nav className="bg-white border-b px-6">
      <div className="flex gap-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => onSelect(t)}
            className={`py-3 text-sm font-medium border-b-2 capitalize transition-colors ${
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
    </nav>
  );
}

function TabContent({ tab, token }: { tab: Tab; token: string }) {
  if (tab === "customers") return <CustomerManager token={token} />;
  if (tab === "shipments") return <ShipmentManager token={token} />;
  return <PackageManager token={token} />;
}

export default function AdminApp() {
  if (!import.meta.env.VITE_AUTH0_DOMAIN) {
    return <AdminPanelDev />;
  }
  return <AdminPanelAuth />;
}

function AdminPanelDev() {
  const [tab, setTab] = useState<Tab>("customers");

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <h1 className="text-base font-semibold text-gray-900">
          SecureShip Admin
        </h1>
        <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          Dev mode — Auth0 not configured
        </span>
      </header>

      <TabNav tab={tab} onSelect={setTab} />

      <main className="p-6">
        <TabContent tab={tab} token="" />
      </main>
    </div>
  );
}

function AdminPanelAuth() {
  const {
    isLoading,
    isAuthenticated,
    loginWithRedirect,
    logout,
    user,
    getAccessTokenSilently,
  } = useAuth0();
  const [tab, setTab] = useState<Tab>("customers");
  // null until Auth0 answers — rendering a manager before then fires an unauthenticated request.
  const [token, setToken] = useState<string | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    getAccessTokenSilently()
      .then((t) => {
        if (!cancelled) setToken(t ?? "");
      })
      .catch((e) => {
        if (!cancelled)
          setTokenError(e?.message ?? "Could not get an access token");
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, getAccessTokenSilently]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500 text-sm">Loading…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-xl shadow-sm border p-10 text-center max-w-sm w-full">
          <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-6 h-6 text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <h1 className="text-lg font-semibold text-gray-900 mb-1">
            SecureShip Admin
          </h1>
          <p className="text-sm text-gray-500 mb-6">
            Sign in to manage customers and shipments
          </p>
          <button
            onClick={() => loginWithRedirect()}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Sign in with Auth0
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <h1 className="text-base font-semibold text-gray-900">
          SecureShip Admin
        </h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">{user?.email}</span>
          <button
            onClick={() =>
              logout({
                logoutParams: { returnTo: window.location.origin + "/admin" },
              })
            }
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Sign out
          </button>
        </div>
      </header>

      <TabNav tab={tab} onSelect={setTab} />

      <main className="p-6">
        {tokenError ? (
          <p className="text-red-600 text-sm">
            Could not get an access token: {tokenError}
          </p>
        ) : token === null ? (
          <p className="text-sm text-gray-500">Loading…</p>
        ) : (
          <TabContent tab={tab} token={token} />
        )}
      </main>
    </div>
  );
}
