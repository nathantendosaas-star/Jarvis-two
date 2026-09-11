import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

const ignoredWatchPaths = [
  '**/.git/**',
  '**/.venv/**',
  '**/.storage/**',
  '**/artifacts/**',
  '**/backend/**',
  '**/node_modules/**',
  '**/__pycache__/**',
  '**/.pytest_cache/**',
  '**/build/**',
  '**/coverage/**',
  '**/dist/**',
];

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    optimizeDeps: {
      include: ['react', 'react-dom/client', 'lucide-react'],
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify - file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {
        ignored: ignoredWatchPaths,
      },
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  };
});
