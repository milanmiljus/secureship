import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Auth0Provider } from '@auth0/auth0-react'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1 },
    mutations: { retry: 0 },
  },
})

const isAdmin = window.location.pathname.startsWith('/admin')

const needsAuth = Boolean(
  import.meta.env.VITE_AUTH0_DOMAIN && import.meta.env.VITE_AUTH0_CLIENT_ID
)

const root = (
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {isAdmin && needsAuth ? (
        <Auth0Provider
          domain={import.meta.env.VITE_AUTH0_DOMAIN || ''}
          clientId={import.meta.env.VITE_AUTH0_CLIENT_ID || ''}
          authorizationParams={{
            redirect_uri: window.location.origin + '/admin',
            audience: import.meta.env.VITE_AUTH0_AUDIENCE || '',
          }}
        >
          <App />
        </Auth0Provider>
      ) : (
        <App />
      )}
    </QueryClientProvider>
  </StrictMode>
)

createRoot(document.getElementById('root')!).render(root)
