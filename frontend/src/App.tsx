import ChatWindow from './components/Chat/ChatWindow'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <header className="mb-4 text-center">
          <h1 className="text-2xl font-bold text-gray-900">SecureShip Support</h1>
          <p className="text-sm text-gray-500 mt-1">Chat with our assistant to track your shipments</p>
        </header>
        <ChatWindow />
      </div>
    </div>
  )
}
