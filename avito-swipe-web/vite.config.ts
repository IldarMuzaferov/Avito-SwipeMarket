import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Порт 3000 нужен потому, что бэкенд разрешает CORS только для http://localhost:3000
export default defineConfig({
  plugins: [react()],
  server: { port: 3000, strictPort: true },
});
