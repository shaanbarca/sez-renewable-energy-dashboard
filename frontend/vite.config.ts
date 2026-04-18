import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const frontendEnv = loadEnv(mode, __dirname, '');
  const repoEnv = loadEnv(mode, path.resolve(__dirname, '..'), '');
  const mapboxToken =
    frontendEnv.VITE_MAPBOX_TOKEN ?? repoEnv.VITE_MAPBOX_TOKEN ?? repoEnv.MAPBOX_TOKEN ?? '';

  return {
    plugins: [react()],
    define: {
      'import.meta.env.VITE_MAPBOX_TOKEN': JSON.stringify(mapboxToken),
    },
    server: {
      port: 5173,
      proxy: {
        '/api': 'http://localhost:8000',
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            maplibre: ['maplibre-gl', 'react-map-gl'],
            charts: ['recharts'],
          },
        },
      },
    },
  };
});
