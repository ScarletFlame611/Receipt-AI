import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Прокси на FastAPI: фронт и бэк живут на одном origin в dev,
// поэтому CORS не нужен. Префиксы соответствуют роутерам бэкенда.
const target = process.env.VITE_API_TARGET || 'http://localhost:8000'
const proxy = Object.fromEntries(
  ['/auth', '/receipts', '/analytics', '/admin', '/categories', '/api'].map(
    (p) => [p, { target, changeOrigin: true }]
  )
)

export default defineConfig({
  plugins: [react()],
  // host: true — слушать на IPv4 и IPv6 (иначе Vite может встать только на ::1,
  // и браузер по 127.0.0.1 получит ERR_CONNECTION_REFUSED).
  server: { host: true, port: 5173, strictPort: true, proxy },
})
