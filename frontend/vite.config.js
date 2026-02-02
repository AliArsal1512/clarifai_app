import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/generate-cfg': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/ast-json': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/get-submission': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/delete-submission': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/rename-submission': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/process-folder': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'app/static/react-build',
    emptyOutDir: true,
  },
});

