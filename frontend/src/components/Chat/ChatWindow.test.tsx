import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ChatWindow from './ChatWindow'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 0 } } })

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('ChatWindow', () => {
  beforeEach(() => {
    localStorage.clear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: 'test-session-id', state: 'anonymous' }),
    })
  })

  it('renders the chat interface', () => {
    renderWithProviders(<ChatWindow />)
    expect(screen.getByText('SecureShip Assistant')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Type a message/)).toBeInTheDocument()
  })

  it('has a send button', () => {
    renderWithProviders(<ChatWindow />)
    expect(screen.getByText('Send')).toBeInTheDocument()
  })
})
