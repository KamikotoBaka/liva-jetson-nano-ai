import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
        host: '0.0.0.0',
        port: 5173,
        strictPort: true,
        allowedHosts:[
                'jetson-va.local',
                '192.168.3.23'
        ],
      hmr: {
        clientPort: 443,
        protocol: 'wss',
        host: 'jetson-va.local',
        },
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',

    },
  },
})