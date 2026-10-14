import { defineConfig } from 'orval'

export default defineConfig({
  secureship: {
    input: {
      target: 'http://localhost:8000/openapi.json',
    },
    output: {
      mode: 'single',
      target: './src/api/secureship.ts',
      client: 'react-query',
      override: {
        mutator: {
          path: './src/lib/axiosClient.ts',
          name: 'customAxios',
        },
      },
    },
  },
})
