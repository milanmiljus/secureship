import { useState } from 'react'
import CustomerManager from './CustomerManager'
import ShipmentManager from './ShipmentManager'

type Tab = 'customers' | 'shipments'

export default function AdminApp() {
  const [tab, setTab] = useState<Tab>('customers')
  const [token, setToken] = useState<string>(
    () => localStorage.getItem('admin_token') || ''
  )
  const [tokenInput, setTokenInput] = useState('')

  const handleTokenSave = () => {
    localStorage.setItem('admin_token', tokenInput)
    setToken(tokenInput)
    setTokenInput('')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900">SecureShip Admin</h1>
        <div className="flex items-center gap-2 text-sm">
          {token ? (
            <span className="text-green-600 font-medium">Auth token set</span>
          ) : (
            <span className="text-amber-600">Dev mode (no token required)</span>
          )}
          <input
            placeholder="Bearer token (optional)"
            className="border rounded px-2 py-1 text-xs w-48"
            value={tokenInput}
            onChange={e => setTokenInput(e.target.value)}
          />
          <button
            className="px-2 py-1 bg-gray-800 text-white rounded text-xs"
            onClick={handleTokenSave}
          >Save</button>
        </div>
      </header>

      <nav className="bg-white border-b px-6">
        <div className="flex gap-6">
          {(['customers', 'shipments'] as Tab[]).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-3 text-sm font-medium border-b-2 capitalize transition-colors ${
                tab === t
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </nav>

      <main className="p-6">
        {tab === 'customers' && <CustomerManager token={token} />}
        {tab === 'shipments' && <ShipmentManager token={token} />}
      </main>
    </div>
  )
}
